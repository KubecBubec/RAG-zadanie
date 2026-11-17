"""RAG pipeline: otázka -> (ontológia) -> vyhľadanie -> prompt -> LLM."""
from __future__ import annotations

from dataclasses import dataclass, field

from index import Index
from ontology import Analysis, Ontology

SYSTEM_PROMPT = """Si asistent fiktívnej realitnej kancelárie SemReal Žilina. Odpovedaj po slovensky, \
vecne a stručne, VÝHRADNE na základe poskytnutého kontextu.

Kontext môže mať tri časti:
1. ONTOLÓGIA – definície pojmov, hierarchia tried a obmedzenia (napr. čo je garsónka, čo je disjunktné). \
Použi ju na správne pochopenie pojmov a vzťahov.
2. ZNALOSTNÝ GRAF – presné štruktúrované fakty o inzerátoch získané SPARQL dopytom. Pri cenách, \
výmerách a počtoch izieb majú tieto fakty prednosť.
3. DOKUMENTY – úryvky z PDF dokumentov označené [D1], [D2], ...

Pravidlá:
- Za každé tvrdenie uveď zdroj v hranatých zátvorkách: [D1], [D2] ... alebo [KG] pre znalostný graf, \
[ONT] pre ontológiu.
- Ak sa otázka pýta na ponuku (ktoré, aké, čo máte, zoznam), vymenuj VŠETKY zodpovedajúce inzeráty zo \
ZNALOSTNÉHO GRAFU ako odrážky: ID inzerátu, typ nehnuteľnosti, lokalita, výmera, cena.
- Pri otázkach na pravidlá (zmluvy, kaucia, provízie, postupy) vychádzaj hlavne z DOKUMENTOV a uveď aj \
zákonné limity, ak sú v nich spomenuté.
- Ak informácia v kontexte nie je, povedz to otvorene a nič si nevymýšľaj.
- Ceny uvádzaj v eurách, pri prenájme ako mesačné nájomné."""


@dataclass
class Retrieval:
    question: str
    use_ontology: bool
    search_query: str
    chunks: list[dict] = field(default_factory=list)
    analysis: Analysis | None = None


class RAG:
    def __init__(self, onto: Ontology, index: Index):
        self.onto, self.index = onto, index

    def retrieve(self, question: str, use_ontology: bool = True, k: int = 5) -> Retrieval:
        if not use_ontology:
            hits = self.index.search(question, n=k)
            for h in hits:
                h["bonus"], h["score"] = 0.0, h["similarity"]
            return Retrieval(question, False, question, hits)

        a = self.onto.analyze(question)
        # 1) rozšírenie dopytu o súvisiace pojmy z ontológie (podtriedy, nadtriedy, lokality)
        q = question + (" (súvisiace pojmy: " + ", ".join(a.expansion) + ")" if a.expansion else "")
        hits = self.index.search(q, n=max(20, 4 * k))
        # 2) re-ranking: bonus za zhodu pojmov ontológie medzi otázkou a úryvkom
        wanted = set(a.concept_set)
        for c in a.classes:
            wanted |= {u.split("#")[-1] for u in map(str, self.onto.descendants(c))}
        for h in hits:
            overlap = wanted & self.onto.expand_concepts(set(h["concepts"]))
            h["matched"] = sorted(overlap)
            h["bonus"] = min(0.12, 0.04 * len(overlap))
            h["score"] = h["similarity"] + h["bonus"]
        hits.sort(key=lambda h: -h["score"])
        return Retrieval(question, True, q, hits[:k], a)

    def messages(self, r: Retrieval, history: list[dict] | None = None) -> list[dict]:
        parts = []
        a = r.analysis if r.use_ontology else None
        if a and a.context:
            parts.append("=== ONTOLÓGIA [ONT] ===\n" + a.context)
        docs = [f"[D{i}] ({c['source']}, strana {c['page']})\n{c['text']}" for i, c in enumerate(r.chunks, 1)]
        parts.append("=== DOKUMENTY ===\n" + "\n\n".join(docs))
        # fakty z grafu idú až za dokumenty – bližšie k otázke, malé modely ich tak lepšie použijú
        if a and a.facts:
            parts.append("=== ZNALOSTNÝ GRAF [KG] – výsledok SPARQL dopytu: inzeráty, ktoré presne spĺňajú "
                         "podmienky otázky (typ, lokalita, cena) ===\n" + "\n".join(f"- {f}" for f in a.facts))
        user = "\n\n".join(parts) + f"\n\n=== OTÁZKA ===\n{r.question}"
        msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
        for h in (history or [])[-4:]:  # krátka pamäť konverzácie
            msgs.append({"role": h["role"], "content": h["content"]})
        msgs.append({"role": "user", "content": user})
        return msgs
