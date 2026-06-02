"""Tests for tender-analysis executive summary."""

import unittest

from tender_analysis.llm_summary import generate_executive_summary


class TestTenderSummary(unittest.TestCase):
    def test_rule_based_summary(self):
        charts = {
            "overview": {"total": 100, "count_1y": 40, "count_3y": 80},
            "amount_stats": {"total": 5000, "median": 12},
            "province": {"provinces": ["广东", "北京"], "counts": [30, 20]},
            "vendor_rank": {"vendors": ["公司A"], "counts": [5]},
            "market_pipeline": {"awarded": 60, "pending": 40},
        }
        stats = {"dedup_count": 95, "original_count": 120}
        out = generate_executive_summary(charts, stats, "工业相机", use_llm=False)
        self.assertIn("执行摘要", out["markdown"])
        self.assertTrue(out["insights"])
        self.assertEqual(out["source"], "rules")


if __name__ == "__main__":
    unittest.main()
