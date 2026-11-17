"""Tenký klient pre Ollama API (embeddingy + chat so streamovaním)."""
from __future__ import annotations

import json
import os
from typing import Iterator

import requests

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://ollama:11434").rstrip("/")
LLM_MODEL = os.environ.get("LLM_MODEL", "gemma3:4b")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "bge-m3")
NUM_CTX = int(os.environ.get("NUM_CTX", "6144"))
_eg = os.environ.get("EMBED_NUM_GPU", "0").strip()
EMBED_NUM_GPU = int(_eg) if _eg else None  # prázdne = nech rozhodne Ollama
_lg = os.environ.get("LLM_NUM_GPU", "").strip()
LLM_NUM_GPU = int(_lg) if _lg else None  # počet vrstiev LLM na GPU; prázdne = automaticky


def available_models() -> list[str]:
    r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=10)
    r.raise_for_status()
    return [m["name"] for m in r.json().get("models", [])]


def embed(texts: list[str], batch: int = 16) -> list[list[float]]:
    out: list[list[float]] = []
    for i in range(0, len(texts), batch):
        payload = {"model": EMBED_MODEL, "input": texts[i:i + batch]}
        if EMBED_NUM_GPU is not None:
            # 0 = embeddingy na CPU, aby LLM dostal celú VRAM (dôležité pri 4 GB GPU)
            payload["options"] = {"num_gpu": EMBED_NUM_GPU}
        r = requests.post(f"{OLLAMA_URL}/api/embed", json=payload, timeout=600)
        r.raise_for_status()
        out += r.json()["embeddings"]
    return out


KEEP_ALIVE = os.environ.get("OLLAMA_KEEP_ALIVE", "30m")


def _llm_options(temperature: float = 0.2) -> dict:
    # rovnaké voľby pri warmupe aj pri chate – inak by Ollama model načítala znova
    options = {"temperature": temperature, "num_ctx": NUM_CTX}
    if LLM_NUM_GPU is not None:
        options["num_gpu"] = LLM_NUM_GPU
    return options


def warmup() -> None:
    """Načíta LLM aj embedding model do pamäte vopred (prvé načítanie z disku trvá 1–2 min)."""
    try:
        embed(["warmup"])
        requests.post(f"{OLLAMA_URL}/api/generate", timeout=900, json={
            "model": LLM_MODEL, "prompt": "", "keep_alive": KEEP_ALIVE, "options": _llm_options()})
    except Exception:  # noqa: BLE001 – warmup je len optimalizácia
        pass


def chat_stream(messages: list[dict], temperature: float = 0.2) -> Iterator[str]:
    options = _llm_options(temperature)
    with requests.post(f"{OLLAMA_URL}/api/chat", stream=True, timeout=600, json={
        "model": LLM_MODEL,
        "messages": messages,
        "stream": True,
        "keep_alive": KEEP_ALIVE,
        "options": options,
    }) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if not line:
                continue
            data = json.loads(line)
            if "error" in data:
                raise RuntimeError(data["error"])
            yield data.get("message", {}).get("content", "")
            if data.get("done"):
                break
