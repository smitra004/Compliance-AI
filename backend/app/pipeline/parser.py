"""Document parsing. Handles PDF (pdfplumber -> pymupdf -> OCR fallback),
DOCX and plain text. Designed to degrade gracefully if an optional
dependency or the tesseract binary is unavailable."""
from __future__ import annotations

import io
import re
from pathlib import Path

# Marker inserted by doc_remediator.append_remediation_appendix at the start
# of the audit-trail section appended to every downloaded remediated
# document. That section intentionally repeats each violation's original
# (non-compliant) text under "Original Clause: ..." for auditability — but
# if the scanner re-reads that text on a future upload, it re-detects those
# already-resolved violations as brand-new ones, causing an infinite loop of
# "fix -> append record of old text -> re-detect old text -> fix again"
# across repeated re-uploads/re-scans. Truncating the parsed text at this
# marker ensures only the operative (already-remediated) document body is
# ever evaluated, so a document that reached 100% stays at 100%.
_APPENDIX_MARKER = "Remediation Appendix"


def _strip_appendix(text: str) -> str:
    if not text:
        return text
    idx = text.find(_APPENDIX_MARKER)
    if idx == -1:
        return text
    return text[:idx]


def _parse_pdf(data: bytes) -> str:
    text = ""
    # 1) pdfplumber (best for layout + tables)
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            pages = [p.extract_text() or "" for p in pdf.pages]
        text = "\n".join(pages)
    except Exception:
        text = ""

    # 2) pymupdf fallback
    if len(text.strip()) < 30:
        try:
            import fitz  # pymupdf
            doc = fitz.open(stream=data, filetype="pdf")
            text = "\n".join(page.get_text() for page in doc)
        except Exception:
            pass

    # 3) OCR fallback only when text extraction is essentially empty
    if len(text.strip()) < 30:
        try:
            import fitz
            import pytesseract
            from PIL import Image
            doc = fitz.open(stream=data, filetype="pdf")
            ocr_pages = []
            for page in doc:
                pix = page.get_pixmap(dpi=200)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                ocr_pages.append(pytesseract.image_to_string(img))
            text = "\n".join(ocr_pages)
        except Exception:
            pass
    return text


def _parse_docx(data: bytes) -> str:
    try:
        import docx
        document = docx.Document(io.BytesIO(data))
        return "\n".join(p.text for p in document.paragraphs)
    except Exception:
        return ""


def parse_document(filename: str, data: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        text = _parse_pdf(data)
    elif suffix in (".docx", ".doc"):
        text = _parse_docx(data)
    else:
        # txt / md / anything else: best-effort decode
        try:
            text = data.decode("utf-8", errors="ignore")
        except Exception:
            text = ""
    return _strip_appendix(text)
