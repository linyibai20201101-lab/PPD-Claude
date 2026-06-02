"""FastAPI routes for image-to-ppt."""

from __future__ import annotations

from typing import Callable, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from .analyzer import analyze_image, analyze_images
from .exporter import build_presentation, export_filename
from .models import AnalyzeResponse, ExportRequest, SlideSpec
from .ocr_engine import ocr_available, ocr_backend_name
from .pdf_parser import pdf_to_pages
from .vision_enhancer import enhance_slide_with_vision

router = APIRouter(prefix="/api/image-to-ppt", tags=["image-to-ppt"])

_get_client: Optional[Callable] = None
_default_model: str = "mimo-v2.5-pro"
_api_key_configured: bool = False


def configure_router(
    get_anthropic_client: Optional[Callable] = None,
    default_model: str = "mimo-v2.5-pro",
    api_key_configured: bool = False,
) -> None:
    global _get_client, _default_model, _api_key_configured
    _get_client = get_anthropic_client
    _default_model = default_model
    _api_key_configured = api_key_configured


@router.get("/status")
async def status():
    return {
        "ocr_available": ocr_available(),
        "ocr_backend": ocr_backend_name(),
        "vision_available": _api_key_configured,
        "pdf_supported": True,
    }


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    files: List[UploadFile] = File(...),
    use_vision: bool = Form(False),
    detect_shapes: bool = Form(True),
    detect_images: bool = Form(True),
):
    if not ocr_available():
        raise HTTPException(
            status_code=503,
            detail="OCR 未安装。请运行: pip install rapidocr-onnxruntime 或 paddleocr",
        )

    image_items: list[tuple[bytes, Optional[str]]] = []

    for upload in files:
        data = await upload.read()
        if not data:
            continue
        name = upload.filename or "image"
        lower = name.lower()

        if lower.endswith(".pdf"):
            for page in pdf_to_pages(data, filename=name):
                image_items.append((page.image_bytes, page.name))
        else:
            image_items.append((data, name))

    if not image_items:
        raise HTTPException(status_code=400, detail="未收到有效图片或 PDF 文件")

    slides = analyze_images(
        image_items,
        detect_shapes_flag=detect_shapes,
        detect_images=detect_images,
    )

    if use_vision and _get_client and _api_key_configured:
        enhanced: List[SlideSpec] = []
        for slide, (img_bytes, _) in zip(slides, image_items):
            enhanced.append(
                enhance_slide_with_vision(
                    slide,
                    img_bytes,
                    _get_client,
                    _default_model,
                )
            )
        slides = enhanced

    return AnalyzeResponse(slides=slides)


@router.post("/reanalyze")
async def reanalyze(
    file: UploadFile = File(...),
    use_vision: bool = Form(False),
    detect_shapes: bool = Form(True),
    detect_images: bool = Form(True),
):
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="空文件")

    slide = analyze_image(
        data,
        source_name=file.filename,
        detect_shapes_flag=detect_shapes,
        detect_images=detect_images,
    )

    if use_vision and _get_client and _api_key_configured:
        slide = enhance_slide_with_vision(slide, data, _get_client, _default_model)

    return slide


@router.post("/export")
async def export_pptx(request: ExportRequest):
    if not request.slides:
        raise HTTPException(status_code=400, detail="slides 不能为空")

    try:
        pptx_bytes = build_presentation(request.slides)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出失败: {e}")

    filename = export_filename(request.filename)
    return Response(
        content=pptx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
