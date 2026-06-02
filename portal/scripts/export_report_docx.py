#!/usr/bin/env python3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from annual_report.exporter import export_docx, export_filename
from annual_report.storage import load_report

report_id = sys.argv[1] if len(sys.argv) > 1 else "20260601_4c408ba5"
data = load_report(report_id)
meta = data.get("meta") or {}
base = f"{meta.get('company_name') or '公司'}_{meta.get('report_year') or '年报'}_财报分析"
docx_bytes = export_docx(data["result"], title=base)

report_dir = ROOT / "annual_report_data" / report_id
out_report = report_dir / "report.docx"
out_desktop = Path(r"c:\Users\qiyz\Desktop") / export_filename(base, "docx")

out_report.write_bytes(docx_bytes)
out_desktop.write_bytes(docx_bytes)
print(out_desktop)
print(out_report)
print(len(docx_bytes))
