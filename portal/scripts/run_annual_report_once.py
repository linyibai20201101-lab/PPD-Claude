#!/usr/bin/env python3
"""One-off annual report analysis from CLI."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

import anthropic

from annual_report.engine import run_analysis


def get_client():
    kwargs = {"api_key": os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")}
    base = os.getenv("ANTHROPIC_BASE_URL")
    if base:
        kwargs["base_url"] = base
    return anthropic.Anthropic(**kwargs)


def main():
    pdf_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"c:\Users\qiyz\Desktop\申棱年报.pdf")
    company = sys.argv[2] if len(sys.argv) > 2 else "广东申菱环境系统股份有限公司"
    year = sys.argv[3] if len(sys.argv) > 3 else "2025"
    model = os.getenv("ANTHROPIC_DEFAULT_MODEL", "mimo-v2.5-pro")

    pdf_bytes = pdf_path.read_bytes()
    print(f"PDF: {pdf_path.name} ({len(pdf_bytes)} bytes)")
    print(f"Company: {company}  Year: {year}  Model: {model}")

    def on_progress(phase, pct, msg):
        print(f"[{pct:3d}%] {phase}: {msg}", flush=True)

    out = run_analysis(
        get_client,
        model,
        pdf_bytes,
        pdf_path.name,
        company_name=company,
        report_year=year,
        section_mode=True,
        force_ocr=False,
        on_progress=on_progress,
    )

    print("\n=== DONE ===")
    print("report_id:", out["report_id"])
    print("verification_score:", out.get("verification", {}).get("score"))
    print("metrics:", out.get("metrics"))
    report_path = ROOT / "annual_report_data" / out["report_id"] / "report.md"
    print("report_path:", report_path)
    print("\n--- preview (first 2500 chars) ---")
    print(out["result"][:2500])


if __name__ == "__main__":
    main()
