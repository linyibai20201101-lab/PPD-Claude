"""Tender product analysis engine — stats + detail + attachments."""

from __future__ import annotations

import os
from typing import Any, Callable, Dict, List, Optional

from dotenv import load_dotenv

from .dedupe import dedupe_projects
from .detail_fetcher import fetch_details
from .export import render_report_md
from .loader import DATA_DIR, filter_rows, load_rows_from_job
from .match_audit import build_unmatched_audit, filter_for_retry, has_attachment
from .product_lines import build_product_lines
from .stats import compute_stats_summary, prepare_projects_df
from .storage import load_projects_enriched, new_report_id, report_dir, save_report

PORTAL_ROOT = DATA_DIR.parent
load_dotenv(PORTAL_ROOT / ".env")


def _credentials(
    phone: Optional[str] = None,
    password: Optional[str] = None,
) -> tuple[str, str]:
    u = (phone or os.getenv("JIANYU_PHONE", "")).strip()
    p = password if password is not None else os.getenv("JIANYU_PASSWORD", "")
    if not u:
        raise ValueError("请配置 JIANYU_PHONE 或在请求中填写剑鱼账号")
    return u, p


def _merge_retry_records(all_records: List[dict], retried: List[dict]) -> List[dict]:
    """Replace retried rows in full list by 详情链接 / 项目名称."""
    keys = {
        (str(r.get("详情链接") or r.get("source_url") or ""), str(r.get("项目名称") or ""))
        for r in retried
    }
    key_set = {k for k in keys if k[0] or k[1]}
    merged: List[dict] = []
    retried_map = {
        (str(r.get("详情链接") or r.get("source_url") or ""), str(r.get("项目名称") or "")): r
        for r in retried
    }
    for rec in all_records:
        k = (str(rec.get("详情链接") or rec.get("source_url") or ""), str(rec.get("项目名称") or ""))
        if k in key_set and k in retried_map:
            merged.append(retried_map[k])
        else:
            merged.append(rec)
    return merged


def run_product_analysis(
    *,
    source_job_id: str,
    keywords: Optional[str] = None,
    only_with_attachment: bool = False,
    fetch_detail: bool = True,
    parse_attachments: bool = True,
    max_projects: int = 50,
    headless: bool = False,
    jianyu_phone: Optional[str] = None,
    jianyu_password: Optional[str] = None,
    from_report_id: Optional[str] = None,
    retry_mode: Optional[str] = None,
    on_progress: Optional[Callable[[str, int, str], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> Dict[str, Any]:
    def prog(phase: str, pct: int, msg: str) -> None:
        if on_progress:
            on_progress(phase, pct, msg)

    def cancelled() -> bool:
        return bool(cancel_check and cancel_check())

    report_id = new_report_id()
    work_dir = report_dir(report_id)
    attach_root = work_dir / "projects"

    retry_from = (from_report_id or "").strip()
    is_retry = bool(retry_from)

    if is_retry:
        prog("load", 5, f"从报告 {retry_from} 加载并重跑…")
        try:
            from .storage import load_report

            prev = load_report(retry_from)
        except FileNotFoundError as e:
            raise ValueError(f"源报告不存在: {retry_from}") from e
        meta_prev = prev.get("meta") or {}
        source_job_id = meta_prev.get("source_job_id") or source_job_id
        keyword = (keywords or meta_prev.get("keyword") or prev.get("stats", {}).get("keyword") or "").strip()
        records = load_projects_enriched(retry_from)
        if not records:
            raise ValueError("源报告无项目数据，无法重跑")
        subset = filter_for_retry(records, retry_mode or "failed")
        if not subset:
            raise ValueError(f"没有符合重跑条件（{retry_mode or 'failed'}）的项目")
        prog("load", 12, f"重跑 {len(subset)} / {len(records)} 个项目")
    else:
        prog("load", 5, f"加载任务数据 {source_job_id}…")
        rows, detected_kw = load_rows_from_job(source_job_id)
        keyword = (keywords or detected_kw or "").strip() or detected_kw

        records = filter_rows(
            rows,
            only_with_attachment=only_with_attachment,
            max_projects=max_projects,
        )
        if not records:
            raise ValueError("没有可分析的项目记录（请检查筛选条件）")

        raw_count = len(records)
        records = dedupe_projects(records)
        deduped_count = len(records)

        prog(
            "load",
            12,
            f"共 {deduped_count} 个项目"
            + (f"（列表 {raw_count} 条已去重）" if raw_count != deduped_count else ""),
        )
        subset = None

    was_cancelled = False

    if fetch_detail and cancelled():
        fetch_detail = False
        was_cancelled = True
        prog("detail", 18, "已中止，跳过详情抓取…")

    if fetch_detail:
        user, pwd = _credentials(jianyu_phone, jianyu_password)
        auth_dir = DATA_DIR / source_job_id
        do_attach = parse_attachments

        def detail_cb(done: int, total: int, title: str) -> None:
            if do_attach:
                pct = 15 + int(60 * done / max(total, 1))
                label = "详情+附件"
            else:
                pct = 15 + int(45 * done / max(total, 1))
                label = "详情"
            prog("detail", pct, f"{label} {done}/{total}: {title}")

        prog(
            "detail",
            15,
            "登录剑鱼并抓取详情"
            + ("、下载解析附件…" if do_attach else "（产品/金额）…"),
        )
        detail_targets = subset if is_retry else records
        retried = fetch_details(
            detail_targets,
            username=user,
            password=pwd,
            keyword=keyword,
            auth_dir=auth_dir,
            attach_root=attach_root if do_attach else None,
            parse_attachments=do_attach,
            headless=headless,
            on_progress=detail_cb,
            cancel_check=cancel_check,
        )
        records = _merge_retry_records(records, retried) if is_retry else retried
        if cancelled():
            was_cancelled = True
            prog("detail", 72, "详情抓取已中止，正在汇总已抓取数据…")

    if cancelled():
        was_cancelled = True

    prog("analyze", 78, "统计与产品行统筹…")
    projects_df, prep_meta = prepare_projects_df(records, keyword=keyword)
    records_out = projects_df.to_dict(orient="records")

    master_df = build_product_lines(records_out, keyword=keyword)
    stats = compute_stats_summary(projects_df, master_df, keyword, source_job_id)
    stats.update(prep_meta)
    unmatched = build_unmatched_audit(records_out)
    stats["unmatched_projects"] = unmatched
    stats["unmatched_count"] = len(unmatched)
    if parse_attachments:
        att_projects = sum(1 for r in records_out if has_attachment(r))
        parsed_ok = int(sum(1 for r in records_out if (r.get("附件解析数") or 0) > 0))
        stats["attachment_projects"] = att_projects
        stats["attachment_parsed_projects"] = parsed_ok
        stats["attachment_parse_rate_pct"] = (
            round(100.0 * parsed_ok / att_projects, 1) if att_projects else 0.0
        )

    report_md = render_report_md(stats, master_df)

    prog("save", 92, "保存报告…")
    phase = "stats_detail_attach" if parse_attachments else "stats_detail"
    meta = {
        "report_id": report_id,
        "source_job_id": source_job_id,
        "keyword": keyword,
        "only_with_attachment": only_with_attachment,
        "fetch_detail": fetch_detail,
        "parse_attachments": parse_attachments,
        "max_projects": max_projects,
        "phase": phase,
        "maturity": "L1+" if parse_attachments else "L1",
        "retry_from_report_id": retry_from or None,
        "retry_mode": retry_mode if is_retry else None,
        "cancelled": was_cancelled,
    }
    save_report(
        report_id,
        meta=meta,
        projects=records_out,
        master_df=master_df,
        stats=stats,
        report_md=report_md,
    )

    prog("save", 100, "已中止并保存" if was_cancelled else "完成")

    return {
        "report_id": report_id,
        "keyword": keyword,
        "stats": stats,
        "report_md": report_md,
        "meta": meta,
        "cancelled": was_cancelled,
    }
