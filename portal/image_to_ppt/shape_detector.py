"""OpenCV-based rectangle and line detection."""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image


@dataclass
class DetectedShape:
    shape: str  # rect | line
    x: float
    y: float
    w: float
    h: float
    fill: Optional[str] = None
    stroke: Optional[str] = None
    stroke_width: float = 0


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02x}{g:02x}{b:02x}"


def _dominant_color(img: np.ndarray, x: int, y: int, w: int, h: int) -> str:
    roi = img[y : y + h, x : x + w]
    if roi.size == 0:
        return "#cccccc"
    mean = roi.reshape(-1, 3).mean(axis=0)
    return _rgb_to_hex(int(mean[0]), int(mean[1]), int(mean[2]))


def _overlaps(a: Tuple[float, float, float, float], b: Tuple[float, float, float, float], thresh: float = 0.3) -> bool:
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


def detect_shapes(
    image_bytes: bytes,
    text_boxes: Optional[List[Tuple[float, float, float, float]]] = None,
    min_area_ratio: float = 0.002,
) -> List[DetectedShape]:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    arr = np.array(img)
    h, w = arr.shape[:2]
    min_area = w * h * min_area_ratio

    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    dilated = cv2.dilate(edges, kernel, iterations=1)

    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    shapes: List[DetectedShape] = []
    text_boxes = text_boxes or []

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area:
            continue
        x, y, bw, bh = cv2.boundingRect(cnt)
        if bw < 8 or bh < 8:
            continue
        bbox = (float(x), float(y), float(bw), float(bh))
        if any(_overlaps(bbox, tb) for tb in text_boxes):
            continue

        approx = cv2.approxPolyDP(cnt, 0.02 * cv2.arcLength(cnt, True), True)
        fill = _dominant_color(arr, x, y, bw, bh)

        if len(approx) == 4 and bw > 20 and bh > 20:
            shapes.append(
                DetectedShape(shape="rect", x=x, y=y, w=bw, h=bh, fill=fill)
            )
        elif bh <= 4 and bw > 40:
            shapes.append(
                DetectedShape(
                    shape="line",
                    x=x,
                    y=y,
                    w=bw,
                    h=max(bh, 2),
                    stroke=fill,
                    stroke_width=2,
                )
            )

    shapes.sort(key=lambda s: s.w * s.h, reverse=True)
    return shapes[:30]
