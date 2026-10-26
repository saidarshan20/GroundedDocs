"""Load exact, pinned ONNX model snapshots for repeatable indexing and search."""

from pathlib import Path


def pinned_snapshot(root: Path, repo: str, revision: str, files: list[str]) -> str:
    from huggingface_hub import snapshot_download

    return snapshot_download(repo_id=repo, revision=revision, cache_dir=str(root / ".model-cache"), allow_patterns=files)


def embedding_model(root: Path, config: dict):
    from fastembed import TextEmbedding

    location = pinned_snapshot(root, config["embedding_repo"], config["embedding_revision"],
                               ["config.json", "model_optimized.onnx", "tokenizer.json", "tokenizer_config.json", "special_tokens_map.json", "vocab.txt"])
    return TextEmbedding(model_name=config["embedding_model"], specific_model_path=location)


def reranking_model(root: Path, config: dict):
    from fastembed.rerank.cross_encoder import TextCrossEncoder

    location = pinned_snapshot(root, config["reranker_repo"], config["reranker_revision"],
                               ["config.json", "onnx/model.onnx", "tokenizer.json", "tokenizer_config.json", "special_tokens_map.json", "vocab.txt"])
    return TextCrossEncoder(model_name=config["reranker_model"], specific_model_path=location)
