"""Tests for attachment text extraction."""

import tempfile
import unittest
from pathlib import Path

from tender_product_analysis.attachment_parser import extract_text_from_file


class TestAttachmentParser(unittest.TestCase):
    def test_missing_file(self):
        self.assertEqual(extract_text_from_file(Path("/nonexistent/x.pdf")), "")

    def test_unsupported_ext(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"hello")
            p = Path(f.name)
        try:
            self.assertEqual(extract_text_from_file(p), "")
        finally:
            p.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
