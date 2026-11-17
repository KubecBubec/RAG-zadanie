# RAG-zadanie (Sémantický Web)

Lokálny RAG (Retrieval-Augmented Generation) asistent pre **realitnú kanceláriu**, prepojený s OWL ontológiou
z predošlého zadania. Všetko beží lokálne v Dockeri: LLM cez [Ollama](https://ollama.com), vektorová databáza
ChromaDB, ontológia cez rdflib/SPARQL, webové rozhranie v Streamlite.

| Úloha zo zadania | Kde |
|---|---|
| Spojazdniť RAG u seba | `docker-compose.yml`, `app/` |
| Napojiť na ontológiu | `ontology/`, `app/ontology.py`, [dokumentácia §3](docs/DOKUMENTACIA.md#3-úloha-ontológie-v-systéme) |
| Pridať ±10 PDF z domény | `data/pdfs/` (11 PDF), generátor `tools/generate_data.py` |
| Zabaliť do apky | Streamlit aplikácia na <http://localhost:8501> |
| Dokumentácia | [`docs/DOKUMENTACIA.md`](docs/DOKUMENTACIA.md) |

## Rýchly štart

Treba mať nainštalovaný Docker Desktop. Prvé spustenie stiahne asi 5 GB modelov.

```bash
docker compose up -d
```

S NVIDIA GPU (rýchlejšie):

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

Potom otvor <http://localhost:8501>. Pri prvom štarte sa PDF dokumenty zaindexujú (asi 1 minúta).

Iný model (napr. rýchlejší na slabšom HW): vytvor v koreňovom priečinku súbor `.env` s riadkom
`LLM_MODEL=qwen2.5:3b` a spusti `docker compose up -d` znova.

## Štruktúra

```
app/                 Streamlit aplikácia (RAG pipeline, ontológia, indexovanie)
ontology/            realitna-kancelaria.owl (pôvodná) + lexikon.ttl + instancie.ttl
data/pdfs/           11 doménových PDF dokumentov
tools/               generate_data.py (PDF + inštancie), evaluate.py (porovnanie s/bez ontológie)
docs/                dokumentácia a výsledky evaluácie
```
