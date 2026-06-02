"""FastAPI routes for tender-product-analysis."""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from tender_info.jianyu_client import is_configured

from .jobs import create_job, get_job, request_cancel
from .models import JobStatusResponse, ReportListItem, TenderProductRunRequest, TenderProductRunResponse
from .storage import REPORT_DIR, load_report, list_reports

router = APIRouter(prefix="/api/tender-product-analysis", tags=["tender-product-analysis"])

SKILL_ID = "tender-product-analysis"


@router.get("/status")
async def status():
    return {
        "status": "ready",
        "skill": SKILL_ID,
        "message": "关键词+属性匹配；详情与附件 PDF/Word 解析；页内产品表+Excel",
        "phase": "keyword_match_attach",
        "jianyu_configured": is_configured(),
        "docs": "/skills/tender-product-analysis/SKILL.md",
    }


@router.post("/run", response_model=TenderProductRunResponse)
async def run(request: TenderProductRunRequest):
    if not request.from_report_id and not request.source_job_id.strip():
        raise HTTPException(status_code=400, detail="请提供 source_job_id 或 from_report_id（重跑）")
    if request.fetch_detail and not request.jianyu_phone and not is_configured():
        raise HTTPException(
            status_code=400,
            detail="详情抓取需剑鱼账号：配置 .env 的 JIANYU_PHONE/JIANYU_PASSWORD 或在请求中填写",
        )

    job = create_job(request.model_dump())
    return TenderProductRunResponse(
        status="accepted",
        message="任务已提交",
        job_id=job.id,
    )


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    """中止正在运行的产品分析；已抓取的项目与附件会尽量写入报告。"""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    if job.status in ("completed", "failed", "cancelled"):
        raise HTTPException(status_code=400, detail="任务已结束，无法中止")
    if not request_cancel(job_id):
        raise HTTPException(status_code=400, detail="无法中止该任务")
    return {
        "status": "cancelling",
        "job_id": job_id,
        "message": "中止请求已发送，将在当前项目处理完成后停止",
    }


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def job_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    resp = JobStatusResponse(
        job_id=job.id,
        status=job.status,
        phase=job.phase,
        progress=job.progress,
        message=job.message,
        error=job.error,
    )
    if job.result:
        resp.report_id = job.result.get("report_id")
        resp.stats = job.result.get("stats")
    return resp


@router.get("/reports")
async def reports_list(limit: int = 30):
    items = []
    for r in list_reports(limit):
        items.append(
            ReportListItem(
                report_id=r.get("report_id", ""),
                keyword=r.get("keyword"),
                source_job_id=r.get("source_job_id"),
                saved_at=r.get("saved_at"),
                project_count=r.get("project_count"),
            )
        )
    return {"reports": items}


@router.get("/reports/{report_id}")
async def get_report(report_id: str):
    try:
        data = load_report(report_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="报告不存在")
    return data


@router.get("/reports/{report_id}/export")
async def export_report(report_id: str, format: str = "xlsx"):
    d = REPORT_DIR / report_id
    if not d.is_dir():
        raise HTTPException(status_code=404, detail="报告不存在")
    if format == "md":
        p = d / "report.md"
        if not p.is_file():
            raise HTTPException(status_code=404, detail="report.md 不存在")
        return FileResponse(p, media_type="text/markdown", filename=f"{report_id}.md")
    if format == "xlsx":
        p = d / "products_master.xlsx"
        if not p.is_file():
            raise HTTPException(status_code=404, detail="products_master.xlsx 不存在")
        return FileResponse(
            p,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=f"{report_id}_products.xlsx",
        )
    raise HTTPException(status_code=400, detail="format 支持 md / xlsx")
