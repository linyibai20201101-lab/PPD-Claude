"""Extract plain text from annual report PDF files (text layer + OCR fallback)."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

import fitz

MAX_PDF_PAGES = int(os.getenv("ANNUAL_REPORT_MAX_PDF_PAGES", "250"))
# Legacy cap for optional preview truncation only; full extraction no longer cuts by this.
MAX_TEXT_CHARS = int(os.getenv("ANNUAL_REPORT_MAX_TEXT_CHARS", "0"))
MIN_CHARS_PER_PAGE = 40
OCR_DPI = 120

PAGE_MARKER_RE = re.compile(r"---\s*第\s*(\d+)\s*页\s*---")


@dataclass
class PdfPage:
    page_num: int
    text: str
    source: str = ""


@dataclass
class PdfExtractResult:
    pages: list[PdfPage] = field(default_factory=list)
    text: str = ""
    page_count: int = 0
    pages_used: int = 0
    truncated: bool = False
    filename: str = ""
    extract_method: str = "text"  # text | ocr | mixed


def _ocr_page_text(page: fitz.Page, dpi: int = OCR_DPI) -> str:
    try:
        from image_to_ppt.ocr_engine import extract_text_blocks, merge_text_lines, ocr_available
    except ImportError:
        return ""

    if not ocr_available():
        return ""

    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=matrix, alpha=False)
    image_bytes = pix.tobytes("png")

    try:
        blocks = extract_text_blocks(image_bytes)
        merged = merge_text_lines(blocks)
        return "\n".join(b.text for b in merged if b.text.strip())
    except Exception:
        return ""


def _page_block(page_num: int, page_text: str) -> str:
    return f"--- 第 {page_num} 页 ---\n{page_text}"


def pages_to_text(pages: list[PdfPage], *, max_chars: int | None = None) -> str:
    parts = [_page_block(p.page_num, p.text) for p in pages if p.text.strip()]
    full = "\n\n".join(parts)
    if max_chars and max_chars > 0 and len(full) > max_chars:
        return full[:max_chars] + "\n\n[…文本因长度限制已截断，后续页面未纳入分析…]"
    return full


def parse_pages_from_text(full_text: str) -> list[PdfPage]:
    """Rebuild page list from stored extracted text (for section rerun)."""
    if not full_text.strip():
        return []

    parts = re.split(r"(?=---\s*第\s*\d+\s*页\s*---)", full_text)
    pages: list[PdfPage] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        m = PAGE_MARKER_RE.match(part)
        if not m:
            continue
        page_num = int(m.group(1))
        body = PAGE_MARKER_RE.sub("", part, count=1).strip()
        pages.append(PdfPage(page_num=page_num, text=body))
    return pages


def pdf_extract_pages(
    pdf_bytes: bytes,
    filename: str = "report.pdf",
    max_pages: int = MAX_PDF_PAGES,
    force_ocr: bool = False,
) -> PdfExtractResult:
    """Extract all PDF pages individually (no global character truncation)."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page_count = len(doc)
    pages_used = min(page_count, max_pages)
    pages: list[PdfPage] = []
    text_pages = 0
    ocr_pages = 0

    for i in range(pages_used):
        page = doc[i]
        page_text = page.get_text("text").strip() if not force_ocr else ""

        if force_ocr or len(page_text) < MIN_CHARS_PER_PAGE:
            ocr_text = _ocr_page_text(page)
            if ocr_text:
                page_text = ocr_text
                ocr_pages += 1
            elif page_text:
                text_pages += 1
        else:
            text_pages += 1

        if page_text:
            pages.append(PdfPage(page_num=i + 1, text=page_text, source=filename))

    doc.close()

    if ocr_pages and text_pages:
        method = "mixed"
    elif ocr_pages:
        method = "ocr"
    else:
        method = "text"

    full_text = pages_to_text(pages)
    truncated = page_count > pages_used

    return PdfExtractResult(
        pages=pages,
        text=full_text,
        page_count=page_count,
        pages_used=pages_used,
        truncated=truncated,
        filename=filename,
        extract_method=method,
    )


def pdf_to_text(
    pdf_bytes: bytes,
    filename: str = "report.pdf",
    max_pages: int = MAX_PDF_PAGES,
    max_chars: int | None = None,
    force_ocr: bool = False,
) -> PdfExtractResult:
    """Backward-compatible wrapper; max_chars only applies when > 0."""
    result = pdf_extract_pages(
        pdf_bytes,
        filename=filename,
        max_pages=max_pages,
        force_ocr=force_ocr,
    )
    cap = max_chars if max_chars is not None else MAX_TEXT_CHARS
    if cap and cap > 0 and len(result.text) > cap:
        result = PdfExtractResult(
            pages=result.pages,
            text=pages_to_text(result.pages, max_chars=cap),
            page_count=result.page_count,
            pages_used=result.pages_used,
            truncated=True,
            filename=result.filename,
            extract_method=result.extract_method,
        )
    return result


def ocr_available() -> bool:
    try:
        from image_to_ppt.ocr_engine import ocr_available as _ocr

        return _ocr()
    except ImportError:
        return False
