"""Ensure product reports with Excel NaN cells serialize for API responses."""

import math
import unittest

from tender_product_analysis.storage import _json_safe, _sanitize_records


class TestStorageJsonSafe(unittest.TestCase):
    def test_nan_to_none(self):
        self.assertIsNone(_json_safe(float("nan")))

    def test_sanitize_records(self):
        rows = _sanitize_records([{"单价": float("nan"), "数量": 1}])
        self.assertIsNone(rows[0]["单价"])
        self.assertFalse(math.isnan(rows[0]["数量"]))


if __name__ == "__main__":
    unittest.main()
