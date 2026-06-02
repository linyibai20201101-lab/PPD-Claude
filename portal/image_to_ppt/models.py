"""SlideSpec schema and coordinate conversion."""

from __future__ import annotations

import uuid
from typing import Annotated, List, Literal, Optional, Union

from pydantic import BaseModel, Field

SLIDE_WIDTH_IN = 10.0


def new_id(prefix: str = "el") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


class TextElement(BaseModel):
    type: Literal["text"] = "text"
    id: str = Field(default_factory=lambda: new_id("text"))
    x: float
    y: float
    w: float
    h: float
    text: str
    fontSize: Optional[float] = None
    color: str = "#1a1a1a"
    bold: bool = False
    align: Literal["left", "center", "right"] = "left"
    confidence: Optional[float] = None


class ShapeElement(BaseModel):
    type: Literal["shape"] = "shape"
    id: str = Field(default_factory=lambda: new_id("shape"))
    shape: Literal["rect", "line"] = "rect"
    x: float
    y: float
    w: float
    h: float
    fill: Optional[str] = None
    stroke: Optional[str] = None
    strokeWidth: float = 0


class ImageElement(BaseModel):
    type: Literal["image"] = "image"
    id: str = Field(default_factory=lambda: new_id("img"))
    x: float
    y: float
    w: float
    h: float
    src: str


SlideElement = Annotated[
    Union[TextElement, ShapeElement, ImageElement],
    Field(discriminator="type"),
]


class SlideSpec(BaseModel):
    width: int
    height: int
    elements: List[SlideElement] = Field(default_factory=list)
    thumbnail: Optional[str] = None
    sourceName: Optional[str] = None
    backgroundImage: Optional[str] = None
    sourceImage: Optional[str] = None


class AnalyzeResponse(BaseModel):
    slides: List[SlideSpec]


class ExportRequest(BaseModel):
    slides: List[SlideSpec]
    filename: str = "presentation"


def slide_height_in(slide_width: int, slide_height: int) -> float:
    if slide_width <= 0:
        return SLIDE_WIDTH_IN * 9 / 16
    return SLIDE_WIDTH_IN * slide_height / slide_width


def px_to_in(value: float, slide_px: int, slide_in: float) -> float:
    if slide_px <= 0:
        return 0.0
    return value / slide_px * slide_in


def px_rect_to_in(
    x: float, y: float, w: float, h: float, slide_w: int, slide_h: int
) -> tuple[float, float, float, float]:
    sw = SLIDE_WIDTH_IN
    sh = slide_height_in(slide_w, slide_h)
    return (
        px_to_in(x, slide_w, sw),
        px_to_in(y, slide_h, sh),
        px_to_in(w, slide_w, sw),
        px_to_in(h, slide_h, sh),
    )


def estimate_font_size_px(text_h: float) -> float:
    return max(8.0, min(text_h * 0.75, 96.0))
