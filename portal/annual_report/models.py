"""Pydantic models for annual-report."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class UsageStats(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0


class AnnualReportAnalyzeMeta(BaseModel):
    filename: str = ""
    page_count: int = 0
    pages_used: int = 0
    text_truncated: bool = False
    extract_method: str = "text"
    model: str = ""
    usage: UsageStats = Field(default_factory=UsageStats)
    analysis_mode: str = "section"
    section_count: int = 0
    company_name: str = ""
    report_year: str = ""
    report_id: Optional[str] = None
    compare_years: List[str] = Field(default_factory=list)
    verification_score: Optional[float] = None


class AnnualReportResponse(BaseModel):
    status: str
    message: str
    result: Optional[str] = None
    meta: Optional[AnnualReportAnalyzeMeta] = None
    report_id: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    verification: Optional[Dict[str, Any]] = None


class TemplateResponse(BaseModel):
    template: str
    source: str


class JobCreateResponse(BaseModel):
    status: str
    job_id: str
    message: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    phase: str
    progress: int
    message: str
    logs: List[str] = Field(default_factory=list)
    report_id: Optional[str] = None
    result: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ReportListItem(BaseModel):
    report_id: str
    company_name: str = ""
    report_year: str = ""
    filename: str = ""
    saved_at: str = ""
    model: str = ""
    extract_method: str = ""
    compare_years: List[str] = Field(default_factory=list)


class ReportListResponse(BaseModel):
    reports: List[ReportListItem]


class SectionRerunRequest(BaseModel):
    extra_instructions: Optional[str] = None
    model: Optional[str] = None
    max_tokens: int = 4096


class AgentQueryRequest(BaseModel):
    message: str
    report_id: Optional[str] = None
    company_name: Optional[str] = None
    model: Optional[str] = None
    max_tokens: Optional[int] = 2048


class AgentQueryResponse(BaseModel):
    content: str
    intent: str
    actions: List[Dict[str, Any]] = Field(default_factory=list)
