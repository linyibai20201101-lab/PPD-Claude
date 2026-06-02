"""Export products_master.xlsx, stats JSON, and Markdown report."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Dict

import pandas as pd


def write_products_master(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(path, index=False, engine="openpyxl")


def write_stats(summary: Dict[str, Any], path: Path) -> None:
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


def render_report_md(summary: Dict[str, Any], master_df: pd.DataFrame) -> str:
    kw = summary.get("keyword", "")
    lines = [
        f"# {kw} 标书产品信息分析报告",
        "",
        f"> 生成时间：{summary.get('generated_at', date.today().isoformat())}  ",
        f"> 来源任务：`{summary.get('source_job_id', '')}`  ",
        f"> 阶段：**统计 + 详情**（关键词+产品属性匹配正文/附件清单）",
        "",
        "---",
        "",
        "## 一、执行摘要",
        "",
        f"- 项目样本：**{summary.get('project_count', 0)}** 条",
        f"- 产品明细行：**{summary.get('product_line_count', 0)}** 行",
        f"- 详情抓取成功：**{summary.get('detail_fetched_ok', 0)}** 条",
        f"- 有附件项目：**{summary.get('with_attachment_count', 0)}** 条",
    ]
    if summary.get("total_amount_万元") is not None:
        lines.append(f"- 项目金额合计：**{summary['total_amount_万元']}** 万元")
    if summary.get("total_quantity"):
        lines.append(f"- 产品数量合计（可解析）：**{summary['total_quantity']}**")

    lines.extend(["", "---", "", "## 二、项目级统计（金额）", ""])
    if summary.get("mean_amount_万元") is not None:
        lines.append(
            f"- 平均金额 {summary.get('mean_amount_万元')} 万元 · "
            f"中位数 {summary.get('median_amount_万元')} 万元"
        )
    top_v = summary.get("top_vendors_by_amount") or []
    if top_v:
        lines.append("")
        lines.append("| 中标单位 | 金额(万元) |")
        lines.append("|----------|------------|")
        for row in top_v[:10]:
            lines.append(f"| {row['vendor']} | {row['amount_万元']} |")

    lines.extend(["", "---", "", "## 三、产品级统计", ""])
    top_p = summary.get("top_products_by_count") or []
    if top_p:
        lines.append("")
        lines.append("| 产品/关键词 | 出现次数 |")
        lines.append("|-------------|----------|")
        for row in top_p[:15]:
            lines.append(f"| {row['product']} | {row['count']} |")
    else:
        lines.append("")
        lines.append(
            "（未命中关键词产品行：请确认检索词、或开启附件 PDF/Word 解析）"
        )

    matched = summary.get("keyword_matched_lines")
    if matched is not None:
        lines.extend(["", f"- 关键词匹配产品行：**{matched}** / {summary.get('product_line_count', 0)}"])

    lines.extend([
        "",
        "---",
        "",
        "## 四、数据文件",
        "",
        "- `products_master.xlsx` — 项目+产品统筹宽表",
        "- `stats_summary.json` — 统计 JSON",
        "- `projects_enriched.json` — 项目层 enrichment",
        "",
        "## 五、下一步（附件阶段）",
        "",
        "对有附件项目：跳转原文 → 下载 PDF/Word → 参数键值并入本表。",
        "",
    ])
    return "\n".join(lines)
