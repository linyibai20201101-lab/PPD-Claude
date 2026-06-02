"""FastAPI routes for annual-report."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel

from llm_config import is_allowed_model

from .agent import agent_help, run_agent_query
from .competitor_context import competitor_benchmark_url, industry_research_url
from .engine import rerun_section, run_analysis
from .exporter import export_docx, export_filename, export_pdf, export_xlsx
from .jobs import create_job, get_job, list_jobs, run_job_async
from .models import (
    AnnualReportAnalyzeMeta,
    AnnualReportResponse,
    AgentQueryRequest,
    AgentQueryResponse,
    JobCreateResponse,
    JobStatusResponse,
    ReportListItem,
    ReportListResponse,
    SectionRerunRequest,
    TemplateResponse,
    UsageStats,
)
from .pdf_extractor import ocr_available
from .storage import load_metrics, load_report, load_verification, list_reports
from .template_loader import load_default_template, resolve_skills_dir
from .template_sections import split_template

router = APIRouter(prefix="/api/annual-report", tags=["annual-report"])

SKILL_ID = "annual-report"

_get_client: Optional[Callable] = None
_default_model: str = "mimo-v2.5-pro"
_api_key_configured: bool = False
_skills_dir: Optional[Path] = None
_base_url: Optional[str] = None


def configure_router(
    get_anthropic_client: Optional[Callable] = None,
    default_model: str = "mimo-v2.5-pro",
    api_key_configured: bool = False,
    skills_dir: Optional[Path] = None,
    base_url: Optional[str] = None,
) -> None:
    global _get_client, _default_model, _api_key_configured, _skills_dir, _base_url
    _get_client = get_anthropic_client
    _default_model = default_model or "mimo-v2.5-pro"
    _api_key_configured = api_key_configured
    _skills_dir = skills_dir
    _base_url = base_url


def _ensure_llm() -> None:
    if not _api_key_configured or not _get_client:
        raise HTTPException(
            status_code=503,
            detail="未配置大模型 API Key。请在 portal/.env 设置 ANTHROPIC_API_KEY",
        )


def _resolve_model(model: str) -> str:
    chosen = (model or _default_model).strip()
    if not is_allowed_model(chosen, _base_url):
        raise HTTPException(status_code=400, detail=f"不支持的模型: {chosen}")
    return chosen


async def _read_template(template_file: UploadFile | None) -> str:
    if template_file is not None:
        tpl_bytes = await template_file.read()
        if not tpl_bytes:
            raise HTTPException(status_code=400, detail="自定义模板文件为空")
        try:
            return tpl_bytes.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="模板文件须为 UTF-8 编码的 Markdown")
    try:
        return load_default_template(_skills_dir)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


async def _read_pdf(file: UploadFile) -> tuple[bytes, str]:
    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="PDF 文件为空")
    filename = file.filename or "report.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="仅支持 PDF 文件")
    return pdf_bytes, filename


def _parse_list_field(raw: str) -> List[str]:
    if not raw or not raw.strip():
        return []
    return [x.strip() for x in raw.replace("，", ",").split(",") if x.strip()]


def _meta_from_dict(meta: dict) -> AnnualReportAnalyzeMeta:
    usage = meta.get("usage") or {}
    return AnnualReportAnalyzeMeta(
        filename=meta.get("filename") or "",
        page_count=meta.get("page_count") or 0,
        pages_used=meta.get("pages_used") or 0,
        text_truncated=bool(meta.get("text_truncated")),
        extract_method=meta.get("extract_method") or "text",
        model=meta.get("model") or "",
        usage=UsageStats(
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
        ),
        analysis_mode=meta.get("analysis_mode") or "section",
        section_count=meta.get("section_count") or 0,
        company_name=meta.get("company_name") or "",
        report_year=meta.get("report_year") or "",
        report_id=meta.get("report_id"),
        compare_years=meta.get("compare_years") or [],
        verification_score=meta.get("verification_score"),
    )


def _run_worker_kwargs(
    pdf_bytes,
    filename,
    template_md,
    company_name,
    report_year,
    extra_instructions,
    competitors,
    industry,
    section_mode,
    force_ocr,
    max_tokens,
    extra_pdf_items,
):
    def worker(on_progress):
        assert _get_client is not None
        return run_analysis(
            _get_client,
            _resolve_model(""),
            pdf_bytes,
            filename,
            template_md=template_md,
            company_name=company_name.strip() or None,
            report_year=report_year.strip() or None,
            extra_instructions=extra_instructions.strip() or None,
            competitors=competitors or None,
            industry=industry.strip() or None,
            section_mode=section_mode,
            force_ocr=force_ocr,
            max_tokens=max_tokens,
            extra_pdf_items=extra_pdf_items or None,
            on_progress=on_progress,
        )
    return worker


@router.get("/status")
async def status():
    template_ok = False
    try:
        load_default_template(_skills_dir)
        template_ok = True
    except FileNotFoundError:
        pass

    ready = _api_key_configured and template_ok
    return {
        "status": "ready" if ready else "degraded",
        "skill": SKILL_ID,
        "llm_configured": _api_key_configured,
        "template_available": template_ok,
        "ocr_available": ocr_available(),
        "default_model": _default_model,
        "features": {
            "section_mode": True,
            "async_jobs": True,
            "report_history": True,
            "ocr_fallback": ocr_available(),
            "multi_pdf": True,
            "section_rerun": True,
            "metrics_json": True,
            "verification": True,
            "export_docx_pdf_xlsx": True,
            "agent_query": True,
            "l2_competitor_link": True,
        },
        "message": "就绪：完整年报分析能力已启用" if ready else "请配置 ANTHROPIC_API_KEY",
    }


@router.get("/template", response_model=TemplateResponse)
async def get_template():
    try:
        content = load_default_template(_skills_dir)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    source = str(resolve_skills_dir(_skills_dir) / "annual-report" / "templates" / "output-template.md")
    return TemplateResponse(template=content, source=source)


@router.get("/sections")
async def list_sections():
    template = load_default_template(_skills_dir)
    sections = split_template(template)
    return {
        "sections": [
            {"section_id": s.section_id, "title": s.title, "order": s.order}
            for s in sections
        ]
    }


@router.get("/agent/help")
async def agent_help_endpoint():
    return agent_help()


@router.post("/agent/query", response_model=AgentQueryResponse)
async def agent_query(body: AgentQueryRequest):
    _ensure_llm()
    model = _resolve_model(body.model or "")
    assert _get_client is not None
    out = run_agent_query(
        _get_client,
        model,
        body.message,
        report_id=body.report_id,
        company=body.company_name,
        max_tokens=body.max_tokens or 2048,
    )
    return AgentQueryResponse(
        content=out["content"],
        intent=out.get("intent") or "chat",
        actions=out.get("actions") or [],
    )


@router.get("/links")
async def orchestration_links(
    report_id: str = "",
    company: str = "",
    peers: str = "",
    industry: str = "",
):
    peer_list = _parse_list_field(peers)
    return {
        "competitor_benchmark": competitor_benchmark_url(
            report_id=report_id, company=company, peers=peer_list, industry=industry
        ),
        "industry_research": industry_research_url(company=company, industry=industry),
    }


@router.get("/reports", response_model=ReportListResponse)
async def reports_list(limit: int = 30):
    items = [ReportListItem(**r) for r in list_reports(limit=limit)]
    return ReportListResponse(reports=items)


@router.get("/reports/{report_id}")
async def get_report(report_id: str):
    try:
        data = load_report(report_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {
        "status": "ok",
        "report_id": report_id,
        "result": data["result"],
        "meta": data["meta"],
        "metrics": data.get("metrics"),
        "verification": data.get("verification"),
        "sections": list((data.get("sections") or {}).keys()),
    }


@router.get("/reports/{report_id}/metrics")
async def get_metrics(report_id: str):
    m = load_metrics(report_id)
    if m is None:
        raise HTTPException(status_code=404, detail="metrics.json 不存在")
    return {"report_id": report_id, "metrics": m}


@router.get("/reports/{report_id}/verification")
async def get_verification(report_id: str):
    v = load_verification(report_id)
    if v is None:
        raise HTTPException(status_code=404, detail="verification.json 不存在")
    return {"report_id": report_id, "verification": v}


@router.get("/reports/{report_id}/export")
async def export_report(report_id: str, format: str = "md"):
    try:
        data = load_report(report_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    meta = data.get("meta") or {}
    base = f"{meta.get('company_name') or '公司'}_{meta.get('report_year') or '年报'}_财报分析"
    fmt = format.lower()

    if fmt == "md":
        filename = export_filename(base, "md")
        return PlainTextResponse(
            content=data["result"],
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    if fmt == "docx":
        try:
            content = export_docx(data["result"], title=base)
        except ImportError as e:
            raise HTTPException(status_code=503, detail=str(e))
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{export_filename(base, "docx")}"'},
        )
    if fmt == "pdf":
        try:
            content = export_pdf(data["result"], title=base)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"PDF 导出失败: {e}")
        return Response(
            content=content,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{export_filename(base, "pdf")}"'},
        )
    if fmt == "xlsx":
        metrics = data.get("metrics") or load_metrics(report_id) or {}
        content = export_xlsx(metrics)
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{export_filename(base, "xlsx")}"'},
        )
    raise HTTPException(status_code=400, detail="format 支持: md, docx, pdf, xlsx")


@router.get("/reports/{report_id}/download")
async def download_report(report_id: str):
    return await export_report(report_id, format="md")


@router.post("/reports/{report_id}/sections/{section_id}/rerun")
async def section_rerun(report_id: str, section_id: str, body: SectionRerunRequest):
    _ensure_llm()
    model = _resolve_model(body.model or "")
    job = create_job()

    def worker(on_progress):
        assert _get_client is not None
        return rerun_section(
            _get_client,
            model,
            report_id,
            section_id,
            extra_instructions=body.extra_instructions,
            max_tokens=body.max_tokens or 4096,
            on_progress=on_progress,
        )

    run_job_async(job.id, worker)
    return JobCreateResponse(status="queued", job_id=job.id, message=f"章节 {section_id} 重跑任务已提交")


@router.get("/jobs")
async def jobs_list(limit: int = 20):
    jobs = list_jobs(limit=limit)
    return {
        "jobs": [
            {
                "job_id": j.id,
                "status": j.status,
                "phase": j.phase,
                "progress": j.progress,
                "message": j.message,
                "report_id": j.report_id,
            }
            for j in jobs
        ]
    }


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def job_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        phase=job.phase,
        progress=job.progress,
        message=job.message,
        logs=job.logs,
        report_id=job.report_id,
        result=job.result,
        meta=job.meta,
        error=job.error,
    )


@router.post("/run", response_model=JobCreateResponse)
async def run_async(
    file: UploadFile = File(...),
    extra_files: List[UploadFile] = File(default=[]),
    template_file: UploadFile | None = File(None),
    company_name: str = Form(""),
    report_year: str = Form(""),
    compare_years: str = Form(""),
    competitors: str = Form(""),
    industry: str = Form(""),
    extra_instructions: str = Form(""),
    model: str = Form(""),
    section_mode: bool = Form(True),
    force_ocr: bool = Form(False),
    max_tokens: int = Form(8192),
):
    _ensure_llm()
    chosen_model = _resolve_model(model)
    pdf_bytes, filename = await _read_pdf(file)
    template_md = await _read_template(template_file)

    years = _parse_list_field(compare_years)
    extra_items = []
    for i, ef in enumerate(extra_files):
        if not ef.filename:
            continue
        eb, fn = await _read_pdf(ef)
        yr = years[i + 1] if len(years) > i + 1 else (years[-1] if years else f"对比{i + 1}")
        extra_items.append((eb, fn, yr))

    job = create_job()

    def worker(on_progress):
        assert _get_client is not None
        return run_analysis(
            _get_client,
            chosen_model,
            pdf_bytes,
            filename,
            template_md=template_md,
            company_name=company_name.strip() or None,
            report_year=(years[0] if years else report_year.strip()) or None,
            extra_instructions=extra_instructions.strip() or None,
            competitors=_parse_list_field(competitors) or None,
            industry=industry.strip() or None,
            section_mode=section_mode,
            force_ocr=force_ocr,
            max_tokens=max_tokens,
            extra_pdf_items=extra_items or None,
            on_progress=on_progress,
        )

    run_job_async(job.id, worker)
    return JobCreateResponse(status="queued", job_id=job.id, message="分析任务已提交")


@router.post("/analyze", response_model=AnnualReportResponse)
async def analyze_sync(
    file: UploadFile = File(...),
    extra_files: List[UploadFile] = File(default=[]),
    template_file: UploadFile | None = File(None),
    company_name: str = Form(""),
    report_year: str = Form(""),
    compare_years: str = Form(""),
    competitors: str = Form(""),
    industry: str = Form(""),
    extra_instructions: str = Form(""),
    model: str = Form(""),
    section_mode: bool = Form(True),
    force_ocr: bool = Form(False),
    max_tokens: int = Form(8192),
):
    _ensure_llm()
    chosen_model = _resolve_model(model)
    pdf_bytes, filename = await _read_pdf(file)
    template_md = await _read_template(template_file)
    max_tokens = max(1024, min(int(max_tokens), 16384))
    years = _parse_list_field(compare_years)
    extra_items = []
    for i, ef in enumerate(extra_files):
        if not ef.filename:
            continue
        eb, fn = await _read_pdf(ef)
        yr = years[i + 1] if len(years) > i + 1 else f"对比{i + 1}"
        extra_items.append((eb, fn, yr))

    try:
        assert _get_client is not None
        out = run_analysis(
            _get_client,
            chosen_model,
            pdf_bytes,
            filename,
            template_md=template_md,
            company_name=company_name.strip() or None,
            report_year=(years[0] if years else report_year.strip()) or None,
            extra_instructions=extra_instructions.strip() or None,
            competitors=_parse_list_field(competitors) or None,
            industry=industry.strip() or None,
            section_mode=section_mode,
            force_ocr=force_ocr,
            max_tokens=max_tokens,
            extra_pdf_items=extra_items or None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 分析失败: {e}")

    meta = out["meta"]
    return AnnualReportResponse(
        status="ok",
        message=out["message"],
        result=out["result"],
        report_id=out["report_id"],
        meta=_meta_from_dict(meta),
        metrics=out.get("metrics"),
        verification=out.get("verification"),
    )
