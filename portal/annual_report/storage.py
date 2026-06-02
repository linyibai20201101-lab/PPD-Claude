"""Persist annual report analysis outputs."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

PORTAL_ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = PORTAL_ROOT / "annual_report_data"


def new_report_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d") + "_" + uuid.uuid4().hex[:8]


def report_dir(report_id: str) -> Path:
    return REPORT_DIR / report_id


def save_report(
    report_id: str,
    markdown: str,
    meta: Dict[str, Any],
    pdf_bytes: Optional[bytes] = None,
    sections: Optional[Dict[str, str]] = None,
    extracted_text: Optional[str] = None,
    metrics: Optional[Dict[str, Any]] = None,
    verification: Optional[Dict[str, Any]] = None,
    extra_pdfs: Optional[Dict[str, bytes]] = None,
) -> Path:
    d = report_dir(report_id)
    d.mkdir(parents=True, exist_ok=True)

    (d / "report.md").write_text(markdown, encoding="utf-8")
    meta = {**meta, "report_id": report_id, "saved_at": datetime.now(timezone.utc).isoformat()}
    (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    if pdf_bytes:
        (d / "source.pdf").write_bytes(pdf_bytes)

    if extra_pdfs:
        for name, data in extra_pdfs.items():
            safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in name)[:80]
            (d / safe).write_bytes(data)

    if extracted_text is not None:
        (d / "extracted_text.txt").write_text(extracted_text, encoding="utf-8")

    if sections:
        sec_dir = d / "sections"
        sec_dir.mkdir(exist_ok=True)
        for sid, content in sections.items():
            safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in sid)[:80]
            (sec_dir / f"{safe}.md").write_text(content, encoding="utf-8")

    if metrics is not None:
        (d / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    if verification is not None:
        (d / "verification.json").write_text(json.dumps(verification, ensure_ascii=False, indent=2), encoding="utf-8")

    return d


def load_extracted_text(report_id: str) -> str:
    p = report_dir(report_id) / "extracted_text.txt"
    if p.is_file():
        return p.read_text(encoding="utf-8")
    return ""


def load_sections(report_id: str) -> Dict[str, str]:
    sec_dir = report_dir(report_id) / "sections"
    if not sec_dir.is_dir():
        return {}
    out: Dict[str, str] = {}
    for f in sec_dir.glob("*.md"):
        out[f.stem] = f.read_text(encoding="utf-8")
    return out


def load_metrics(report_id: str) -> Optional[Dict[str, Any]]:
    p = report_dir(report_id) / "metrics.json"
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def load_verification(report_id: str) -> Optional[Dict[str, Any]]:
    p = report_dir(report_id) / "verification.json"
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def update_report_content(
    report_id: str,
    markdown: str,
    sections: Optional[Dict[str, str]] = None,
    meta_patch: Optional[Dict[str, Any]] = None,
) -> None:
    d = report_dir(report_id)
    if not d.is_dir():
        raise FileNotFoundError(f"报告不存在: {report_id}")
    (d / "report.md").write_text(markdown, encoding="utf-8")
    if sections:
        sec_dir = d / "sections"
        sec_dir.mkdir(exist_ok=True)
        for sid, content in sections.items():
            safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in sid)[:80]
            (sec_dir / f"{safe}.md").write_text(content, encoding="utf-8")
    if meta_patch:
        meta_path = d / "meta.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.is_file() else {}
        meta.update(meta_patch)
        meta["updated_at"] = datetime.now(timezone.utc).isoformat()
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def load_report(report_id: str) -> Dict[str, Any]:
    d = report_dir(report_id)
    if not d.is_dir():
        raise FileNotFoundError(f"报告不存在: {report_id}")

    md_path = d / "report.md"
    meta_path = d / "meta.json"
    if not md_path.is_file():
        raise FileNotFoundError(f"报告文件不存在: {report_id}")

    meta: Dict[str, Any] = {}
    if meta_path.is_file():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))

    return {
        "report_id": report_id,
        "result": md_path.read_text(encoding="utf-8"),
        "meta": meta,
        "metrics": load_metrics(report_id),
        "verification": load_verification(report_id),
        "sections": load_sections(report_id),
    }


def list_reports(limit: int = 30) -> List[Dict[str, Any]]:
    if not REPORT_DIR.is_dir():
        return []

    items: List[Dict[str, Any]] = []
    for d in sorted(REPORT_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if not d.is_dir():
            continue
        meta_path = d / "meta.json"
        if not meta_path.is_file():
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            items.append(
                {
                    "report_id": d.name,
                    "company_name": meta.get("company_name") or "",
                    "report_year": meta.get("report_year") or "",
                    "filename": meta.get("filename") or "",
                    "saved_at": meta.get("saved_at") or "",
                    "model": meta.get("model") or "",
                    "extract_method": meta.get("extract_method") or "",
                    "compare_years": meta.get("compare_years") or [],
                }
            )
        except Exception:
            continue
        if len(items) >= limit:
            break
    return items
