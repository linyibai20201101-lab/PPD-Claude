"""Load tender list data from tender-info job directory."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any, List, Tuple

PORTAL_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PORTAL_ROOT / "tender_raw_data"


def _parse_attachment_flag(val: Any) -> bool:
    if val is None:
        return False
    s = str(val).strip().lower()
    return s in ("true", "1", "yes", "是") or val is True


def load_rows_from_job(source_job_id: str) -> Tuple[List[dict], str]:
    job_dir = DATA_DIR / source_job_id
    if not job_dir.is_dir():
        raise FileNotFoundError(f"标书获取任务不存在: {source_job_id}")

    keyword = "标书产品"

    csv_files = sorted(job_dir.glob("filtered_*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    if csv_files:
        rows = _read_csv(csv_files[0])
        keyword = csv_files[0].stem.replace("filtered_", "") or keyword
        return rows, keyword

    for pattern in ("jianyu_*.json", "partial_results.json"):
        candidates = sorted(job_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
        for jp in candidates:
            if not jp.is_file():
                continue
            data = json.loads(jp.read_text(encoding="utf-8"))
            if isinstance(data, list) and data:
                m = re.search(r"jianyu_(.+?)_\d{8}", jp.name)
                if m:
                    keyword = m.group(1)
                return data, keyword

    raise FileNotFoundError(f"任务 {source_job_id} 下未找到 CSV/JSON 数据")


def _read_csv(path: Path) -> List[dict]:
    rows: List[dict] = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            rows.append(dict(row))
    return rows


def normalize_row(row: dict) -> dict:
    """Unify column names for downstream."""
    out = dict(row)
    if "预算金额" in out and "金额" not in out:
        out["金额"] = out["预算金额"]
    if "发布时间" in out and "日期" not in out:
        out["日期"] = out["发布时间"]
    if "项目类型" in out and "状态" not in out:
        out["状态"] = out["项目类型"]
    out["有附件"] = _parse_attachment_flag(out.get("有附件"))
    return out


def filter_rows(
    rows: List[dict],
    *,
    only_with_attachment: bool = False,
    max_projects: int | None = None,
) -> List[dict]:
    items = [normalize_row(r) for r in rows if str(r.get("项目名称", "")).strip()]
    if only_with_attachment:
        items = [r for r in items if r.get("有附件")]
    if max_projects and max_projects > 0:
        items = items[:max_projects]
    return items
