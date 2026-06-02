"""Tests for qty/price/total parsing and reconciliation."""

import unittest

from tender_product_analysis.amount_fields import (
    detect_table_header,
    parse_tabular_product_row,
    reconcile_amounts,
)


class TestAmountFields(unittest.TestCase):
    def test_reconcile_swap_price_total(self):
        # qty=4, swapped: "单价" column is actually line total
        r = reconcile_amounts(4, 79200, 19800)
        self.assertAlmostEqual(float(r["单价"]), 19800.0, places=0)
        self.assertAlmostEqual(float(r["总价"]), 79200.0, places=0)
        self.assertIn("swapped", " ".join(r.get("_amount_notes", [])))

    def test_reconcile_consistent(self):
        r = reconcile_amounts("4.00(台)", "19800", "79200")
        self.assertEqual(r["_amount_confidence"], "high")
        self.assertEqual(r["数量"], 4)
        self.assertEqual(r["单位"], "台")

    def test_gov_strict_row(self):
        line = (
            "1-18\t其他广播、电视、电影设备\t无线内部通话主机\t纳雅\tAFDI-BS450\t"
            "4.00(台)\t19,800.00\t79,200.00"
        )
        p = parse_tabular_product_row(line)
        self.assertIsNotNone(p)
        self.assertEqual(p["数量"], 4)
        self.assertAlmostEqual(float(p["单价"]), 19800.0)
        self.assertAlmostEqual(float(p["总价"]), 79200.0)

    def test_header_detection(self):
        text = "品目号\t品目名称\t采购标的\t品牌\t规格型号\t数量（单位）\t单价(元)\t总价(元)\n"
        text += "1-1\t设备\t测试产品\t品牌A\tX1\t2.00(套)\t1000.00\t2000.00"
        col = detect_table_header(text.splitlines())
        self.assertIsNotNone(col)
        p = parse_tabular_product_row(text.splitlines()[-1], col)
        self.assertEqual(p["产品名称"], "测试产品")
        self.assertEqual(p["数量"], 2)


if __name__ == "__main__":
    unittest.main()
