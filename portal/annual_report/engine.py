"""Annual report analysis engine."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

from .analyzer import analyze_annual_report, analyze_by_sections, analyze_section
from .competitor_context import build_competitor_instructions
from .metrics_extractor import extract_metrics
from .pdf_extractor import PdfPage, pdf_extract_pages, parse_pages_from_text
from .storage import (
    load_extracted_text,
    load_report,
    load_sections,
    new_report_id,
    report_dir,
    save_report,
    update_report_content,
)
from .template_loader import load_default_template
from .template_sections import split_template
from .verifier import verify_report_numbers

import json


def _merge_pdf_texts(
    items: List[Tuple[str, str, str, List[PdfPage], int, bool]],
) -> Tuple[str, List[PdfPage], Dict[str, Any]]:
    """items: (filename, year_label, text, pages, page_count, truncated)"""
    parts = []
    all_pages: List[PdfPage] = []
    total_extracted = 0
    methods = set()
    truncated = False
    page_count = 0
    for filename, year, text, pages, file_page_count, file_truncated in items:
        header = f"===== 年报文件：{filename}（{year or '年度未标注'}）====="
        parts.append(header + "\n" + text)
        all_pages.extend(pages)
        total_extracted += len(pages)
        page_count = max(page_count, file_page_count)
        truncated = truncated or file_truncated
        if "ocr" in text.lower():
            methods.add("ocr")
    combined = "\n\n".join(parts)
    meta = {
        "filename": items[0][0] if items else "",
        "page_count": page_count,
        "pages_used": total_extracted,
        "truncated": truncated,
        "extract_method": "mixed" if len(methods) > 1 else (methods.pop() if methods else "text"),
        "compare_years": [y for _, y, _, _, _, _ in items if y],
        "file_count": len(items),
        "section_read_mode": True,
    }
    return combined, all_pages, meta


def extract_pdfs(
    pdf_items: List[Tuple[bytes, str, str]],
    force_ocr: bool = False,
    on_progress: Optional[Callable[[str, int, str], None]] = None,
) -> Tuple[str, List[PdfPage], Dict[str, Any], Dict[str, bytes]]:
    """pdf_items: (bytes, filename, year_label)"""
    extracted_items: List[Tuple[str, str, str, List[PdfPage], int, bool]] = []
    raw_map: Dict[str, bytes] = {}

    for i, (pdf_bytes, filename, year) in enumerate(pdf_items):
        if on_progress:
            on_progress("extract", 5 + int(10 * i / max(len(pdf_items), 1)), f"解析 PDF：{filename}")
        result = pdf_extract_pages(pdf_bytes, filename=filename, force_ocr=force_ocr)
        if not result.text.strip():
            raise ValueError(f"未能从 {filename} 提取文本")
        extracted_items.append(
            (filename, year, result.text, result.pages, result.page_count, result.truncated)
        )
        key = f"source_{year or i}.pdf" if year else (f"source_{i}.pdf" if i else "source.pdf")
        raw_map[key if i else "source.pdf"] = pdf_bytes

    combined, all_pages, meta = _merge_pdf_texts(extracted_items)
    return combined, all_pages, meta, raw_map


def _build_instructions(
    extra_instructions: Optional[str],
    competitors: Optional[List[str]] = None,
    industry: Optional[str] = None,
    compare_years: Optional[List[str]] = None,
) -> Optional[str]:
    parts = []
    if compare_years and len(compare_years) > 1:
        parts.append(
            f"## 多年报对比\n本次纳入年度：{', '.join(compare_years)}。"
            "请在财务分析、经营分析章节给出跨年度同比对比与趋势解读。"
        )
    comp = build_competitor_instructions(competitors or [], industry or "")
    if comp:
        parts.append(comp)
    if extra_instructions and extra_instructions.strip():
        parts.append(extra_instructions.strip())
    return "\n\n".join(parts) if parts else None


def _post_process(
    get_client: Callable,
    model: str,
    markdown: str,
    pdf_text: str,
    meta: Dict[str, Any],
    on_progress: Optional[Callable[[str, int, str], None]] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    if on_progress:
        on_progress("verify", 88, "抽取关键指标…")
    metrics = extract_metrics(
        markdown,
        meta,
        get_client=get_client,
        model=model,
        pdf_excerpt=pdf_text[:15000],
        use_llm=True,
    )
    if on_progress:
        on_progress("verify", 92, "校验报告数字…")
    verification = verify_report_numbers(markdown, pdf_text).to_dict()
    return metrics, verification


def run_analysis(
    get_client: Callable,
    model: str,
    pdf_bytes: bytes,
    filename: str,
    *,
    template_md: Optional[str] = None,
    company_name: Optional[str] = None,
    report_year: Optional[str] = None,
    extra_instructions: Optional[str] = None,
    competitors: Optional[List[str]] = None,
    industry: Optional[str] = None,
    section_mode: bool = True,
    force_ocr: bool = False,
    max_tokens: int = 8192,
    save_pdf: bool = True,
    extra_pdf_items: Optional[List[Tuple[bytes, str, str]]] = None,
    on_progress: Optional[Callable[[str, int, str], None]] = None,
) -> Dict[str, Any]:
    pdf_items = [(pdf_bytes, filename, report_year or "")]
    if extra_pdf_items:
        pdf_items.extend(extra_pdf_items)

    def progress(phase: str, pct: int, msg: str) -> None:
        if on_progress:
            on_progress(phase, pct, msg)

    progress("extract", 5, "正在解析 PDF…")
    combined_text, pdf_pages, extract_meta, pdf_map = extract_pdfs(
        pdf_items, force_ocr=force_ocr, on_progress=on_progress
    )
    progress(
        "extract",
        15,
        f"PDF 解析完成（{extract_meta.get('pages_used', 0)}/{extract_meta.get('page_count', 0)} 页，按章节分读）",
    )

    template = template_md or load_default_template()
    instructions = _build_instructions(
        extra_instructions,
        competitors=competitors,
        industry=industry,
        compare_years=extract_meta.get("compare_years"),
    )

    pdf_meta = {**extract_meta, "filename": filename}

    progress("analyze", 20, "正在调用 AI 分析…")

    if section_mode:
        sections = split_template(template)

        def section_cb(sec, done, total):
            pct = 20 + int(60 * done / max(total, 1))
            progress("analyze", pct, f"正在生成：{sec.title}（{done}/{total}）")

        out = analyze_by_sections(
            get_client,
            model,
            sections,
            combined_text,
            company_name=company_name,
            report_year=report_year,
            extra_instructions=instructions,
            pdf_meta=pdf_meta,
            pdf_pages=pdf_pages,
            max_tokens_per_section=min(4096, max_tokens),
            on_section_done=section_cb,
        )
        mode = "section"
    else:
        out = analyze_annual_report(
            get_client,
            model,
            template,
            combined_text,
            company_name=company_name,
            report_year=report_year,
            extra_instructions=instructions,
            pdf_meta=pdf_meta,
            max_tokens=max_tokens,
        )
        mode = "full"

    metrics, verification = _post_process(
        get_client, model, out["result"], combined_text, pdf_meta, on_progress
    )

    progress("save", 95, "正在保存报告…")
    report_id = new_report_id()
    meta = {
        "company_name": company_name or "",
        "report_year": report_year or "",
        "filename": filename,
        "page_count": extract_meta.get("page_count", 0),
        "pages_used": extract_meta.get("pages_used", 0),
        "text_truncated": extract_meta.get("truncated", False),
        "section_read_mode": extract_meta.get("section_read_mode", True),
        "extract_method": extract_meta.get("extract_method", "text"),
        "model": out["model"],
        "usage": out["usage"],
        "analysis_mode": mode,
        "section_count": len(out.get("sections") or {}),
        "compare_years": extract_meta.get("compare_years") or [],
        "competitors": competitors or [],
        "industry": industry or "",
        "verification_score": verification.get("score"),
    }
    meta["report_id"] = report_id

    primary_pdf = pdf_map.get("source.pdf", pdf_bytes)
    extra_pdfs = {k: v for k, v in pdf_map.items() if k != "source.pdf"} or None

    save_report(
        report_id,
        out["result"],
        meta,
        pdf_bytes=primary_pdf if save_pdf else None,
        sections=out.get("sections") or None,
        extracted_text=combined_text,
        metrics=metrics,
        verification=verification,
        extra_pdfs=extra_pdfs if save_pdf else None,
    )

    progress("save", 100, "分析完成")

    return {
        "report_id": report_id,
        "result": out["result"],
        "meta": meta,
        "metrics": metrics,
        "verification": verification,
        "status": "ok",
        "message": "分析完成",
    }


def rerun_section(
    get_client: Callable,
    model: str,
    report_id: str,
    section_id: str,
    *,
    extra_instructions: Optional[str] = None,
    max_tokens: int = 4096,
    on_progress: Optional[Callable[[str, int, str], None]] = None,
) -> Dict[str, Any]:
    data = load_report(report_id)
    meta = data["meta"]
    pdf_pages: List[PdfPage] = []
    pdf_text = load_extracted_text(report_id)
    pdf_path = report_dir(report_id) / "source.pdf"
    if pdf_path.is_file():
        result = pdf_extract_pages(pdf_path.read_bytes(), filename="source.pdf")
        pdf_pages = result.pages
        pdf_text = result.text
    elif not pdf_text:
        raise ValueError("无法获取原文，请重新上传分析")
    elif not pdf_pages:
        from .pdf_extractor import parse_pages_from_text

        pdf_pages = parse_pages_from_text(pdf_text)

    template = load_default_template()
    sections = split_template(template)
    target = next((s for s in sections if s.section_id == section_id), None)
    if not target:
        raise ValueError(f"未知章节: {section_id}")

    if on_progress:
        on_progress("analyze", 30, f"重跑章节：{target.title}")

    pdf_meta = {
        "filename": meta.get("filename"),
        "page_count": meta.get("page_count"),
        "pages_used": meta.get("pages_used"),
        "truncated": meta.get("text_truncated"),
        "section_read_mode": True,
    }

    new_content, usage = analyze_section(
        get_client,
        model,
        target,
        pdf_text,
        company_name=meta.get("company_name"),
        report_year=meta.get("report_year"),
        extra_instructions=extra_instructions,
        pdf_meta=pdf_meta,
        pdf_pages=pdf_pages or None,
        max_tokens=max_tokens,
    )

    section_map = load_sections(report_id)
    section_map[section_id] = new_content

    ordered = split_template(template)
    merged_parts = []
    for sec in ordered:
        if sec.section_id in section_map:
            merged_parts.append(section_map[sec.section_id])
        elif sec.section_id == section_id:
            merged_parts.append(new_content)
    markdown = "\n\n".join(merged_parts).strip()

    metrics, verification = _post_process(get_client, model, markdown, pdf_text, meta, on_progress)

    update_report_content(report_id, markdown, sections=section_map, meta_patch={
        "usage": usage,
        "verification_score": verification.get("score"),
        "rerun_section": section_id,
    })

    d = report_dir(report_id)
    (d / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    (d / "verification.json").write_text(json.dumps(verification, ensure_ascii=False, indent=2), encoding="utf-8")

    if on_progress:
        on_progress("save", 100, "章节已更新")

    return {
        "report_id": report_id,
        "section_id": section_id,
        "result": markdown,
        "section_content": new_content,
        "metrics": metrics,
        "verification": verification,
        "status": "ok",
        "message": f"章节 {target.title} 已重新生成",
    }
