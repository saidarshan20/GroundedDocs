"""GroundedDocs public demo. Run with: streamlit run streamlit_app.py"""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st
from grounded_docs.answer import answer_question
from grounded_docs.auth import authenticate
from grounded_docs.ingest import load_index
from grounded_docs.models import embedding_model, reranking_model
from grounded_docs.retrieve import MODES, SearchEngine
from grounded_docs.uploads import create_upload_chunks

ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))


@st.cache_resource(show_spinner="Loading local search models...")
def search_engine() -> SearchEngine:
    chunks, vectors, _ = load_index(ROOT)
    embedder = embedding_model(ROOT, CONFIG)
    reranker = reranking_model(ROOT, CONFIG)
    return SearchEngine(chunks, vectors, embedder, reranker, CONFIG["retrieval_candidates"], CONFIG["rrf_k"])


def main() -> None:
    st.set_page_config(page_title="GroundedDocs", page_icon="📚", layout="wide")
    st.title("GroundedDocs")
    st.caption("Evidence-first answers from a fictional document collection")
    if "principal" not in st.session_state:
        st.session_state.principal = None
    if st.session_state.principal is None:
        with st.form("login"):
            user = st.selectbox("Demo account", ["guest", "alice", "bob"])
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in")
        if submitted:
            principal = authenticate(user, password, dict(st.secrets["users"]))
            if principal:
                st.session_state.principal = principal
                st.rerun()
            else:
                st.error("Account or password was incorrect.")
        st.info("These are synthetic documents and public demo accounts. Credentials are in the project README.")
        return
    user = st.session_state.principal
    left, right = st.columns([4, 1])
    left.write(f"Signed in as **{user}**")
    if right.button("Log out"):
        st.session_state.clear()
        st.rerun()
    st.subheader("Your document")
    st.caption("Upload one text-based PDF, Markdown, or TXT file (up to 5 MB). It stays in this app session's memory, is not saved to disk, and is cleared on logout.")
    if "upload_widget_version" not in st.session_state:
        st.session_state.upload_widget_version = 0
    with st.form("upload"):
        uploaded = st.file_uploader("Choose a document", type=["pdf", "md", "txt"],
                                    key=f"session_upload_{st.session_state.upload_widget_version}")
        upload_submitted = st.form_submit_button("Use this document")
    if upload_submitted:
        if uploaded is None:
            st.warning("Choose a document first.")
        else:
            try:
                chunks = create_upload_chunks(uploaded.name, uploaded.getvalue(), user, CONFIG)
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
        if st.button("Clear uploaded document"):
            st.session_state.pop("upload_chunks", None)
            st.session_state.pop("upload_vectors", None)
            st.session_state.upload_widget_version += 1
            st.rerun()
        scope = st.radio("Search scope", ["Uploaded document only", "Uploaded document + sample library"],
                         horizontal=True)
    else:
        scope = "Sample library"
    mode = st.selectbox("Retrieval mode", MODES, index=3,
                        help="Reranked uses hybrid retrieval followed by a cross-encoder.")
    with st.form("question"):
        question = st.text_input("Ask a question about the documents")
        asked = st.form_submit_button("Find evidence")
    if asked:
        if not question.strip():
            st.warning("Enter a question first.")
        else:
            try:
                engine = search_engine()
                if has_upload:
                    engine = engine.with_upload(st.session_state.upload_chunks, st.session_state.upload_vectors,
                                                include_base=scope != "Uploaded document only")
                results = engine.search(question, user, mode, limit=10)
                threshold = CONFIG["abstention_threshold"] if mode == "reranked" else None
                outcome = answer_question(question, results, threshold)
            except (OSError, ValueError) as exc:
                st.error(f"Search could not start: {exc}")
            else:
                st.subheader("Answer")
                st.write(outcome["answer"])
                if outcome["citation"]:
                    citation = outcome["citation"]
                    st.caption(f"Source: {citation['title']} · {citation['location']} · {citation['chunk_id']}")
                    st.text_area("Supporting excerpt", outcome["excerpt"], height=130)
                with st.expander("Top results and scores"):
                    for item in outcome["trace"][:5]:
                        chunk = item["chunk"]
                        score_text = ", ".join(f"{key}={value:.3f}" for key, value in item["scores"].items())
                        st.markdown(f"**{chunk['title']}** · {chunk['chunk_id']} · {score_text}")
                        st.write(chunk["text"])
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
