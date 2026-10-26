"""Reproducible retrieval and answer benchmark, with manual citation review."""

from __future__ import annotations

import hashlib
import json
import platform
import sys
import time
from pathlib import Path

from grounded_docs.answer import answer_question
from grounded_docs.ingest import jsonl_records
from grounded_docs.retrieve import MODES, SearchEngine


def validate_labels(root: Path) -> list[dict]:
    records = jsonl_records(root / "labels" / "questions.jsonl")
    if len(records) != 60 or len({r["question_id"] for r in records}) != 60:
        raise ValueError("Expected 60 unique labeled questions")
    manifest = jsonl_records(root / "corpus" / "manifest.jsonl")
    grants = {r["doc_id"]: set(r["allowed_users"]) for r in manifest}
    for record in records:
        user = record["user_id"]
        if record["split"] not in {"dev", "test"} or user not in {"guest", "alice", "bob"}:
            raise ValueError(f"Invalid split or user for {record['question_id']}")
        relevant = record["relevant_doc_ids"]
        if record["answerable"] != bool(relevant):
            raise ValueError(f"Invalid answerability for {record['question_id']}")
        if any(doc not in grants or user not in grants[doc] for doc in relevant):
            raise ValueError(f"Relevant document is not permitted for {record['question_id']}")
        if any(doc not in grants or user in grants[doc] for doc in record.get("forbidden_doc_ids", [])):
            raise ValueError(f"Invalid forbidden document for {record['question_id']}")
    counts = {(split, answerable): sum(r["split"] == split and r["answerable"] == answerable for r in records)
              for split in ("dev", "test") for answerable in (True, False)}
    if counts != {("dev", True): 10, ("dev", False): 5, ("test", True): 30, ("test", False): 15}:
        raise ValueError(f"Unexpected label split: {counts}")
    return records


def percentile95(samples: list[float]) -> float:
    ordered = sorted(samples)
    return ordered[max(0, (95 * len(ordered) + 99) // 100 - 1)]


def run_benchmark(root: Path, engine: SearchEngine, index_info: dict, config: dict) -> dict:
    records = [r for r in validate_labels(root) if r["split"] == "test"]
    # Warm each execution path once, then exclude model/index initialization.
    for mode in MODES:
        result = engine.search(records[0]["question"], records[0]["user_id"], mode, limit=10)
        answer_question(records[0]["question"], result, config["abstention_threshold"] if mode == "reranked" else None)
    timings: dict[str, list[float]] = {mode: [] for mode in MODES}
    first_pass: dict[str, list[dict]] = {mode: [] for mode in MODES}
    for pass_number in range(3):
        for mode in MODES:
            for record in records:
                start = time.perf_counter()
                found = engine.search(record["question"], record["user_id"], mode, limit=10)
                outcome = answer_question(record["question"], found,
                                          config["abstention_threshold"] if mode == "reranked" else None)
                elapsed = (time.perf_counter() - start) * 1000
                timings[mode].append(elapsed)
                if pass_number == 0:
                    retrieved = [r["chunk"]["doc_id"] for r in found]
                    if any(record["user_id"] not in r["chunk"]["allowed_users"] for r in found):
                        raise AssertionError("Access leak in benchmark")
                    first_pass[mode].append({
                        "question_id": record["question_id"], "user_id": record["user_id"],
                        "answerable": record["answerable"], "relevant_doc_ids": record["relevant_doc_ids"],
                        "retrieved_doc_ids": retrieved, "retrieved_chunk_ids": [r["chunk"]["chunk_id"] for r in found],
                        "answer": outcome["answer"], "citation": outcome["citation"],
                        "abstained": outcome["abstained"], "first_pass_ms": round(elapsed, 3),
                    })
    aggregate = {}
    for mode in MODES:
        rows = first_pass[mode]
        answerable = [r for r in rows if r["answerable"]]
        negative = [r for r in rows if not r["answerable"]]
        aggregate[mode] = {
            "recall_at_5": sum(bool(set(r["relevant_doc_ids"]) & set(r["retrieved_doc_ids"][:5])) for r in answerable) / len(answerable),
            "recall_at_10": sum(bool(set(r["relevant_doc_ids"]) & set(r["retrieved_doc_ids"][:10])) for r in answerable) / len(answerable),
            "p95_ms": round(percentile95(timings[mode]), 3),
            "coverage": sum(not r["abstained"] for r in answerable) / len(answerable),
            "negative_abstention_accuracy": sum(r["abstained"] for r in negative) / len(negative),
            "external_api_usd_per_query": 0.0,
        }
    reranked_nonabstaining = [r for r in first_pass["reranked"] if r["answerable"] and not r["abstained"]]
    judgment_path = root / "labels" / "citation_judgments.jsonl"
    judgments = {j["question_id"]: j for j in jsonl_records(judgment_path)} if judgment_path.exists() else {}
    reviewed: list[bool] = []
    for row in reranked_nonabstaining:
        judgment = judgments.get(row["question_id"])
        answer_hash = hashlib.sha256(row["answer"].encode("utf-8")).hexdigest()
        if judgment and judgment.get("answer_sha256") == answer_hash and isinstance(judgment.get("supported"), bool):
            reviewed.append(judgment["supported"])
    aggregate["reranked"]["citation_correctness"] = (
        sum(reviewed) / len(reranked_nonabstaining) if len(reviewed) == len(reranked_nonabstaining) and reviewed else None
    )
    return {
        "method": "Three warm timed passes over 45 held-out questions; retrieval plus answer, excluding startup and index load. Nearest-rank p95.",
        "environment": {"python": sys.version.split()[0], "platform": platform.platform(),
                        "processor": platform.processor(), "ram_gb": total_ram_gb()},
        "models": {"embedding": config["embedding_model"], "embedding_revision": config["embedding_revision"],
                   "reranker": config["reranker_model"], "reranker_revision": config["reranker_revision"]},
        "corpus_fingerprint": index_info["corpus_fingerprint"], "chunk_count": index_info["chunk_count"],
        "question_counts": {"held_out_answerable": 30, "held_out_negative": 15},
        "citation_judgments_complete": len(reviewed) == len(reranked_nonabstaining),
        "citation_judgments_count": len(reviewed),
        "aggregate": aggregate, "per_query": first_pass,
        "cost_note": "External API spend is $0.00/query. Host CPU, electricity, and paid tiers are excluded.",
    }


def total_ram_gb() -> float | None:
    if sys.platform == "win32":
        import ctypes

        class MemoryStatus(ctypes.Structure):
            _fields_ = [("length", ctypes.c_ulong), ("memory_load", ctypes.c_ulong),
                        ("total_phys", ctypes.c_ulonglong), ("avail_phys", ctypes.c_ulonglong),
                        ("total_page_file", ctypes.c_ulonglong), ("avail_page_file", ctypes.c_ulonglong),
                        ("total_virtual", ctypes.c_ulonglong), ("avail_virtual", ctypes.c_ulonglong),
                        ("avail_extended_virtual", ctypes.c_ulonglong)]

        state = MemoryStatus()
        state.length = ctypes.sizeof(state)
        return round(state.total_phys / (1024 ** 3), 2) if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(state)) else None
    try:
        import os

        return round(os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE") / (1024 ** 3), 2)
    except (AttributeError, ValueError):
        return None


def markdown_table(result: dict) -> str:
    lines = ["# GroundedDocs benchmark", "", result["method"], "",
             f"Corpus fingerprint: `{result['corpus_fingerprint']}`; chunks: {result['chunk_count']}.", "",
             "| Mode | Recall@5 | Recall@10 | p95 ms | Coverage | Negative abstention | External API $/query |",
             "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for mode, row in result["aggregate"].items():
        lines.append(f"| {mode} | {row['recall_at_5']:.3f} | {row['recall_at_10']:.3f} | {row['p95_ms']:.1f} | "
                     f"{row['coverage']:.3f} | {row['negative_abstention_accuracy']:.3f} | $0.00 |")
    correctness = result["aggregate"]["reranked"]["citation_correctness"]
    lines += ["", f"Reranked citation correctness: {correctness:.3f}." if correctness is not None else
              "Reranked citation correctness: pending manual review of every non-abstaining held-out answer.",
              "", result["cost_note"], ""]
    return "\n".join(lines)
