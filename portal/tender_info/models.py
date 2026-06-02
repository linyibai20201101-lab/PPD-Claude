"""Pydantic models for tender-info (剑鱼标讯)."""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from .jianyu_options import DEFAULT_SEARCH_SCOPES


class QueryType(str, Enum):
    """兼容旧接口；新页面以搜索范围为准。"""

    product = "product"
    enterprise = "enterprise"


class TenderInfoRequest(BaseModel):
    """用户从页面提交的任务参数（对标剑鱼工作台查询维度）"""

    keywords: str = Field(..., min_length=1, description="搜索关键词")
    region: str = Field(default="全国", description="地区，默认全国")
    publish_time_preset: str = Field(
        default="1y",
        description="发布时间快捷项：7d/30d/1y/3y/5y/custom",
    )
    date_from: Optional[str] = Field(default=None, description="自定义开始日期 YYYY-MM-DD")
    date_to: Optional[str] = Field(default=None, description="自定义结束日期 YYYY-MM-DD")
    search_scopes: List[str] = Field(
        default_factory=lambda: list(DEFAULT_SEARCH_SCOPES),
        description="搜索范围 id 列表",
    )
    info_types: List[str] = Field(
        default_factory=list,
        description="信息类型；空列表表示「全部」",
    )

    max_pages: int = Field(default=5, ge=1, le=50)
    skip_detail: bool = Field(default=True, description="跳过详情页，加快列表检索")
    headless: bool = Field(default=False, description="无头浏览器；遇验证码建议关闭")
    only_awarded: bool = Field(default=True, description="默认仅返回已中标/成交记录")
    include_pending: bool = Field(
        default=False, description="同时包含招标/预告等未中标公告（已中标仍排在前）"
    )

    # 兼容旧字段
    query_type: QueryType = QueryType.product

    jianyu_phone: Optional[str] = Field(default=None, description="剑鱼标讯登录手机号")
    jianyu_password: Optional[str] = Field(default=None, description="剑鱼标讯登录密码")
    use_saved_credentials: bool = Field(
        default=False, description="使用 portal/.env 中已保存的账号"
    )

    @field_validator("search_scopes")
    @classmethod
    def ensure_scopes(cls, v: List[str]) -> List[str]:
        if not v:
            return list(DEFAULT_SEARCH_SCOPES)
        return v

    @field_validator("region")
    @classmethod
    def normalize_region(cls, v: str) -> str:
        s = (v or "").strip()
        return s or "全国"


class BidRecord(BaseModel):
    project_name: str
    buyer: Optional[str] = None
    winner: Optional[str] = None
    amount: Optional[str] = None
    bid_date: Optional[str] = None
    region: Optional[str] = None
    project_type: Optional[str] = None
    industry: Optional[str] = None
    source_url: Optional[str] = None


class TenderInfoResponse(BaseModel):
    status: str
    message: str
    job_id: Optional[str] = None
    query_type: Optional[str] = None
    keywords: Optional[str] = None
    total: int = 0
    total_raw: int = 0
    total_awarded: int = 0
    total_pending: int = 0
    records: List[BidRecord] = Field(default_factory=list)
    report_markdown: Optional[str] = None
    csv_download: Optional[str] = None
    logs: List[str] = Field(default_factory=list)


class JobStatusResponse(BaseModel):
    job_id: str
    status: str  # queued | running | completed | failed
    message: str = ""
    phase: str = "queued"
    logs: List[str] = Field(default_factory=list)
    progress: int = 0
    result: Optional[TenderInfoResponse] = None
