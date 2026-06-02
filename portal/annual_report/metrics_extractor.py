"""Extract structured financial metrics from report markdown / PDF text."""

from __future__ import annotations

import json
import re
from typing import Any, Callable, Dict, List, Optional

METRIC_KEYS = [
    "company_name",
    "report_year",
    "revenue",
    "revenue_yoy",
    "net_profit",
    "net_profit_yoy",
    "gross_margin",
    "net_margin",
    "roe",
    "debt_ratio",
    "operating_cashflow",
    "rd_expense",
    "rd_ratio",
    "eps",
]


def _parse_number(raw: str) -> Optional[float]:
    s = raw.strip().replace(",", "").replace("，", "")
    m = re.search(r"(-?\d+\.?\d*)\s*(%|％)?", s)
    if not m:
        return None
    val = float(m.group(1))
    if m.group(2):
        return val
    if "亿" in s:
        return val * 1e8
    if "万" in s:
        return val * 1e4
    return val


def extract_metrics_regex(markdown: str, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Rule-based extraction as fallback."""
    meta = meta or {}
    metrics: Dict[str, Any] = {
        "company_name": meta.get("company_name") or "",
        "report_year": meta.get("report_year") or "",
    }

    patterns = {
        "revenue": r"营业收入[^\d]*?(-?\d[\d,.]*)\s*(亿|万|元|%|％)?",
        "net_profit": r"(?:归母净利润|净利润)[^\d]*?(-?\d[\d,.]*)\s*(亿|万|元|%|％)?",
        "gross_margin": r"毛利率[^\d]*?(-?\d[\d,.]*)\s*(%|％)",
        "roe": r"ROE[^\d]*?(-?\d[\d,.]*)\s*(%|％)",
        "operating_cashflow": r"经营活动.*?现金流[^\d]*?(-?\d[\d,.]*)\s*(亿|万|元)?",
        "rd_expense": r"研发费用[^\d]*?(-?\d[\d,.]*)\s*(亿|万|元)?",
        "rd_ratio": r"研发.*?占.*?营收[^\d]*?(-?\d[\d,.]*)\s*(%|％)",
        "eps": r"(?:每股收益|EPS)[^\d]*?(-?\d[\d,.]*)\s*元?",
    }

    for key, pat in patterns.items():
        m = re.search(pat, markdown, re.I | re.S)
        if m:
            unit = m.group(2) or ""
            metrics[key] = _parse_number(m.group(1) + unit)

    yoy_pat = r"同比[^\d]*?(-?\d[\d.]*)\s*(%|％)"
    yoys = re.findall(yoy_pat, markdown)
    if yoys:
        metrics["revenue_yoy"] = _parse_number(yoys[0][0] + (yoys[0][1] or "%"))

    metrics["_source"] = "regex"
    return metrics


def extract_metrics_llm(
    get_client: Callable,
    model: str,
    markdown: str,
    pdf_excerpt: str = "",
) -> Dict[str, Any]:
    client = get_client()
    prompt = f"""从以下年报分析 Markdown 中提取关键财务指标，输出 JSON 对象（不要 markdown 代码块）。

字段（无法确定则 null）：
company_name, report_year, revenue, revenue_yoy, net_profit, net_profit_yoy,
gross_margin, net_margin, roe, debt_ratio, operating_cashflow, rd_expense, rd_ratio, eps

数值：金额用「元」为单位的数字；百分比用数字不带%符号。

## 分析报告
{markdown[:12000]}

## 原文摘录（辅助）
{pdf_excerpt[:8000]}
"""
    response = client.messages.create(
        model=model,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    text = ""
    for block in response.content:
        if getattr(block, "text", None):
            text += block.text
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    data = json.loads(text)
    data["_source"] = "llm"
    return data


def extract_metrics(
    markdown: str,
    meta: Optional[Dict[str, Any]] = None,
    *,
    get_client: Optional[Callable] = None,
    model: Optional[str] = None,
    pdf_excerpt: str = "",
    use_llm: bool = True,
) -> Dict[str, Any]:
    if use_llm and get_client and model:
        try:
            return extract_metrics_llm(get_client, model, markdown, pdf_excerpt)
        except Exception:
            pass
    return extract_metrics_regex(markdown, meta)


def metrics_to_rows(metrics: Dict[str, Any]) -> List[List[Any]]:
    labels = {
        "company_name": "公司名称",
        "report_year": "报告年度",
        "revenue": "营业收入(元)",
        "revenue_yoy": "营收同比(%)",
        "net_profit": "归母净利润(元)",
        "net_profit_yoy": "净利润同比(%)",
        "gross_margin": "毛利率(%)",
        "net_margin": "净利率(%)",
        "roe": "ROE(%)",
        "debt_ratio": "资产负债率(%)",
        "operating_cashflow": "经营现金流(元)",
        "rd_expense": "研发费用(元)",
        "rd_ratio": "研发/营收(%)",
        "eps": "每股收益(元)",
    }
    rows = [["指标", "数值"]]
    for k, label in labels.items():
        if k in metrics and metrics[k] is not None and not k.startswith("_"):
            rows.append([label, metrics[k]])
    return rows
