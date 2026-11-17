"""Porovnanie RAG bez ontológie vs. RAG s ontológiou na sade testovacích otázok.

Spustenie (stack musí bežať):
    docker compose exec app python /workspace/tools/evaluate.py
    docker compose exec -e LLM_MODEL=qwen2.5:3b app python /workspace/tools/evaluate.py

Výstup: docs/evaluacia_<model>.md
"""
from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, "/app")

import llm  # noqa: E402
from index import Index  # noqa: E402
from ontology import Ontology, norm  # noqa: E402
from rag import RAG  # noqa: E402

WS = Path(os.environ.get("WORKSPACE", "/workspace"))

# (otázka, kľúčové údaje, ktoré by správna odpoveď mala obsahovať; "a|b" = stačí jedna z alternatív)
QUESTIONS = [
    ("Ktoré jednoizbové byty máte na predaj v Žiline?", ["INZ-101", "INZ-102"]),
    ("Môžem si na záhrade v Závodí postaviť rodinný dom?", ["nie|nemôž|nemoz"]),
    ("Aké nehnuteľnosti ponúkate v meste Žilina do 100 000 €?", ["INZ-101", "INZ-204", "INZ-206"]),
    ("Ktoré nehnuteľnosti spravuje Peter Hruška?", ["INZ-201", "INZ-203", "INZ-204"]),
    ("Aká je kaucia pri prenájme bytu?", ["trojnásob|3-násob|3 násob|tri mesa|3 mesa|tri nájom|3 nájom"]),
    ("Koľko stojí provízia pri predaji domu?", ["4 %"]),
    ("Kedy sú naplánované obhliadky?", ["2026-11-24", "2026-11-26"]),
]


def _n(s: str) -> str:
    return re.sub(r"\s+", "", norm(s))


def contains(answer: str, expected: str) -> bool:
    """Tolerantné porovnanie: bez diakritiky, medzier a veľkých písmen; "a|b" = alternatívy."""
    return any(_n(alt) in _n(answer) for alt in expected.split("|"))


def main():
    only = sys.argv[1:]  # voliteľne indexy otázok
    onto = Ontology([WS / "ontology" / f for f in ("realitna-kancelaria.owl", "lexikon.ttl", "instancie.ttl")])
    index = Index(WS / "data" / "pdfs", Path(os.environ.get("INDEX_DIR", "/index")), onto)
    if not index.is_fresh():
        index.build()
    rag = RAG(onto, index)
    out = [f"# Evaluácia: RAG bez ontológie vs. s ontológiou\n",
           f"Model: `{llm.LLM_MODEL}`, embeddingy: `{llm.EMBED_MODEL}`, top-k = 5\n",
           "Skóre = podiel očakávaných kľúčových údajov, ktoré odpoveď obsahuje.\n"]
    summary = []
    for qi, (q, expected) in enumerate(QUESTIONS):
        if only and str(qi) not in only:
            continue
        out.append(f"\n## {qi + 1}. {q}\n\n*Očakávané:* {', '.join(e.split('|')[0] for e in expected)}\n")
        row = [q]
        for use in (False, True):
            r = rag.retrieve(q, use_ontology=use, k=5)
            t0 = time.time()
            ans = "".join(llm.chat_stream(rag.messages(r)))
            dt = time.time() - t0
            hit = sum(1 for e in expected if contains(ans, e))
            score = hit / len(expected)
            row += [score, dt]
            label = "S ontológiou" if use else "Bez ontológie"
            srcs = ", ".join(f"{c['source']}:{c['page']}" for c in r.chunks)
            out.append(f"\n### {label} — skóre {hit}/{len(expected)}, {dt:.1f} s\n")
            if use and r.analysis:
                out.append(f"*Rozpoznané pojmy:* {', '.join(m.label for m in r.analysis.matches) or '–'}  \n")
                out.append(f"*Fakty z KG:* {len(r.analysis.facts)}  \n")
            out.append(f"*Zdroje:* {srcs}\n\n> " + ans.strip().replace("\n", "\n> ") + "\n")
            print(f"[{qi + 1}] {label}: {hit}/{len(expected)} ({dt:.1f}s)", flush=True)
        summary.append(row)

    out.append("\n## Súhrn\n\n| Otázka | Bez ontológie | S ontológiou |\n|---|---|---|\n")
    for q, s0, t0, s1, t1 in summary:
        out.append(f"| {q} | {s0:.0%} ({t0:.0f} s) | {s1:.0%} ({t1:.0f} s) |\n")
    if summary:
        a0 = sum(r[1] for r in summary) / len(summary)
        a1 = sum(r[3] for r in summary) / len(summary)
        out.append(f"| **Priemer** | **{a0:.0%}** | **{a1:.0%}** |\n")
    path = WS / "docs" / f"evaluacia_{llm.LLM_MODEL.replace(':', '_')}.md"
    path.parent.mkdir(exist_ok=True)
    path.write_text("".join(out), encoding="utf-8")
    print("Uložené:", path)


if __name__ == "__main__":
    main()
