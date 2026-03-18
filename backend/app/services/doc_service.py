"""
Document parsing service.

Word (.docx) → markitdown  (fast, synchronous)
PDF  (.pdf)  → pymupdf4llm (fast, no GPU, good for structured academic PDFs)

If a PDF fails or quality is insufficient, set use_ocr=True to route to marker
(marker is heavier and slower — reserved as fallback, not installed by default).
"""
import tempfile
import os
from pathlib import Path


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc"}


def parse_document(filename: str, content: bytes) -> str:
    """Parse Word or PDF bytes into Markdown string."""
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {ext}. Supported: {', '.join(SUPPORTED_EXTENSIONS)}")

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        if ext in (".docx", ".doc"):
            return _parse_word(tmp_path)
        else:
            return _parse_pdf(tmp_path)
    finally:
        os.unlink(tmp_path)


def _parse_word(path: str) -> str:
    from markitdown import MarkItDown
    md = MarkItDown()
    result = md.convert(path)
    return result.text_content


def _parse_pdf(path: str) -> str:
    import pymupdf4llm
    return pymupdf4llm.to_markdown(path)
