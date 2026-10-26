import json
from pathlib import Path

import pytest
from grounded_docs.ingest import load_index
from grounded_docs.models import embedding_model, reranking_model
from grounded_docs.retrieve import SearchEngine

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def engine():
    config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    chunks, vectors, _ = load_index(ROOT)
    embedder = embedding_model(ROOT, config)
    reranker = reranking_model(ROOT, config)
    return SearchEngine(chunks, vectors, embedder, reranker, config["retrieval_candidates"], config["rrf_k"])
