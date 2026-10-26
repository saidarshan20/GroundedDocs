"""Run from the project root: python -m scripts.run_benchmark."""

import json
from pathlib import Path

from grounded_docs.evaluate import markdown_table, run_benchmark
from grounded_docs.ingest import load_index
from grounded_docs.models import embedding_model, reranking_model
from grounded_docs.retrieve import SearchEngine


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    config = json.loads((root / "config.json").read_text(encoding="utf-8"))
    chunks, vectors, info = load_index(root)
    embedder = embedding_model(root, config)
    reranker = reranking_model(root, config)
    engine = SearchEngine(chunks, vectors, embedder, reranker, config["retrieval_candidates"], config["rrf_k"])
    result = run_benchmark(root, engine, info, config)
    output = root / "results"
    output.mkdir(exist_ok=True)
    (output / "benchmark.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output / "benchmark.md").write_text(markdown_table(result), encoding="utf-8")
    print(markdown_table(result))


if __name__ == "__main__":
    main()
