"""Choose the reranker abstention cutoff from development questions only."""

import json
from pathlib import Path

from grounded_docs.evaluate import validate_labels
from grounded_docs.ingest import load_index
from grounded_docs.models import embedding_model, reranking_model
from grounded_docs.retrieve import SearchEngine


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "config.json"
    config = json.loads(path.read_text(encoding="utf-8"))
    chunks, vectors, _ = load_index(root)
    embedder = embedding_model(root, config)
    reranker = reranking_model(root, config)
    engine = SearchEngine(chunks, vectors, embedder, reranker, config["retrieval_candidates"], config["rrf_k"])
    samples = []
    for record in validate_labels(root):
        if record["split"] == "dev":
            found = engine.search(record["question"], record["user_id"], "reranked", limit=3)
            score = found[0]["scores"]["reranker"] if found else float("-inf")
            samples.append((score, record["answerable"]))
    unique = sorted({score for score, _ in samples})
    candidates = [unique[0] - 1] + [(a + b) / 2 for a, b in zip(unique, unique[1:])] + [unique[-1] + 1]
    def balanced_accuracy(threshold: float) -> float:
        positives = [score >= threshold for score, expected in samples if expected]
        negatives = [score < threshold for score, expected in samples if not expected]
        return (sum(positives) / len(positives) + sum(negatives) / len(negatives)) / 2
    threshold = max(candidates, key=lambda candidate: (balanced_accuracy(candidate), candidate))
    config["abstention_threshold"] = round(threshold, 6)
    path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    print(f"Development balanced accuracy: {balanced_accuracy(threshold):.3f}; threshold: {threshold:.6f}")


if __name__ == "__main__":
    main()
