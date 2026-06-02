"""Tests for keyword + attribute product matching."""

import unittest

from tender_product_analysis.product_matcher import (
    build_match_profile,
    extract_products_from_text,
    merge_product_lists,
)


class TestProductMatcher(unittest.TestCase):
    def test_profile_no_short_fragments(self):
        p = build_match_profile("AFDI-BS450")
        terms = p.match_terms()
        self.assertNotIn("AF", terms)
        self.assertNotIn("50", terms)

    def test_gov_table_only_matching_skus(self):
        text = """
品目号\t品目名称\t采购标的\t品牌\t规格型号\t数量（单位）\t单价(元)\t总价(元)
1-15\t其他广播、电视、电影设备\t延时服务器\t瑞得霖科\tUltraRP2-DE21C\t1.00(套)\t108,800.00\t108,800.00
1-18\t其他广播、电视、电影设备\t无线内部通话主机\t纳雅\tAFDI-BS450\t4.00(台)\t19,800.00\t79,200.00
1-20\t其他广播、电视、电影设备\t无线内部通话腰包\t纳雅\tAFDI-PT420\t24.00(个)\t2,980.00\t71,520.00
1-24\t其他广播、电视、电影设备\t电脑图案切割灯\t珠江\tPR-2927\t60.00(台)\t20,400.00\t1,224,000.00
"""
        products = extract_products_from_text(text, "AFDI-BS450")
        names = [p["产品名称"] for p in products]
        self.assertIn("无线内部通话主机", names)
        self.assertNotIn("延时服务器", names)
        self.assertNotIn("电脑图案切割灯", names)
        self.assertEqual(len(products), 1)

    def test_merge_prefers_attachment(self):
        detail = [{"产品名称": "相机A", "型号": "X1", "单价": "", "参数来源": "detail_page:table"}]
        att = [{"产品名称": "相机A", "型号": "X1", "单价": 1000, "参数来源": "attachment:标书.pdf"}]
        merged = merge_product_lists(detail, att)
        self.assertEqual(merged[0]["单价"], 1000)


if __name__ == "__main__":
    unittest.main()
