"""Tests for annual_report module."""

from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path

import fitz

from annual_report.metrics_extractor import extract_metrics_regex
from annual_report.pdf_extractor import PdfPage, pages_to_text, parse_pages_from_text
from annual_report.storage import save_report, load_report, list_reports
from annual_report.template_sections import split_template, slice_text_for_section, slice_pages_for_section
from annual_report.verifier import verify_report_numbers


SAMPLE_TEMPLATE = """# 测试模板

## 一、核心摘要

### 经营概览
- 占位

## 二、财务分析

### 利润表
| 指标 | 数值 |
|------|------|
| 营业收入 | |
"""


def _make_pdf(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


class TestTemplateSections(unittest.TestCase):
    def test_split_template(self):
        sections = split_template(SAMPLE_TEMPLATE)
        self.assertGreaterEqual(len(sections), 2)
        self.assertTrue(any("摘要" in s.title for s in sections))

    def test_slice_text_for_section(self):
        sections = split_template(SAMPLE_TEMPLATE)
        pdf_text = "--- 第 1 页 ---\n营业收入 100亿元\n--- 第 2 页 ---\n公司治理\n"
        excerpt = slice_text_for_section(pdf_text, sections[-1])
        self.assertIn("营业收入", excerpt)

    def test_slice_pages_for_section_tail_bias(self):
        sections = split_template(SAMPLE_TEMPLATE)
        fin = next(s for s in sections if "财务" in s.title)
        pages = [
            PdfPage(1, "公司简介"),
            PdfPage(2, "经营讨论"),
            PdfPage(3, "合并利润表 营业收入 100亿元"),
            PdfPage(4, "财务报表附注 应收账款"),
        ]
        excerpt = slice_pages_for_section(pages, fin, max_chars=5000)
        self.assertIn("利润表", excerpt)
        self.assertIn("附注", excerpt)

    def test_parse_pages_from_text(self):
        text = "--- 第 1 页 ---\nA\n\n--- 第 2 页 ---\nB"
        pages = parse_pages_from_text(text)
        self.assertEqual(len(pages), 2)
        self.assertEqual(pages[1].text.strip(), "B")


class TestMetrics(unittest.TestCase):
    def test_regex_extract(self):
        md = "本年度营业收入 **100** 亿元，同比 **+10%**，毛利率 **25%**"
        m = extract_metrics_regex(md, {"company_name": "测试公司", "report_year": "2024"})
        self.assertEqual(m.get("company_name"), "测试公司")


class TestVerifier(unittest.TestCase):
    def test_verify_match(self):
        pdf = "公司2024年营业收入100亿元，净利润10亿元"
        md = "营业收入 **100** 亿元，净利润 **10** 亿元"
        r = verify_report_numbers(md, pdf)
        self.assertGreater(r.matched_count, 0)
        self.assertGreaterEqual(r.score, 0.5)


class TestStorage(unittest.TestCase):
    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            import annual_report.storage as st

            orig = st.REPORT_DIR
            st.REPORT_DIR = Path(tmp)
            try:
                rid = "test001_abc"
                save_report(rid, "# 报告\n", {"company_name": "X"}, metrics={"revenue": 1})
                data = load_report(rid)
                self.assertIn("报告", data["result"])
                self.assertEqual(data["metrics"]["revenue"], 1)
                self.assertGreaterEqual(len(list_reports()), 1)
            finally:
                st.REPORT_DIR = orig


if __name__ == "__main__":
    unittest.main()
