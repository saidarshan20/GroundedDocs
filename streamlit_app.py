"""GroundedDocs public demo. Run with: streamlit run streamlit_app.py"""

from __future__ import annotations

import hashlib
import html
import importlib
import json
from pathlib import Path

import streamlit as st
from grounded_docs.answer import answer_question
from grounded_docs.auth import authenticate, demo_hashes
from grounded_docs import ingest as ingest_module
from grounded_docs import models as models_module
from grounded_docs import openrouter as openrouter_module
from grounded_docs import retrieve as retrieve_module
from grounded_docs import uploads as uploads_module

ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
ENGINE_CACHE_KEY = hashlib.sha256(b"".join((ROOT / name).read_bytes() for name in (
    "grounded_docs/ingest.py", "grounded_docs/models.py", "grounded_docs/retrieve.py",
    "grounded_docs/uploads.py",
    "config.json", "index/build_info.json",
))).hexdigest()


@st.cache_resource(show_spinner="Loading local search models...")
def _load_search_engine(cache_key: str) -> retrieve_module.SearchEngine:
    # Streamlit reruns this script without necessarily reloading imported modules.
    # A new source/index key must also create an instance of the current class.
    importlib.reload(ingest_module)
    importlib.reload(models_module)
    importlib.reload(retrieve_module)
    importlib.reload(uploads_module)
    chunks, vectors, _ = ingest_module.load_index(ROOT)
    embedder = models_module.embedding_model(ROOT, CONFIG)
    reranker = models_module.reranking_model(ROOT, CONFIG)
    return retrieve_module.SearchEngine(chunks, vectors, embedder, reranker,
                                        CONFIG["retrieval_candidates"], CONFIG["rrf_k"])


def search_engine() -> retrieve_module.SearchEngine:
    engine = _load_search_engine(ENGINE_CACHE_KEY)
    if not hasattr(engine, "embed_passages") or not hasattr(engine, "with_upload"):
        _load_search_engine.clear()
        engine = _load_search_engine(ENGINE_CACHE_KEY)
    return engine


def _style_workspace() -> None:
    """Style only GroundedDocs-owned markup; leave Streamlit widget internals alone."""
    dark = st.context.theme.type == "dark"
    palette = ({"card": "#172637", "border": "#304459", "muted": "#A3B7C5",
                "text": "#E7F0F4", "accent": "#70E0D4", "empty": "#132535"}
               if dark else
               {"card": "#FFFFFF", "border": "#DFE8EE", "muted": "#64788C",
                "text": "#14273B", "accent": "#147E78", "empty": "#F9FCFC"})
    variables = "; ".join(f"--gd-{name}: {value}" for name, value in palette.items())
    st.markdown(f"<style>:root {{{variables};}}</style>", unsafe_allow_html=True)
    st.markdown("""
    <style>
      .gd-hero { position: relative; overflow: hidden; padding: 2.5rem 2.8rem;
        border-radius: 1.3rem; color: #f5fbff;
        background: radial-gradient(circle at 88% 18%, rgba(48, 213, 196, .24), transparent 31%),
                    linear-gradient(135deg, #102238 0%, #173954 100%);
        box-shadow: 0 18px 45px rgba(16, 34, 56, .12); margin-bottom: 1.25rem; }
      .gd-hero::after { content: ''; position: absolute; right: -4rem; bottom: -8rem;
        width: 21rem; height: 21rem; border: 1px solid rgba(185, 240, 235, .25);
        border-radius: 50%; box-shadow: 0 0 0 3rem rgba(185, 240, 235, .055),
        0 0 0 6rem rgba(185, 240, 235, .045); pointer-events: none; }
      .gd-kicker { color: #6fe1d4; font-size: .73rem; font-weight: 800;
        letter-spacing: .16em; text-transform: uppercase; margin-bottom: .8rem; }
      .gd-hero h1 { color: #fff; font-size: clamp(2rem, 4vw, 3.4rem);
        line-height: 1.08; letter-spacing: -.045em; max-width: 13ch;
        margin: 0 0 .8rem; }
      .gd-hero p { color: #d4e2eb; max-width: 40rem; font-size: 1.05rem;
        line-height: 1.6; margin: 0; }
      .gd-stat { min-height: 6.3rem; padding: 1rem 1.15rem;
        border: 1px solid var(--gd-border); border-radius: 1rem; background: var(--gd-card); }
      .gd-stat-label { color: var(--gd-muted); font-size: .68rem; font-weight: 800;
        letter-spacing: .13em; text-transform: uppercase; }
      .gd-stat-value { color: var(--gd-text); font-size: 1.05rem; font-weight: 750;
        margin-top: .45rem; line-height: 1.25; }
      .gd-stat-note { color: var(--gd-muted); font-size: .78rem; margin-top: .28rem; }
      .gd-brand { font-size: 1.22rem; font-weight: 800; letter-spacing: -.04em;
        color: var(--gd-text); margin: .3rem 0 .2rem; }
      .gd-brand-mark { color: var(--gd-accent); margin-right: .38rem; }
      .gd-side-note { color: var(--gd-muted); font-size: .84rem; line-height: 1.5;
        margin-bottom: 1rem; }
      .gd-section-label { color: var(--gd-accent); font-size: .73rem; font-weight: 800;
        letter-spacing: .13em; text-transform: uppercase; margin: .2rem 0 .6rem; }
      .gd-empty { text-align: center; border: 1px dashed var(--gd-border); border-radius: 1.1rem;
        padding: 2.5rem 1.5rem; background: var(--gd-empty); color: var(--gd-muted); }
      .gd-empty strong { display: block; color: var(--gd-text); font-size: 1.25rem;
        margin-bottom: .35rem; }
      @media (max-width: 700px) { .gd-hero { padding: 1.8rem 1.5rem; }
        .gd-hero::after { opacity: .4; } }
    </style>
    """, unsafe_allow_html=True)


def _stat(label: str, value: str, note: str) -> None:
    st.markdown(
        f'<div class="gd-stat"><div class="gd-stat-label">{html.escape(label)}</div>'
        f'<div class="gd-stat-value">{html.escape(value)}</div>'
        f'<div class="gd-stat-note">{html.escape(note)}</div></div>',
        unsafe_allow_html=True,
    )


def _hero(login: bool = False) -> None:
    headline = "Find the answer. Show the source." if login else "Answers you can verify."
    description = ("Search documents, inspect the evidence, and see how each answer was found."
                   if login else "Ask a question, compare retrieval methods, and follow every answer back to its document.")
    st.markdown(f'<div class="gd-hero"><div class="gd-kicker">GroundedDocs / evidence workspace</div>'
                f'<h1>{headline}</h1><p>{description}</p></div>', unsafe_allow_html=True)


def main() -> None:
    st.set_page_config(page_title="GroundedDocs | Evidence workspace", page_icon="◈",
                       layout="wide", initial_sidebar_state="expanded")
    _style_workspace()
    if "principal" not in st.session_state:
        st.session_state.principal = None
    if st.session_state.principal is None:
        left, right = st.columns([1.25, 1], gap="large")
        with left:
            _hero(login=True)
            st.markdown("#### What you can explore")
            st.write("Search a fictional document library, upload one of your own text-based files, and inspect exact citations.")
            st.caption("The demo accounts show how document permissions change search results.")
            st.caption("Appearance: open the ⋮ menu at the top right and choose Theme → Light, Dark, or System.")
        with right:
            with st.container(border=True):
                st.markdown('<div class="gd-section-label">Workspace access</div>', unsafe_allow_html=True)
                st.subheader("Sign in to explore")
                with st.form("login", border=False):
                    user = st.selectbox("Demo account", ["guest", "alice", "bob"])
                    password = st.text_input("Password", type="password")
                    submitted = st.form_submit_button("Sign in", use_container_width=True)
                st.caption("Demo passwords are published in the README. Use these accounts only with suitable test documents.")
        if submitted:
            try:
                hashes = demo_hashes(ROOT, st.secrets)
            except ValueError as exc:
                st.error(str(exc))
                return
            principal = authenticate(user, password, hashes)
            if principal:
                st.session_state.principal = principal
                st.rerun()
            else:
                st.error("Account or password was incorrect.")
        return
    user = st.session_state.principal
    with st.sidebar:
        st.markdown('<div class="gd-brand"><span class="gd-brand-mark">◈</span> GroundedDocs</div>',
                    unsafe_allow_html=True)
        st.markdown('<div class="gd-side-note">A small workspace for answers with inspectable sources.</div>',
                    unsafe_allow_html=True)
        account_left, account_right = st.columns([2, 1])
        account_left.caption(f"SIGNED IN · {user.upper()}")
        if account_right.button("Log out"):
            st.session_state.clear()
            st.rerun()
        st.divider()
        st.markdown("#### 01 · Your source")
        st.caption(f"PDF, Markdown, or TXT · 5 MB · {uploads_module.MAX_UPLOAD_CHUNKS} passages")
        st.caption("Uploads stay in this app session's memory and are cleared on logout.")
        if "upload_widget_version" not in st.session_state:
            st.session_state.upload_widget_version = 0
        with st.form("upload"):
            uploaded = st.file_uploader("Choose a document", type=["pdf", "md", "txt"],
                                        key=f"session_upload_{st.session_state.upload_widget_version}")
            upload_submitted = st.form_submit_button("Use this document", use_container_width=True)
        if upload_submitted:
            if uploaded is None:
                st.warning("Choose a document first.")
            else:
                try:
                    chunks = uploads_module.create_upload_chunks(uploaded.name, uploaded.getvalue(), user, CONFIG)
                    with st.spinner("Indexing your document locally..."):
                        vectors = search_engine().embed_passages([chunk["text"] for chunk in chunks])
                except (OSError, ValueError) as exc:
                    st.error(f"Upload could not be indexed: {exc}")
                else:
                    st.session_state.upload_chunks = chunks
                    st.session_state.upload_vectors = vectors
                    st.success(f"Ready: {chunks[0]['title']} ({len(chunks)} searchable passages).")
        has_upload = bool(st.session_state.get("upload_chunks"))
        if has_upload:
            chunks = st.session_state.upload_chunks
            st.info(f"Current upload: {chunks[0]['title']} ({len(chunks)} passages).")
            if st.button("Clear uploaded document", use_container_width=True):
                st.session_state.pop("upload_chunks", None)
                st.session_state.pop("upload_vectors", None)
                st.session_state.upload_widget_version += 1
                st.rerun()
            scope = st.radio("Search scope", ["Uploaded document only", "Uploaded document + sample library"])
        else:
            scope = "Sample library"
            st.caption("Searching the fictional sample library. Upload a file to change the source.")
        st.divider()
        st.markdown("#### 02 · Search options")
        mode = st.selectbox("Retrieval mode", retrieve_module.MODES, index=3,
                            help="Reranked uses hybrid retrieval followed by a cross-encoder.")
        router_key = openrouter_module.api_key(ROOT, dict(st.secrets))
        use_openrouter = st.checkbox("Organize answer with OpenRouter (free model)", value=False,
                                     disabled=not router_key)
        if router_key:
            st.caption("Optional: sends your question and up to 15 short permitted excerpts to OpenRouter. Use only suitable documents.")
        else:
            st.caption("Add OPENROUTER_API_KEY to the local .env file to enable this option.")
        st.divider()
        st.caption("Appearance · ⋮ menu (top right) → Theme → Light / Dark / System")

    _hero()
    scope_label = {"Sample library": "Sample library", "Uploaded document only": "Your upload",
                   "Uploaded document + sample library": "Upload + library"}[scope]
    source_note = (f"{len(st.session_state.upload_chunks)} passages ready" if has_upload
                   else "Fictional demo documents")
    display_mode = {"bm25": "BM25 keywords", "dense": "Dense vectors", "hybrid": "Hybrid fusion",
                    "reranked": "Reranked hybrid"}[mode]
    status_cols = st.columns(3, gap="medium")
    with status_cols[0]:
        _stat("Source", scope_label, source_note)
    with status_cols[1]:
        _stat("Search method", display_mode, "Switch modes in the sidebar")
    with status_cols[2]:
        _stat("Answer style", "AI-selected excerpts" if use_openrouter else "Exact source extract",
              "Citations stay visible")

    st.write("")
    with st.container(border=True):
        st.markdown('<div class="gd-section-label">Ask a question</div>', unsafe_allow_html=True)
        st.markdown("### Search your documents")
        with st.form("question", border=False):
            question = st.text_input("Ask a question about the documents",
                                     placeholder="e.g. How many pages may a guest print per visit?")
            asked = st.form_submit_button("Find evidence", use_container_width=True)
        st.caption("The answer is copied from a permitted source. Open the evidence panel to check it.")
    view_key = (user, st.session_state.upload_chunks[0]["doc_id"] if has_upload else None,
                scope, mode, use_openrouter)
    if st.session_state.get("last_answer", {}).get("view_key") != view_key:
        st.session_state.pop("last_answer", None)
    if asked:
        st.session_state.pop("last_answer", None)
        if not question.strip():
            st.warning("Enter a question first.")
        else:
            try:
                with st.spinner("Searching permitted documents..."):
                    engine = search_engine()
                    if has_upload:
                        engine = engine.with_upload(st.session_state.upload_chunks, st.session_state.upload_vectors,
                                                    include_base=scope != "Uploaded document only")
                    results = engine.search(question, user, mode, limit=10)
                    threshold = CONFIG["abstention_threshold"] if mode == "reranked" else None
                    outcome = answer_question(question, results, threshold)
                    organized = None
                    router_error = None
                    if use_openrouter and not outcome["abstained"]:
                        try:
                            organized = openrouter_module.organize_evidence(
                                question, results, router_key,
                                outcome["citation"]["chunk_id"] if outcome["citation"] else None)
                        except ValueError as exc:
                            router_error = str(exc)
            except (OSError, ValueError) as exc:
                st.error(f"Search could not start: {exc}")
            else:
                st.session_state.last_answer = {"view_key": view_key, "question": question.strip(),
                                                "outcome": outcome, "organized": organized,
                                                "router_error": router_error}
    stored = st.session_state.get("last_answer")
    st.write("")
    if stored:
        outcome = stored["outcome"]
        organized = stored["organized"]
        router_error = stored["router_error"]
        answer_col, evidence_col = st.columns([1.5, 1], gap="large")
        with answer_col, st.container(border=True):
            st.markdown('<div class="gd-section-label">Result</div>', unsafe_allow_html=True)
            st.markdown("### Answer")
            st.caption(f"QUESTION · {stored['question']}")
            if outcome["abstained"]:
                st.info(outcome["answer"])
            else:
                if router_error:
                    st.warning(f"{router_error} Showing the local evidence instead.")
                if organized:
                    for position, entry in enumerate(organized, 1):
                        st.caption(f"SOURCE EXCERPT {position:02d}")
                        st.code(entry["quote"], language=None)
                    st.caption("OpenRouter selected excerpt IDs; every word shown above comes from the cited sources.")
                else:
                    if "\n" in outcome["answer"]:
                        st.code(outcome["answer"], language=None)
                    else:
                        st.write(outcome["answer"])
        with evidence_col, st.container(border=True):
            st.markdown('<div class="gd-section-label">Provenance</div>', unsafe_allow_html=True)
            st.markdown("### Inspect the source")
            if organized:
                for position, entry in enumerate(organized, 1):
                    st.caption(f"Source {position:02d}: {entry['title']} · {entry['location']} · {entry['chunk_id']}")
                    with st.expander(f"Supporting passage {position:02d}"):
                        st.text(entry["excerpt"])
            elif outcome["citation"]:
                citation = outcome["citation"]
                st.caption(f"Source: {citation['title']} · {citation['location']} · {citation['chunk_id']}")
                st.text_area("Supporting excerpt", outcome["excerpt"], height=180)
            else:
                st.caption("No source was cited because the evidence did not pass the answer check.")
        with st.expander("Top results and scores"):
            for item in outcome["trace"][:5]:
                chunk = item["chunk"]
                score_text = ", ".join(f"{key}={value:.3f}" for key, value in item["scores"].items())
                st.markdown(f"**{chunk['title']}** · {chunk['chunk_id']} · {score_text}")
                st.write(chunk["text"])
    else:
        st.markdown('<div class="gd-empty"><strong>Your evidence will appear here.</strong>'
                    'Choose a source, ask a question, and inspect the cited passage beside the answer.</div>',
                    unsafe_allow_html=True)
    with st.expander("How GroundedDocs finds an answer"):
        st.markdown("**1. Filter** documents by the signed-in account. **2. Search** with keywords and meaning vectors. "
                    "**3. Rerank** likely passages if selected. **4. Extract** source text or abstain. "
                    "**5. Cite** the exact document location. OpenRouter can optionally choose among prepared excerpts.")
    benchmark_path = ROOT / "results" / "benchmark.json"
    if benchmark_path.exists():
        benchmark = json.loads(benchmark_path.read_text(encoding="utf-8"))
        with st.expander("Measured benchmark"):
            st.caption(f"Bundled sample corpus only (excludes your upload). Measured on {benchmark['environment']['platform']} with {benchmark['question_counts']['held_out_answerable']} held-out answerable questions")
            st.table({mode: {key: value for key, value in row.items() if key in {"recall_at_5", "recall_at_10", "p95_ms"}}
                      for mode, row in benchmark["aggregate"].items()})
            st.write(benchmark["cost_note"])
            if not benchmark["citation_judgments_complete"]:
                st.caption("Citation correctness is pending manual review.")


if __name__ == "__main__":
    main()
