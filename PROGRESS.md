# GroundedDocs progress tracker

This file is the handoff point for later sessions. Read `GroundedDocs.md` first, then this file. Keep all project files in this directory. Update the checklist and the checkpoint after every completed phase.

## Checklist

- [x] Phase 1, step 1: Python 3.11 environment, pinned dependencies, Git, secrets example.
- [x] Phase 1, step 2: 30 synthetic documents, manifest, 60 validated labels.
- [x] Phase 2, step 3: deterministic ingestion and committed vector index.
- [x] Phase 2, step 4: authentication, access filtering, four search modes.
- [x] Phase 2, step 5: extractive answers, abstention, exact citations.
- [x] Phase 3, step 6: Streamlit demo, login/question/PDF citation/logout smoke check.
- [x] Phase 3, step 7: reproducible benchmark and 30 manual citation judgments.
- [x] Phase 3, step 8: 15 tests, README, final local server health check.
- [ ] Deployment: push standalone repo and verify free live demo.

## Current checkpoint

- Date: 2026-10-26 (Asia/Calcutta).
- State: Local project complete and reviewable. External publication remains.
- Environment: Python 3.11.15 in `.python/`, virtual environment in `.venv/`, Linux-compatible pinned `requirements.txt`. Local model files are in ignored `.model-cache/`.
- Verification completed: 30 documents, 60 labels, 59 chunks including a PDF page; deterministic repeated index build; four search modes; development-only threshold; 15 tests passed; dependency check passed; AppTest login, question, page citation and logout; local Streamlit health endpoint returned HTTP 200. Final held-out reranked metrics: recall@5 1.000, p95 455.2 ms, 30/30 supported citations, and negative abstention 0.800. These figures apply only to the synthetic corpus and measured machine.
- Next: publish this standalone Git repository, deploy `streamlit_app.py` on Streamlit Community Cloud with Python 3.11 and the ignored local `secrets.toml` contents in Cloud Secrets, verify the live URL, then add it and screenshots to `README.md`.
- Open items: live deployment requires external publication. No `GroundedDocs` repository currently exists under the connected GitHub account `saidarshan20`; GitHub CLI is unavailable, and the connected GitHub toolset has no repository-creation operation. Local synthetic password hashes are in ignored `.streamlit/secrets.toml`; published demo passwords are in `scripts/setup_demo_secrets.py`.

## Resume command

Open a shell in `GroundedDocs/`, read this file, run `git status --short`, and continue at the first unchecked step. Do not claim benchmark results until `results/benchmark.json` has been generated from the final index.
