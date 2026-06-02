"""Pydantic models for tender-analysis."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ExecutiveSummary(BaseModel):
    markdown: Optional[str] = None
    paragraph: Optional[str] = None
    insights: Optional[List[str]] = None
    source: Optional[str] = None


class TenderAnalysisRequest(BaseModel):
    """分析请求：来自标书获取任务或直传记录。"""

    job_id: Optional[str] = Field(default=None, description="tender-info 任务 ID")
    keywords: Optional[str] = Field(default=None, description="报告标题关键词")
    records: Optional[List[Dict[str, Any]]] = Field(default=None, description="直传记录列表")
    enable_llm_summary: bool = Field(default=True, description="生成执行摘要（无 Key 时用规则引擎）")


class AnalysisOverview(BaseModel):
    total: int = 0
    count_1y: int = 0
    count_3y: int = 0
    with_amount: int = 0
    with_winner: int = 0


class TenderAnalysisResponse(BaseModel):
    status: str
    message: str
    report_id: Optional[str] = None
    keywords: Optional[str] = None
    report_url: Optional[str] = None
    download_url: Optional[str] = None
    overview: Optional[AnalysisOverview] = None
    stats: Optional[Dict[str, Any]] = None
    executive_summary: Optional[ExecutiveSummary] = None
