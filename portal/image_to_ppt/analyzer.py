"""Main image analysis pipeline."""

from __future__ import annotations

import base64
import io
from typing import List, Optional

from PIL import Image

from .layout_merger import merge_to_slide_spec
from .models import ShapeElement, SlideSpec, TextElement
from .ocr_engine import extract_text_blocks, merge_text_lines
from .shape_detector import detect_shapes


def _bytes_to_data_url(image_bytes: bytes) -> str:
    media = "image/png"
    if image_bytes[:3] == b"\xff\xd8\xff":
        media = "image/jpeg"
    b64 = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{media};base64,{b64}"


def _make_thumbnail(image_bytes: bytes, max_size: int = 240) -> str:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img.thumbnail((max_size, max_size))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"


def analyze_image(
    image_bytes: bytes,
    source_name: Optional[str] = None,
    detect_shapes_flag: bool = True,
    detect_images: bool = True,
) -> SlideSpec:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    width, height = img.size

    raw_blocks = extract_text_blocks(image_bytes)
    merged_blocks = merge_text_lines(raw_blocks)

    text_boxes = [(b.x, b.y, b.w, b.h) for b in merged_blocks]
    shapes = detect_shapes(image_bytes, text_boxes=text_boxes) if detect_shapes_flag else []

    return merge_to_slide_spec(
        image_bytes=image_bytes,
        width=width,
        height=height,
        ocr_blocks=merged_blocks,
        shapes=shapes,
        include_images=detect_images,
        source_name=source_name,
        thumbnail=_make_thumbnail(image_bytes),
        source_image=_bytes_to_data_url(image_bytes),
    )


def analyze_images(
    items: List[tuple[bytes, Optional[str]]],
    detect_shapes_flag: bool = True,
    detect_images: bool = True,
) -> List[SlideSpec]:
    slides: List[SlideSpec] = []
    for image_bytes, name in items:
        slides.append(
            analyze_image(
                image_bytes,
                source_name=name,
                detect_shapes_flag=detect_shapes_flag,
                detect_images=detect_images,
            )
        )
    return slides
