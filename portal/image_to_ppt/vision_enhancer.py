"""Optional Vision LLM layout enhancement via MiMo / Anthropic API."""

from __future__ import annotations

import base64
import json
import os
import re
from typing import Callable, List, Optional

from .models import ShapeElement, SlideSpec, TextElement, new_id


LAYOUT_PROMPT = """分析这张幻灯片/海报图片，返回 JSON 数组，每个元素描述一个可见对象。
仅返回 JSON，不要 markdown 代码块。

格式：
[
  {"type":"text","x":0,"y":0,"w":100,"h":30,"text":"文字","fontSize":24,"color":"#000000","bold":false,"align":"left"},
  {"type":"shape","shape":"rect","x":0,"y":0,"w":200,"h":100,"fill":"#667eea"},
  {"type":"image","x":0,"y":0,"w":100,"h":100}
]

规则：
- 坐标为相对图片宽高的像素值（图片宽={width}px，高={height}px）
- type 只能是 text、shape、image
- image 类型不需要 src 字段
- 尽量覆盖主要文字块和明显色块
"""


def _parse_json_array(text: str) -> list:
    text = text.strip()
    match = re.search(r"\[[\s\S]*\]", text)
    if match:
        return json.loads(match.group())
    return json.loads(text)


def _elements_from_ai(raw: list, slide_w: int, slide_h: int) -> List:
    elements = []
    for item in raw:
        t = item.get("type")
        if t == "text" and item.get("text"):
            elements.append(
                TextElement(
                    id=new_id("text"),
                    x=float(item.get("x", 0)),
                    y=float(item.get("y", 0)),
                    w=float(item.get("w", 100)),
                    h=float(item.get("h", 30)),
                    text=str(item["text"]),
                    fontSize=item.get("fontSize"),
                    color=item.get("color", "#1a1a1a"),
                    bold=bool(item.get("bold", False)),
                    align=item.get("align", "left"),
                    confidence=0.5,
                )
            )
        elif t == "shape":
            elements.append(
                ShapeElement(
                    id=new_id("shape"),
                    shape=item.get("shape", "rect"),
                    x=float(item.get("x", 0)),
                    y=float(item.get("y", 0)),
                    w=float(item.get("w", 100)),
                    h=float(item.get("h", 50)),
                    fill=item.get("fill"),
                    stroke=item.get("stroke"),
                    strokeWidth=float(item.get("strokeWidth", 0)),
                )
            )
    return elements


def enhance_slide_with_vision(
    slide: SlideSpec,
    image_bytes: bytes,
    get_client: Callable,
    model: str,
    min_confidence: float = 0.85,
) -> SlideSpec:
    """Re-analyze slide with vision model when OCR confidence is low."""
    text_els = [e for e in slide.elements if isinstance(e, TextElement)]
    avg_conf = (
        sum(e.confidence or 0 for e in text_els) / len(text_els) if text_els else 0
    )
    if text_els and avg_conf >= min_confidence and len(text_els) >= 3:
        return slide

    api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")
    if not api_key:
        return slide

    b64 = base64.b64encode(image_bytes).decode("ascii")
    media_type = "image/png"
    if image_bytes[:3] == b"\xff\xd8\xff":
        media_type = "image/jpeg"

    prompt = LAYOUT_PROMPT.replace("{width}", str(slide.width)).replace(
        "{height}", str(slide.height)
    )

    try:
        client = get_client()
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": b64,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )
        text = ""
        for block in response.content:
            if getattr(block, "type", None) == "text":
                text += block.text

        raw = _parse_json_array(text)
        ai_elements = _elements_from_ai(raw, slide.width, slide.height)
        if not ai_elements:
            return slide

        shapes = [e for e in ai_elements if isinstance(e, ShapeElement)]
        texts = [e for e in ai_elements if isinstance(e, TextElement)]
        images = [e for e in slide.elements if e.type == "image"]

        return SlideSpec(
            width=slide.width,
            height=slide.height,
            elements=[*shapes, *images, *texts],
            thumbnail=slide.thumbnail,
            sourceName=slide.sourceName,
            backgroundImage=slide.backgroundImage,
            sourceImage=slide.sourceImage,
        )
    except Exception:
        return slide
