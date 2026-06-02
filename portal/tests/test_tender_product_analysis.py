"""Tests for tender_product_analysis (no browser)."""

import json
import tempfile
import unittest
from pathlib import Path

from tender_product_analysis.loader import filter_rows, load_rows_from_job
from tender_product_analysis.product_lines import build_product_lines
from tender_product_analysis.stats import compute_stats_summary, prepare_projects_df


class TestLoader(unittest.TestCase):
    def test_filter_and_product_lines(self):
        rows = [
            {
                "项目名称": "测试项目A",
                "预算金额": "100万元",
                "地区": "广东-广州市",
                "采购单位": "某大学",
                "中标单位": "某公司",
                "有附件": True,
                "详情链接": "https://example.com/a",
                "产品明细": json.dumps(
                    [{"产品名称": "工业相机", "数量": 2, "单价": 1000}], ensure_ascii=False
                ),
            }
        ]
        items = filter_rows(rows, max_projects=10)
        self.assertEqual(len(items), 1)
        master = build_product_lines(items, keyword="工业相机")
        self.assertEqual(len(master), 1)
        self.assertEqual(master.iloc[0]["产品名称"], "工业相机")

    def test_load_from_temp_job_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            import tender_product_analysis.loader as L

            orig = L.DATA_DIR
            L.DATA_DIR = Path(tmp)
            try:
                job = Path(tmp) / "job123"
                job.mkdir()
                csv = job / "filtered_test.csv"
                csv.write_text(
                    "项目名称,预算金额,地区,有附件,详情链接\n"
                    "项目1,10万,北京,True,https://x.com/1\n",
                    encoding="utf-8-sig",
                )
                rows, kw = load_rows_from_job("job123")
                self.assertEqual(len(rows), 1)
                self.assertEqual(kw, "test")
            finally:
                L.DATA_DIR = orig


class TestStats(unittest.TestCase):
    def test_compute_summary(self):
        records = [
            {
                "项目名称": "P1",
                "金额": "50万",
                "地区": "广东-深圳",
                "中标单位": "甲公司",
                "有附件": False,
                "详情抓取": "ok",
                "产品明细": [{"产品名称": "相机", "数量": 3}],
            }
        ]
        pdf, _ = prepare_projects_df(records, keyword="相机")
        master = build_product_lines(records)
        s = compute_stats_summary(pdf, master, "相机", "job1")
        self.assertEqual(s["project_count"], 1)
        self.assertGreaterEqual(s.get("product_line_count", 0), 1)


if __name__ == "__main__":
    unittest.main()
