import pytest

from grounded_docs.retrieve import MODES


@pytest.mark.parametrize("mode", MODES)
def test_restricted_document_never_leaks(engine, mode):
    question = "When is Alice's prototype review?"
    for principal in ("guest", "bob"):
        found = engine.search(question, principal, mode, limit=10)
        assert all(principal in item["chunk"]["allowed_users"] for item in found)
        assert all(item["chunk"]["doc_id"] != "alice01" for item in found)


def test_account_switch_does_not_reuse_results(engine):
    question = "When is Alice's prototype review?"
    alice = engine.search(question, "alice", "reranked", limit=10)
    bob = engine.search(question, "bob", "reranked", limit=10)
    alice_again = engine.search(question, "alice", "reranked", limit=10)
    assert any(item["chunk"]["doc_id"] == "alice01" for item in alice)
    assert all(item["chunk"]["doc_id"] != "alice01" for item in bob)
    assert [r["chunk"]["chunk_id"] for r in alice] == [r["chunk"]["chunk_id"] for r in alice_again]


def test_invalid_principal_fails_closed(engine):
    with pytest.raises(ValueError):
        engine.search("visitor badge", "admin", "hybrid")
