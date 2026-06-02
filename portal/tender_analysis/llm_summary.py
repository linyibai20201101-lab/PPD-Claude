"""LLM executive summary for tender market HTML reports."""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

SYSTEM_PROMPT = """你是招投标市场分析顾问。根据结构化统计数据撰写中文执行摘要。
要求：
1. 先写一段 120–200 字的总体结论（趋势、规模、结构）。
2. 再列 3 条要点（每条一行，以「- 」开头），聚焦：区域、金额段、头部厂商或采购形式。
3. 不要编造数据中没有的数字；样本不足时如实说明。
4. 只输出 Markdown，不要代码块。"""


def llm_available() -> bool:
    return bool(
        os.getenv("DEEPSEEK_API_KEY", "").strip()
        or os.getenv("ANTHROPIC_API_KEY", "").strip()
    )


def _get_client():
    import anthropic

    if os.getenv("DEEPSEEK_API_KEY", "").strip():
        return anthropic.Anthropic(
            api_key=os.getenv("DEEPSEEK_API_KEY", "").strip(),
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/anthropic"),
        )
    return anthropic.Anthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY", "").strip(),
        base_url=os.getenv("ANTHROPIC_BASE_URL") or None,
    )


def _default_model() -> str:
    if os.getenv("DEEPSEEK_API_KEY", "").strip():
        return os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    return os.getenv("ANTHROPIC_DEFAULT_MODEL", "claude-sonnet-4-20250514")


def _compact_stats(charts: Dict[str, Any], stats: dict, keyword: str) -> str:
    payload = {
        "keyword": keyword,
        "dedup": stats,
        "overview": charts.get("overview"),
        "amount_stats": charts.get("amount_stats"),
        "top_provinces": charts.get("province"),
        "top_vendors": charts.get("vendor_rank"),
        "org_type": charts.get("org_type"),
        "procurement_form": charts.get("procurement_form"),
        "market_pipeline": charts.get("market_pipeline"),
        "attachment_rate": charts.get("attachment_rate"),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _rule_based_summary(charts: Dict[str, Any], stats: dict, keyword: str) -> str:
    ov = charts.get("overview") or {}
    amt = charts.get("amount_stats") or {}
    prov = charts.get("province") or {}
    vend = charts.get("vendor_rank") or {}
    pipe = charts.get("market_pipeline") or {}
    lines = [
        f"## 执行摘要 · {keyword}",
        "",
        (
            f"本次样本在去重后共 **{stats.get('dedup_count', ov.get('total', 0))}** 条标讯记录，"
            f"近 1 年 **{ov.get('count_1y', 0)}** 条、近 3 年 **{ov.get('count_3y', 0)}** 条。"
            f"可识别金额的项目合计约 **{amt.get('total', 0):,.0f} 万元**（中位数 {amt.get('median', 0)} 万元）。"
        ),
        "",
        "### 关键洞察",
        "",
    ]
    if prov.get("provinces"):
        top3 = prov["provinces"][:3]
        lines.append(f"- **区域集中**：项目数量靠前的省份包括 { '、'.join(top3) }。")
    if vend.get("vendors"):
        lines.append(f"- **厂商格局**：中标频次较高的单位包括 { '、'.join(vend['vendors'][:3]) }。")
    if pipe:
        lines.append(
            f"- **成交结构**：已成交/中标约 {pipe.get('awarded', 0)} 条，"
            f"招标/预告类约 {pipe.get('pending', 0)} 条。"
        )
    lines.append("- **说明**：本摘要由规则引擎生成；配置 `DEEPSEEK_API_KEY` 或 `ANTHROPIC_API_KEY` 后可启用 LLM 深化解读。")
    return "\n".join(lines)


def _parse_insights(md: str) -> Tuple[str, List[str]]:
    insights: List[str] = []
    for line in md.splitlines():
        s = line.strip()
        if s.startswith("- ") or s.startswith("* ") or re.match(r"^\d+[\.\)、]", s):
            insights.append(re.sub(r"^[-*\d\.\)、\s]+", "", s))
    paragraph = ""
    for line in md.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("-") or s.startswith("*"):
            continue
        paragraph += s
        if len(paragraph) > 80:
            break
    return paragraph[:500], insights[:5]


def generate_executive_summary(
    charts: Dict[str, Any],
    stats: dict,
    keyword: str,
    *,
    use_llm: bool = True,
) -> Dict[str, Any]:
    """Return {markdown, paragraph, insights, source: llm|rules}."""
    if use_llm and llm_available():
        try:
            client = _get_client()
            user = (
                f"关键词：{keyword}\n\n统计数据：\n"
                f"{_compact_stats(charts, stats, keyword)}\n\n请输出执行摘要 Markdown。"
            )
            resp = client.messages.create(
                model=_default_model(),
                max_tokens=1200,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user}],
            )
            text = ""
            for block in resp.content:
                if hasattr(block, "text"):
                    text += block.text
            paragraph, insights = _parse_insights(text)
            if not insights and paragraph:
                insights = [paragraph[:120]]
            return {
                "markdown": text.strip(),
                "paragraph": paragraph,
                "insights": insights[:3],
                "source": "llm",
            }
        except Exception as exc:
            md = _rule_based_summary(charts, stats, keyword)
            p, ins = _parse_insights(md)
            return {
                "markdown": md + f"\n\n> LLM 未可用：{exc}",
                "paragraph": p,
                "insights": ins[:3],
                "source": "rules_fallback",
                "error": str(exc),
            }

    md = _rule_based_summary(charts, stats, keyword)
    p, ins = _parse_insights(md)
    return {"markdown": md, "paragraph": p, "insights": ins[:3], "source": "rules"}
