"""Run from the project root: python -m scripts.build_index."""

from pathlib import Path

from grounded_docs.ingest import build_index


if __name__ == "__main__":
    print(build_index(Path(__file__).resolve().parents[1]))
