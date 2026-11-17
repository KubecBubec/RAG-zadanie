"""Streamlit aplikácia: RAG nad dokumentmi realitnej kancelárie prepojený s ontológiou."""
from __future__ import annotations

import os
import threading
import time
from pathlib import Path

import pandas as pd
import streamlit as st

import llm
from index import Index
from rdflib.namespace import RDF

from ontology import PREFIXES, Analysis, Ontology
from rag import RAG

WORKSPACE = Path(os.environ.get("WORKSPACE", Path(__file__).resolve().parents[1]))
ONTO_FILES = [WORKSPACE / "ontology" / f for f in ("realitna-kancelaria.owl", "lexikon.ttl", "instancie.ttl")]
PDF_DIR = WORKSPACE / "data" / "pdfs"
INDEX_DIR = Path(os.environ.get("INDEX_DIR", WORKSPACE / "data" / "index"))

st.set_page_config(page_title="RAG – Realitná kancelária", page_icon="🏠", layout="wide")


@st.cache_resource(show_spinner="Načítavam ontológiu…")
def load_ontology() -> Ontology:
    return Ontology(ONTO_FILES)


@st.cache_resource(show_spinner=False)
def load_index(_onto: Ontology) -> Index:
    return Index(PDF_DIR, INDEX_DIR, _onto)


def wait_for_ollama():
    for _ in range(60):
        try:
            return llm.available_models()
        except Exception:  # noqa: BLE001
            time.sleep(2)
    st.error(f"Ollama nie je dostupná na {llm.OLLAMA_URL}.")
    st.stop()


onto = load_ontology()
models = wait_for_ollama()
missing = [m for m in (llm.LLM_MODEL, llm.EMBED_MODEL) if not any(x.split(":")[0] == m.split(":")[0] and
                                                                   (":" not in m or x == m) for x in models)]
if missing:
    st.warning(f"V Ollame chýbajú modely: {', '.join(missing)}. Spusti `docker compose up` (služba ollama-init).")
    st.stop()

@st.cache_resource(show_spinner=False)
def start_warmup() -> threading.Thread:
    """Raz po štarte aplikácie načíta modely na pozadí, aby prvá otázka nečakala na disk."""
    t = threading.Thread(target=llm.warmup, daemon=True)
    t.start()
    return t


warmup_thread = start_warmup()
index = load_index(onto)
if not index.is_fresh():
    bar = st.progress(0.0, "Indexujem PDF dokumenty…")
    n = index.build(lambda p, msg: bar.progress(p, f"Indexujem PDF dokumenty… {msg}"))
    bar.empty()
    st.toast(f"Zaindexovaných {n} úryvkov.")
rag = RAG(onto, index)

# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Nastavenia")
    use_onto = st.toggle("Použiť ontológiu", value=True,
                         help="Vypni pre porovnanie s obyčajným RAG (len vektorové vyhľadávanie).")
    top_k = st.slider("Počet úryvkov (top-k)", 2, 10, 5)
    st.caption(f"LLM: `{llm.LLM_MODEL}`  \nEmbeddingy: `{llm.EMBED_MODEL}`  \nOllama: `{llm.OLLAMA_URL}`")
    st.caption(f"Úryvkov v indexe: {index.col.count()}")
    if st.button("🗑️ Vymazať konverzáciu"):
        st.session_state.history = []
        st.rerun()

st.title("🏠 RAG asistent realitnej kancelárie")
st.caption("Lokálny LLM (Ollama) + vektorová databáza (ChromaDB) + OWL ontológia (rdflib, SPARQL)")

# st.radio namiesto st.tabs: zvolená stránka ostane aktívna aj po kliknutí na tlačidlo (rerun)
page = st.radio("Stránka", ["💬 Chat", "🧠 Ontológia", "📄 Dokumenty"], horizontal=True, label_visibility="collapsed")

# ---------------------------------------------------------------------------
EXAMPLES = [
    "Aké garsónky ponúkate na predaj a za koľko?",
    "Hľadám dvojizbový byt na Vlčincoch, čo máte?",
    "Môžem si na záhrade v Závodí postaviť rodinný dom?",
    "Aká je kaucia pri prenájme bytu?",
    "Ktoré nehnuteľnosti spravuje Peter Hruška?",
    "Koľko stojí provízia pri predaji domu?",
]


def stream_with_status(gen, model_loading: bool):
    """Kým nepríde prvý token, ukazuje spinner (načítanie modelu + spracovanie promptu trvá desiatky sekúnd)."""
    msg = ("Načítavam model do pamäte a generujem odpoveď… (prvá otázka po štarte môže trvať 1–2 minúty)"
           if model_loading else "Generujem odpoveď…")
    with st.spinner(msg):
        first = next(gen, "")
    yield first
    yield from gen


def render_details(ret):
    if ret.use_ontology and ret.analysis:
        a = ret.analysis
        with st.expander(f"🧠 Ontológia: rozpoznané pojmy ({len(a.matches)})"):
            if a.matches:
                st.dataframe(pd.DataFrame([{"v texte": m.surface, "pojem": m.label,
                                            "IRI": ":" + str(m.uri).split("#")[-1], "druh": m.kind}
                                           for m in a.matches]), hide_index=True, use_container_width=True)
            else:
                st.write("Žiadne pojmy z ontológie neboli rozpoznané.")
            if a.expansion:
                st.markdown("**Rozšírenie dopytu:** " + ", ".join(a.expansion))
            if a.context:
                st.code(a.context, language="text")
        if a.facts:
            with st.expander(f"🔗 Znalostný graf: fakty zo SPARQL ({len(a.facts)})"):
                for f in a.facts:
                    st.markdown(f"- {f}")
                st.code(a.sparql, language="sparql")
    with st.expander(f"📄 Zdroje ({len(ret.chunks)})"):
        for i, c in enumerate(ret.chunks, 1):
            extra = f" · bonus z ontológie +{c['bonus']:.2f} ({', '.join(c.get('matched', []))})" if c.get("bonus") else ""
            st.markdown(f"**[D{i}] {c['source']}**, strana {c['page']} — podobnosť {c['similarity']:.3f}{extra}")
            st.caption(c["text"])


if page == "💬 Chat":
    if "history" not in st.session_state:
        st.session_state.history = []
    for msg in st.session_state.history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("ret"):
                render_details(msg["ret"])

    question = st.chat_input("Opýtajte sa na ponuku, zmluvy, obhliadky, lokality…") or st.session_state.pop("pending", None)
    if not st.session_state.history and not question:
        st.markdown("**Skúste napríklad:**")
        cols = st.columns(3)
        for i, ex in enumerate(EXAMPLES):
            if cols[i % 3].button(ex, use_container_width=True):
                st.session_state.pending = ex
                st.rerun()

    if question:
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            with st.spinner("Hľadám v ontológii a dokumentoch…"):
                ret = rag.retrieve(question, use_ontology=use_onto, k=top_k)
                msgs = rag.messages(ret, [{"role": h["role"], "content": h["content"]}
                                          for h in st.session_state.history])
            t0 = time.time()
            answer = st.write_stream(stream_with_status(llm.chat_stream(msgs), warmup_thread.is_alive()))
            st.caption(f"⏱️ {time.time() - t0:.1f} s · {'s ontológiou' if use_onto else 'bez ontológie'}")
            render_details(ret)
        st.session_state.history += [{"role": "user", "content": question},
                                     {"role": "assistant", "content": answer, "ret": ret}]

# ---------------------------------------------------------------------------
if page == "🧠 Ontológia":
    stats = onto.stats()
    cols = st.columns(len(stats))
    for col, (k, v) in zip(cols, stats.items()):
        col.metric(k, v)
    st.caption("Načítané súbory: " + ", ".join(onto.files))

    left, right = st.columns([1, 1])
    with left:
        st.subheader("Hierarchia tried")
        st.markdown("\n".join(onto.tree_lines()))
    with right:
        st.subheader("Detail triedy")
        classes = onto.all_classes()
        sel = st.selectbox("Trieda", classes, format_func=lambda c: f"{onto.label(c)} (:{str(c).split('#')[-1]})",
                           index=next((i for i, c in enumerate(classes) if str(c).endswith("#Garsonka")), 0))
        st.code(onto._context_text(Analysis(classes=[sel])), language="text")
        inst = [i for i in onto.g.subjects(RDF.type, sel)]
        if inst:
            st.markdown("**Inštancie:** " + ", ".join(sorted(onto.label(i) for i in inst)))

        st.subheader("Test rozpoznávania pojmov")
        txt = st.text_input("Text", "Predávam 2-izbový byt v Žiline na Hlinách, obhliadka možná v sobotu.")
        st.write([f"{m.surface} → {m.label}" for m in onto.find(txt)])

    st.subheader("SPARQL konzola")
    examples = {
        "Byty na predaj do 160 000 € (s odvodzovaním podtried)": """SELECT ?id (GROUP_CONCAT(DISTINCT ?typ; separator=", ") AS ?typy) ?lokalita ?vymera ?cena WHERE {
  ?inz a :PredajnyInzerat ; rdfs:label ?id ; :cena ?cena ; :ponukaNehnutelnost ?n .
  ?n a ?t ; :nachadzaSaV ?l ; :vymera ?vymera .
  ?t rdfs:subClassOf* :Byt .
  ?t rdfs:label ?typ . ?l rdfs:label ?lokalita .
  FILTER(?cena <= 160000)
} GROUP BY ?id ?lokalita ?vymera ?cena ORDER BY ?cena""",
        "Všetko v meste Žilina (tranzitívne jeSucastou)": """SELECT ?id ?lokalita ?cena WHERE {
  ?inz :ponukaNehnutelnost ?n ; rdfs:label ?id ; :cena ?cena .
  ?n :nachadzaSaV ?l . ?l :jeSucastou* :Mesto_Zilina ; rdfs:label ?lokalita .
} ORDER BY ?lokalita""",
        "Počet inzerátov podľa makléra": """SELECT ?makler (COUNT(?inz) AS ?pocet) (AVG(?cena) AS ?priemernaCena) WHERE {
  ?m rkx:spravuje ?inz ; rdfs:label ?makler . ?inz :cena ?cena .
} GROUP BY ?makler""",
        "Prepojenie inštancií na PDF dokumenty": """SELECT ?dokument (COUNT(?x) AS ?pocetInstancii) WHERE {
  ?x rkx:zdrojovyDokument ?dokument .
} GROUP BY ?dokument ORDER BY ?dokument""",
        "Odvodené nadtriedy garsónky": """SELECT ?nadtrieda WHERE { :Garsonka rdfs:subClassOf+ ?n . ?n rdfs:label ?nadtrieda }""",
    }
    ex = st.selectbox("Príklad", list(examples))
    q = st.text_area("Dopyt (prefixy :, rkx:, rdfs:, owl:, skos:, xsd: sú doplnené automaticky)",
                     examples[ex], height=180, key=f"sparql_{ex}")
    if st.button("▶️ Spustiť SPARQL"):
        try:
            res = onto.g.query(PREFIXES + q)
            rows = [{str(v): (str(r[v]).split("#")[-1] if r[v] is not None else "") for v in res.vars} for r in res]
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
            st.caption(f"{len(rows)} riadkov")
        except Exception as e:  # noqa: BLE001
            st.error(str(e))

# ---------------------------------------------------------------------------
if page == "📄 Dokumenty":
    st.subheader("Zaindexované dokumenty a ich prepojenie na ontológiu")
    st.caption("Stĺpec „pojmy“ ukazuje, ktoré triedy/inštancie ontológie sa v úryvkoch dokumentu najčastejšie vyskytujú "
               "(sémantická anotácia pri indexovaní).")
    st.dataframe(pd.DataFrame(index.documents_overview()), hide_index=True, use_container_width=True)

    up = st.file_uploader("Pridať PDF dokumenty", type="pdf", accept_multiple_files=True)
    c1, c2 = st.columns(2)
    if c1.button("💾 Uložiť a preindexovať", disabled=not up):
        for f in up:
            (PDF_DIR / f.name).write_bytes(f.getbuffer())
        bar = st.progress(0.0)
        n = index.build(lambda p, msg: bar.progress(p, msg))
        st.success(f"Hotovo, {n} úryvkov.")
        st.rerun()
    if c2.button("🔄 Preindexovať všetko"):
        bar = st.progress(0.0)
        n = index.build(lambda p, msg: bar.progress(p, msg))
        st.success(f"Hotovo, {n} úryvkov.")
