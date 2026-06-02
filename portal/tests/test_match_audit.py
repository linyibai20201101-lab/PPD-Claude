"""Tests for unmatched audit and retry filtering."""

import unittest

from tender_product_analysis.match_audit import build_unmatched_audit, filter_for_retry


class TestMatchAudit(unittest.TestCase):
    def test_unmatched_no_hit(self):
        records = [
            {
                "项目名称": "项目A",
                "详情抓取": "ok",
                "匹配策略": "keyword_no_hit",
                "产品数量": 0,
            }
        ]
        audit = build_unmatched_audit(records)
        self.assertEqual(len(audit), 1)
        self.assertIn("未命中", audit[0]["原因"])

    def test_filter_failed_retry(self):
        records = [
            {"项目名称": "A", "详情抓取": "ok", "详情链接": "http://x"},
            {"项目名称": "B", "详情抓取": "failed: timeout", "详情链接": "http://y"},
        ]
        out = filter_for_retry(records, "failed")
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["项目名称"], "B")


if __name__ == "__main__":
    unittest.main()
