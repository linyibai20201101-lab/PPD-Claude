"""Request/response models for tender-product-analysis."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class TenderProductRunRequest(BaseModel):
    source_job_id: str = Field("", description="tender-info 任务 ID；重跑时可留空并从 from_report_id 推断")
    keywords: Optional[str] = ""
    only_with_attachment: bool = False
    fetch_detail: bool = True
    parse_attachments: bool = True
    max_projects: int = Field(50, ge=1, le=200)
    headless: bool = False
    jianyu_phone: Optional[str] = None
    jianyu_password: Optional[str] = None
    from_report_id: Optional[str] = Field(
        None, description="基于已有报告重跑失败/未命中/附件队列"
    )
    retry_mode: Optional[str] = Field(
        "failed",
        description="failed | no_match | attachments",
    )


class TenderProductRunResponse(BaseModel):
    status: str
    message: str
    job_id: Optional[str] = None


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    phase: str = ""
    progress: int = 0
    message: str = ""
    error: Optional[str] = None
    report_id: Optional[str] = None
    stats: Optional[Dict[str, Any]] = None


class ReportListItem(BaseModel):
    report_id: str
    keyword: Optional[str] = None
    source_job_id: Optional[str] = None
    saved_at: Optional[str] = None
    project_count: Optional[int] = None
