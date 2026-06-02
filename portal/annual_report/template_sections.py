"""Split analysis template into sections for chapter-wise LLM calls."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

from .pdf_extractor import PdfPage, parse_pages_from_text

SECTION_MAX_CHARS = int(os.getenv("ANNUAL_REPORT_SECTION_MAX_CHARS", "45000"))


@dataclass
class TemplateSection:
    section_id: str
    title: str
    content: str
    order: int


# Keywords to pick relevant PDF pages per section (Chinese annual report headings)
SECTION_HINTS: dict[str, list[str]] = {
    "核心摘要": ["摘要", "公司简介", "主要会计数据", "财务指标", "经营情况讨论", "营业收入", "净利润"],
    "公司概况": ["公司简介", "股东", "股本", "子公司", "员工", "董事", "监事", "高管", "实际控制人"],
    "行业与市场": ["行业", "市场", "竞争", "产业链", "风险因素", "经营环境", "同行业"],
    "经营分析": ["主营业务", "产品", "客户", "供应商", "产销", "销售模式", "采购", "分产品", "分地区"],
    "财务分析": [
        "利润表",
        "资产负债表",
        "现金流量",
        "营业收入",
        "净利润",
        "毛利率",
        "研发费用",
        "财务报告",
        "合并财务报表",
        "附注",
        "会计政策",
        "资产减值",
        "应收",
        "存货",
    ],
    "研发与战略": ["研发", "技术", "专利", "在研", "未来发展", "战略规划", "核心竞争力"],
    "公司治理与资本回报": ["治理", "内控", "关联交易", "担保", "分红", "利润分配", "审计意见", "募集资金"],
    "综合结论与建议": ["结论", "展望", "风险", "经营情况讨论与分析", "未来发展"],
    "附录": ["附", "财务报表", "审计报告", "附注", "合并资产负债表", "合并利润表", "合并现金流量表"],
}

# Prefer pages near the start of the document (page index, 0-based)
SECTION_HEAD_PAGES: dict[str, int] = {
    "核心摘要": 20,
    "公司概况": 35,
}

# Prefer pages in the tail of the document (fraction of total pages from which to boost)
SECTION_TAIL_BIAS: dict[str, float] = {
    "财务分析": 0.4,
    "附录": 0.5,
    "公司治理与资本回报": 0.35,
}


def _slug(title: str) -> str:
    t = re.sub(r"^[#\s\d、.．]+", "", title).strip()
    t = re.sub(r"[（(].*?[）)]", "", t).strip()
    return t or "section"


def _resolve_hint_key(section: TemplateSection) -> str:
    hint_key = section.section_id
    for key in SECTION_HINTS:
        if key in section.title or key in section.section_id:
            return key
    return hint_key


def split_template(template_md: str) -> list[TemplateSection]:
    """Split on level-2 headings (## …)."""
    lines = template_md.splitlines()
    sections: list[TemplateSection] = []
    current_title: str | None = None
    current_lines: list[str] = []
    order = 0

    header_re = re.compile(r"^##\s+(.+)$")

    for line in lines:
        m = header_re.match(line)
        if m:
            if current_title is not None:
                sections.append(
                    TemplateSection(
                        section_id=_slug(current_title),
                        title=current_title.strip(),
                        content="\n".join(current_lines).strip(),
                        order=order,
                    )
                )
                order += 1
            current_title = m.group(1).strip()
            current_lines = [line]
        elif current_title is not None:
            current_lines.append(line)

    if current_title is not None:
        sections.append(
            TemplateSection(
                section_id=_slug(current_title),
                title=current_title.strip(),
                content="\n".join(current_lines).strip(),
                order=order,
            )
        )

    if not sections:
        sections.append(
            TemplateSection(
                section_id="full",
                title="完整报告",
                content=template_md.strip(),
                order=0,
            )
        )
    return sections


def _score_page(
    page: PdfPage,
    *,
    keywords: list[str],
    page_index: int,
    total_pages: int,
    head_pages: int,
    tail_bias: float,
) -> int:
    score = sum(page.text.count(kw) for kw in keywords)
    if head_pages and page_index < head_pages:
        score += 3
    if tail_bias and total_pages > 0:
        tail_start = int(total_pages * tail_bias)
        if page_index >= tail_start:
            score += 4
    return score


def slice_pages_for_section(
    pages: list[PdfPage],
    section: TemplateSection,
    max_chars: int = SECTION_MAX_CHARS,
) -> str:
    """Pick PDF pages for one template section (chapter-wise read)."""
    if not pages:
        return ""

    hint_key = _resolve_hint_key(section)
    keywords = SECTION_HINTS.get(hint_key, SECTION_HINTS.get(section.section_id, []))
    head_pages = SECTION_HEAD_PAGES.get(hint_key, 0)
    tail_bias = SECTION_TAIL_BIAS.get(hint_key, 0.0)
    total = len(pages)

    scored: list[tuple[int, int, PdfPage]] = []
    for idx, page in enumerate(pages):
        score = _score_page(
            page,
            keywords=keywords,
            page_index=idx,
            total_pages=total,
            head_pages=head_pages,
            tail_bias=tail_bias,
        )
        scored.append((score, idx, page))

    scored.sort(key=lambda x: (-x[0], x[1]))

    selected: list[PdfPage] = []
    selected_indices: set[int] = set()
    total_chars = 0

    for score, idx, page in scored:
        if score == 0 and selected:
            continue
        block = f"--- 第 {page.page_num} 页 ---\n{page.text}"
        block_len = len(block) + 2
        if total_chars + block_len > max_chars and selected:
            break
        if idx not in selected_indices:
            selected.append(page)
            selected_indices.add(idx)
            total_chars += block_len
        if total_chars >= max_chars:
            break

    if not selected:
        for page in pages[: max(1, max_chars // 2000)]:
            block = f"--- 第 {page.page_num} 页 ---\n{page.text}"
            if total_chars + len(block) > max_chars and selected:
                break
            selected.append(page)
            total_chars += len(block)

    selected.sort(key=lambda p: p.page_num)
    return "\n\n".join(f"--- 第 {p.page_num} 页 ---\n{p.text}" for p in selected)


def slice_text_for_section(full_text: str, section: TemplateSection, max_chars: int = SECTION_MAX_CHARS) -> str:
    """Pick PDF page chunks most relevant to a template section."""
    pages = parse_pages_from_text(full_text)
    if pages:
        return slice_pages_for_section(pages, section, max_chars=max_chars)

    if not full_text.strip():
        return ""
    return full_text[:max_chars]
