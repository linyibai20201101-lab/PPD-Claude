"""LLM-powered annual report analysis."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from .pdf_extractor import PdfPage
from .template_sections import TemplateSection, slice_pages_for_section, slice_text_for_section

SYSTEM_PROMPT = """你是一位资深财务分析师与行业研究专家，擅长阅读 A 股/港股上市公司年度报告与财务报表。

你的任务：根据用户提供的「章节模板」和「年报 PDF 提取文本」，生成该章节的 Markdown 内容。

硬性要求：
1. **只输出当前章节**：不要输出其他章节标题；保留模板中该章节的标题层级（## / ### 等）。
2. **数据优先来自 PDF**：表格与列表用年报中的真实数字填充；无法找到的数据写「未披露」或「待补充」，勿编造。
3. **页码引用**：关键数据后标注来源页，格式 `（来源：第 N 页）` 或 `（第 N 页）`。
4. **可推导则计算**：同比、占比、毛利率等，在 PDF 提供足够数据时自行计算。
5. **分析要有观点**：摘要与财务章节需有简明结论，而非仅罗列。
6. **输出格式**：纯 Markdown，不要用 ```markdown 代码块包裹。
7. **语言**：简体中文，专业、客观。"""

SYSTEM_PROMPT_FULL = """你是一位资深财务分析师与行业研究专家，擅长阅读 A 股/港股上市公司年度报告与财务报表。

你的任务：根据用户提供的「输出模板」和「年报 PDF 提取文本」，生成一份完整、结构化的 Markdown 分析报告。

硬性要求：
1. **严格遵循模板章节结构**：保留全部标题，不得擅自删除章节。
2. **数据优先来自 PDF**；无法找到的数据写「未披露」或「待补充」，勿编造。
3. **页码引用**：关键数据标注 `（第 N 页）`。
4. **可推导则计算**同比、占比、毛利率等。
5. **输出格式**：纯 Markdown 正文，不要用代码块包裹全文。
6. **语言**：简体中文。"""


def _extract_response_text(content) -> str:
    texts = []
    for block in content:
        if getattr(block, "type", None) == "text" and getattr(block, "text", None):
            texts.append(block.text)
    if texts:
        return "\n".join(texts).strip()
    for block in content:
        if getattr(block, "text", None):
            return block.text.strip()
    raise ValueError("API 返回内容为空")


def _strip_fence(text: str) -> str:
    if not text.startswith("```"):
        return text.strip()
    lines = text.splitlines()
    if lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _section_excerpt(
    section: TemplateSection,
    pdf_text: str,
    pdf_pages: Optional[List[PdfPage]] = None,
) -> str:
    if pdf_pages:
        return slice_pages_for_section(pdf_pages, section)
    return slice_text_for_section(pdf_text, section)


def build_section_prompt(
    section: TemplateSection,
    pdf_text: str,
    *,
    company_name: Optional[str] = None,
    report_year: Optional[str] = None,
    extra_instructions: Optional[str] = None,
    pdf_meta: Optional[Dict[str, Any]] = None,
    pdf_pages: Optional[List[PdfPage]] = None,
) -> str:
    meta = pdf_meta or {}
    excerpt = _section_excerpt(section, pdf_text, pdf_pages)
    lines = [
        f"## 当前章节：{section.title}",
        "",
        "### 章节模板（按此结构输出本章）",
        "",
        section.content,
        "",
        "---",
        "",
        "## 分析上下文",
        "",
    ]
    if company_name:
        lines.append(f"- 公司名称：{company_name}")
    if report_year:
        lines.append(f"- 报告年度：{report_year}")
    if meta.get("filename"):
        lines.append(f"- PDF：{meta['filename']}")
    if extra_instructions and extra_instructions.strip():
        lines.extend(["", "### 用户补充要求", "", extra_instructions.strip()])
    lines.extend(
        [
            "",
            "---",
            "",
            "## 与本章相关的年报摘录",
            "",
            excerpt.strip() or "（无相关文本）",
            "",
            "---",
            "",
            f"请只输出「{section.title}」章节的 Markdown 内容。",
        ]
    )
    return "\n".join(lines)


def build_user_prompt(
    template_md: str,
    pdf_text: str,
    *,
    company_name: Optional[str] = None,
    report_year: Optional[str] = None,
    extra_instructions: Optional[str] = None,
    pdf_meta: Optional[Dict[str, Any]] = None,
) -> str:
    meta = pdf_meta or {}
    lines = [
        "## 输出模板（必须按此结构输出）",
        "",
        template_md.strip(),
        "",
        "---",
        "",
        "## 分析上下文",
        "",
    ]
    if company_name:
        lines.append(f"- 公司名称（用户指定）：{company_name}")
    if report_year:
        lines.append(f"- 报告年度（用户指定）：{report_year}")
    if meta.get("filename"):
        lines.append(f"- PDF 文件名：{meta['filename']}")
    if meta.get("page_count") is not None:
        note = ""
        if meta.get("truncated"):
            note = "（超出页数上限，未读取全部页面）"
        elif meta.get("section_read_mode"):
            note = "（按章节分次读取 PDF 相关页）"
        lines.append(
            f"- PDF 共 {meta['page_count']} 页，本次提取 {meta.get('pages_used', '?')} 页{note}"
        )
    if extra_instructions and extra_instructions.strip():
        lines.extend(["", "## 用户补充要求", "", extra_instructions.strip()])
    lines.extend(
        [
            "",
            "---",
            "",
            "## 年报 PDF 提取文本",
            "",
            pdf_text.strip() or "（未能从 PDF 提取到有效文本）",
            "",
            "---",
            "",
            "请现在开始输出完整的 Markdown 分析报告。",
        ]
    )
    return "\n".join(lines)


def _call_llm(
    get_client: Callable,
    model: str,
    system: str,
    user_prompt: str,
    max_tokens: int,
) -> tuple[str, Dict[str, int]]:
    client = get_client()
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user_prompt}],
    )
    text = _strip_fence(_extract_response_text(response.content))
    usage = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    }
    return text, usage


def analyze_section(
    get_client: Callable,
    model: str,
    section: TemplateSection,
    pdf_text: str,
    *,
    company_name: Optional[str] = None,
    report_year: Optional[str] = None,
    extra_instructions: Optional[str] = None,
    pdf_meta: Optional[Dict[str, Any]] = None,
    pdf_pages: Optional[List[PdfPage]] = None,
    max_tokens: int = 4096,
) -> tuple[str, Dict[str, int]]:
    prompt = build_section_prompt(
        section,
        pdf_text,
        company_name=company_name,
        report_year=report_year,
        extra_instructions=extra_instructions,
        pdf_meta=pdf_meta,
        pdf_pages=pdf_pages,
    )
    return _call_llm(get_client, model, SYSTEM_PROMPT, prompt, max_tokens)


def analyze_annual_report(
    get_client: Callable,
    model: str,
    template_md: str,
    pdf_text: str,
    *,
    company_name: Optional[str] = None,
    report_year: Optional[str] = None,
    extra_instructions: Optional[str] = None,
    pdf_meta: Optional[Dict[str, Any]] = None,
    max_tokens: int = 8192,
) -> Dict[str, Any]:
    user_prompt = build_user_prompt(
        template_md,
        pdf_text,
        company_name=company_name,
        report_year=report_year,
        extra_instructions=extra_instructions,
        pdf_meta=pdf_meta,
    )
    result_text, usage = _call_llm(get_client, model, SYSTEM_PROMPT_FULL, user_prompt, max_tokens)
    return {"result": result_text, "model": model, "usage": usage, "sections": {}}


def analyze_by_sections(
    get_client: Callable,
    model: str,
    sections: List[TemplateSection],
    pdf_text: str,
    *,
    company_name: Optional[str] = None,
    report_year: Optional[str] = None,
    extra_instructions: Optional[str] = None,
    pdf_meta: Optional[Dict[str, Any]] = None,
    pdf_pages: Optional[List[PdfPage]] = None,
    max_tokens_per_section: int = 4096,
    on_section_done: Optional[Callable[[TemplateSection, int, int], None]] = None,
) -> Dict[str, Any]:
    parts: list[str] = []
    section_map: dict[str, str] = {}
    total_usage = {"input_tokens": 0, "output_tokens": 0}
    total = len(sections)

    for idx, section in enumerate(sections):
        text, usage = analyze_section(
            get_client,
            model,
            section,
            pdf_text,
            company_name=company_name,
            report_year=report_year,
            extra_instructions=extra_instructions,
            pdf_meta=pdf_meta,
            pdf_pages=pdf_pages,
            max_tokens=max_tokens_per_section,
        )
        parts.append(text)
        section_map[section.section_id] = text
        total_usage["input_tokens"] += usage["input_tokens"]
        total_usage["output_tokens"] += usage["output_tokens"]
        if on_section_done:
            on_section_done(section, idx + 1, total)

    return {
        "result": "\n\n".join(parts).strip(),
        "model": model,
        "usage": total_usage,
        "sections": section_map,
    }
