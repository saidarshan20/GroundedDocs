import io
import json
from unittest.mock import patch

import pytest

from grounded_docs.openrouter import MODEL, api_key, organize_evidence


def result(text, chunk_id="doc:1"):
    return {"chunk": {"text": text, "chunk_id": chunk_id, "title": "Demo.txt",
                      "page": None, "section": "s1", "allowed_users": ["guest"]},
            "scores": {"reranker": 2.0}}


def response(ids):
    return io.BytesIO(json.dumps({"choices": [{"message": {
        "content": json.dumps({"ids": ids})}}]}).encode("utf-8"))


def test_local_env_key_is_loaded_without_tracking_or_echoing_it(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    (tmp_path / ".env").write_text('OPENROUTER_API_KEY="local-test-key"\n', encoding="utf-8")
    assert api_key(tmp_path) == "local-test-key"


def test_openrouter_selects_only_locally_held_cited_evidence():
    text = "Delete a container\ndocker rm <container_name>"
    with patch("grounded_docs.openrouter.urlopen", return_value=response(["S1"])) as send:
        selected = organize_evidence("deleting a container", [result(text)], "test-key")
    request = send.call_args.args[0]
    payload = json.loads(request.data)
    assert payload["model"] == MODEL == "nvidia/nemotron-3.5-super-vl:free"
    assert payload["reasoning"] == {"enabled": False}
    assert json.loads(payload["messages"][1]["content"])["evidence"] == [{"id": "S1", "text": text}]
    assert selected == [{"quote": text, "chunk_id": "doc:1",
                         "title": "Demo.txt", "location": "s1", "excerpt": text}]


@pytest.mark.parametrize("ids", [
    ["S2"],
    ["S1", "S1"],
    [],
])
def test_openrouter_rejects_invalid_ids_or_empty_output(ids):
    with patch("grounded_docs.openrouter.urlopen", return_value=response(ids)):
        with pytest.raises(ValueError, match="invalid excerpt IDs"):
            organize_evidence("deleting a container", [result("docker rm <container_name>")], "test-key")


def test_openrouter_does_not_display_model_written_text():
    model_output = io.BytesIO(json.dumps({"choices": [{"message": {
        "content": '{"quotes":[{"id":"S1","quote":"Invented claim"}]}'
    }}]}).encode("utf-8"))
    with patch("grounded_docs.openrouter.urlopen", return_value=model_output):
        with pytest.raises(ValueError, match="invalid excerpt IDs"):
            organize_evidence("deleting a container", [result("docker rm <container_name>")], "test-key")


def test_openrouter_reports_exhausted_output_budget():
    no_content = io.BytesIO(json.dumps({"choices": [{"message": {"content": None},
                                                    "finish_reason": "length"}]}).encode("utf-8"))
    with patch("grounded_docs.openrouter.urlopen", return_value=no_content):
        with pytest.raises(ValueError, match="output budget"):
            organize_evidence("deleting a container", [result("docker rm <container_name>")], "test-key")
