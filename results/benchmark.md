# GroundedDocs benchmark

Three warm timed passes over 45 held-out questions; retrieval plus answer, excluding startup and index load. Nearest-rank p95.

Corpus fingerprint: `2470cc0030a6db7b0bcc2688cf948547bd5eb818d6ac0deb69bd014a7a7070b3`; chunks: 59.

| Mode | Recall@5 | Recall@10 | p95 ms | Coverage | Negative abstention | External API $/query |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| bm25 | 1.000 | 1.000 | 0.9 | 1.000 | 0.067 | $0.00 |
| dense | 1.000 | 1.000 | 40.1 | 1.000 | 0.000 | $0.00 |
| hybrid | 1.000 | 1.000 | 10.5 | 1.000 | 0.000 | $0.00 |
| reranked | 1.000 | 1.000 | 455.2 | 1.000 | 0.800 | $0.00 |

Reranked citation correctness: 1.000.

External API spend is $0.00/query. Host CPU, electricity, and paid tiers are excluded.
