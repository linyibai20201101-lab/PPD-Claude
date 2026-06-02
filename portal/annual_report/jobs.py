"""Async job store for annual report analysis."""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class AnalysisJob:
    id: str
    status: str = "queued"
    phase: str = "queued"
    progress: int = 0
    message: str = "任务已排队"
    logs: List[str] = field(default_factory=list)
    report_id: Optional[str] = None
    result: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


_lock = threading.Lock()
_jobs: Dict[str, AnalysisJob] = {}


def create_job() -> AnalysisJob:
    job = AnalysisJob(id=uuid.uuid4().hex[:12])
    with _lock:
        _jobs[job.id] = job
    return job


def get_job(job_id: str) -> Optional[AnalysisJob]:
    with _lock:
        return _jobs.get(job_id)


def list_jobs(limit: int = 20) -> List[AnalysisJob]:
    with _lock:
        jobs = list(_jobs.values())
    jobs.sort(key=lambda j: j.id, reverse=True)
    return jobs[:limit]


def _update(job_id: str, **kwargs) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return
        for k, v in kwargs.items():
            setattr(job, k, v)


def append_log(job_id: str, line: str) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if not job or not line:
            return
        job.logs.append(line)
        if len(job.logs) > 200:
            job.logs = job.logs[-200:]


def run_job_async(
    job_id: str,
    worker: Callable[[Callable[[str, int, str], None]], Dict[str, Any]],
) -> None:
    def on_progress(phase: str, pct: int, msg: str) -> None:
        append_log(job_id, f"[{phase}] {msg}")
        _update(job_id, status="running", phase=phase, progress=pct, message=msg)

    def _run() -> None:
        _update(job_id, status="running", phase="start", progress=1, message="任务开始")
        try:
            result = worker(on_progress)
            meta = dict(result.get("meta") or {})
            if result.get("metrics"):
                meta["metrics"] = result["metrics"]
            if result.get("verification"):
                meta["verification"] = result["verification"]
            _update(
                job_id,
                status="completed",
                phase="done",
                progress=100,
                message=result.get("message", "分析完成"),
                report_id=result.get("report_id"),
                result=result.get("result"),
                meta=meta,
            )
        except Exception as e:
            append_log(job_id, f"[error] {e}")
            _update(
                job_id,
                status="failed",
                phase="error",
                progress=0,
                message="分析失败",
                error=str(e),
            )

    threading.Thread(target=_run, daemon=True).start()
