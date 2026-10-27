import io
import json
from unittest.mock import patch

import pytest

from grounded_docs.openrouter import MODEL, api_key, organize_evidence


def result(text, chunk_id="doc:1"):
    return {"chunk": {"text": text, "chunk_id": chunk_id, "title": "Demo.txt",
                      "page": None, "section": "s1", "allowed_users": ["guest"]},
            "scores": {"reranker": 2.0}}


def response(quotes):
    return io.BytesIO(json.dumps({"choices": [{"message": {
        "content": json.dumps({"quotes": quotes})}}]}).encode("utf-8"))


def test_local_env_key_is_loaded_without_tracking_or_echoing_it(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    (tmp_path / ".env").write_text('OPENROUTER_API_KEY="local-test-key"\n', encoding="utf-8")
    assert api_key(tmp_path) == "local-test-key"


def test_openrouter_selects_only_exact_cited_evidence():
    text = "Delete a container\ndocker rm <container_name>"
    with patch("grounded_docs.openrouter.urlopen", return_value=response([
        {"id": "E1", "quote": "docker rm <container_name>"}
    ])) as send:
        selected = organize_evidence("deleting a container", [result(text)], "test-key")
    request = send.call_args.args[0]
    payload = json.loads(request.data)
    assert payload["model"] == MODEL == "nvidia/nemotron-3.5-super-vl:free"
    assert json.loads(payload["messages"][1]["content"])["evidence"] == [{"id": "E1", "text": text}]
    assert selected == [{"quote": "docker rm <container_name>", "chunk_id": "doc:1",
                         "title": "Demo.txt", "location": "s1", "excerpt": text}]


@pytest.mark.parametrize("quotes", [
    [{"id": "E1", "quote": "docker rm removes containers safely"}],
    [{"id": "E2", "quote": "docker rm"}],
    [],
])
def test_openrouter_rejects_unsupported_or_empty_output(quotes):
    with patch("grounded_docs.openrouter.urlopen", return_value=response(quotes)):
        with pytest.raises(ValueError, match="ungrounded or invalid"):
            organize_evidence("deleting a container", [result("docker rm <container_name>")], "test-key")
