"""Product-focused statistics (amount, quantity, product TOP)."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd

PORTAL_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PORTAL_ROOT / "skills" / "tender-analysis" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from data_cleaner import clean_amount, extract_province, get_region  # noqa: E402
from info_extractor import enrich_dataframe  # noqa: E402


def _parse_jianyu_date(text: Any, ref=None) -> Any:
    import re
    from datetime import timedelta

    ref = ref or date.today()
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return pd.NaT
    s = str(text).strip()
    if not s:
        return pd.NaT
    if re.search(r"(小时前|分钟前|刚刚|今天)", s):
        return pd.Timestamp(ref)
    m = re.match(r"(\d+)天前", s)
    if m:
        return pd.Timestamp(ref - timedelta(days=int(m.group(1))))
    m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
    if m:
        return pd.Timestamp(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.match(r"(\d{1,2})-(\d{1,2})", s)
    if m:
        return pd.Timestamp(ref.year, int(m.group(1)), int(m.group(2)))
    return pd.to_datetime(s, errors="coerce")


def prepare_projects_df(records: List[dict], keyword: str = "") -> Tuple[pd.DataFrame, dict]:
    df = pd.DataFrame(records)
    if df.empty:
        return df, {}

    if "金额" not in df.columns and "预算金额" in df.columns:
        df["金额"] = df["预算金额"]
    if "日期" not in df.columns and "发布时间" in df.columns:
        df["日期"] = df["发布时间"]

    if "金额" in df.columns:
        df["金额_万元"] = df["金额"].apply(clean_amount)
    if "地区" in df.columns:
        df["省份"] = df["地区"].apply(extract_province)
        df["大区"] = df["省份"].apply(get_region)

    df = enrich_dataframe(
        df,
        project_col="项目名称" if "项目名称" in df.columns else None,
        buyer_col="采购单位" if "采购单位" in df.columns else None,
        vendor_col="中标单位" if "中标单位" in df.columns else None,
        detail_col="项目名称",
        keyword=keyword,
    )

    detail_ok = int((df.get("详情抓取", pd.Series()) == "ok").sum()) if "详情抓取" in df.columns else 0
    with_products = int((df.get("产品数量", 0).fillna(0).astype(float) > 0).sum()) if "产品数量" in df.columns else 0

    meta = {
        "project_count": len(df),
        "detail_fetched_ok": detail_ok,
        "projects_with_product_lines": with_products,
    }
    if "product_line_count" not in meta:
        meta["dedupe_note"] = "同项目多条公告已在分析前合并"
    return df, meta


def compute_stats_summary(
    projects_df: pd.DataFrame,
    master_df: pd.DataFrame,
    keyword: str,
    source_job_id: str,
) -> Dict[str, Any]:
    summary: Dict[str, Any] = {
        "keyword": keyword,
        "source_job_id": source_job_id,
        "generated_at": date.today().isoformat(),
        "project_count": len(projects_df),
        "product_line_count": len(master_df),
        "with_attachment_count": 0,
        "detail_fetched_ok": 0,
    }

    if projects_df.empty:
        return summary

    if "有附件" in projects_df.columns:
        summary["with_attachment_count"] = int(
            projects_df["有附件"].apply(lambda x: str(x).lower() in ("true", "1") or x is True).sum()
        )
    if "详情抓取" in projects_df.columns:
        summary["detail_fetched_ok"] = int((projects_df["详情抓取"] == "ok").sum())

    if "金额_万元" in projects_df.columns:
        amounts = projects_df["金额_万元"].dropna()
        if len(amounts):
            summary["total_amount_万元"] = round(float(amounts.sum()), 2)
            summary["median_amount_万元"] = round(float(amounts.median()), 2)
            summary["mean_amount_万元"] = round(float(amounts.mean()), 2)

    if "省份" in projects_df.columns:
        prov_df = projects_df[projects_df["省份"] != "未知"]
        summary["projects_by_region"] = {
            str(k): int(v) for k, v in prov_df["省份"].value_counts().head(10).items()
        }
        if "金额_万元" in projects_df.columns:
            amt_reg = prov_df.groupby("省份")["金额_万元"].sum().sort_values(ascending=False).head(10)
            summary["amount_by_region"] = {str(k): round(float(v), 2) for k, v in amt_reg.items()}

    if "中标单位" in projects_df.columns and "金额_万元" in projects_df.columns:
        vend = (
            projects_df[projects_df["中标单位"].notna() & (projects_df["中标单位"].astype(str).str.strip() != "")]
            .groupby("中标单位")["金额_万元"]
            .sum()
            .sort_values(ascending=False)
            .head(10)
        )
        summary["top_vendors_by_amount"] = [
            {"vendor": str(k), "amount_万元": round(float(v), 2)} for k, v in vend.items()
        ]

    if not master_df.empty and "产品名称" in master_df.columns:
        names = master_df[master_df["产品名称"].astype(str).str.strip() != ""]["产品名称"].value_counts().head(15)
        summary["top_products_by_count"] = [
            {"product": str(k), "count": int(v)} for k, v in names.items()
        ]

        qty_col = master_df["数量"]
        numeric_qty = pd.to_numeric(qty_col, errors="coerce")
        summary["lines_with_quantity"] = int(numeric_qty.notna().sum())
        summary["total_quantity"] = int(numeric_qty.sum()) if numeric_qty.notna().any() else 0

        if "匹配得分" in master_df.columns:
            scores = pd.to_numeric(master_df["匹配得分"], errors="coerce")
            summary["keyword_matched_lines"] = int((scores >= 35).sum())
        else:
            src = master_df.get("参数来源", pd.Series())
            summary["keyword_matched_lines"] = int(
                src.astype(str).str.contains("detail_page|attachment", regex=True).sum()
            )

    return summary
