"""Persist tender-info job metadata across portal restarts."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .crawler_runner import OUTPUT_BASE

INDEX_FILE = OUTPUT_BASE / "_jobs_index.json"
_JOB_ID_RE = re.compile(r"^[a-f0-9]{8,16}$")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_index() -> List[Dict[str, Any]]:
    if not INDEX_FILE.is_file():
        return []
    try:
        data = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict) and isinstance(data.get("jobs"), list):
        return [x for x in data["jobs"] if isinstance(x, dict)]
    return []


def _write_index(entries: List[Dict[str, Any]]) -> None:
    OUTPUT_BASE.mkdir(parents=True, exist_ok=True)
    INDEX_FILE.write_text(
        json.dumps({"jobs": entries}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def save_job_record(meta: Dict[str, Any]) -> None:
    """Upsert job into global index and write per-job job_meta.json."""
    job_id = str(meta.get("job_id") or "").strip()
    if not job_id or not _JOB_ID_RE.match(job_id):
        return

    meta = {**meta, "job_id": job_id, "updated_at": _utc_now()}
    job_dir = OUTPUT_BASE / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "job_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    entries = _read_index()
    entries = [e for e in entries if e.get("job_id") != job_id]
    entries.insert(0, meta)
    _write_index(entries[:200])


def load_job_meta(job_id: str) -> Optional[Dict[str, Any]]:
    if not _JOB_ID_RE.match(job_id):
        return None
    p = OUTPUT_BASE / job_id / "job_meta.json"
    if p.is_file():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    for e in _read_index():
        if e.get("job_id") == job_id:
            return e
    return _scan_dir_meta(job_id)


def _scan_dir_meta(job_id: str) -> Optional[Dict[str, Any]]:
    d = OUTPUT_BASE / job_id
    if not d.is_dir():
        return None
    csv_files = list(d.glob("filtered_*.csv")) + list(d.glob("jianyu_*.csv"))
    if not csv_files:
        return None
    latest = max(csv_files, key=lambda p: p.stat().st_mtime)
    total = 0
    try:
        import csv

        with open(latest, encoding="utf-8-sig", newline="") as f:
            total = max(0, sum(1 for _ in csv.DictReader(f)))
    except OSError:
        pass
    return {
        "job_id": job_id,
        "keywords": latest.stem.replace("filtered_", "").replace("jianyu_", ""),
        "status": "completed",
        "total": total,
        "csv_download": f"/api/tender-info/download/{job_id}/{latest.name}",
        "saved_at": datetime.fromtimestamp(latest.stat().st_mtime, tz=timezone.utc).isoformat(),
        "recovered_from_disk": True,
    }


def list_persisted_jobs(limit: int = 30) -> List[Dict[str, Any]]:
    entries = _read_index()
    seen = {e.get("job_id") for e in entries}
    for d in sorted(OUTPUT_BASE.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if not d.is_dir() or d.name.startswith("_") or d.name == "auth_state.json":
            continue
        if not _JOB_ID_RE.match(d.name) or d.name in seen:
            continue
        meta = load_job_meta(d.name) or _scan_dir_meta(d.name)
        if meta:
            entries.append(meta)
            seen.add(d.name)
    entries.sort(key=lambda x: x.get("updated_at") or x.get("saved_at") or "", reverse=True)
    return entries[:limit]


def restore_job_rows(job_id: str) -> tuple[Optional[Dict[str, Any]], List[dict]]:
    """Load meta + rows from job directory for UI restore."""
    meta = load_job_meta(job_id)
    if not meta:
        return None, []

    from .crawler_runner import _load_rows_from_output

    rows = _load_rows_from_output(OUTPUT_BASE / job_id, lambda _line: None)
    if rows:
        if meta.get("total", 0) == 0:
            meta["total"] = len(rows)
    elif meta.get("total", 0) == 0 and meta.get("recovered_from_disk"):
        meta = _scan_dir_meta(job_id) or meta
    return meta, rows
