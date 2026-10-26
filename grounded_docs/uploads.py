"""Turn one session-only uploaded document into access-tagged search chunks."""

from __future__ import annotations

import hashlib
import io
import re
from pathlib import Path
from typing import Iterator

from grounded_docs.ingest import USERS, chunk_text, normalize, sha256

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_UPLOAD_CHUNKS = 120
ALLOWED_SUFFIXES = frozenset({".pdf", ".md", ".txt"})


def safe_filename(name: str) -> str:
    base = name.replace("\\", "/").split("/")[-1]
    clean = re.sub(r"[^A-Za-z0-9._-]", "_", base).strip("._")[:80]
    if not clean or Path(clean).suffix.lower() not in ALLOWED_SUFFIXES:
        raise ValueError("Choose a PDF, Markdown, or TXT file.")
    return clean


def uploaded_sections(name: str, data: bytes) -> Iterator[tuple[str, int | None, str]]:
    suffix = Path(name).suffix.lower()
    if suffix == ".pdf":
        from pypdf import PdfReader

        try:
            reader = PdfReader(io.BytesIO(data))
            if reader.is_encrypted:
                raise ValueError("Password-protected PDFs are not supported.")
            for page_number, page in enumerate(reader.pages, 1):
                text = normalize(page.extract_text() or "")
                if text:
                    yield f"page-{page_number}", page_number, text
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError("Could not read this PDF. Use a text-based, unencrypted PDF.") from exc
    else:
        try:
            source = data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError("Markdown and TXT uploads must use UTF-8 text.") from exc
        if suffix == ".txt":
            text = normalize(source)
            if text:
                yield "s1-text", None, text
        else:
            heading = "intro"
            section_number = 0
            lines: list[str] = []
            for line in source.splitlines():
                if re.match(r"^#{1,6}\s+", line):
                    text = normalize(" ".join(lines))
                    if text:
                        yield f"s{section_number}-{heading}", None, text
                    section_number += 1
                    heading = re.sub(r"[^a-z0-9]+", "-", line.lstrip("# ").lower()).strip("-") or "untitled"
                    lines = []
                else:
                    lines.append(line)
            text = normalize(" ".join(lines))
            if text:
                yield f"s{section_number}-{heading}", None, text


def create_upload_chunks(name: str, data: bytes, principal: str, config: dict) -> list[dict]:
    if principal not in USERS:
        raise ValueError("Sign in before uploading a document.")
    filename = safe_filename(name)
    if not data:
        raise ValueError("The uploaded file is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("The uploaded file exceeds the 5 MB limit.")
    doc_id = "upload-" + hashlib.sha256(data).hexdigest()[:16]
    chunks: list[dict] = []
    for section, page, text in uploaded_sections(filename, data):
        for ordinal, passage in enumerate(chunk_text(text, config["chunk_words"], config["chunk_overlap_words"]), 1):
            if len(chunks) >= MAX_UPLOAD_CHUNKS:
                raise ValueError("The document is too long for this demo (120 chunks maximum).")
            chunks.append({
                "chunk_id": f"{doc_id}:{section}:{ordinal:03d}",
                "doc_id": doc_id,
                "title": filename,
                "path": f"Session upload: {filename}",
                "page": page,
                "section": section,
                "text": passage,
                "text_sha256": sha256(passage.encode("utf-8")),
                "allowed_users": [principal],
                "origin": "session_upload",
            })
    if not chunks:
        raise ValueError("No searchable text was found. Scanned PDFs need OCR, which this demo does not include.")
    return chunks
