"""剑鱼标讯检索与报告生成."""

from __future__ import annotations

import asyncio
from typing import List, Optional

from .crawler_runner import CrawlCancelledError, run_crawl
from .job_index import save_job_record
from .jobs import Job, create_job, get_job, is_cancel_requested, request_cancel
from .models import BidRecord, TenderInfoRequest, TenderInfoResponse, JobStatusResponse


def is_configured() -> bool:
    import os

    return bool(os.getenv("JIANYU_PHONE", "").strip())


def records_to_markdown(
    records: List[BidRecord],
    keywords: str,
    region: Optional[str] = None,
    stats: Optional[dict] = None,
    query_summary: Optional[str] = None,
) -> str:
    lines = [
        f"# 标书信息获取报告",
        "",
        f"- 关键词：{keywords}",
        f"- 地区：{region or '全国'}",
    ]
    if query_summary:
        lines.append(f"- 查询条件：{query_summary}")
    if stats:
        lines.append(
            f"- 统计：共 {stats.get('total_raw', 0)} 条匹配，"
            f"已中标 {stats.get('total_awarded', 0)} 条，"
            f"招标/预告 {stats.get('total_pending', 0)} 条"
        )
    lines.extend(["", "## 记录列表", ""])
    if not records:
        lines.append("（无匹配记录）")
        return "\n".join(lines)

    lines.append("| 类型 | 项目名称 | 采购单位 | 中标单位 | 金额 | 时间 | 地区 |")
    lines.append("|------|----------|----------|----------|------|------|------|")
    for r in records:
        lines.append(
            f"| {r.project_type or ''} | {r.project_name} | {r.buyer or ''} | {r.winner or ''} | "
            f"{r.amount or ''} | {r.bid_date or ''} | {r.region or ''} |"
        )
    return "\n".join(lines)


def _query_summary(request: TenderInfoRequest) -> str:
    from .jianyu_options import SCOPE_ID_TO_LABEL, PUBLISH_TIME_PRESETS

    preset_labels = {p["id"]: p["label"] for p in PUBLISH_TIME_PRESETS}
    time_label = preset_labels.get(request.publish_time_preset, request.publish_time_preset)
    if request.publish_time_preset == "custom" and request.date_from:
        time_label = f"{request.date_from} ~ {request.date_to or '今'}"
    scopes = "、".join(SCOPE_ID_TO_LABEL.get(s, s) for s in request.search_scopes)
    types = "全部" if not request.info_types else "、".join(request.info_types)
    return f"发布时间 {time_label}；范围 {scopes}；类型 {types}"


def _run_job_sync(job: Job, request: TenderInfoRequest) -> None:
    job.status = "running"
    job.message = "正在登录剑鱼标讯并检索…"
    job.progress = 10

    def log(line: str) -> None:
        job.append_log(line)
        if "[抓取]" in line:
            job.progress = min(90, job.progress + 5)
        if "[完成]" in line or "[解析]" in line:
            job.progress = min(95, job.progress + 3)

    try:
        records, csv_path, stats = run_crawl(
            request,
            log,
            output_subdir=job.id,
            job_id=job.id,
            should_cancel=lambda: is_cancel_requested(job.id),
            on_proc_started=job.set_proc,
        )
        job.clear_proc()
        report = records_to_markdown(
            records,
            request.keywords,
            request.region,
            stats,
            query_summary=_query_summary(request),
        )

        download_url = None
        if csv_path:
            rel = csv_path.replace("\\", "/")
            if "/tender_raw_data/" in rel:
                download_url = "/api/tender-info/download/" + rel.split("/tender_raw_data/")[-1]

        was_cancelled = is_cancel_requested(job.id)
        msg = (
            f"已中止，保留 {len(records)} 条（已中标 {stats['total_awarded']} / 未中标 {stats['total_pending']}）"
            if was_cancelled
            else f"检索完成，共 {len(records)} 条（已中标 {stats['total_awarded']} / 未中标 {stats['total_pending']}）"
        )

        job.result = TenderInfoResponse(
            status="cancelled" if was_cancelled else "ok",
            message=msg,
            job_id=job.id,
            query_type=request.query_type.value,
            keywords=request.keywords,
            total=len(records),
            total_raw=stats["total_raw"],
            total_awarded=stats["total_awarded"],
            total_pending=stats["total_pending"],
            records=records,
            report_markdown=report,
            csv_download=download_url,
            logs=job.logs.copy(),
        )
        job.status = "cancelled" if was_cancelled else "completed"
        job.message = job.result.message
        job.progress = 100
        save_job_record(
            {
                "job_id": job.id,
                "keywords": request.keywords,
                "region": request.region,
                "status": job.status,
                "total": len(records),
                "total_raw": stats.get("total_raw"),
                "total_awarded": stats.get("total_awarded"),
                "total_pending": stats.get("total_pending"),
                "csv_download": download_url,
                "query_type": request.query_type.value,
            }
        )
    except CrawlCancelledError as e:
        job.clear_proc()
        job.status = "cancelled"
        job.message = str(e)
        job.append_log(f"[中止] {e}")
        job.progress = 100
    except Exception as e:
        job.clear_proc()
        job.status = "failed"
        job.message = str(e)
        job.append_log(f"[错误] {e}")
        job.progress = 100


async def start_crawl_job(request: TenderInfoRequest) -> Job:
    job = create_job()
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, _run_job_sync, job, request)
    return job


def cancel_crawl_job(job_id: str) -> bool:
    return request_cancel(job_id)


def job_to_response(job: Job) -> JobStatusResponse:
    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        message=job.message,
        phase=job.phase,
        logs=job.logs,
        progress=job.progress,
        result=job.result,
    )
