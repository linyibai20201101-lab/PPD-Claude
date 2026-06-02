"""FastAPI routes for tender-info."""

import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

from .jianyu_client import cancel_crawl_job, is_configured, job_to_response, start_crawl_job
from .jianyu_options import default_query_options
from .job_index import list_persisted_jobs, restore_job_rows
from .jobs import get_job
from .models import BidRecord
from .models import JobStatusResponse, TenderInfoRequest, TenderInfoResponse

router = APIRouter(prefix="/api/tender-info", tags=["tender-info"])

SKILL_ID = "tender-info"
DATA_DIR = Path(__file__).resolve().parent.parent / "tender_raw_data"


def _job_preview_path(job_id: str) -> Path | None:
    job_dir = DATA_DIR / job_id
    latest = job_dir / "latest.png"
    if latest.is_file():
        return latest
    shots = sorted(job_dir.glob("step_*.png"), key=lambda p: p.stat().st_mtime, reverse=True)
    return shots[0] if shots else None


@router.get("/status")
async def status():
    return {
        "status": "ready",
        "skill": SKILL_ID,
        "platform": "剑鱼标讯",
        "platform_url": "https://www.jianyu360.com/",
        "jianyu_configured": is_configured(),
        "message": "填写账号与关键词后点击「开始执行任务」",
        "supports_page_credentials": True,
    }


@router.get("/query-options")
async def query_options():
    """返回与剑鱼工作台对齐的查询维度选项。"""
    return default_query_options()


@router.post("/run", response_model=TenderInfoResponse)
async def run(request: TenderInfoRequest):
    """提交检索任务，立即返回 job_id；前端轮询 /jobs/{id} 获取进度与结果。"""
    if not request.use_saved_credentials and not request.jianyu_phone and not is_configured():
        raise HTTPException(
            status_code=400,
            detail="请填写剑鱼标讯账号密码，或勾选「使用已保存账号」并在 .env 配置 JIANYU_PHONE",
        )

    job = await start_crawl_job(request)
    return TenderInfoResponse(
        status="accepted",
        message="任务已提交，正在执行",
        job_id=job.id,
        query_type=request.query_type.value,
        keywords=request.keywords,
    )


@router.get("/jobs")
async def list_jobs(limit: int = 30):
    """历史任务（重启 portal 后仍可从磁盘恢复）。"""
    return {"jobs": list_persisted_jobs(limit)}


@router.get("/jobs/{job_id}/restore")
async def restore_job(job_id: str):
    """从 tender_raw_data/{job_id} 加载 CSV/JSON 供前端展示。"""
    meta, rows = restore_job_rows(job_id)
    if not meta:
        raise HTTPException(status_code=404, detail="任务数据不存在")
    records = [
        BidRecord(
            project_name=str(r.get("项目名称", "") or ""),
            buyer=str(r.get("采购单位", "") or "") or None,
            winner=str(r.get("中标单位", "") or "") or None,
            amount=str(r.get("预算金额", "") or "") or None,
            bid_date=str(r.get("发布时间", "") or "") or None,
            region=str(r.get("地区", "") or "") or None,
            project_type=str(r.get("项目类型", "") or "") or None,
            industry=str(r.get("行业类型", "") or "") or None,
            source_url=str(r.get("详情链接", "") or "") or None,
        )
        for r in rows
        if str(r.get("项目名称", "") or "").strip()
    ]
    return {
        "job_id": job_id,
        "meta": meta,
        "total": len(records),
        "keywords": meta.get("keywords", ""),
        "csv_download": meta.get("csv_download"),
        "records": records,
    }


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    return job_to_response(job)


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    """中止正在运行的爬取任务；已抓取的数据会尽量保留。"""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    if job.status in ("completed", "failed", "cancelled"):
        raise HTTPException(status_code=400, detail="任务已结束，无法中止")
    if not cancel_crawl_job(job_id):
        raise HTTPException(status_code=400, detail="无法中止该任务")
    return {"status": "cancelling", "job_id": job_id, "message": "中止请求已发送"}


@router.get("/jobs/{job_id}/stream")
async def stream_job(job_id: str):
    """SSE：实时推送任务日志与状态。"""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")

    async def event_generator():
        last_log = 0
        while True:
            j = get_job(job_id)
            if not j:
                yield f"data: {json.dumps({'type': 'error', 'message': '任务不存在'}, ensure_ascii=False)}\n\n"
                break

            if len(j.logs) > last_log:
                for line in j.logs[last_log:]:
                    payload = {"type": "log", "line": line}
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                last_log = len(j.logs)

            preview = _job_preview_path(job_id)
            status_payload = {
                "type": "status",
                "status": j.status,
                "phase": j.phase,
                "progress": j.progress,
                "message": j.message,
                "has_preview": preview is not None,
                "log_count": len(j.logs),
            }
            yield f"data: {json.dumps(status_payload, ensure_ascii=False)}\n\n"

            if j.status in ("completed", "failed", "cancelled"):
                if j.result:
                    yield f"data: {json.dumps({'type': 'done', 'result': j.result.model_dump()}, ensure_ascii=False)}\n\n"
                elif j.status == "cancelled":
                    payload = {"type": "cancelled", "message": j.message}
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                break

            await asyncio.sleep(0.4)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/jobs/{job_id}/preview")
async def job_preview(job_id: str):
    """任务最新浏览器截图。"""
    path = _job_preview_path(job_id)
    if not path:
        raise HTTPException(status_code=404, detail="暂无截图")
    return FileResponse(path, media_type="image/png", headers={"Cache-Control": "no-store"})


@router.get("/download/{file_path:path}")
async def download_file(file_path: str):
    """下载抓取生成的 CSV（仅限 tender_raw_data 目录内）。"""
    target = (DATA_DIR / file_path).resolve()
    if not str(target).startswith(str(DATA_DIR.resolve())):
        raise HTTPException(status_code=403, detail="非法路径")
    if not target.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(
        target,
        media_type="text/csv",
        filename=target.name,
    )
