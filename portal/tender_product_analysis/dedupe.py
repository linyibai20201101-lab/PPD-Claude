"""Project-level deduplication before product extraction."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import List

PORTAL_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PORTAL_ROOT / "skills" / "tender-analysis" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from jianyu_crawler import deduplicate_results  # noqa: E402


def dedupe_projects(records: List[dict]) -> List[dict]:
    """Merge duplicate tender announcements for the same underlying project."""
    if not records:
        return records
    out = deduplicate_results(records)
    for r in out:
        r.pop("_clean_name", None)
    return out
