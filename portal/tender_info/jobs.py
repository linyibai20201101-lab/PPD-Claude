"""In-memory async job store for tender-info crawl tasks."""

from __future__ import annotations

import subprocess
import threading
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .models import TenderInfoResponse


@dataclass
class Job:
    id: str
    status: str = "queued"
    message: str = "任务已排队"
    phase: str = "queued"
    logs: List[str] = field(default_factory=list)
    progress: int = 0
    result: Optional[TenderInfoResponse] = None
    cancel_requested: bool = False
    _proc: Optional[subprocess.Popen] = field(default=None, repr=False)

    def append_log(self, line: str) -> None:
        if line:
            self.logs.append(line)
            if len(self.logs) > 500:
                self.logs = self.logs[-500:]
            self._update_phase_from_log(line)

    def _update_phase_from_log(self, line: str) -> None:
        if "[登录]" in line or "[截图] 01_login" in line:
            self.phase = "login"
            self.progress = max(self.progress, 15)
        elif "[搜索]" in line or "[截图] 02_search" in line:
            self.phase = "search"
            self.progress = max(self.progress, 30)
        elif "[抓取]" in line or "[截图] 03_page" in line:
            self.phase = "crawl"
            self.progress = min(85, self.progress + 8)
        elif "[详情]" in line:
            self.phase = "detail"
            self.progress = min(90, self.progress + 2)
        elif "[筛选]" in line or "[解析]" in line or "[导出]" in line:
            self.phase = "filter"
            self.progress = max(self.progress, 92)
        elif "[完成]" in line:
            self.phase = "done"
            self.progress = max(self.progress, 98)
        elif "[中止]" in line:
            self.phase = "done"
            self.progress = max(self.progress, 95)
        elif "[错误]" in line:
            self.phase = "error"

    def set_proc(self, proc: subprocess.Popen) -> None:
        self._proc = proc

    def clear_proc(self) -> None:
        self._proc = None


_lock = threading.Lock()
_jobs: Dict[str, Job] = {}


def create_job() -> Job:
    job = Job(id=uuid.uuid4().hex[:12])
    with _lock:
        _jobs[job.id] = job
    return job


def get_job(job_id: str) -> Optional[Job]:
    with _lock:
        return _jobs.get(job_id)


def is_cancel_requested(job_id: str) -> bool:
    with _lock:
        job = _jobs.get(job_id)
        return bool(job and job.cancel_requested)


def request_cancel(job_id: str) -> bool:
    """标记任务中止；若子进程在运行则尝试终止。"""
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return False
        if job.status in ("completed", "failed", "cancelled"):
            return False
        job.cancel_requested = True
        job.message = "正在中止任务…"
        proc = job._proc

    if proc and proc.poll() is None:
        try:
            proc.terminate()
        except Exception:
            pass
    return True


def list_recent_jobs(limit: int = 20) -> List[Job]:
    with _lock:
        jobs = list(_jobs.values())
    jobs.sort(key=lambda j: j.id, reverse=True)
    return jobs[:limit]
