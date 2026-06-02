"""FastAPI routes for tender-analysis."""

import shutil
import uuid
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from .engine import REPORT_DIR, run_analysis
from .llm_summary import llm_available
from .models import (
    AnalysisOverview,
    ExecutiveSummary,
    TenderAnalysisRequest,
    TenderAnalysisResponse,
)

UPLOAD_DIR = REPORT_DIR / "_uploads"

router = APIRouter(prefix="/api/tender-analysis", tags=["tender-analysis"])

SKILL_ID = "tender-analysis"


def _report_paths(report_id: str) -> Path:
    d = REPORT_DIR / report_id
    if not d.is_dir():
        raise HTTPException(status_code=404, detail="报告不存在")
    html = d / "report.html"
    if not html.is_file():
        raise HTTPException(status_code=404, detail="报告文件不存在")
    return html


def _attachment_headers(display_name: str, report_id: str) -> dict[str, str]:
    """RFC 5987：中文文件名须 UTF-8 编码，否则 Starlette 会 latin-1 报错导致 500。"""
    ascii_fallback = f"tender_report_{report_id}.html"
    encoded = quote(display_name, safe="")
    return {
        "Content-Disposition": (
            f'attachment; filename="{ascii_fallback}"; filename*=UTF-8\'\'{encoded}'
        )
    }


@router.get("/status")
async def status():
    return {
        "status": "ready",
        "skill": SKILL_ID,
        "message": "可接收标书获取任务数据并生成 HTML 分析报告",
        "llm_summary": llm_available(),
        "csv_upload": True,
        "dimensions": [
            "招投标概况（近1年/3年、年度与月度趋势）",
            "采购单位类型分析",
            "采购地区分布分析",
            "招投标金额分析",
            "采购形式分析",
            "单位·地区·金额交叉分析",
            "市场趋势补充（厂商、行业、成交结构）",
        ],
    }


@router.post("/run", response_model=TenderAnalysisResponse)
async def analyze(request: TenderAnalysisRequest):
    if not request.job_id and not request.records:
        raise HTTPException(status_code=400, detail="请提供 job_id（来自标书获取）或 records")

    try:
        result = run_analysis(
            job_id=request.job_id,
            records=request.records,
            keywords=request.keywords,
            enable_llm_summary=request.enable_llm_summary,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {e}") from e

    rid = result["report_id"]
    ov = result.get("overview") or {}
    stats = result.get("stats") or {}

    es = result.get("executive_summary") or {}
    return TenderAnalysisResponse(
        status="ok",
        message=f"报告已生成：{result['keywords']}，共 {stats.get('dedup_count', 0)} 条有效样本",
        report_id=rid,
        keywords=result["keywords"],
        report_url=f"/api/tender-analysis/reports/{rid}",
        download_url=f"/api/tender-analysis/reports/{rid}/download",
        overview=AnalysisOverview(
            total=ov.get("total", 0),
            count_1y=ov.get("count_1y", 0),
            count_3y=ov.get("count_3y", 0),
            with_amount=ov.get("with_amount", 0),
            with_winner=ov.get("with_winner", 0),
        ),
        stats=stats,
        executive_summary=ExecutiveSummary(
            markdown=es.get("markdown"),
            paragraph=es.get("paragraph"),
            insights=es.get("insights"),
            source=es.get("source"),
        ),
    )


@router.post("/run/upload", response_model=TenderAnalysisResponse)
async def analyze_upload(
    file: UploadFile = File(...),
    keywords: str = Form(""),
    enable_llm_summary: str = Form("true"),
):
    """上传 CSV/Excel，不依赖 tender-info 任务（S3.5）。"""
    use_llm = str(enable_llm_summary).lower() in ("true", "1", "on", "yes")
    name = (file.filename or "").lower()
    if not name.endswith((".csv", ".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="仅支持 .csv / .xlsx / .xls")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(name).suffix
    dest = UPLOAD_DIR / f"{uuid.uuid4().hex[:10]}{suffix}"
    try:
        with dest.open("wb") as f:
            shutil.copyfileobj(file.file, f)
        result = run_analysis(
            csv_path=str(dest),
            keywords=keywords.strip() or None,
            enable_llm_summary=use_llm,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {e}") from e

    rid = result["report_id"]
    ov = result.get("overview") or {}
    stats = result.get("stats") or {}
    es = result.get("executive_summary") or {}
    return TenderAnalysisResponse(
        status="ok",
        message=f"已分析上传文件，共 {stats.get('dedup_count', 0)} 条有效样本",
        report_id=rid,
        keywords=result["keywords"],
        report_url=f"/api/tender-analysis/reports/{rid}",
        download_url=f"/api/tender-analysis/reports/{rid}/download",
        overview=AnalysisOverview(
            total=ov.get("total", 0),
            count_1y=ov.get("count_1y", 0),
            count_3y=ov.get("count_3y", 0),
            with_amount=ov.get("with_amount", 0),
            with_winner=ov.get("with_winner", 0),
        ),
        stats=stats,
        executive_summary=ExecutiveSummary(
            markdown=es.get("markdown"),
            paragraph=es.get("paragraph"),
            insights=es.get("insights"),
            source=es.get("source"),
        ),
    )


@router.get("/reports/{report_id}")
async def view_report(report_id: str):
    """在线查看 HTML 报告。"""
    path = _report_paths(report_id)
    return FileResponse(path, media_type="text/html; charset=utf-8")


@router.get("/reports/{report_id}/download")
async def download_report(report_id: str):
    """下载 HTML 报告文件。"""
    path = _report_paths(report_id)
    meta_keywords = "标讯分析"
    meta_file = REPORT_DIR / report_id / "meta.json"
    if meta_file.is_file():
        import json

        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        meta_keywords = meta.get("keywords") or meta_keywords
    filename = f"标讯分析_{meta_keywords}_{report_id}.html"
    return FileResponse(
        path,
        media_type="text/html; charset=utf-8",
        headers=_attachment_headers(filename, report_id),
    )
