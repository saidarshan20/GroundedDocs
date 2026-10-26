from grounded_docs.answer import ABSTENTION, answer_question


def test_answer_copies_exact_permitted_evidence(engine):
    question = "How many pages may a guest print per visit?"
    found = engine.search(question, "guest", "reranked", limit=10)
    outcome = answer_question(question, found, threshold=None)
    assert not outcome["abstained"]
    assert outcome["answer"] in outcome["excerpt"]
    assert outcome["citation"]["doc_id"] == "pub12"
    assert outcome["citation"]["location"] == "page 1"


def test_high_threshold_abstains_without_citation(engine):
    found = engine.search("When is Alice's prototype review?", "bob", "reranked", limit=10)
    outcome = answer_question("When is Alice's prototype review?", found, threshold=1e9)
    assert outcome["abstained"]
    assert outcome["answer"] == ABSTENTION
    assert outcome["citation"] is None
