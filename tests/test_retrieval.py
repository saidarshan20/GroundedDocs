import json
from pathlib import Path

import pytest

from grounded_docs.evaluate import validate_labels
from grounded_docs.ingest import create_chunks, load_index
from grounded_docs.retrieve import MODES

ROOT = Path(__file__).resolve().parents[1]


def test_corpus_and_index_are_current():
    config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    chunks = create_chunks(ROOT, config)
    indexed, vectors, info = load_index(ROOT)
    assert len({c["doc_id"] for c in chunks}) == 30
    assert [c["chunk_id"] for c in chunks] == [c["chunk_id"] for c in indexed]
    assert len(vectors) == info["chunk_count"] == len(chunks)
    assert any(c["page"] == 1 and c["doc_id"] == "pub12" for c in chunks)


def test_labels_have_expected_split():
    records = validate_labels(ROOT)
    assert len(records) == 60


@pytest.mark.parametrize("mode", MODES)
def test_search_mode_returns_permitted_and_stable_results(engine, mode):
    first = engine.search("Where is the emergency assembly point?", "guest", mode, limit=10)
    second = engine.search("Where is the emergency assembly point?", "guest", mode, limit=10)
    assert first
    assert [r["chunk"]["chunk_id"] for r in first] == [r["chunk"]["chunk_id"] for r in second]
    assert all("guest" in r["chunk"]["allowed_users"] for r in first)
