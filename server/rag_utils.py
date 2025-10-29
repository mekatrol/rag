import os
import hashlib
from pathlib import Path
from typing import List, Dict, Mapping
import torch
import numpy as np
from chromadb import PersistentClient
from chromadb.api.types import QueryResult
from sentence_transformers import SentenceTransformer
from pypdf import PdfReader
from docx import Document as DocxDocument
import httpx

# ---- Config ----
EMBED_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
MAX_TOK = int(os.getenv("MAX_CHUNK_TOKENS", "220"))
OVERLAP = int(os.getenv("CHUNK_OVERLAP", "40"))
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
COLLECTION = os.getenv("COLLECTION_NAME", "docs")
DATA_DIR = os.getenv("DATA_DIR", "./data")
DB_PATH = os.getenv("CHROMA_PATH", "./chroma_db")

# ---- Globals ----
_client = PersistentClient(path=DB_PATH)
_model = SentenceTransformer(
    EMBED_MODEL, device="cuda" if torch.cuda.is_available() else "cpu"
)

MetaVal = str | int | float | bool | None
MetaMap = Mapping[str, MetaVal]


# ---- Tokenization / chunking ----
def _tok(text: str) -> list[str]:
    return text.split()


def _detok(toks: list[str]) -> str:
    return " ".join(toks)


def chunk_text(text: str) -> List[str]:
    toks = _tok(text)
    out: List[str] = []
    i = 0
    while i < len(toks):
        j = min(i + MAX_TOK, len(toks))
        out.append(_detok(toks[i:j]))
        if j == len(toks):
            break
        i = j - OVERLAP
    return out


# ---- File loaders ----
def load_text(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="ignore")
    if ext == ".pdf":
        r = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in r.pages)
    if ext == ".docx":
        d = DocxDocument(str(path))
        return "\n".join(p.text for p in d.paragraphs)
    return ""


def iter_files(root: str | Path) -> list[Path]:
    root = Path(root)
    return [
        p
        for p in root.rglob("*")
        if p.is_file() and p.suffix.lower() in {".pdf", ".txt", ".md", ".docx"}
    ]


# ---- IDs ----
def doc_id(path: Path, idx: int) -> str:
    h = hashlib.blake2b((str(path) + f":{idx}").encode(), digest_size=8).hexdigest()
    return h


# ---- Chroma helpers ----
def get_collection(name: str):
    return _client.get_or_create_collection(name, metadata={"hnsw:space": "cosine"})


# ---- Ingestion ----
def ingest_dir(root: str, collection: str = COLLECTION) -> tuple[int, int]:
    col = get_collection(collection)
    files = iter_files(root)
    n_chunks_total = 0

    for f in files:
        text = load_text(f)
        if not text:
            continue
        chunks = chunk_text(text)
        if not chunks:
            continue

        ids: list[str] = [doc_id(f, i) for i, _ in enumerate(chunks)]

        metas: list[dict[str, str | int | float | bool | None]] = [
            {"path": str(f), "chunk_index": int(i)} for i, _ in enumerate(chunks)
        ]

        vecs = _model.encode(
            chunks,
            batch_size=64,
            convert_to_numpy=True,
            normalize_embeddings=True,
            device="cuda" if torch.cuda.is_available() else "cpu",
        )

        # All lists, lengths must match
        assert len(ids) == len(chunks) == len(metas) == len(vecs)

        col.add(
            ids=ids,  # list[str]
            documents=chunks,  # list[str]
            metadatas=metas,  # list[dict]
            embeddings=vecs,  # list[list[float]]
        )
        n_chunks_total += len(chunks)

    return len(files), n_chunks_total


# ---- Retrieval ----
def search(query: str, top_k: int = 4, collection: str = COLLECTION) -> List[Dict]:
    col = get_collection(collection)
    qvec = _model.encode([query], convert_to_numpy=True, normalize_embeddings=True)[0]
    res: QueryResult = col.query(
        query_embeddings=[qvec.astype(np.float32).tolist()],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    docs: List[Dict] = []
    docs_list = res.get("documents") or []
    if not docs_list or not docs_list[0]:
        return docs

    for i in range(len(docs_list[0])):
        meta_row = (res.get("metadatas") or [[]])[0][i] or {}
        dist = (res.get("distances") or [[0.0]])[0][i] or 0.0
        docs.append(
            {
                "text": docs_list[0][i],
                "path": meta_row.get("path", ""),
                "chunk_index": meta_row.get("chunk_index", 0),
                "score": float(1.0 - float(dist)),
            }
        )
    return docs


# ---- Generation via Ollama ----
def format_prompt(q: str, ctxs: List[Dict]) -> str:
    ctx = "\n\n".join(f"[Source {i + 1}] {c['text']}" for i, c in enumerate(ctxs))
    return (
        "You answer using only the sources below. If unsure, say you don't know.\n\n"
        f"Question: {q}\n\nSources:\n{ctx}\n\nAnswer:"
    )


def ollama_generate(prompt: str) -> str:
    with httpx.Client(timeout=120) as s:
        r = s.post(
            f"{OLLAMA_HOST}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
        )
        r.raise_for_status()
        return r.json().get("response", "").strip()


def answer_with_rag(q: str, ctxs: List[Dict]) -> tuple[str, List[Dict]]:
    prompt = format_prompt(q, ctxs)
    return ollama_generate(prompt), ctxs
