"""PDF to page images via PyMuPDF."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import fitz


MAX_PDF_PAGES = 50


@dataclass
class PdfPage:
    index: int
    name: str
    image_bytes: bytes
    width: int
    height: int


def pdf_to_pages(pdf_bytes: bytes, filename: str = "document.pdf", dpi: int = 150) -> List[PdfPage]:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page_count = min(len(doc), MAX_PDF_PAGES)
    pages: List[PdfPage] = []
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)

    base_name = filename.rsplit(".", 1)[0] if filename else "document"

    for i in range(page_count):
        page = doc[i]
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        pages.append(
            PdfPage(
                index=i,
                name=f"{base_name}_page{i + 1}.png",
                image_bytes=pix.tobytes("png"),
                width=pix.width,
                height=pix.height,
            )
        )

    doc.close()
    return pages
