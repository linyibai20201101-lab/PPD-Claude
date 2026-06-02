"""Lightweight NL agent for annual report module (L3 entry)."""

from __future__ import annotations

import json
import re
from typing import Any, Callable, Dict, List, Optional

from .competitor_context import competitor_benchmark_url, industry_research_url
from .storage import list_reports, load_report

AGENT_SYSTEM = """你是年报财报分析助手。你可以：
1. 解答用户使用年报分析模块的问题
2. 根据用户问题检索已有报告摘要
3. 建议下一步操作（分析、对比、跳转竞品分析）

若用户要分析 PDF，请引导其前往 /annual-report/ 页面上传。
若用户问某公司已分析报告，根据提供的报告列表回答。
回答简洁，使用简体中文。"""


def _list_summary(limit: int = 10) -> str:
    reports = list_reports(limit=limit)
    if not reports:
        return "（暂无历史报告）"
    lines = []
    for r in reports:
        label = f"{r.get('company_name') or '?'} {r.get('report_year') or ''}".strip()
        lines.append(f"- {label} · id={r['report_id']} · {r.get('saved_at', '')[:10]}")
    return "\n".join(lines)


def detect_intent(message: str) -> str:
    m = message.lower()
    if any(k in message for k in ("列表", "历史", "有哪些报告", "已分析")):
        return "list_reports"
    if re.search(r"(报告|分析)[^\d]*([0-9]{8}_[a-f0-9]+)", message):
        return "get_report"
    if any(k in message for k in ("竞品", "竞争对手", "benchmark")):
        return "competitor_link"
    if any(k in message for k in ("行业", "industry")):
        return "industry_link"
    if any(k in message for k in ("怎么用", "如何", "帮助", "help")):
        return "help"
    return "chat"


def agent_help() -> Dict[str, Any]:
    return {
        "skill": "annual-report",
        "entry_url": "/annual-report/",
        "capabilities": [
            "上传 PDF 按模板分章分析",
            "多年报对比",
            "分章重跑",
            "导出 MD/DOCX/PDF/XLSX",
            "关键指标 JSON + 数字校验",
        ],
        "tools": [
            {"name": "list_reports", "description": "列出历史分析报告"},
            {"name": "get_report", "description": "按 report_id 读取报告摘要"},
            {"name": "competitor_link", "description": "生成竞品分析跳转链接"},
        ],
        "example_queries": [
            "有哪些已分析的年报？",
            "打开竞品分析对比比亚迪",
            "年报分析模块怎么用？",
        ],
    }


def run_agent_query(
    get_client: Callable,
    model: str,
    message: str,
    *,
    report_id: Optional[str] = None,
    company: Optional[str] = None,
    max_tokens: int = 2048,
) -> Dict[str, Any]:
    intent = detect_intent(message)
    context_parts = [f"用户问题：{message}", "", "## 历史报告", _list_summary()]

    actions: List[Dict[str, Any]] = []

    if intent == "list_reports":
        actions.append({"type": "list_reports", "reports": list_reports(15)})

    rid = report_id
    if not rid:
        m = re.search(r"([0-9]{8}_[a-f0-9]{8,})", message)
        if m:
            rid = m.group(1)

    if intent == "get_report" and rid:
        try:
            data = load_report(rid)
            context_parts.extend(["", f"## 报告 {rid} 摘要（前 3000 字）", data["result"][:3000]])
            actions.append({"type": "report_loaded", "report_id": rid})
        except FileNotFoundError:
            context_parts.append(f"\n报告 {rid} 不存在。")

    if intent == "competitor_link":
        url = competitor_benchmark_url(report_id=rid or "", company=company or "")
        actions.append({"type": "link", "url": url, "label": "打开竞品对标分析"})
        context_parts.append(f"\n跳转链接：{url}")

    if intent == "industry_link":
        url = industry_research_url(company=company or "")
        actions.append({"type": "link", "url": url, "label": "打开行业研究"})
        context_parts.append(f"\n跳转链接：{url}")

    if intent == "help":
        return {"content": json.dumps(agent_help(), ensure_ascii=False, indent=2), "actions": actions, "intent": intent}

    client = get_client()
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=AGENT_SYSTEM,
        messages=[{"role": "user", "content": "\n".join(context_parts)}],
    )
    text = ""
    for block in response.content:
        if getattr(block, "text", None):
            text += block.text

    return {"content": text.strip(), "actions": actions, "intent": intent}
