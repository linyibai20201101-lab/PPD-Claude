"""OCR text extraction with PaddleOCR (fallback: RapidOCR)."""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np
from PIL import Image

_ocr_instance = None
_ocr_backend: Optional[str] = None


@dataclass
class OcrBlock:
    text: str
    x: float
    y: float
    w: float
    h: float
    confidence: float


def _quad_to_bbox(quad) -> Tuple[float, float, float, float]:
    xs = [p[0] for p in quad]
    ys = [p[1] for p in quad]
    x0, y0 = min(xs), min(ys)
    return x0, y0, max(xs) - x0, max(ys) - y0


def _get_ocr():
    global _ocr_instance, _ocr_backend
    if _ocr_instance is not None:
        return _ocr_instance, _ocr_backend

    try:
        from paddleocr import PaddleOCR

        _ocr_instance = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
        _ocr_backend = "paddleocr"
        return _ocr_instance, _ocr_backend
    except Exception:
        pass

    try:
        from rapidocr_onnxruntime import RapidOCR

        _ocr_instance = RapidOCR()
        _ocr_backend = "rapidocr"
        return _ocr_instance, _ocr_backend
    except Exception:
        pass

    return None, None


def ocr_backend_name() -> Optional[str]:
    _, backend = _get_ocr()
    return backend


def ocr_available() -> bool:
    return _get_ocr()[0] is not None


def _image_to_array(image_bytes: bytes) -> np.ndarray:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    return np.array(img)


def extract_text_blocks(image_bytes: bytes) -> List[OcrBlock]:
    ocr, backend = _get_ocr()
    if ocr is None:
        raise RuntimeError(
            "OCR 未就绪。请安装: pip install paddleocr paddlepaddle "
            "或 pip install rapidocr-onnxruntime"
        )

    arr = _image_to_array(image_bytes)
    blocks: List[OcrBlock] = []

    if backend == "paddleocr":
        result = ocr.ocr(arr, cls=True)
        if not result or not result[0]:
            return blocks
        for line in result[0]:
            quad, (text, conf) = line
            x, y, w, h = _quad_to_bbox(quad)
            text = (text or "").strip()
            if text:
                blocks.append(OcrBlock(text=text, x=x, y=y, w=w, h=h, confidence=float(conf)))
    else:
        result, _ = ocr(arr)
        if not result:
            return blocks
        for item in result:
            quad, text, conf = item
            x, y, w, h = _quad_to_bbox(quad)
            text = (text or "").strip()
            if text:
                blocks.append(OcrBlock(text=text, x=x, y=y, w=w, h=h, confidence=float(conf)))

    return blocks


def merge_text_lines(blocks: List[OcrBlock], y_threshold: float = 0.5) -> List[OcrBlock]:
    """Merge OCR lines on the same row into paragraph boxes."""
    if not blocks:
        return []

    sorted_blocks = sorted(blocks, key=lambda b: (b.y, b.x))
    merged: List[OcrBlock] = []
    group: List[OcrBlock] = [sorted_blocks[0]]

    def flush():
        if not group:
            return
        x = min(b.x for b in group)
        y = min(b.y for b in group)
        x2 = max(b.x + b.w for b in group)
        y2 = max(b.y + b.h for b in group)
        text = " ".join(b.text for b in group)
        conf = sum(b.confidence for b in group) / len(group)
        merged.append(OcrBlock(text=text, x=x, y=y, w=x2 - x, h=y2 - y, confidence=conf))
        group.clear()

    for block in sorted_blocks[1:]:
        ref = group[-1]
        avg_h = (ref.h + block.h) / 2
        same_row = abs(block.y - ref.y) < avg_h * y_threshold
        close_x = block.x - (ref.x + ref.w) < avg_h * 2
        if same_row and close_x:
            group.append(block)
        else:
            flush()
            group.append(block)
    flush()
    return merged
