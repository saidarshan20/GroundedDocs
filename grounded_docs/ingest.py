"""Validate source documents and build a deterministic, access-tagged index."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Iterator

import numpy as np

USERS = frozenset({"guest", "alice", "bob"})


def jsonl_records(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize(text: str) -> str:
    return " ".join(text.split())


def sections(path: Path) -> Iterator[tuple[str, int | None, str]]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        for page_number, page in enumerate(reader.pages, 1):
            text = normalize(page.extract_text() or "")
            if not text:
                raise ValueError(f"No extractable text on {path}, page {page_number}")
            yield f"page-{page_number}", page_number, text
    elif suffix == ".md":
        heading = "intro"
        lines: list[str] = []
        section_number = 0
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("#") and re.match(r"^#{1,6}\s+", line):
                if lines and normalize(" ".join(lines)):
                    yield f"s{section_number}-{heading}", None, normalize(" ".join(lines))
                section_number += 1
                heading = re.sub(r"[^a-z0-9]+", "-", line.lstrip("# ").lower()).strip("-") or "untitled"
                lines = []
            else:
                lines.append(line)
        if lines and normalize(" ".join(lines)):
            yield f"s{section_number}-{heading}", None, normalize(" ".join(lines))
    elif suffix == ".txt":
        text = normalize(path.read_text(encoding="utf-8"))
        if text:
            yield "s1-text", None, text
    else:
        raise ValueError(f"Unsupported document type: {path}")


def chunk_text(text: str, size: int, overlap: int) -> Iterator[str]:
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError("Chunk size must be positive and overlap smaller than size")
    words = text.split()
    start = 0
    while start < len(words):
        end = min(start + size, len(words))
        yield " ".join(words[start:end])
        if end == len(words):
            break
        start = end - overlap


def load_manifest(root: Path) -> list[dict]:
    records = jsonl_records(root / "corpus" / "manifest.jsonl")
    seen: set[str] = set()
    for record in records:
        doc_id = record["doc_id"]
        if not re.fullmatch(r"[a-z0-9_-]+", doc_id) or doc_id in seen:
            raise ValueError(f"Invalid or duplicate document ID: {doc_id}")
        seen.add(doc_id)
        grants = record["allowed_users"]
        if not grants or len(grants) != len(set(grants)) or not set(grants) <= USERS:
            raise ValueError(f"Invalid grants for {doc_id}")
        relative = Path(record["path"])
        if relative.is_absolute() or ".." in relative.parts or not (root / relative).is_file():
            raise ValueError(f"Invalid or missing document path for {doc_id}")
        if relative.suffix.lower() not in {".md", ".txt", ".pdf"}:
            raise ValueError(f"Unsupported document type for {doc_id}")
    return records


def create_chunks(root: Path, config: dict) -> list[dict]:
    chunks: list[dict] = []
    for record in load_manifest(root):
        doc_id = record["doc_id"]
        source = root / record["path"]
        count = 0
        for section, page, text in sections(source):
            for ordinal, passage in enumerate(chunk_text(text, config["chunk_words"], config["chunk_overlap_words"]), 1):
                chunks.append({
                    "chunk_id": f"{doc_id}:{section}:{ordinal:03d}",
                    "doc_id": doc_id,
                    "title": record["title"],
                    "path": record["path"],
                    "page": page,
                    "section": section,
                    "text": passage,
                    "text_sha256": sha256(passage.encode("utf-8")),
                    "allowed_users": record["allowed_users"],
                })
                count += 1
        if count == 0:
            raise ValueError(f"No extractable text in {source}")
    ids = [chunk["chunk_id"] for chunk in chunks]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate chunk IDs")
    return chunks


def corpus_fingerprint(root: Path, config: dict) -> str:
    digest = hashlib.sha256()
    manifest_path = root / "corpus" / "manifest.jsonl"
    digest.update(manifest_path.read_bytes())
    for record in load_manifest(root):
        digest.update(record["path"].encode())
        digest.update((root / record["path"]).read_bytes())
    for key in ("embedding_model", "embedding_repo", "embedding_revision", "chunk_words", "chunk_overlap_words"):
        digest.update(f"{key}={config[key]}".encode())
    return digest.hexdigest()


def build_index(root: Path) -> dict:
    from grounded_docs.models import embedding_model

    config = json.loads((root / "config.json").read_text(encoding="utf-8"))
    chunks = create_chunks(root, config)
    model = embedding_model(root, config)
    embeddings = np.asarray(list(model.passage_embed([c["text"] for c in chunks])), dtype=np.float32)
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    embeddings = embeddings / np.maximum(norms, 1e-12)
    if len(embeddings) != len(chunks) or not np.isfinite(embeddings).all():
        raise ValueError("Invalid generated embeddings")
    folder = root / "index"
    folder.mkdir(exist_ok=True)
    (folder / "chunks.jsonl").write_text("".join(json.dumps(c, ensure_ascii=False) + "\n" for c in chunks), encoding="utf-8")
    np.save(folder / "embeddings.npy", embeddings)
    info = {"corpus_fingerprint": corpus_fingerprint(root, config), "embedding_model": config["embedding_model"],
            "embedding_revision": config["embedding_revision"], "reranker_model": config["reranker_model"],
            "reranker_revision": config["reranker_revision"], "chunk_count": len(chunks),
            "embedding_dimensions": embeddings.shape[1]}
    (folder / "build_info.json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    return info


def load_index(root: Path) -> tuple[list[dict], np.ndarray, dict]:
    config = json.loads((root / "config.json").read_text(encoding="utf-8"))
    folder = root / "index"
    info = json.loads((folder / "build_info.json").read_text(encoding="utf-8"))
    if info["corpus_fingerprint"] != corpus_fingerprint(root, config):
        raise ValueError("Index is stale; run python -m scripts.build_index")
    chunks = jsonl_records(folder / "chunks.jsonl")
    vectors = np.load(folder / "embeddings.npy", allow_pickle=False)
    if len(chunks) != len(vectors) or len(chunks) != info["chunk_count"]:
        raise ValueError("Index row count mismatch")
    return chunks, vectors, info
