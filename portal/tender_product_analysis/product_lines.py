"""Build L2 product lines and master table from project records."""

from __future__ import annotations

import json
import re
from typing import Any, List

import pandas as pd

GOV_ITEM_ROW = re.compile(
    r"^(?:\d+-\d+)\t[^\t]+\t([^\t]+)\t"
)


def _parse_products_field(raw: Any) -> List[dict]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    s = str(raw).strip()
    if not s:
        return []
    try:
        data = json.loads(s)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def _normalize_product_name(raw: str) -> str:
    """If name is a full tab-separated bid row, extract 采购标的 column."""
    s = (raw or "").strip()
    if not s:
        return ""
    if "\t" in s:
        m = re.match(
            r"^(?:\d+-\d+)\t[^\t]+\t([^\t]+)\t", s
        )
        if m:
            return m.group(1).strip()
        parts = s.split("\t")
        if len(parts) >= 3:
            return parts[2].strip()
    return s[:120]


def build_product_lines(records: List[dict], keyword: str = "") -> pd.DataFrame:
    rows: List[dict] = []
    for pi, rec in enumerate(records):
        project_id = rec.get("id") or f"p{pi+1}"
        products = _parse_products_field(rec.get("产品明细"))
        base = {
            "project_id": project_id,
            "项目名称": rec.get("项目名称", ""),
            "发布时间": rec.get("发布时间") or rec.get("日期", ""),
            "地区": rec.get("地区", ""),
            "预算金额": rec.get("预算金额") or rec.get("金额", ""),
            "项目类型": rec.get("项目类型") or rec.get("状态", ""),
            "行业类型": rec.get("行业类型", ""),
            "采购单位": rec.get("采购单位", ""),
            "中标单位": rec.get("中标单位", ""),
            "有附件": rec.get("有附件", False),
            "详情链接": rec.get("详情链接", ""),
            "详情抓取": rec.get("详情抓取", ""),
            "产品数量_详情": rec.get("产品数量", 0),
        }

        if products:
            seen: set[str] = set()
            li = 0
            for prod in products:
                if not isinstance(prod, dict):
                    continue
                pname = _normalize_product_name(
                    prod.get("产品名称") or prod.get("name", "")
                )
                model = str(prod.get("型号") or prod.get("model", "")).strip()
                dedupe_key = f"{pname}|{model}"
                if not pname or dedupe_key in seen:
                    continue
                seen.add(dedupe_key)

                li += 1
                row = {**base, "line_id": f"{project_id}_L{li}"}
                row["产品名称"] = pname
                row["品牌"] = prod.get("品牌", "")
                row["型号"] = model
                row["数量"] = prod.get("数量") or prod.get("qty", "")
                row["单位"] = prod.get("单位", "")
                row["单价"] = prod.get("单价") or prod.get("price", "")
                row["行金额"] = prod.get("总价") or prod.get("参考金额") or ""
                row["参数来源"] = prod.get("参数来源", "detail_page")
                row["匹配得分"] = prod.get("匹配得分", "")
                row["匹配关键词"] = prod.get("匹配关键词", keyword)
                specs = prod.get("规格参数") or {}
                if isinstance(specs, dict) and specs:
                    row["规格摘要"] = " · ".join(
                        f"{k}:{v}" for k, v in list(specs.items())[:6]
                    )
                else:
                    row["规格摘要"] = ""
                rows.append(row)
        else:
            row = {**base, "line_id": f"{project_id}_L0"}
            row["产品名称"] = _guess_product_from_title(rec.get("项目名称", ""), keyword)
            row["品牌"] = ""
            row["型号"] = ""
            row["数量"] = rec.get("总数量", "")
            row["单价"] = ""
            row["行金额"] = ""
            row["参数来源"] = "project_only"
            row["规格摘要"] = ""
            rows.append(row)

    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df.drop_duplicates(
        subset=["project_id", "产品名称", "型号"],
        keep="first",
    ).reset_index(drop=True)


def _guess_product_from_title(title: str, keyword: str) -> str:
    if keyword and keyword in title:
        return keyword
    return title[:60] if title else ""
