# GroundedDocs progress tracker

This file is the handoff point for later sessions. Read `GroundedDocs.md` first, then this file. Keep all project files in this directory. Update the checklist and the checkpoint after every completed phase.

## Checklist

- [x] Phase 1, step 1: Python 3.11 environment, pinned dependencies, Git, secrets example.
- [x] Phase 1, step 2: 30 synthetic documents, manifest, 60 validated labels.
- [x] Phase 2, step 3: deterministic ingestion and committed vector index.
- [x] Phase 2, step 4: authentication, access filtering, four search modes.
- [x] Phase 2, step 5: extractive answers, abstention, exact citations.
- [x] Phase 3, step 6: Streamlit demo, login/question/PDF citation/logout smoke check, and session-only document upload.
- [x] Phase 3, step 7: reproducible benchmark and 30 manual citation judgments.
- [x] Phase 3, step 8: 26 tests, README, final local server health check.
- [x] GitHub: publish standalone public repository and verify it.
- [ ] Streamlit deployment: deferred by the user until they test and understand the project.

## Current checkpoint

- Date: 2026-10-26 (Asia/Calcutta).
- State: Local project complete and public on GitHub. Streamlit deployment is deferred by the user.
- Environment: Python 3.11.15 in `.python/`, virtual environment in `.venv/`, Linux-compatible pinned `requirements.txt`. Local model files are in ignored `.model-cache/`.
- Verification completed: 30 bundled documents, 60 labels, 59 bundled chunks including a PDF page; deterministic repeated index build; four search modes; development-only threshold; 26 tests passed; dependency check passed; AppTest login, upload, search, page citation, logout, and account isolation; local Streamlit health endpoint returned HTTP 200. The upload tests cover TXT and PDF parsing, limits, and per-session search isolation. Final held-out **bundled-corpus** reranked metrics: recall@5 1.000, p95 455.2 ms, 30/30 supported citations, and negative abstention 0.800. These figures do not measure uploads and apply only to the synthetic corpus and measured machine.
- Upload cache fix: a user's still-running Streamlit process held a pre-upload `SearchEngine` instance and raised `AttributeError: embed_passages`. `streamlit_app.py` now keys its cached engine by retrieval/model/index source hashes, reloads those modules on a cache miss, and checks that upload methods exist. The full 24-test suite passed after the fix. Restarting the existing Streamlit process once is still the safest way to discard its old Python imports.
- Uploaded PDF answer fix: a real four-page Docker cheat sheet was previously collapsed into page-sized text, causing the same long answer for multiple questions. PDF uploads now split on visual paragraph groups while retaining heading/command line breaks and page citations. Exact uploaded headings resolve close reranker ties. A local, upload-only reranked check on the user's PDF returned distinct short entries for container deletion (`docker rm`), logs (`docker logs`), running containers (`docker ps`), and image deletion (`docker rmi`). The user's PDF remains untracked and must not be committed. The full 26-test suite passed after this fix. Existing app sessions must restart Streamlit and re-upload the PDF to get the new chunks.
- Local Git checkpoint: run `git log -1 --oneline` for the latest commit; the branch tracks `origin/main`.
- GitHub source: https://github.com/saidarshan20/GroundedDocs (`main`). The user created the empty public repository and the local committed tree was pushed successfully.
- Next: have the user restart Streamlit, re-upload their PDF, and check several questions locally. Deploy `streamlit_app.py` on Streamlit Community Cloud only after they ask to resume deployment; then verify the live URL and add it and screenshots to `README.md`.
- Open items: Streamlit deployment and actual signed-in portfolio screenshots. Local synthetic password hashes are in ignored `.streamlit/secrets.toml`; published demo passwords are in `scripts/setup_demo_secrets.py`. The computer-use skill forbids automating login dialogs, so signed-in screenshot capture needs a manual capture or another authorized, supported method.

## GitHub-only publication handoff

- User approved **public GitHub publication only** and explicitly deferred Streamlit deployment until they have tested and understood the project.
- An automatic approval review rejected opening the Firefox window because it currently displays an unrelated private Claude session. Do not retry that window or work around the rejection.
- The connected GitHub tools could not create a repository, so the user created public `saidarshan20/GroundedDocs` and supplied its URL.
- The local `main` branch was pushed to `origin/main`. GitHub publication is complete; Streamlit remains undeployed.

## Resume command

Open a shell in `GroundedDocs/`, read this file, run `git status --short`, and continue at the first unchecked step. Do not claim benchmark results until `results/benchmark.json` has been generated from the final index.
