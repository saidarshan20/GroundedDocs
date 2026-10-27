  

# GroundedDocs — end-to-end build guide

## 1. What we're building

GroundedDocs is an evidence-first document question-answering app for people who need to find an answer and inspect its source. It searches a bundled collection or one document uploaded for the current session with keyword and semantic retrieval, combines the results, reranks them, and returns a short extractive answer with a citation. Each signed-in user can search only documents granted to that account, and an upload stays in its owner's app session. An optional OpenRouter step organizes exact source quotes after access filtering; its output is checked against the cited passage. A reproducible benchmark on the bundled collection measures the local extractive path.

## 2. What to expect

### Final features and finished output

- A live Streamlit demo with sign-in, a question box, an answer or explicit abstention, cited excerpts, document/page references, and a compact retrieval trace showing the top results and scores.
- A command-line ingestion pipeline for local Markdown, plain text, and text-based PDF files. It creates stable document/chunk IDs, records access grants, and precomputes embeddings. Scanned PDFs and OCR are excluded.
- A Streamlit uploader for one PDF, Markdown, or TXT file at a time (5 MB and 256 searchable passages maximum). Its chunks and vectors stay in session memory, can be searched alone or with the bundled library, and are cleared on logout; uploads are excluded from the benchmark.
- Four comparable retrieval modes: BM25, dense vectors, reciprocal-rank fused hybrid, and hybrid followed by cross-encoder reranking.
- An optional OpenRouter answer organizer using `nvidia/nemotron-3.5-super-vl:free`; it selects short verbatim quotes from permitted evidence, and the app validates them before display.
- Server-side access filtering before any ranking, answer selection, result display, or benchmark scoring. Synthetic Alice, Bob, and guest accounts make the behavior testable.
- A labeled question set, repeatable benchmark command, machine-readable results, a generated README results table, and automated checks for access leaks and citations. Report measured numbers only; never invent results.
- A public GitHub repository containing source, synthetic sample documents, labels, build instructions, screenshots, and a link to the deployed demo.

### Tech stack

| Choice                             | Reason                                                                          |
| ---------------------------------- | ------------------------------------------------------------------------------- |
| Python 3.11                        | One language for document processing, retrieval, evaluation, and UI.            |
| Streamlit                          | Fast Python UI with free Community Cloud deployment.                            |
| `pypdf`                          | Extract text and page numbers from text-based PDFs without an external service. |
| `rank-bm25`                      | Implements the keyword baseline directly, making it easy to compare.            |
| FastEmbed + ONNX Runtime           | Runs embedding and reranking models locally on CPU without API charges.         |
| `BAAI/bge-small-en-v1.5`         | Compact English embedding model for the dense baseline.                         |
| `Xenova/ms-marco-MiniLM-L-6-v2`  | Small cross-encoder for reranking the hybrid shortlist.                         |
| NumPy + JSON/JSONL                 | Small-corpus vector scoring and inspectable, portable index/benchmark files.    |
| `pytest`                         | Checks access control, retrieval behavior, and citation integrity.              |
| GitHub + Streamlit Community Cloud | Free source hosting and a shareable live app.                                   |

Use a fresh virtual environment and commit a fully pinned `requirements.txt` from it. Commit the generated index and model version identifiers; rebuild the index whenever documents, grants, chunking, or embedding model change.

**Estimated build time:** 24–32 focused hours for the original local build, plus the optional API extension. **Out of scope:** unverified LLM-generated prose, OCR, arbitrary external websites, production identity management, large-scale vector databases, and durable storage for uploads or edits made in the live demo. Displayed answer text is copied from permitted evidence; if the system has no sufficiently relevant permitted evidence, it abstains.

## 3. Build steps

### Fixed design and project layout

Use a standalone Git repository rooted at `GroundedDocs/`. Keep the synthetic corpus immutable in Git. Create 30 short, original English documents about a fictional organization's policies and operations: 12 readable by all three accounts, 9 granted only to Alice, and 9 granted only to Bob. Publish no real confidential material. Public demo passwords are for trying the synthetic access policy; they do not protect secrets because anyone can read them in the README.

The application has three principals: `guest`, `alice`, and `bob`. Store a password hash for each account in Streamlit secrets, never plaintext in code or Git. Each document has an explicit `allowed_users` list; there is no implicit administrator bypass. The retrieval function accepts the authenticated principal, obtains the permitted chunk IDs, and scores **only** that subset. Caches that contain query results must include the principal and index version in their key. The UI must call this same retrieval function and must not expose a file browser or download link that bypasses it.

An uploaded file belongs only to the current Streamlit session, regardless of whether another visitor signs in with the same public demo account. Accept one `.pdf`, `.md`, or `.txt` file of at most 5 MB and 256 searchable passages. Decode text as UTF-8, reject encrypted/scanned PDFs, sanitize the displayed filename, and give its chunks the current principal as their only access grant. Embed it with the pinned model and keep its chunks/vectors in session memory; never write them to disk or a global cache. Search it alone by default, with an option to combine it with the bundled collection. Clearing the upload or logging out removes it. The committed benchmark continues to evaluate only the bundled collection.

Use 180-word chunks with 40-word overlap, never crossing a PDF page or a Markdown/text section boundary. Normalize whitespace, retain the original text, and assign `doc_id` from the manifest plus `chunk_id = doc_id:page_or_section:ordinal`. For each chunk store document title, relative source path, page number when relevant, section, text, allowed users, and SHA-256 of the text. Precompute normalized float32 embeddings for all chunks. BM25 tokenization is lowercase alphanumeric words; dense score is cosine similarity. For each query, rank permitted chunks independently by BM25 and dense score, take each top 20, and fuse their ranks with reciprocal rank fusion `sum(1/(60 + rank))`, with ranks starting at 1. Cross-encode the hybrid top 20 and show the top 5. Break ties by `chunk_id` so results are deterministic. The first cited answer is the highest-ranked sentence in the top 3 reranked chunks using non-stopword question-token overlap; return at most two sentences from the same chunk. Abstain if the top reranker score is below a threshold selected only on the development labels; record that threshold in `config.json`. A citation always points to the exact chunk that contains the extracted sentence. Never combine fragments into a sentence the source did not say.

```text
GroundedDocs/
├── GroundedDocs.md             # this guide
├── README.md                   # portfolio page and Cloud app entry metadata only if needed
├── streamlit_app.py            # login and question UI
├── requirements.txt            # pinned direct and transitive dependencies
├── .gitignore
├── .streamlit/
│   └── secrets.example.toml    # names and placeholders; never real hashes
├── config.json                 # model IDs, retrieval settings, abstention threshold
├── corpus/
│   ├── manifest.jsonl          # doc ID, title, path, grants
│   └── docs/                   # original synthetic .md/.txt/.pdf documents
├── index/
│   ├── chunks.jsonl            # chunk metadata and text
│   ├── embeddings.npy          # rows align with chunks.jsonl
│   └── build_info.json          # source hashes and embedding model ID
├── labels/
│   ├── questions.jsonl         # account, question, relevant doc IDs, expected answerability
│   └── rubric.md               # labeling and citation judgment rules
├── grounded_docs/
│   ├── ingest.py
│   ├── uploads.py
│   ├── auth.py
│   ├── retrieve.py
│   ├── answer.py
│   ├── openrouter.py
│   └── evaluate.py
├── scripts/
│   ├── build_index.py
│   └── run_benchmark.py
├── results/
│   ├── benchmark.json
│   └── benchmark.md
├── tests/
│   ├── test_access.py
│   ├── test_retrieval.py
│   ├── test_citations.py
│   └── test_uploads.py
└── assets/                     # screenshots and short demo GIF
```

### Phase 1 — setup and corpus

**Step 1: Initialize the environment.** Create the layout above, a Git repo, and a Python 3.11 virtual environment. Install `streamlit`, `pypdf`, `rank-bm25`, `fastembed`, `numpy`, `pytest`, and `bcrypt` into the fresh environment, then freeze all installed versions into `requirements.txt`. Add `.venv/`, `.streamlit/secrets.toml`, caches, and local benchmark scratch files to `.gitignore`. Files: repository root, `requirements.txt`, `.gitignore`, `.streamlit/secrets.example.toml`. **Done when:** the virtual environment runs `python --version` as 3.11.x, `pip check` passes, and no real secret is tracked.

```powershell
cd GroundedDocs
git init
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install streamlit pypdf rank-bm25 fastembed numpy pytest bcrypt
python -m pip freeze > requirements.txt
python -m pip check
```

On macOS/Linux, use `python3.11 -m venv .venv` and `source .venv/bin/activate`; the remaining Python commands are the same. Required secrets in `.streamlit/secrets.toml` and Cloud settings are `[users] guest_hash`, `alice_hash`, and `bob_hash` (bcrypt hashes). Generate each hash locally with `bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()`; put only placeholder strings in `secrets.example.toml`. The local extractive path needs no API key. For optional answer organization, add `OPENROUTER_API_KEY` to an ignored `.env` file, an environment variable, or a top-level Cloud secret. Give the sample account passwords to demo viewers in the README, and use only fictional data.

**Step 2: Write the source corpus and labels.** Author the 30 synthetic documents and `corpus/manifest.jsonl` with the exact grants above. Include questions whose wording differs from the source wording, exact-keyword questions, and negative cases. Create `labels/questions.jsonl` with 60 records: 40 answerable for the specified account, 10 whose relevant document exists but is forbidden to that account, and 10 genuinely unanswerable. Each record has `question_id`, `user_id`, `question`, `relevant_doc_ids` (empty for the last 20), and `answerable`; for forbidden cases also record `forbidden_doc_ids` for the access audit. Split 10 answerable plus 5 negative questions for development and the remaining 30 answerable plus 15 negative questions for a held-out test; keep the split in each record. Files: `corpus/`, `labels/`. **Done when:** a validation script confirms unique IDs, valid paths/grants, the exact 60-question counts, and no missing relevant document.

### Phase 2 — ingestion and retrieval

**Step 3: Build the index.** Implement document loading, whitespace cleanup, deterministic chunking, PDF page retention, manifest validation, embedding generation, and `build_info.json` fingerprinting. Make `scripts/build_index.py` rebuild from scratch in manifest order; fail on empty PDF extraction, duplicate IDs, missing grants, or changed model settings. Files: `grounded_docs/ingest.py`, `scripts/build_index.py`, `index/`, `config.json`. Command: `python -m scripts.build_index`. **Done when:** two consecutive builds produce identical chunk IDs/text hashes, `embeddings.npy` row count equals the chunk count, and no chunk crosses a page or section boundary.

**Step 4: Add authorization and four search modes.** Verify a submitted password against the corresponding bcrypt hash, keep only the principal in Streamlit session state, and clear it on logout. Implement the permitted-chunk filter in the core retrieval API, then BM25, dense cosine, hybrid fusion, and reranking as specified above. Cache only shared immutable models/index data; do not share principal-specific search results between users. Files: `grounded_docs/auth.py`, `grounded_docs/retrieve.py`, `config.json`, `tests/test_access.py`, `tests/test_retrieval.py`. **Done when:** every mode returns only permitted chunks, Alice and Bob get distinct results on a restricted query, and a query with no permitted hit returns an empty list.

For local login, read `GroundedDocs/.streamlit/secrets.toml` by the project's absolute path so launching Streamlit from another folder cannot select unrelated demo hashes. If that file is absent, use Streamlit's configured secrets for Cloud. A missing or malformed secrets table is a setup error, not an incorrect-password result.

**Step 5: Produce grounded answers and citations.** Select the best sentence from permitted reranked chunks, apply the development-set abstention threshold, and format a citation with title, page or section, and chunk ID. Return the answer, exact supporting excerpt, and retrieval trace as structured data so UI and tests use the same result. For missing/weak evidence, return “I couldn't find enough evidence in documents you can access.” Files: `grounded_docs/answer.py`, `tests/test_citations.py`. **Done when:** each non-abstaining answer is a verbatim substring of its cited permitted chunk and an access-denied or unanswerable query does not cite a forbidden document.

### Phase 3 — demo and evaluation

**Step 6: Build the demo.** Create a login screen, a one-file upload form, and a question form. Index uploads in session memory, default to searching the upload alone, and offer a combined search option; clear uploaded search data on logout. Show answer/abstention, citation and source excerpt, and an expandable top-5 trace with retrieval-mode scores; include a mode selector for comparing baselines, but use reranked hybrid as the default answer mode. Show the benchmark summary from committed `results/benchmark.json` and label it as bundled-corpus-only. Cache models with `st.cache_resource`, load the committed index once, and avoid rebuilding it on each Streamlit rerun. Files: `streamlit_app.py`, `grounded_docs/uploads.py`, `.streamlit/secrets.example.toml`, `assets/`, `tests/test_uploads.py`. Command: `streamlit run streamlit_app.py`. **Done when:** all three accounts can sign in, search their allowed bundled sources, upload and search their own document, clear it, and log out; a fresh local launch does not require an API key.

**Step 6a: Add optional grounded OpenRouter organization.** Keep the local answer and abstention as the baseline. Add an off-by-default checkbox that explains it sends the question and up to five already-permitted passages to OpenRouter. Load `OPENROUTER_API_KEY` from the environment, ignored local `.env`, or top-level Streamlit secret; use `nvidia/nemotron-3.5-super-vl:free` via `POST https://openrouter.ai/api/v1/chat/completions`. Ask for JSON containing one to three evidence IDs and exact contiguous source quotes. Reject the entire response if a quote is missing, altered, duplicated, uncited, or longer than 600 characters; construct citations from local chunk metadata. Never call the API after abstention. Retry one transient 429/5xx error, then fall back to the local answer on any failure. Files: `.gitignore`, `grounded_docs/openrouter.py`, `streamlit_app.py`, `tests/test_openrouter.py`, `README.md`. **Done when:** the real API returns validated quotes on a synthetic example, tests reject invented text and invalid IDs, `.env` is ignored, and the app works without an API key.

**Step 7: Benchmark and audit.** Run all four modes on the same held-out questions and permitted corpus. Define recall@5 and recall@10 as the fraction of the 30 held-out answerable questions with any labeled relevant **document** in the top k chunks; count each question once. Report citation correctness for the reranked-answer path as the number of non-abstaining held-out answers whose cited excerpt actually supports the answer, divided by all non-abstaining held-out answers; judge these manually with `labels/rubric.md` and record each judgment. Also report coverage (non-abstentions / 30) and abstention accuracy on the 15 negative questions. Warm each model once, then run three timed passes over held-out questions, recording retrieval-plus-answer wall time with `perf_counter`; exclude startup/index loading and report p95 by mode plus machine CPU/RAM/Python versions. Report external API cost per query as `$0.00` for this **local baseline** because inference is local; the optional OpenRouter path is outside this benchmark. Host CPU/electricity is excluded. Files: `grounded_docs/evaluate.py`, `scripts/run_benchmark.py`, `results/benchmark.json`, `results/benchmark.md`, `labels/rubric.md`. Command: `python -m scripts.run_benchmark`. **Done when:** raw per-query results, aggregate table, timing method, model IDs, corpus/index fingerprints, and manual citation judgments reproduce the README table without hand-editing values.

**Step 8: Final tests and release check.** Run `python -m pytest`, rebuild the index, rerun the benchmark, and run the app locally. Test all four modes with Alice/Bob/guest, including exact and paraphrased questions, forbidden-document questions, unanswerable questions, empty input, and repeated requests across account changes. Inspect one PDF page citation and one Markdown section citation manually. Files: `tests/`, `index/`, `results/`, `README.md`. **Done when:** tests pass, no forbidden chunk ID/text appears in answer, trace, logs, or cached results, benchmark files match the final index fingerprint, and the README contains only measured claims.

## 4. Beginner walkthrough

Think of ingestion as preparing a searchable card catalog. The script reads each document, breaks it into small passages, attaches the document's title, location, and allowed users, then gives each passage a numerical vector that captures its meaning. The keyword index keeps the passage words; the vector file keeps those meaning vectors. Both are built ahead of time so asking a question is fast.

When a person signs in, the app identifies their account. The search code first keeps only passages that account may read. It then asks two different searchers to rank them: BM25 rewards matching words, while dense search compares the question's vector with passage vectors to catch paraphrases. Reciprocal rank fusion combines those two lists without assuming their scores use the same scale. A cross-encoder reads the question and each of the 20 shortlisted passages together and reranks them more carefully.

An uploaded document follows the same chunk-and-embed process, but only in memory for that app session. By default, a question searches just that upload, which makes it easy to check its answers. The user can choose to search the upload and bundled collection together. Logout clears the upload; another session cannot see it, even if it uses the same demo account. If deployed later, uploading would transmit the file to that app host, so use only documents appropriate for that host.

The answer step copies one or two useful sentences from a top permitted passage and links them to that passage's exact source. If its evidence score is too weak, it says it cannot answer. This extractive approach makes citations easy to inspect, but it will not synthesize an answer spread across several documents. The benchmark uses questions we label in advance to test which search method finds the right document, whether the displayed citation really supports an answer, how long queries take, and whether an account ever sees restricted material. A good benchmark may show that a simpler mode wins on some questions; report that plainly.

If the user turns on OpenRouter organization, the app sends only the question and the top permitted passages after the local answer passes abstention. The model chooses exact snippets and their passage IDs, then the app checks each snippet against the original passage and creates the citation. The model cannot add wording from its own knowledge to the displayed answer because changed or invented text fails this check. If the free endpoint is unavailable or the format fails validation, the user sees the local extractive answer. The model may still choose a less relevant quote, and the source itself can be wrong, so inspect the cited passage.

## 5. Deployment and portfolio

**Best free live host: [Streamlit Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud).** It deploys from GitHub for free. Its resource limits can change, and idle apps hibernate, so keep the sample corpus small, cache the ONNX models, and expect a cold start. Git remains the source of truth; session uploads are temporary and do not survive logout or server restart. Uploading to a hosted app sends the file to that host. [Cloud deployment steps](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy) and [secret handling](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management) are documented by Streamlit.

1. Finish local tests and benchmark, commit `requirements.txt`, corpus, index, labels, results, and app code. Check `git status` and `git ls-files` to ensure `.streamlit/secrets.toml` and real passwords are absent.
2. Create a **public, standalone** GitHub repository named `GroundedDocs` and push the contents of this folder as its repository root. A standalone repo avoids ambiguous dependency and path discovery when deploying from a larger resume-project workspace.
3. Sign in at `https://share.streamlit.io`, connect GitHub, select **Create app** → **Yup, I have an app**, choose that repository and branch, and set the entrypoint to `streamlit_app.py`.
4. Open **Advanced settings**, select Python **3.11**, and paste the real `[users]` bcrypt hashes from local `secrets.toml` into **Secrets**. Add a top-level `OPENROUTER_API_KEY` only if the optional organizer should be available online. Choose a memorable subdomain and deploy. Never paste plaintext passwords or the API key into Git.
5. Open the public URL, wake the app if it has hibernated, sign in with each published synthetic demo account, run an allowed and a forbidden question, and verify the citations and benchmark panel. If build/runtime fails, use the app's **Manage app** logs; reduce corpus or model memory only after measuring the failure, then rebuild and rebenchmark.

**README outline:** problem and one screenshot; live demo and synthetic login credentials; 60-second usage; architecture/data flow; access-control design and its public-demo limitation; optional OpenRouter consent and exact-quote validation; corpus and labeling method; local-path benchmark table with BM25/dense/hybrid/reranked recall@5 and @10, p95 latency, citation correctness/coverage, and `$0.00` external API cost for that path; environment and reproducibility commands; limitations; license. Link the raw `results/benchmark.json` and explain that public example passwords do not secure confidential data.

**Demo assets:** a screenshot of the answer with its source excerpt and page/section; a side-by-side search-mode result comparison; a short recording that signs in as Alice, finds her document, switches to Bob, and shows that the same restricted document is absent; and a benchmark table screenshot. Hide typed passwords in recordings.

**Resume bullets** (replace bracketed values with actual measured results):

- Built GroundedDocs, a document Q&A app with BM25, dense retrieval, rank fusion, cross-encoder reranking, and source-linked extractive answers across [N] indexed documents.
- Created a reproducible [N]-question benchmark comparing four retrieval modes; achieved [measured recall@5] and [measured p95 latency] on the held-out set, with [measured citation correctness] citation correctness.
- Implemented per-user document filtering and automated access-leak tests for three demo accounts; deployed a public Streamlit demo with `$0.00` external API cost per query.

## Assumptions

- The five numbered entries in `1st_step.txt` are priorities, so item 1, GroundedDocs, is the only project covered here.
- The original request specified no dataset, document domain, answer-generation service, or host. The later user request specified OpenRouter and the Nemotron 3.5 Super VL family; use its distinct `:free` route only for optional exact-quote selection. The bundled corpus remains fictional and the benchmark remains local-only.
- The target is a small, portfolio-scale English corpus rather than a production confidential document service. Public synthetic credentials demonstrate filtering behavior but provide no real secrecy.
- Measured benchmark values cannot be known before implementation. The guide fixes the measurement protocol and leaves numbers as results to be produced, not promises.
