"""Persist tender product analysis outputs."""

from __future__ import annotations

import json
import math
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

PORTAL_ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = PORTAL_ROOT / "tender_product_data"


def _json_safe(value: Any) -> Any:
    """Convert pandas/numpy NaN to None so FastAPI JSON encoding does not 500."""
    if value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, (np.floating, np.integer)):
        if np.isnan(value):
            return None
        return value.item() if hasattr(value, "item") else float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


def _sanitize_records(records: List[dict]) -> List[dict]:
    return [{k: _json_safe(v) for k, v in rec.items()} for rec in records]


def new_report_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d") + "_" + uuid.uuid4().hex[:8]


def report_dir(report_id: str) -> Path:
    d = REPORT_DIR / report_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_report(
    report_id: str,
    *,
    meta: Dict[str, Any],
    projects: List[dict],
    master_df: pd.DataFrame,
    stats: Dict[str, Any],
    report_md: str,
) -> Path:
    d = report_dir(report_id)
    (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    (d / "projects_enriched.json").write_text(
        json.dumps(projects, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (d / "report.md").write_text(report_md, encoding="utf-8")
    from .export import write_products_master, write_stats

    write_products_master(master_df, d / "products_master.xlsx")
    (d / "products_master.json").write_text(
        master_df.to_json(orient="records", force_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_stats(stats, d / "stats_summary.json")
    unmatched = stats.get("unmatched_projects")
    if isinstance(unmatched, list):
        (d / "unmatched_projects.json").write_text(
            json.dumps(unmatched, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return d


def load_report(report_id: str) -> Dict[str, Any]:
    d = report_dir(report_id)
    if not (d / "meta.json").is_file():
        raise FileNotFoundError(report_id)
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    report_md = (d / "report.md").read_text(encoding="utf-8") if (d / "report.md").is_file() else ""
    stats = {}
    sp = d / "stats_summary.json"
    if sp.is_file():
        stats = json.loads(sp.read_text(encoding="utf-8"))

    products: List[dict] = []
    pj = d / "products_master.json"
    if pj.is_file():
        raw = json.loads(pj.read_text(encoding="utf-8"))
        products = raw if isinstance(raw, list) else []
    elif (d / "products_master.xlsx").is_file():
        df = pd.read_excel(d / "products_master.xlsx")
        products = df.where(pd.notna(df), None).to_dict(orient="records")
    products = _sanitize_records(products)

    unmatched: List[dict] = []
    um = d / "unmatched_projects.json"
    if um.is_file():
        raw_um = json.loads(um.read_text(encoding="utf-8"))
        unmatched = raw_um if isinstance(raw_um, list) else []

    return {
        "report_id": report_id,
        "meta": meta,
        "report_md": report_md,
        "stats": stats,
        "products": products,
        "product_line_count": len(products),
        "unmatched_projects": unmatched,
        "dir": str(d),
    }


def load_projects_enriched(report_id: str) -> List[dict]:
    p = report_dir(report_id) / "projects_enriched.json"
    if not p.is_file():
        raise FileNotFoundError(f"projects_enriched.json missing for {report_id}")
    raw = json.loads(p.read_text(encoding="utf-8"))
    return raw if isinstance(raw, list) else []


def list_reports(limit: int = 30) -> List[Dict[str, Any]]:
    if not REPORT_DIR.is_dir():
        return []
    items = []
    for p in sorted(REPORT_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if not p.is_dir():
            continue
        meta_path = p / "meta.json"
        if not meta_path.is_file():
            continue
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta["report_id"] = p.name
        meta["saved_at"] = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).isoformat()
        items.append(meta)
        if len(items) >= limit:
            break
    return items
