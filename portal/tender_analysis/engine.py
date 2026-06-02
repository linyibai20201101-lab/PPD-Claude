"""标讯分析引擎：清洗、统计、生成 HTML 报告."""

from __future__ import annotations

import json
import re
import sys
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

PORTAL_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PORTAL_ROOT / "skills" / "tender-analysis" / "scripts"
DATA_DIR = PORTAL_ROOT / "tender_raw_data"
REPORT_DIR = DATA_DIR / "analysis"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from data_cleaner import clean_and_dedup, get_region  # noqa: E402
from info_extractor import enrich_dataframe  # noqa: E402


def _parse_jianyu_date(text: Any, ref: Optional[date] = None) -> Optional[pd.Timestamp]:
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return None
    ref = ref or date.today()
    s = str(text).strip()
    if not s or s == "—":
        return None
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
    ts = pd.to_datetime(s, errors="coerce")
    return ts if pd.notna(ts) else None


def records_to_dataframe(records: List[dict]) -> pd.DataFrame:
    rows = []
    for r in records:
        rows.append(
            {
                "项目名称": r.get("project_name") or r.get("项目名称") or "",
                "采购单位": r.get("buyer") or r.get("采购单位") or "",
                "中标单位": r.get("winner") or r.get("中标单位") or "",
                "金额": r.get("amount") or r.get("预算金额") or r.get("金额") or "",
                "日期": r.get("bid_date") or r.get("发布时间") or r.get("日期") or "",
                "地区": r.get("region") or r.get("地区") or "",
                "状态": r.get("project_type") or r.get("项目类型") or r.get("状态") or "",
                "行业类型": r.get("industry") or r.get("行业类型") or "",
                "有附件": r.get("有附件") or r.get("has_attachment") or False,
            }
        )
    return pd.DataFrame(rows)


def load_data_from_job(job_id: str) -> Tuple[pd.DataFrame, str]:
    job_dir = DATA_DIR / job_id
    if not job_dir.is_dir():
        raise FileNotFoundError(f"任务数据不存在: {job_id}")

    keyword = "标讯"
    csv_files = sorted(job_dir.glob("filtered_*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    if csv_files:
        df = pd.read_csv(csv_files[0], encoding="utf-8-sig")
        keyword = csv_files[0].stem.replace("filtered_", "") or keyword
        return df, keyword

    json_candidates = sorted(
        list(job_dir.glob("jianyu_*.json")) + [job_dir / "partial_results.json"],
        key=lambda p: p.stat().st_mtime if p.exists() else 0,
        reverse=True,
    )
    for jp in json_candidates:
        if jp.is_file():
            data = json.loads(jp.read_text(encoding="utf-8"))
            if isinstance(data, list) and data:
                df = pd.DataFrame(data)
                m = re.search(r"jianyu_(.+?)_\d{8}", jp.name)
                if m:
                    keyword = m.group(1)
                return df, keyword

    raise FileNotFoundError(f"任务 {job_id} 下未找到可分析的数据文件")


def normalize_jianyu_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename = {
        "预算金额": "金额",
        "发布时间": "日期",
        "项目类型": "状态",
    }
    for src, dst in rename.items():
        if src in df.columns and dst not in df.columns:
            df = df.rename(columns={src: dst})
    return df


def prepare_dataframe(df: pd.DataFrame, keyword: Optional[str] = None) -> Tuple[pd.DataFrame, dict]:
    df = normalize_jianyu_columns(df.copy())
    if "日期" in df.columns:
        df["日期"] = df["日期"].apply(_parse_jianyu_date)

    df, stats = clean_and_dedup(
        df,
        project_name_col="项目名称" if "项目名称" in df.columns else None,
        buyer_col="采购单位" if "采购单位" in df.columns else None,
        status_col="状态" if "状态" in df.columns else None,
        amount_col="金额" if "金额" in df.columns else None,
        address_col="地区" if "地区" in df.columns else None,
        date_col=None,
    )
    if "日期" in df.columns:
        df["日期"] = pd.to_datetime(df["日期"], errors="coerce")
    df = enrich_dataframe(df, keyword=keyword)
    if "行业类型" in df.columns:
        mask = df["行业类型"].notna() & (df["行业类型"].astype(str).str.strip() != "")
        df.loc[mask, "行业名称"] = df.loc[mask, "行业类型"]
    return df, stats


def _count_in_years(df: pd.DataFrame, years: int) -> int:
    if "日期" not in df.columns:
        return len(df)
    cutoff = pd.Timestamp(date.today() - timedelta(days=365 * years))
    valid = df["日期"].dropna()
    if valid.empty:
        return len(df)
    return int((valid >= cutoff).sum())


def _price_bins(df: pd.DataFrame) -> pd.Series:
    bins = [0, 5, 20, 50, 100, 500, float("inf")]
    labels = ["<5万", "5-20万", "20-50万", "50-100万", "100-500万", ">500万"]
    if "金额_万元" not in df.columns:
        return pd.Series(dtype=int)
    return pd.cut(df["金额_万元"], bins=bins, labels=labels)


def compute_charts(df: pd.DataFrame) -> Dict[str, Any]:
    charts: Dict[str, Any] = {}
    df = df.copy()
    if "日期" in df.columns:
        df["日期"] = pd.to_datetime(df["日期"], errors="coerce")

    charts["overview"] = {
        "total": len(df),
        "count_1y": _count_in_years(df, 1),
        "count_3y": _count_in_years(df, 3),
        "with_amount": int(df["金额_万元"].notna().sum()) if "金额_万元" in df.columns else 0,
        "with_winner": int((df["中标单位"].notna() & (df["中标单位"].astype(str).str.strip() != "")).sum())
        if "中标单位" in df.columns
        else 0,
    }

    if "日期" in df.columns and df["日期"].notna().any():
        df_y = df.dropna(subset=["日期"]).copy()
        df_y["年份"] = df_y["日期"].dt.year
        year_trend = df_y.groupby("年份").size().reset_index(name="数量")
        charts["year_trend"] = {
            "years": year_trend["年份"].astype(int).tolist(),
            "counts": year_trend["数量"].tolist(),
        }
        df_y["年月"] = df_y["日期"].dt.to_period("M").astype(str)
        monthly = df_y.groupby("年月").size().tail(24)
        charts["monthly_trend"] = {
            "months": monthly.index.tolist(),
            "counts": monthly.values.tolist(),
        }

    if "机构类型" in df.columns:
        org_dist = df["机构类型"].value_counts()
        charts["org_type"] = {
            "data": [{"name": k, "value": int(v)} for k, v in org_dist.items()],
        }

    if "省份" in df.columns:
        prov = df[df["省份"] != "未知"]["省份"].value_counts().head(15)
        charts["province"] = {
            "provinces": prov.index.tolist(),
            "counts": prov.values.tolist(),
        }
    if "大区" in df.columns:
        region_dist = df[df["大区"] != "其他"]["大区"].value_counts()
        charts["region_pie"] = {
            "data": [{"name": k, "value": int(v)} for k, v in region_dist.items()],
        }

    if "金额_万元" in df.columns:
        amounts = df["金额_万元"].dropna()
        if len(amounts):
            charts["amount_stats"] = {
                "total": round(float(amounts.sum()), 2),
                "mean": round(float(amounts.mean()), 2),
                "median": round(float(amounts.median()), 2),
                "max": round(float(amounts.max()), 2),
                "count": int(amounts.count()),
            }
        df = df.copy()
        df["价格区间"] = _price_bins(df)
        price_dist = df["价格区间"].value_counts()
        labels = ["<5万", "5-20万", "20-50万", "50-100万", "100-500万", ">500万"]
        charts["price_range"] = {
            "ranges": labels,
            "counts": [int(price_dist.get(l, 0)) for l in labels],
        }
        if "年份" not in df.columns and "日期" in df.columns and pd.api.types.is_datetime64_any_dtype(df["日期"]):
            df["年份"] = df["日期"].dt.year
        if "年份" in df.columns:
            amt_year = df.groupby("年份")["金额_万元"].sum().dropna()
            charts["amount_year_trend"] = {
                "years": [int(y) for y in amt_year.index.tolist()],
                "amounts": [round(float(v), 2) for v in amt_year.values.tolist()],
            }

    proc_col = "状态" if "状态" in df.columns else None
    if proc_col:
        form_dist = df[proc_col].fillna("未知").astype(str).value_counts().head(12)
        charts["procurement_form"] = {
            "data": [{"name": k, "value": int(v)} for k, v in form_dist.items()],
        }
        if "年份" in df.columns:
            form_year = df.groupby(["年份", proc_col]).size().unstack(fill_value=0)
            charts["form_year_trend"] = {
                "years": [int(y) for y in form_year.index.tolist()],
                "forms": form_year.columns.tolist(),
                "series": [
                    {"name": str(c), "data": form_year[c].tolist()} for c in form_year.columns
                ],
            }

    if "机构类型" in df.columns and "省份" in df.columns:
        cross = df.groupby(["机构类型", "省份"]).size().unstack(fill_value=0)
        top_prov = df[df["省份"] != "未知"]["省份"].value_counts().head(8).index
        cross = cross[[c for c in top_prov if c in cross.columns]]
        charts["org_region_cross"] = {
            "orgs": cross.index.tolist(),
            "provinces": cross.columns.tolist(),
            "data": [[int(cross.iloc[i, j]) for j in range(len(cross.columns))] for i in range(len(cross))],
        }

    if "省份" in df.columns and "价格区间" in df.columns:
        rp = df.groupby(["省份", "价格区间"]).size().unstack(fill_value=0)
        top_p = df[df["省份"] != "未知"]["省份"].value_counts().head(8).index
        rp = rp.loc[[p for p in top_p if p in rp.index]]
        charts["region_amount_cross"] = {
            "provinces": rp.index.tolist(),
            "ranges": [str(c) for c in rp.columns.tolist()],
            "data": rp.values.tolist(),
        }

    if "机构类型" in df.columns and "价格区间" in df.columns:
        oa = df.groupby(["机构类型", "价格区间"]).size().unstack(fill_value=0)
        charts["org_amount_cross"] = {
            "orgs": oa.index.tolist(),
            "ranges": [str(c) for c in oa.columns.tolist()],
            "data": oa.values.tolist(),
        }

    if "厂商名称" in df.columns:
        vendors = df[df["厂商名称"] != "未知"]["厂商名称"].value_counts().head(10)
        charts["vendor_rank"] = {
            "vendors": vendors.index.tolist(),
            "counts": vendors.values.tolist(),
        }

    if "行业名称" in df.columns:
        ind = df["行业名称"].value_counts().head(10)
        charts["industry"] = {
            "names": ind.index.tolist(),
            "counts": ind.values.tolist(),
        }

    if proc_col:
        awarded_kw = ("成交", "中标", "结果")
        df_aw = df[proc_col].astype(str).apply(lambda x: any(k in x for k in awarded_kw))
        charts["market_pipeline"] = {
            "awarded": int(df_aw.sum()),
            "pending": int((~df_aw).sum()),
        }

    if "有附件" in df.columns:
        att = df["有附件"].apply(lambda x: str(x).lower() in ("true", "1", "是") or x is True).sum()
        charts["attachment_rate"] = {
            "with_attachment": int(att),
            "without": int(len(df) - att),
        }

    return charts


def _summary_html_block(summary: Optional[Dict[str, Any]]) -> str:
    if not summary or not summary.get("markdown"):
        return ""
    md = summary["markdown"]
    import html as html_mod

    esc = html_mod.escape(md)
    lines = []
    for line in esc.split("\n"):
        if line.startswith("## "):
            lines.append(f'<h2 class="sum-h2">{line[3:]}</h2>')
        elif line.startswith("### "):
            lines.append(f'<h3 class="sum-h3">{line[4:]}</h3>')
        elif line.startswith("- "):
            lines.append(f"<li>{line[2:]}</li>")
        elif line.strip():
            lines.append(f"<p>{line}</p>")
    body = "\n".join(lines)
    if "<li>" in body:
        body = body.replace("<li>", '<ul class="sum-ul"><li>').replace("</li>\n<li>", "</li><li>")
        if "</li>" in body and "</ul>" not in body:
            body = body + "</ul>"
    insights = summary.get("insights") or []
    chips = "".join(f'<span class="insight-chip">{html_mod.escape(str(i)[:80])}</span>' for i in insights[:3])
    src = summary.get("source", "rules")
    return f"""
<div class="executive-summary">
  <div class="sum-head">📝 执行摘要 <span class="sum-src">({src})</span></div>
  <div class="insight-chips">{chips}</div>
  <div class="sum-body">{body}</div>
</div>"""


def generate_html(
    df: pd.DataFrame,
    charts: Dict[str, Any],
    stats: dict,
    keyword: str,
    output_path: Path,
    *,
    executive_summary: Optional[Dict[str, Any]] = None,
) -> None:
    ov = charts.get("overview", {})
    amt = charts.get("amount_stats", {})
    charts_json = json.dumps(charts, ensure_ascii=False)
    gen_time = datetime.now().strftime("%Y-%m-%d %H:%M")

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{keyword} - 标讯分析报告</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: "Microsoft YaHei", -apple-system, sans-serif; background: #f0f2f5; color: #333; }}
.header {{ background: linear-gradient(135deg, #4338ca, #0d9488); color: white; padding: 28px 32px; }}
.header h1 {{ font-size: 26px; font-weight: 700; }}
.header p {{ font-size: 13px; opacity: 0.9; margin-top: 8px; line-height: 1.6; }}
.kpi-row {{ display: flex; gap: 14px; padding: 20px 24px; flex-wrap: wrap; }}
.kpi-card {{ flex: 1; min-width: 150px; background: white; border-radius: 10px;
  padding: 18px; box-shadow: 0 2px 10px rgba(0,0,0,.06); text-align: center; }}
.kpi-card .value {{ font-size: 28px; font-weight: 700; color: #4338ca; }}
.kpi-card .label {{ font-size: 12px; color: #64748b; margin-top: 4px; }}
.section {{ padding: 0 24px 24px; }}
.section-title {{ font-size: 17px; font-weight: 700; color: #1e293b;
  border-left: 4px solid #0d9488; padding-left: 12px; margin: 24px 0 14px; }}
.chart-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(460px, 1fr)); gap: 16px; }}
.chart-card {{ background: white; border-radius: 10px; padding: 16px;
  box-shadow: 0 2px 10px rgba(0,0,0,.06); }}
.chart-card h3 {{ font-size: 14px; color: #475569; margin-bottom: 10px; font-weight: 600; }}
.chart-box {{ width: 100%; height: 320px; }}
.chart-wide {{ grid-column: 1 / -1; }}
.footer {{ text-align: center; padding: 20px; color: #94a3b8; font-size: 12px; }}
.executive-summary {{ background: #fff; margin: 16px 24px 0; border-radius: 12px; padding: 20px 24px;
  box-shadow: 0 2px 12px rgba(0,0,0,.06); border-left: 4px solid #f59e0b; }}
.sum-head {{ font-size: 16px; font-weight: 700; color: #1e293b; margin-bottom: 10px; }}
.sum-src {{ font-size: 12px; color: #94a3b8; font-weight: 400; }}
.insight-chips {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }}
.insight-chip {{ background: #fef3c7; color: #92400e; font-size: 12px; padding: 6px 10px; border-radius: 8px; }}
.sum-body {{ font-size: 14px; line-height: 1.7; color: #334155; }}
.sum-body p {{ margin: 8px 0; }}
.sum-ul {{ margin: 8px 0 8px 20px; }}
</style>
</head>
<body>
<div class="header">
  <h1>📊 {keyword} · 标讯分析报告</h1>
  <p>生成时间：{gen_time} · 原始 {stats.get('original_count', 0)} 条 → 去重后 {stats.get('dedup_count', 0)} 条（去重率 {stats.get('dedup_rate', 0)}%）</p>
</div>
{_summary_html_block(executive_summary)}

<div class="kpi-row">
  <div class="kpi-card"><div class="value">{ov.get('count_1y', 0)}</div><div class="label">近1年项目数</div></div>
  <div class="kpi-card"><div class="value">{ov.get('count_3y', 0)}</div><div class="label">近3年项目数</div></div>
  <div class="kpi-card"><div class="value">{ov.get('total', 0)}</div><div class="label">样本项目总数</div></div>
  <div class="kpi-card"><div class="value">{amt.get('total', 0):,.0f}</div><div class="label">总金额（万元）</div></div>
  <div class="kpi-card"><div class="value">{ov.get('with_winner', 0)}</div><div class="label">含中标单位</div></div>
</div>

<div class="section">
  <div class="section-title">1. 招投标概况</div>
  <div class="chart-grid">
    <div class="chart-card"><h3>年度项目数量趋势</h3><div class="chart-box" id="c_year"></div></div>
    <div class="chart-card"><h3>月度项目趋势（近24个月）</h3><div class="chart-box" id="c_month"></div></div>
  </div>
</div>

<div class="section">
  <div class="section-title">2. 采购单位类型分析</div>
  <div class="chart-grid">
    <div class="chart-card"><h3>采购单位类型分布</h3><div class="chart-box" id="c_org"></div></div>
  </div>
</div>

<div class="section">
  <div class="section-title">3. 采购地区分布分析</div>
  <div class="chart-grid">
    <div class="chart-card"><h3>省份项目数量 Top15</h3><div class="chart-box" id="c_prov"></div></div>
    <div class="chart-card"><h3>大区分布</h3><div class="chart-box" id="c_region"></div></div>
  </div>
</div>

<div class="section">
  <div class="section-title">4. 招投标金额分析</div>
  <div class="chart-grid">
    <div class="chart-card"><h3>价格区间分布</h3><div class="chart-box" id="c_price"></div></div>
    <div class="chart-card"><h3>年度金额趋势（万元）</h3><div class="chart-box" id="c_amt_year"></div></div>
  </div>
</div>

<div class="section">
  <div class="section-title">5. 采购形式分析</div>
  <div class="chart-grid">
    <div class="chart-card"><h3>采购形式 / 公告类型分布</h3><div class="chart-box" id="c_form"></div></div>
    <div class="chart-card chart-wide"><h3>采购形式年度趋势</h3><div class="chart-box" id="c_form_year"></div></div>
  </div>
</div>

<div class="section">
  <div class="section-title">6. 单位 · 地区 · 金额交叉分析</div>
  <div class="chart-grid">
    <div class="chart-card chart-wide"><h3>采购单位类型 × 省份（项目数）</h3><div class="chart-box" id="c_org_reg" style="height:360px"></div></div>
    <div class="chart-card chart-wide"><h3>省份 × 价格区间</h3><div class="chart-box" id="c_reg_amt" style="height:360px"></div></div>
    <div class="chart-card chart-wide"><h3>采购单位类型 × 价格区间</h3><div class="chart-box" id="c_org_amt" style="height:340px"></div></div>
  </div>
</div>

<div class="section">
  <div class="section-title">市场趋势补充</div>
  <div class="chart-grid">
    <div class="chart-card"><h3>中标厂商 Top10</h3><div class="chart-box" id="c_vendor"></div></div>
    <div class="chart-card"><h3>行业分布</h3><div class="chart-box" id="c_ind"></div></div>
    <div class="chart-card"><h3>成交/未成交结构</h3><div class="chart-box" id="c_pipe"></div></div>
  </div>
</div>

<div class="footer">ccbaby 标讯分析 · 数据来源剑鱼标讯 · 报告可离线保存</div>

<script>
const D = {charts_json};

function chart(id, option) {{
  const el = document.getElementById(id);
  if (!el) return;
  const c = echarts.init(el);
  c.setOption(option);
  window.addEventListener('resize', () => c.resize());
}}

if (D.year_trend) chart('c_year', {{
  tooltip: {{ trigger: 'axis' }},
  xAxis: {{ type: 'category', data: D.year_trend.years }},
  yAxis: {{ type: 'value', name: '项目数' }},
  series: [{{ type: 'bar', data: D.year_trend.counts, itemStyle: {{ color: '#4338ca' }},
    label: {{ show: true, position: 'top' }} }}]
}});

if (D.monthly_trend) chart('c_month', {{
  tooltip: {{ trigger: 'axis' }},
  xAxis: {{ type: 'category', data: D.monthly_trend.months, axisLabel: {{ rotate: 45, fontSize: 10 }} }},
  yAxis: {{ type: 'value' }},
  series: [{{ type: 'line', data: D.monthly_trend.counts, smooth: true, areaStyle: {{ opacity: 0.15 }},
    itemStyle: {{ color: '#0d9488' }} }}]
}});

if (D.org_type) chart('c_org', {{
  tooltip: {{ trigger: 'item' }},
  legend: {{ bottom: 0 }},
  series: [{{ type: 'pie', radius: ['38%','68%'], data: D.org_type.data,
    label: {{ formatter: '{{b}}\\n{{d}}%' }} }}]
}});

if (D.province) {{
  const p = D.province.provinces.slice().reverse();
  const c = D.province.counts.slice().reverse();
  chart('c_prov', {{
    tooltip: {{ trigger: 'axis' }},
    xAxis: {{ type: 'value' }},
    yAxis: {{ type: 'category', data: p, axisLabel: {{ fontSize: 11 }} }},
    series: [{{ type: 'bar', data: c, itemStyle: {{ color: '#0d9488' }}, label: {{ show: true, position: 'right' }} }}]
  }});
}}

if (D.region_pie) chart('c_region', {{
  tooltip: {{ trigger: 'item' }},
  series: [{{ type: 'pie', radius: '65%', data: D.region_pie.data }}]
}});

if (D.price_range) chart('c_price', {{
  tooltip: {{ trigger: 'axis' }},
  xAxis: {{ type: 'category', data: D.price_range.ranges }},
  yAxis: {{ type: 'value' }},
  series: [{{ type: 'bar', data: D.price_range.counts, itemStyle: {{ color: '#ea580c' }},
    label: {{ show: true, position: 'top' }} }}]
}});

if (D.amount_year_trend) chart('c_amt_year', {{
  tooltip: {{ trigger: 'axis' }},
  xAxis: {{ type: 'category', data: D.amount_year_trend.years }},
  yAxis: {{ type: 'value', name: '万元' }},
  series: [{{ type: 'line', data: D.amount_year_trend.amounts, smooth: true,
    itemStyle: {{ color: '#dc2626' }}, label: {{ show: true }} }}]
}});

if (D.procurement_form) chart('c_form', {{
  tooltip: {{ trigger: 'item' }},
  legend: {{ type: 'scroll', bottom: 0 }},
  series: [{{ type: 'pie', radius: '62%', data: D.procurement_form.data }}]
}});

if (D.form_year_trend) chart('c_form_year', {{
  tooltip: {{ trigger: 'axis' }},
  legend: {{ bottom: 0, type: 'scroll' }},
  xAxis: {{ type: 'category', data: D.form_year_trend.years }},
  yAxis: {{ type: 'value' }},
  series: D.form_year_trend.series.map(s => ({{ ...s, type: 'bar', stack: 'total' }}))
}});

function heat(id, cfg, xLabel, yLabel) {{
  const data = [];
  cfg.data.forEach((row, yi) => row.forEach((val, xi) => data.push([xi, yi, val])));
  const maxVal = Math.max(1, ...data.map(d => d[2]));
  chart(id, {{
    tooltip: {{ formatter: p => `${{cfg[yLabel][p.data[1]]}} / ${{cfg[xLabel][p.data[0]]}}: ${{p.data[2]}}` }},
    grid: {{ left: 100, right: 40, bottom: 60, top: 20 }},
    xAxis: {{ type: 'category', data: cfg[xLabel], axisLabel: {{ rotate: 30, fontSize: 10 }} }},
    yAxis: {{ type: 'category', data: cfg[yLabel], axisLabel: {{ fontSize: 11 }} }},
    visualMap: {{ min: 0, max: maxVal, calculable: true, orient: 'horizontal', bottom: 0,
      inRange: {{ color: ['#eef2ff','#4338ca'] }} }},
    series: [{{ type: 'heatmap', data, label: {{ show: true }} }}]
  }});
}}

if (D.org_region_cross) heat('c_org_reg', D.org_region_cross, 'provinces', 'orgs');
if (D.region_amount_cross) {{
  const ra = D.region_amount_cross;
  chart('c_reg_amt', {{
    tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'shadow' }} }},
    legend: {{ bottom: 0, type: 'scroll' }},
    xAxis: {{ type: 'category', data: ra.provinces, axisLabel: {{ rotate: 25, fontSize: 10 }} }},
    yAxis: {{ type: 'value' }},
    series: ra.ranges.map((r, ri) => ({{ name: r, type: 'bar', stack: 't', data: ra.data.map(row => row[ri]||0) }}))
  }});
}}
if (D.org_amount_cross) {{
  const oa = D.org_amount_cross;
  chart('c_org_amt', {{
    tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'shadow' }} }},
    legend: {{ bottom: 0, type: 'scroll' }},
    xAxis: {{ type: 'category', data: oa.orgs }},
    yAxis: {{ type: 'value' }},
    series: oa.ranges.map((r, ri) => ({{ name: r, type: 'bar', stack: 't', data: oa.data.map(row => row[ri]||0) }}))
  }});
}}

if (D.vendor_rank) {{
  const v = D.vendor_rank.vendors.slice().reverse();
  const n = D.vendor_rank.counts.slice().reverse();
  chart('c_vendor', {{
    tooltip: {{ trigger: 'axis' }},
    xAxis: {{ type: 'value' }},
    yAxis: {{ type: 'category', data: v, axisLabel: {{ fontSize: 10 }} }},
    series: [{{ type: 'bar', data: n, itemStyle: {{ color: '#7c3aed' }}, label: {{ show: true, position: 'right' }} }}]
  }});
}}

if (D.industry) chart('c_ind', {{
  tooltip: {{ trigger: 'axis' }},
  xAxis: {{ type: 'category', data: D.industry.names, axisLabel: {{ rotate: 25, fontSize: 10 }} }},
  yAxis: {{ type: 'value' }},
  series: [{{ type: 'bar', data: D.industry.counts, itemStyle: {{ color: '#0891b2' }} }}]
}});

if (D.market_pipeline) chart('c_pipe', {{
  tooltip: {{ trigger: 'item' }},
  series: [{{ type: 'pie', radius: '60%', data: [
    {{ name: '已成交/中标', value: D.market_pipeline.awarded }},
    {{ name: '招标/预告', value: D.market_pipeline.pending }}
  ]}}]
}});
</script>
</body>
</html>"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")


def load_csv_file(path: Path, keywords: Optional[str] = None) -> Tuple[pd.DataFrame, str]:
    if path.suffix.lower() in (".xlsx", ".xls"):
        df = pd.read_excel(path)
    else:
        df = pd.read_csv(path, encoding="utf-8-sig")
    kw = keywords or path.stem.replace("filtered_", "") or "标讯"
    return df, kw


def run_analysis(
    *,
    job_id: Optional[str] = None,
    records: Optional[List[dict]] = None,
    keywords: Optional[str] = None,
    csv_path: Optional[str] = None,
    enable_llm_summary: bool = True,
) -> Dict[str, Any]:
    if records:
        df = records_to_dataframe(records)
        kw = keywords or "标讯"
    elif csv_path:
        df, kw = load_csv_file(Path(csv_path), keywords)
        if keywords:
            kw = keywords
    elif job_id:
        df, kw = load_data_from_job(job_id)
        if keywords:
            kw = keywords
    else:
        raise ValueError("请提供 job_id、records 或 csv_path")

    if df.empty:
        raise ValueError("没有可分析的数据")

    df, stats = prepare_dataframe(df, keyword=kw)
    charts = compute_charts(df)

    from .llm_summary import generate_executive_summary

    summary = generate_executive_summary(charts, stats, kw, use_llm=enable_llm_summary)

    report_id = uuid.uuid4().hex[:12]
    out_dir = REPORT_DIR / report_id
    report_path = out_dir / "report.html"
    meta = {
        "report_id": report_id,
        "keywords": kw,
        "job_id": job_id,
        "csv_path": csv_path,
        "generated_at": datetime.now().isoformat(),
        "stats": stats,
        "overview": charts.get("overview", {}),
        "executive_summary": summary,
    }
    generate_html(df, charts, stats, kw, report_path, executive_summary=summary)
    (out_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "summary.md").write_text(summary.get("markdown", ""), encoding="utf-8")

    return {
        "report_id": report_id,
        "keywords": kw,
        "stats": stats,
        "overview": charts.get("overview", {}),
        "report_path": str(report_path),
        "executive_summary": summary,
    }
