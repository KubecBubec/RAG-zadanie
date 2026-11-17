"""Indexovanie PDF dokumentov do vektorovej databázy ChromaDB.

Každý úryvok (chunk) dostane okrem embeddingu aj sémantickú anotáciu:
zoznam pojmov ontológie, ktoré sa v ňom vyskytujú (metadata "concepts").
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

import chromadb
from chromadb.config import Settings
from pypdf import PdfReader

import llm
from ontology import Ontology

COLLECTION = "dokumenty"


@dataclass
class Chunk:
    id: str
    text: str
    source: str
    title: str
    page: int
    concepts: list[str]


def read_pdf(path: Path) -> tuple[str, list[str]]:
    reader = PdfReader(str(path))
    title = (reader.metadata.title if reader.metadata and reader.metadata.title else path.stem)
    pages = [(p.extract_text() or "") for p in reader.pages]
    return str(title), pages


def split_text(text: str, size: int = 900, overlap_sentences: int = 1) -> list[str]:
    """Delenie na úryvky po vetách (~size znakov), s presahom jednej vety."""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s*\n\s*", " ", text).strip()
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-ZÁÄČĎÉÍĹĽŇÓÔŔŠŤÚÝŽ0-9•])", text)
    chunks, cur = [], []
    for s in sentences:
        if cur and len(" ".join(cur + [s])) > size:
            chunks.append(" ".join(cur))
            cur = cur[-overlap_sentences:] if overlap_sentences else []
        cur.append(s)
    if cur:
        chunks.append(" ".join(cur))
    return [c for c in chunks if len(c) > 40]


class Index:
    def __init__(self, pdf_dir: Path, index_dir: Path, onto: Ontology):
        self.pdf_dir, self.index_dir, self.onto = pdf_dir, index_dir, onto
        index_dir.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(index_dir / "chroma"),
                                                settings=Settings(anonymized_telemetry=False))
        self.col = self.client.get_or_create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})
        self.manifest_path = index_dir / "manifest.json"

    # ------------------------------------------------------------------
    def _fingerprint(self) -> dict:
        files = {}
        for p in sorted(self.pdf_dir.glob("*.pdf")):
            files[p.name] = hashlib.md5(p.read_bytes()).hexdigest()
        # zmena lexikónu ontológie => treba nanovo anotovať úryvky
        onto_hash = hashlib.md5(repr([(k, str(v[0])) for k, v in self.onto.lexicon]).encode()).hexdigest()
        return {"files": files, "embed_model": llm.EMBED_MODEL, "onto": onto_hash}

    def is_fresh(self) -> bool:
        if not self.manifest_path.exists() or self.col.count() == 0:
            return False
        return json.loads(self.manifest_path.read_text(encoding="utf-8")) == self._fingerprint()

    def build(self, progress=None) -> int:
        """Kompletne preindexuje všetky PDF. Vracia počet úryvkov."""
        self.client.delete_collection(COLLECTION)
        self.col = self.client.get_or_create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})
        chunks: list[Chunk] = []
        pdfs = sorted(self.pdf_dir.glob("*.pdf"))
        for p in pdfs:
            title, pages = read_pdf(p)
            for pi, page_text in enumerate(pages, start=1):
                for ci, t in enumerate(split_text(page_text)):
                    chunks.append(Chunk(f"{p.name}:{pi}:{ci}", t, p.name, title, pi, self.onto.concepts_in(t)))
        for i in range(0, len(chunks), 16):
            batch = chunks[i:i + 16]
            # do embeddingu dávame aj názov dokumentu – úryvok tak nesie kontext, odkiaľ pochádza
            vecs = llm.embed([f"{c.title}\n{c.text}" for c in batch])
            self.col.add(
                ids=[c.id for c in batch],
                embeddings=vecs,
                documents=[c.text for c in batch],
                metadatas=[{"source": c.source, "title": c.title, "page": c.page,
                            "concepts": "|".join(c.concepts)} for c in batch],
            )
            if progress:
                progress(min(1.0, (i + len(batch)) / max(1, len(chunks))), f"{i + len(batch)}/{len(chunks)} úryvkov")
        self.manifest_path.write_text(json.dumps(self._fingerprint(), ensure_ascii=False, indent=1), encoding="utf-8")
        return len(chunks)

    # ------------------------------------------------------------------
    def search(self, query: str, n: int = 20) -> list[dict]:
        vec = llm.embed([query])[0]
        res = self.col.query(query_embeddings=[vec], n_results=min(n, max(1, self.col.count())))
        out = []
        for i in range(len(res["ids"][0])):
            md = res["metadatas"][0][i]
            out.append({
                "id": res["ids"][0][i],
                "text": res["documents"][0][i],
                "source": md["source"],
                "title": md["title"],
                "page": md["page"],
                "concepts": [c for c in md.get("concepts", "").split("|") if c],
                "similarity": 1.0 - float(res["distances"][0][i]),
            })
        return out

    def documents_overview(self) -> list[dict]:
        data = self.col.get(include=["metadatas"])
        docs: dict[str, dict] = {}
        for md in data["metadatas"]:
            d = docs.setdefault(md["source"], {"súbor": md["source"], "názov": md["title"], "strany": 0,
                                               "úryvky": 0, "pojmy": {}})
            d["strany"] = max(d["strany"], md["page"])
            d["úryvky"] += 1
            for c in filter(None, md.get("concepts", "").split("|")):
                d["pojmy"][c] = d["pojmy"].get(c, 0) + 1
        out = []
        for d in sorted(docs.values(), key=lambda x: x["súbor"]):
            top = sorted(d["pojmy"].items(), key=lambda kv: -kv[1])[:8]
            d["pojmy"] = ", ".join(f"{k} ({v})" for k, v in top)
            out.append(d)
        return out
