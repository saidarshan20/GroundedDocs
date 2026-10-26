"""Access-filtered BM25, dense, hybrid, and reranked search."""

from __future__ import annotations

import re
import threading

import numpy as np

from grounded_docs.ingest import USERS

MODES = ("bm25", "dense", "hybrid", "reranked")


def tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


class SearchEngine:
    def __init__(self, chunks: list[dict], vectors: np.ndarray, embedder: object, reranker: object,
                 candidates: int = 20, rrf_k: int = 60):
        if len(chunks) != len(vectors):
            raise ValueError("Chunk and vector counts differ")
        self.chunks = chunks
        self.vectors = vectors
        self.embedder = embedder
        self.reranker = reranker
        self.candidates = candidates
        self.rrf_k = rrf_k
        self._inference_lock = threading.RLock()

    def search(self, question: str, principal: str, mode: str = "reranked", limit: int = 10) -> list[dict]:
        if principal not in USERS:
            raise ValueError("Unknown principal")
        if mode not in MODES:
            raise ValueError("Unknown search mode")
        terms = tokens(question)
        if not terms:
            return []
        allowed = [i for i, chunk in enumerate(self.chunks) if principal in chunk["allowed_users"]]
        if not allowed:
            return []

        from rank_bm25 import BM25Okapi

        bm25 = BM25Okapi([tokens(self.chunks[i]["text"]) for i in allowed])
        keyword_scores = bm25.get_scores(terms)
        keyword = sorted(zip(allowed, keyword_scores), key=lambda pair: (-float(pair[1]), self.chunks[pair[0]]["chunk_id"]))
        keyword = [(i, float(score)) for i, score in keyword if score > 0]
        if mode == "bm25":
            return [self._result(i, {"bm25": score}) for i, score in keyword[:limit]]

        with self._inference_lock:
            query_vector = np.asarray(next(iter(self.embedder.query_embed(question))), dtype=np.float32)
        query_vector = query_vector / max(float(np.linalg.norm(query_vector)), 1e-12)
        dense_scores = self.vectors[allowed] @ query_vector
        dense = sorted(zip(allowed, dense_scores), key=lambda pair: (-float(pair[1]), self.chunks[pair[0]]["chunk_id"]))
        dense = [(i, float(score)) for i, score in dense]
        if mode == "dense":
            return [self._result(i, {"dense": score}) for i, score in dense[:limit]]

        shortlist: dict[int, dict[str, float]] = {}
        for rank, (i, score) in enumerate(keyword[:self.candidates], 1):
            shortlist.setdefault(i, {})["bm25"] = score
            shortlist[i]["rrf"] = shortlist[i].get("rrf", 0.0) + 1 / (self.rrf_k + rank)
        for rank, (i, score) in enumerate(dense[:self.candidates], 1):
            shortlist.setdefault(i, {})["dense"] = score
            shortlist[i]["rrf"] = shortlist[i].get("rrf", 0.0) + 1 / (self.rrf_k + rank)
        hybrid = sorted(shortlist, key=lambda i: (-shortlist[i]["rrf"], self.chunks[i]["chunk_id"]))
        if mode == "hybrid":
            return [self._result(i, shortlist[i]) for i in hybrid[:limit]]

        rerank_ids = hybrid[:self.candidates]
        with self._inference_lock:
            scores = list(self.reranker.rerank(question, [self.chunks[i]["text"] for i in rerank_ids]))
        if len(scores) != len(rerank_ids):
            raise ValueError("Reranker score count mismatch")
        for i, score in zip(rerank_ids, scores):
            shortlist[i]["reranker"] = float(score)
        ordered = sorted(rerank_ids, key=lambda i: (-shortlist[i]["reranker"], self.chunks[i]["chunk_id"]))
        return [self._result(i, shortlist[i]) for i in ordered[:limit]]

    def _result(self, i: int, scores: dict[str, float]) -> dict:
        return {"chunk": self.chunks[i], "scores": scores.copy()}
