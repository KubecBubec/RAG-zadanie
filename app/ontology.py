"""Práca s ontológiou realitnej kancelárie.

Zodpovednosti:
  * načítať TBox (realitna-kancelaria.owl), lexikón (lexikon.ttl) a ABox (instancie.ttl),
  * jednoduché odvodzovanie (inverzné vlastnosti, klasifikácia tried definovaných cez owl:hasValue),
  * rozpoznať pojmy ontológie v texte (otázka používateľa aj úryvky z PDF),
  * vytvoriť textový "ontologický kontext" pre LLM a dopytovať fakty cez SPARQL.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.collection import Collection
from rdflib.namespace import OWL, RDF, RDFS, SKOS

RK = Namespace("http://www.semanticweb.org/kubo/ontologies/2026/9/realitna-kancelaria#")
RKX = Namespace("http://www.semanticweb.org/kubo/ontologies/2026/9/realitna-kancelaria-rag#")

PREFIXES = f"""PREFIX : <{RK}>
PREFIX rkx: <{RKX}>
PREFIX rdf: <{RDF}>
PREFIX rdfs: <{RDFS}>
PREFIX owl: <{OWL}>
PREFIX skos: <{SKOS}>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
"""


# ---------------------------------------------------------------------------
# Normalizácia slovenského textu a porovnávanie slov
# ---------------------------------------------------------------------------
def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def tokenize(s: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", norm(s))


def word_match(w: str, t: str) -> bool:
    """Zhoda slova z lexikónu `w` so slovom textu `t` tolerantná na skloňovanie
    (byt~bytu, garsonka~garsonku, zmluva~zmluvy). Nahrádza lematizáciu."""
    if w == t:
        return True
    if w.isdigit() or t.isdigit():
        return False
    if len(w) <= 4:
        return t.startswith(w) and len(t) - len(w) <= 2
    cp = 0
    for a, b in zip(w, t):
        if a != b:
            break
        cp += 1
    return cp >= max(4, len(w) - 2) and len(t) <= len(w) + 4


_NUM = r"(\d[\d\s.,]*)\s*(tis(?:íc|ic)?\.?|k)?\s*(?:€|eur)?"


def _to_number(num: str, mult: str | None) -> float:
    v = float(re.sub(r"[\s.]", "", num).replace(",", "."))
    return v * 1000 if mult else v


def parse_price(text: str) -> tuple[float | None, float | None]:
    """Rozpozná cenové ohraničenie v otázke: 'do 100 000 €', 'pod 150 tisíc', 'od 500 eur'."""
    t = text.lower()
    lo = hi = None
    if m := re.search(r"\b(?:do|pod|max(?:imálne|imalne)?|najviac|menej ako|lacnejš\w*(?: ako)?)\s+" + _NUM, t):
        hi = _to_number(m.group(1), m.group(2))
    if m := re.search(r"\b(?:od|nad|min(?:imálne|imalne)?|aspoň|viac ako|drahš\w*(?: ako)?)\s+" + _NUM, t):
        lo = _to_number(m.group(1), m.group(2))
    # ignoruj malé čísla bez meny (napr. "od 2 izieb")
    if hi is not None and hi < 100:
        hi = None
    if lo is not None and lo < 100:
        lo = None
    return lo, hi


_RULE_WORDS = ("kauci", "zabezpek", "provizi", "poplat", "zmluv", "postup", "dan ", "hypot", "vklad",
               "katastr", "vypoved", "ako prebieha", "co treba", "pravidl")


def is_rules_question(text: str) -> bool:
    """Otázka na pravidlá/postupy (odpoveď je v textových dokumentoch, nie v zozname inzerátov)."""
    t = norm(text) + " "
    return any(w in t for w in _RULE_WORDS)


@dataclass
class Match:
    uri: URIRef
    kind: str          # "class" | "individual"
    surface: str       # ako to bolo napísané v texte
    label: str


@dataclass
class Analysis:
    matches: list[Match] = field(default_factory=list)
    classes: list[URIRef] = field(default_factory=list)
    individuals: list[URIRef] = field(default_factory=list)
    expansion: list[str] = field(default_factory=list)
    context: str = ""
    facts: list[str] = field(default_factory=list)
    sparql: str = ""
    price_min: float | None = None
    price_max: float | None = None

    @property
    def concept_set(self) -> set[str]:
        return {local(u) for u in self.classes + self.individuals}


def local(u) -> str:
    s = str(u)
    return s.split("#")[-1] if "#" in s else s.rsplit("/", 1)[-1]


# ---------------------------------------------------------------------------
class Ontology:
    def __init__(self, files: list[Path]):
        self.g = Graph()
        self.g.bind("", RK)
        self.g.bind("rkx", RKX)
        self.files = []
        for f in files:
            if f.exists():
                self.g.parse(str(f), format="xml" if f.suffix in (".owl", ".rdf") else "turtle")
                self.files.append(f.name)
        self.asserted_triples = len(self.g)
        self.inferred: list[tuple] = []
        self._infer()
        self._build_lexicon()

    # ------------------------------------------------------------------ inference
    def _add(self, t):
        if t not in self.g:
            self.g.add(t)
            self.inferred.append(t)

    def _infer(self):
        g = self.g
        # 1) parent z owl:intersectionOf (D ≡ A ⊓ ...) => D ⊑ A
        defined = []  # (D, A, prop, value)
        for d, eq in g.subject_objects(OWL.equivalentClass):
            for lst in g.objects(eq, OWL.intersectionOf):
                parts = list(Collection(g, lst))
                named = [p for p in parts if isinstance(p, URIRef)]
                restr = [p for p in parts if isinstance(p, BNode)]
                for a in named:
                    self._add((d, RDFS.subClassOf, a))
                for r in restr:
                    p, v = g.value(r, OWL.onProperty), g.value(r, OWL.hasValue)
                    if p is not None and v is not None:
                        for a in named:
                            defined.append((d, a, p, v))
        # 2) klasifikácia: C ⊑ A a C ⊑ (p hasValue v)  =>  C ⊑ D   (napr. Garsonka ⊑ JednoizbovyByt)
        for d, a, p, v in defined:
            for c in self.all_classes():
                if c == d or d in self.ancestors(c):
                    continue
                if a in self.ancestors(c):
                    for r in g.objects(c, RDFS.subClassOf):
                        if isinstance(r, BNode) and g.value(r, OWL.onProperty) == p and \
                                g.value(r, OWL.hasValue) is not None and \
                                g.value(r, OWL.hasValue).toPython() == v.toPython():
                            self._add((c, RDFS.subClassOf, d))
        # 3) inverzné vlastnosti
        for p, q in list(g.subject_objects(OWL.inverseOf)):
            for s, o in list(g.subject_objects(p)):
                self._add((o, q, s))
            for s, o in list(g.subject_objects(q)):
                self._add((o, p, s))
        # 4) typovanie inštancií podľa hasValue definícií (byt s pocetIzieb=2 => DvojizbovyByt)
        for d, a, p, v in defined:
            for ind in list(g.subjects(RDF.type, None)):
                if not isinstance(ind, URIRef):
                    continue
                types = set(g.objects(ind, RDF.type))
                if any(a == t or a in self.ancestors(t) for t in types if isinstance(t, URIRef)):
                    val = g.value(ind, p)
                    if val is not None and val.toPython() == v.toPython():
                        self._add((ind, RDF.type, d))

    # ------------------------------------------------------------------ schema helpers
    def all_classes(self) -> list[URIRef]:
        return sorted({c for c in self.g.subjects(RDF.type, OWL.Class) if isinstance(c, URIRef)}, key=str)

    def individuals(self) -> list[URIRef]:
        return sorted({i for i in self.g.subjects(RDF.type, OWL.NamedIndividual) if isinstance(i, URIRef)}, key=str)

    def parents(self, c) -> list[URIRef]:
        return [p for p in self.g.objects(c, RDFS.subClassOf) if isinstance(p, URIRef) and p != c]

    def children(self, c) -> list[URIRef]:
        return [s for s in self.g.subjects(RDFS.subClassOf, c) if isinstance(s, URIRef) and s != c]

    def ancestors(self, c) -> set[URIRef]:
        out, stack = set(), [c]
        while stack:
            for p in self.parents(stack.pop()):
                if p not in out:
                    out.add(p)
                    stack.append(p)
        return out

    def descendants(self, c) -> set[URIRef]:
        out, stack = set(), [c]
        while stack:
            for ch in self.children(stack.pop()):
                if ch not in out:
                    out.add(ch)
                    stack.append(ch)
        return out

    def label(self, u) -> str:
        for lab in self.g.objects(u, RDFS.label):
            if isinstance(lab, Literal) and lab.language in ("sk", None):
                return str(lab)
        name = local(u)
        return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name).replace("_", " ")

    def comment(self, u) -> str:
        for c in self.g.objects(u, RDFS.comment):
            return str(c)
        return ""

    def is_class(self, u) -> bool:
        return (u, RDF.type, OWL.Class) in self.g

    def types(self, ind) -> list[URIRef]:
        ts = [t for t in self.g.objects(ind, RDF.type) if isinstance(t, URIRef) and self.is_class(t)]
        # najšpecifickejší typ prvý
        return sorted(ts, key=lambda t: -len(self.ancestors(t)))

    def disjoint(self, c) -> set[URIRef]:
        out = set(self.g.objects(c, OWL.disjointWith)) | set(self.g.subjects(OWL.disjointWith, c))
        for ax in self.g.subjects(RDF.type, OWL.AllDisjointClasses):
            members = list(Collection(self.g, self.g.value(ax, OWL.members)))
            if c in members:
                out |= {m for m in members if m != c}
        return {o for o in out if isinstance(o, URIRef)}

    def class_expr(self, n) -> str:
        g = self.g
        if isinstance(n, URIRef):
            return self.label(n)
        if (u := g.value(n, OWL.unionOf)) is not None:
            return " alebo ".join(self.class_expr(x) for x in Collection(g, u))
        if (i := g.value(n, OWL.intersectionOf)) is not None:
            return " a zároveň ".join(self.class_expr(x) for x in Collection(g, i))
        p = g.value(n, OWL.onProperty)
        if p is None:
            return "?"
        pl = self.label(p)
        target = g.value(n, OWL.onClass) or g.value(n, OWL.onDataRange)
        tl = self.class_expr(target) if target is not None else ""
        if (v := g.value(n, OWL.hasValue)) is not None:
            return f"{pl} = {v}"
        if (v := g.value(n, OWL.someValuesFrom)) is not None:
            return f"{pl} aspoň jednu: {self.class_expr(v)}"
        if (v := g.value(n, OWL.allValuesFrom)) is not None:
            return f"{pl} iba: {self.class_expr(v)}"
        for pred, word in ((OWL.qualifiedCardinality, "presne"), (OWL.cardinality, "presne"),
                           (OWL.minQualifiedCardinality, "aspoň"), (OWL.minCardinality, "aspoň"),
                           (OWL.maxQualifiedCardinality, "najviac"), (OWL.maxCardinality, "najviac")):
            if (v := g.value(n, pred)) is not None:
                return f"{pl} {word} {v} {tl}".strip()
        return pl

    def axioms(self, c) -> list[str]:
        out = []
        for r in self.g.objects(c, RDFS.subClassOf):
            if isinstance(r, BNode):
                out.append(self.class_expr(r))
        for e in self.g.objects(c, OWL.equivalentClass):
            out.append("definícia: " + self.class_expr(e))
        return out

    def properties_of(self, c) -> list[str]:
        """Vlastnosti, ktorých doménou je trieda c alebo jej predok."""
        scope = {c} | self.ancestors(c)
        out = []
        for p in set(self.g.subjects(RDF.type, OWL.ObjectProperty)) | set(self.g.subjects(RDF.type, OWL.DatatypeProperty)):
            dom = self.g.value(p, RDFS.domain)
            if dom in scope:
                rng = self.g.value(p, RDFS.range)
                out.append(f"{self.label(p)} → {self.label(rng) if rng is not None else '?'}")
        return sorted(out)

    def path_up(self, c) -> str:
        chain, cur = [self.label(c)], c
        seen = {c}
        while True:
            ps = [p for p in self.parents(cur) if p not in seen]
            if not ps:
                break
            cur = max(ps, key=lambda p: len(self.ancestors(p)))  # najšpecifickejší rodič
            seen.add(cur)
            chain.append(self.label(cur))
        return " ⊑ ".join(chain)

    def location_chain(self, ind) -> str:
        chain, cur, seen = [], ind, set()
        while cur is not None and cur not in seen:
            seen.add(cur)
            chain.append(self.label(cur))
            nxt = [o for o in self.g.objects(cur, RK.jeSucastou)]
            # priamy rodič = ten, ktorý sám nie je súčasťou iného kandidáta
            cur = nxt[0] if nxt else None
        return " → ".join(chain)

    # ------------------------------------------------------------------ lexicon / NER
    def _build_lexicon(self):
        entries: dict[tuple, tuple[URIRef, str]] = {}

        def add(text, uri, kind):
            toks = tuple(tokenize(text))
            if toks and toks not in entries:
                entries[toks] = (uri, kind)

        for c in self.all_classes():
            for lab in list(self.g.objects(c, RDFS.label)) + list(self.g.objects(c, SKOS.altLabel)):
                add(str(lab), c, "class")
        lex_types = {RK.Lokalita, RK.Makler, RK.Inzerat, RK.Obhliadka}
        for ind in self.individuals():
            ts = set(self.types(ind))
            if not any(t in lex_types or lex_types & self.ancestors(t) for t in ts):
                continue
            for lab in list(self.g.objects(ind, RDFS.label)) + list(self.g.objects(ind, SKOS.altLabel)):
                add(str(lab), ind, "individual")
                if RK.Makler in ts:  # priezvisko samostatne
                    add(tokenize(str(lab))[-1], ind, "individual")
        # najdlhšie výrazy prvé
        self.lexicon = sorted(entries.items(), key=lambda kv: -len(kv[0]))

    def find(self, text: str) -> list[Match]:
        raw = re.findall(r"\w+", text.lower())
        toks = tokenize(text)
        found, i = [], 0
        while i < len(toks):
            for words, (uri, kind) in self.lexicon:
                n = len(words)
                if i + n <= len(toks) and all(word_match(w, toks[i + k]) for k, w in enumerate(words)):
                    surface = " ".join(raw[i:i + n]) if len(raw) == len(toks) else " ".join(toks[i:i + n])
                    found.append(Match(uri, kind, surface, self.label(uri)))
                    i += n
                    break
            else:
                i += 1
        return found

    def concepts_in(self, text: str) -> list[str]:
        return sorted({local(m.uri) for m in self.find(text)})

    def expand_concepts(self, names: set[str]) -> set[str]:
        """Pojmy úryvku + predkovia tried (úryvok o garsónke je aj o byte)."""
        out = set(names)
        for n in names:
            u = RK[n]
            if self.is_class(u):
                out |= {local(a) for a in self.ancestors(u)}
        return out

    # ------------------------------------------------------------------ query analysis
    def analyze(self, question: str, max_facts: int = 15) -> Analysis:
        a = Analysis(matches=self.find(question))
        for m in a.matches:
            target = a.classes if m.kind == "class" else a.individuals
            if m.uri not in target:
                target.append(m.uri)

        # rozšírenie dopytu o pod/nadtriedy
        exp = []
        for c in a.classes:
            exp += [self.label(d) for d in sorted(self.descendants(c), key=str)][:6]
            exp += [self.label(p) for p in self.parents(c)]
        for i in a.individuals:
            exp += [self.label(t) for t in self.types(i)[:1]]
            exp += [self.label(o) for o in self.g.objects(i, RK.jeSucastou)][:1]
        mentioned = {norm(m.label) for m in a.matches}
        a.expansion = list(dict.fromkeys(e for e in exp if norm(e) not in mentioned))

        a.price_min, a.price_max = parse_price(question)
        a.context = self._context_text(a)
        a.facts, a.sparql = self._facts(a, max_facts, rules_question=is_rules_question(question))
        return a

    def _context_text(self, a: Analysis) -> str:
        lines = []
        for c in a.classes:
            lines.append(f"• Pojem „{self.label(c)}“ (trieda :{local(c)})")
            if cm := self.comment(c):
                lines.append(f"  – definícia: {cm}")
            lines.append(f"  – hierarchia: {self.path_up(c)}")
            if ch := self.children(c):
                lines.append("  – podtriedy: " + ", ".join(self.label(x) for x in ch))
            for ax in self.axioms(c):
                lines.append(f"  – axióm: {ax}")
            if dj := self.disjoint(c):
                lines.append("  – disjunktná s: " + ", ".join(sorted(self.label(x) for x in dj)))
            if props := self.properties_of(c):
                lines.append("  – vlastnosti: " + "; ".join(props))
        for i in a.individuals:
            ts = self.types(i)
            lines.append(f"• Inštancia „{self.label(i)}“ (typ: {self.label(ts[0]) if ts else '?'})")
            if (RK.Lokalita in self.ancestors(ts[0])) if ts else False:
                lines.append(f"  – hierarchia lokalít: {self.location_chain(i)}")
            if pop := self.g.value(i, RKX.popis):
                lines.append(f"  – popis: {pop}")
        return "\n".join(lines)

    # ------------------------------------------------------------------ SPARQL facts
    def _facts(self, a: Analysis, limit: int, rules_question: bool = False) -> tuple[list[str], str]:
        neh = [c for c in a.classes if RK.Nehnutelnost in self.ancestors(c) | {c} and c != RK.Nehnutelnost]
        inz = [c for c in a.classes if RK.Inzerat in self.ancestors(c)]
        locs = [i for i in a.individuals if RK.Lokalita in set().union(*[self.ancestors(t) for t in self.types(i)] or [set()])]
        maks = [i for i in a.individuals if RK.Makler in self.types(i)]
        inz_ids = [i for i in a.individuals if any(RK.Inzerat in self.ancestors(t) for t in self.types(i))]
        has_price = a.price_min is not None or a.price_max is not None
        wants_listings = (neh or inz or locs or maks or inz_ids or has_price
                          or RK.Inzerat in a.classes or RK.Nehnutelnost in a.classes)
        if rules_question and not (locs or maks or inz_ids or has_price):
            # otázka na pravidlá (kaucia, provízia…) – zoznam inzerátov by model len rozptyľoval
            wants_listings = False
        if has_price and not inz:
            # heuristika: sumy nad 5 000 € sú kúpne ceny, menšie sú mesačné nájomné
            ref = a.price_max if a.price_max is not None else a.price_min
            inz = [RK.PredajnyInzerat if ref > 5000 else RK.NajomnyInzerat]

        facts, queries = [], []
        if wants_listings:
            q = self.listing_query(neh, inz, locs, maks, inz_ids, limit, a.price_min, a.price_max)
            queries.append(q)
            for r in self.g.query(q):
                facts.append(self._fmt_listing(r))
        if RK.Makler in a.classes and not maks:
            q = PREFIXES + """SELECT ?m ?name ?popis ?kontakt WHERE {
  ?m a :Makler ; rdfs:label ?name . OPTIONAL { ?m rkx:popis ?popis } OPTIONAL { ?m rkx:kontakt ?kontakt } }"""
            queries.append(q)
            for r in self.g.query(q):
                facts.append(f"Maklér {r.name}: {r.popis}; kontakt {r.kontakt}")
        if any(c in (RK.Obhliadka, RK.PlanovanaObhliadka, RK.UskutocnenaObhliadka) for c in a.classes):
            q = PREFIXES + """SELECT ?o ?typ ?datum ?neh ?k WHERE {
  ?o a ?typ ; rkx:datum ?datum ; rkx:tykaSaNehnutelnosti ?neh . ?typ rdfs:subClassOf :Obhliadka .
  OPTIONAL { ?k :rezervujeObhliadku ?o } } ORDER BY ?datum"""
            queries.append(q)
            for r in self.g.query(q):
                facts.append(f"{self.label(r.o)}: {self.label(r.typ)} dňa {r.datum}, nehnuteľnosť "
                             f"{self.label(r.neh)}, {self.label(r.k) if r.k else '?'}")
        return facts[:limit], "\n\n".join(queries)

    def listing_query(self, neh, inz, locs, maks, inz_ids, limit=15, pmin=None, pmax=None) -> str:
        values = ""
        if pmin is not None:
            values += f"  FILTER(?cena >= {pmin:g})\n"
        if pmax is not None:
            values += f"  FILTER(?cena <= {pmax:g})\n"
        if neh:
            values += "  VALUES ?ciel { " + " ".join(f"<{c}>" for c in neh) + " }\n  ?neh a/rdfs:subClassOf* ?ciel .\n"
        if inz:
            values += "  VALUES ?typInz { " + " ".join(f"<{c}>" for c in inz) + " }\n  ?inz a/rdfs:subClassOf* ?typInz .\n"
        if locs:
            values += "  VALUES ?miesto { " + " ".join(f"<{c}>" for c in locs) + " }\n  ?lok :jeSucastou* ?miesto .\n"
        if maks:
            values += "  VALUES ?mak { " + " ".join(f"<{c}>" for c in maks) + " }\n"
        if inz_ids:
            values += "  VALUES ?inz { " + " ".join(f"<{c}>" for c in inz_ids) + " }\n"
        return PREFIXES + f"""SELECT DISTINCT ?inz ?id ?neh ?lok ?vym ?izby ?cena ?mak ?doc WHERE {{
  ?inz :ponukaNehnutelnost ?neh ; rdfs:label ?id ; :cena ?cena .
  ?neh :nachadzaSaV ?lok ; :vymera ?vym .
  OPTIONAL {{ ?neh :pocetIzieb ?izby }}
  OPTIONAL {{ ?mak rkx:spravuje ?inz }}
  OPTIONAL {{ ?inz rkx:zdrojovyDokument ?doc }}
{values}}} ORDER BY ?cena LIMIT {limit}"""

    def _fmt_listing(self, r) -> str:
        inz_t = self.types(r.inz)
        najom = RK.NajomnyInzerat in inz_t
        neh_t = self.types(r.neh)
        cena = f"{float(r.cena):,.0f}".replace(",", " ") + (" €/mesiac" if najom else " €")
        izby = f", počet izieb {r.izby}" if r.izby is not None else ""
        mak = f", maklér {self.label(r.mak)}" if r.mak is not None else ""
        doc = f" (zdroj: {r.doc})" if r.doc is not None else ""
        loc = " → ".join(self.location_chain(r.lok).split(" → ")[:2])  # napr. Vlčince → Žilina
        return (f"{r.id} [{'prenájom' if najom else 'predaj'}]: {self.label(neh_t[0]) if neh_t else '?'} "
                f"– {loc}, {float(r.vym):g} m²{izby}, cena {cena}{mak}{doc}")

    # ------------------------------------------------------------------ stats / tree
    def stats(self) -> dict:
        return {
            "triedy": len(self.all_classes()),
            "obj. vlastnosti": len(set(self.g.subjects(RDF.type, OWL.ObjectProperty))),
            "dát. vlastnosti": len(set(self.g.subjects(RDF.type, OWL.DatatypeProperty))),
            "inštancie": len(self.individuals()),
            "trojice": self.asserted_triples,
            "odvodené": len(self.inferred),
            "lexikón": len(self.lexicon),
        }

    def roots(self) -> list[URIRef]:
        return [c for c in self.all_classes() if not self.parents(c)]

    def tree_lines(self, c=None, depth=0) -> list[str]:
        if c is None:
            out = []
            for r in self.roots():
                out += self.tree_lines(r, 0)
            return out
        n = len([i for i in self.g.subjects(RDF.type, c) if isinstance(i, URIRef)])
        lines = [f"{'    ' * depth}- **{self.label(c)}** `:{local(c)}`" + (f" ({n} inšt.)" if n else "")]
        for ch in sorted(self.children(c), key=self.label):
            lines += self.tree_lines(ch, depth + 1)
        return lines
