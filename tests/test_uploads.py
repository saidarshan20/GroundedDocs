import json
from pathlib import Path

import pytest

from grounded_docs.answer import answer_question
from grounded_docs.uploads import MAX_UPLOAD_BYTES, create_upload_chunks

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))


def test_markdown_upload_keeps_sections_and_owner():
    source = b"# Schedule\n\n## Pickup\nThe blue shuttle leaves at 7:45 p.m. on Mondays.\n"
    chunks = create_upload_chunks("../My notes.md", source, "alice", CONFIG)
    assert len(chunks) == 1
    assert chunks[0]["title"] == "My_notes.md"
    assert chunks[0]["allowed_users"] == ["alice"]
    assert chunks[0]["section"] == "s2-pickup"
    assert "7:45 p.m. on Mondays" in chunks[0]["text"]


def test_pdf_upload_retains_page_number():
    source = (ROOT / "corpus" / "docs" / "pub12.pdf").read_bytes()
    chunks = create_upload_chunks("printing.pdf", source, "guest", CONFIG)
    assert len(chunks) == 1
    assert chunks[0]["page"] == 1
    assert "ten black-and-white pages" in chunks[0]["text"]


@pytest.mark.parametrize("name,data", [
    ("note.docx", b"text"),
    ("note.txt", b""),
    ("note.txt", b"x" * (MAX_UPLOAD_BYTES + 1)),
    ("note.txt", b"\xff\xfe"),
    ("scan.pdf", b"not a PDF"),
], ids=["unsupported-type", "empty", "too-large", "invalid-utf8", "invalid-pdf"])
def test_invalid_upload_is_rejected(name, data):
    with pytest.raises(ValueError):
        create_upload_chunks(name, data, "alice", CONFIG)


def test_uploaded_chunks_are_session_scoped_and_access_filtered(engine):
    source = b"# Ferry\n\nThe violet ferry leaves Harbor Nine at 6:40 a.m. every Tuesday."
    chunks = create_upload_chunks("private.txt", source, "alice", CONFIG)
    vectors = engine.embed_passages([chunk["text"] for chunk in chunks])
    session_engine = engine.with_upload(chunks, vectors, include_base=False)
    found = session_engine.search("When does the violet ferry leave Harbor Nine?", "alice", "dense")
    assert found and found[0]["chunk"]["doc_id"].startswith("upload-")
    answer = answer_question("When does the violet ferry leave Harbor Nine?", found)
    assert "6:40 a.m. every Tuesday" in answer["answer"]
    assert session_engine.search("violet ferry", "bob", "dense") == []
    assert all(not chunk["doc_id"].startswith("upload-") for chunk in engine.chunks)
