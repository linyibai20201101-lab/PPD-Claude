"""Merge OCR, shapes, and image regions into SlideSpec elements."""

from __future__ import annotations

import base64
import io
from typing import List, Tuple

from PIL import Image

from .models import ImageElement, ShapeElement, SlideElement, SlideSpec, TextElement, estimate_font_size_px, new_id
from .ocr_engine import OcrBlock
from .shape_detector import DetectedShape


def _bbox_overlap(
    a: Tuple[float, float, float, float],
    b: Tuple[float, float, float, float],
    thresh: float = 0.4,
) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ix = max(ax, bx)
    iy = max(ay, by)
    iw = min(ax + aw, bx + bw) - ix
    ih = min(ay + ah, by + bh) - iy
    if iw <= 0 or ih <= 0:
        return False
    inter = iw * ih
    smaller = min(aw * ah, bw * bh)
    return inter / smaller > thresh if smaller > 0 else False


def blocks_to_text_elements(blocks: List[OcrBlock]) -> List[TextElement]:
    elements: List[TextElement] = []
    for block in blocks:
        elements.append(
            TextElement(
                id=new_id("text"),
                x=block.x,
                y=block.y,
                w=block.w,
                h=block.h,
                text=block.text,
                fontSize=estimate_font_size_px(block.h),
                confidence=block.confidence,
            )
        )
    return elements


def shapes_to_elements(shapes: List[DetectedShape]) -> List[ShapeElement]:
    elements: List[ShapeElement] = []
    for shape in shapes:
        elements.append(
            ShapeElement(
                id=new_id("shape"),
                shape=shape.shape,  # type: ignore[arg-type]
                x=shape.x,
                y=shape.y,
                w=shape.w,
                h=shape.h,
                fill=shape.fill,
                stroke=shape.stroke,
                strokeWidth=shape.stroke_width,
            )
        )
    return elements


def detect_image_regions(
    image_bytes: bytes,
    occupied: List[Tuple[float, float, float, float]],
    min_area_ratio: float = 0.01,
) -> List[ImageElement]:
    """Find large non-text non-shape regions and export as cropped images."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    w, h = img.size
    min_area = w * h * min_area_ratio

    # Simple grid scan for uncovered large uniform-ish regions is expensive;
    # use contour-based approach on residual mask instead.
    import numpy as np
    import cv2

    arr = np.array(img)
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    mask = np.ones((h, w), dtype=np.uint8) * 255

    for x, y, bw, bh in occupied:
        x0, y0 = max(0, int(x)), max(0, int(y))
        x1, y1 = min(w, int(x + bw)), min(h, int(y + bh))
        mask[y0:y1, x0:x1] = 0

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    elements: List[ImageElement] = []

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area:
            continue
        x, y, bw, bh = cv2.boundingRect(cnt)
        if bw < 40 or bh < 40:
            continue
        crop = img.crop((x, y, x + bw, y + bh))
        buf = io.BytesIO()
        crop.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        elements.append(
            ImageElement(
                id=new_id("img"),
                x=float(x),
                y=float(y),
                w=float(bw),
                h=float(bh),
                src=f"data:image/png;base64,{b64}",
            )
        )

    return elements[:15]


def merge_to_slide_spec(
    image_bytes: bytes,
    width: int,
    height: int,
    ocr_blocks: List[OcrBlock],
    shapes: List[DetectedShape],
    include_images: bool = True,
    source_name: str | None = None,
    thumbnail: str | None = None,
    source_image: str | None = None,
) -> SlideSpec:
    text_els = blocks_to_text_elements(ocr_blocks)
    shape_els = shapes_to_elements(shapes)

    occupied: List[Tuple[float, float, float, float]] = []
    for el in text_els:
        occupied.append((el.x, el.y, el.w, el.h))
    for el in shape_els:
        occupied.append((el.x, el.y, el.w, el.h))

    image_els: List[ImageElement] = []
    if include_images:
        image_els = detect_image_regions(image_bytes, occupied)

    # Layer order: shapes (back) -> images -> text (front)
    elements: List[SlideElement] = []
    elements.extend(shape_els)
    elements.extend(image_els)
    elements.extend(text_els)

    return SlideSpec(
        width=width,
        height=height,
        elements=elements,
        sourceName=source_name,
        thumbnail=thumbnail,
        sourceImage=source_image,
    )
