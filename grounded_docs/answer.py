"""Extract a verbatim answer and link it to the permitted source chunk."""

from __future__ import annotations

import re

from grounded_docs.retrieve import tokens

ABSTENTION = "I couldn't find enough evidence in documents you can access."
STOPWORDS = frozenset("a an and are as at be by can do does for from how i in is it of on or the to was what when where which who why with you".split())


def sentences(text: str) -> list[str]:
    # A following capital marks a new sentence; keep times such as "8:00 a.m. on weekdays" intact.
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+(?=[A-Z])", text) if part.strip()]


def answer_question(question: str, results: list[dict], threshold: float | None = None) -> dict:
    """Return one exact evidence sentence or an abstention with no citation."""
    if not results or (threshold is not None and results[0]["scores"].get("reranker", float("-inf")) < threshold):
        return {"answer": ABSTENTION, "citation": None, "excerpt": None, "abstained": True, "trace": results}
    query_terms = set(tokens(question)) - STOPWORDS
    # Exact uploaded headings resolve close reranker scores between similar entries.
    candidates_to_read = results[:3]
    if results[0]["chunk"].get("origin") == "session_upload" and "reranker" in results[0]["scores"]:
        top_score = results[0]["scores"]["reranker"]
        exact_heading = [item for item in candidates_to_read
                         if item["chunk"].get("origin") == "session_upload"
                         and item["scores"].get("reranker", float("-inf")) >= top_score - 0.5
                         and set(tokens(item["chunk"]["text"].splitlines()[0])) - STOPWORDS == query_terms]
        if exact_heading:
            candidates_to_read = exact_heading + [item for item in candidates_to_read if item not in exact_heading]
    selected = None
    for item in candidates_to_read:
        candidates = [(len(query_terms & (set(tokens(sentence)) - STOPWORDS)), sentence)
                      for sentence in sentences(item["chunk"]["text"])]
        if candidates:
            _, sentence = max(candidates, key=lambda item: (item[0], -len(item[1])))
            selected = sentence, item["chunk"]
            break
    if selected is None:
        return {"answer": ABSTENTION, "citation": None, "excerpt": None, "abstained": True, "trace": results}
    sentence, chunk = selected
    location = f"page {chunk['page']}" if chunk["page"] is not None else chunk["section"]
    citation = {"chunk_id": chunk["chunk_id"], "doc_id": chunk["doc_id"],
                "title": chunk["title"], "location": location, "path": chunk["path"]}
    assert sentence in chunk["text"]
    return {"answer": sentence, "citation": citation, "excerpt": chunk["text"],
            "abstained": False, "trace": results}
