"""Competitor context and L2 deep links."""

from __future__ import annotations

from typing import List
from urllib.parse import urlencode


def build_competitor_instructions(competitors: List[str], industry: str = "") -> str:
    if not competitors and not industry:
        return ""
    lines = ["## 同行业对比补充（用户指定）", ""]
    if industry:
        lines.append(f"- 所属行业：{industry}")
    if competitors:
        lines.append(f"- 可比公司：{', '.join(competitors)}")
        lines.append("- 请在「同行业对比」章节与「主要竞品动态」中重点分析上述公司。")
    return "\n".join(lines)


def competitor_benchmark_url(
    *,
    report_id: str = "",
    company: str = "",
    peers: List[str] | None = None,
    industry: str = "",
) -> str:
    params = {"from": "annual-report"}
    if report_id:
        params["report_id"] = report_id
    if company:
        params["company"] = company
    if peers:
        params["peers"] = ",".join(peers)
    if industry:
        params["industry"] = industry
    return f"/competitor-benchmark/?{urlencode(params)}"


def industry_research_url(company: str = "", industry: str = "") -> str:
    params = {"from": "annual-report"}
    if company:
        params["company"] = company
    if industry:
        params["industry"] = industry
    return f"/industry-research/?{urlencode(params)}"
