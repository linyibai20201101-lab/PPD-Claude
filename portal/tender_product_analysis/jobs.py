"""Background jobs for tender-product-analysis."""

from __future__ import annotations

import threading
import traceback
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .engine import run_product_analysis


@dataclass
class ProductJob:
    id: str
    status: str = "queued"
    message: str = "排队中"
    phase: str = "queued"
    progress: int = 0
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    params: Dict[str, Any] = field(default_factory=dict)
    cancel_requested: bool = False


_lock = threading.Lock()
_jobs: Dict[str, ProductJob] = {}


def create_job(params: Dict[str, Any]) -> ProductJob:
    job = ProductJob(id=uuid.uuid4().hex[:12], params=params)
    with _lock:
        _jobs[job.id] = job
    t = threading.Thread(target=_run_worker, args=(job.id,), daemon=True)
    t.start()
    return job


def _run_worker(job_id: str) -> None:
    job = get_job(job_id)
    if not job:
        return

    def on_progress(phase: str, pct: int, msg: str) -> None:
        with _lock:
            j = _jobs.get(job_id)
            if j:
                j.phase = phase
                j.progress = pct
                j.message = msg
                if j.status == "queued":
                    j.status = "running"

    try:
        with _lock:
            job.status = "running"
            job.message = "分析中…"

        result = run_product_analysis(
            source_job_id=job.params.get("source_job_id") or "",
            keywords=job.params.get("keywords"),
            only_with_attachment=job.params.get("only_with_attachment", False),
            fetch_detail=job.params.get("fetch_detail", True),
            parse_attachments=job.params.get("parse_attachments", True),
            max_projects=job.params.get("max_projects", 50),
            headless=job.params.get("headless", False),
            jianyu_phone=job.params.get("jianyu_phone"),
            jianyu_password=job.params.get("jianyu_password"),
            from_report_id=job.params.get("from_report_id"),
            retry_mode=job.params.get("retry_mode"),
            on_progress=on_progress,
            cancel_check=lambda: is_cancel_requested(job_id),
        )

        with _lock:
            j = _jobs[job_id]
            if j:
                cancelled = j.cancel_requested or bool(result.get("cancelled"))
                if cancelled:
                    j.status = "cancelled"
                    j.progress = 100
                    j.message = "已中止，已保存部分分析结果"
                else:
                    j.status = "completed"
                    j.progress = 100
                    j.message = "分析完成"
                j.result = result
    except Exception as e:
        with _lock:
            j = _jobs.get(job_id)
            if j:
                j.status = "failed"
                j.message = "分析失败"
                j.error = str(e) or traceback.format_exc()[-500:]


def get_job(job_id: str) -> Optional[ProductJob]:
    with _lock:
        return _jobs.get(job_id)


def is_cancel_requested(job_id: str) -> bool:
    with _lock:
        job = _jobs.get(job_id)
        return bool(job and job.cancel_requested)


def request_cancel(job_id: str) -> bool:
    """请求中止；详情抓取循环会在当前项目结束后退出并保存部分结果。"""
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return False
        if job.status in ("completed", "failed", "cancelled") or job.cancel_requested:
            return False
        job.cancel_requested = True
        job.message = "正在中止，已抓取的数据将尽量保留…"
        return True
