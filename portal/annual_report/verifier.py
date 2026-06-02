"""Cross-check numeric claims in report against PDF source text."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class VerificationIssue:
    kind: str  # missing | mismatch
    value: str
    context: str
    message: str


@dataclass
class VerificationResult:
    checked_count: int = 0
    matched_count: int = 0
    issues: List[VerificationIssue] = field(default_factory=list)
    score: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checked_count": self.checked_count,
            "matched_count": self.matched_count,
            "score": round(self.score, 3),
            "issues": [
                {"kind": i.kind, "value": i.value, "context": i.context, "message": i.message}
                for i in self.issues
            ],
        }


def _normalize_num(s: str) -> str:
    return re.sub(r"[,\s，]", "", s)


def _extract_report_numbers(markdown: str, limit: int = 80) -> List[tuple[str, str]]:
    """Extract significant numbers from markdown tables and bold figures."""
    found: List[tuple[str, str]] = []
    seen = set()

    for m in re.finditer(r"\*\*(\d[\d,.]*(?:\.\d+)?)\s*(%|％|亿|万|元)?\*\*", markdown):
        val = m.group(0)
        if val not in seen:
            seen.add(val)
            ctx = markdown[max(0, m.start() - 30) : m.end() + 30].replace("\n", " ")
            found.append((m.group(1) + (m.group(2) or ""), ctx))

    for line in markdown.splitlines():
        if "|" not in line or line.count("|") < 3:
            continue
        cells = [c.strip() for c in line.split("|") if c.strip()]
        for cell in cells:
            if re.match(r"^-?\d[\d,.]*(%|％|亿|万)?$", cell.replace(" ", "")):
                key = _normalize_num(cell)
                if key not in seen and len(key) >= 2:
                    seen.add(key)
                    found.append((cell, line[:120]))

    return found[:limit]


def verify_report_numbers(markdown: str, pdf_text: str) -> VerificationResult:
    result = VerificationResult()
    pdf_norm = _normalize_num(pdf_text)

    numbers = _extract_report_numbers(markdown)
    result.checked_count = len(numbers)

    for val, ctx in numbers:
        core = _normalize_num(re.sub(r"(%|％|亿|万|元)", "", val))
        if len(core) < 2:
            continue
        if core in pdf_norm or val.replace(" ", "") in pdf_text:
            result.matched_count += 1
        else:
            # allow partial match for decimals
            alt = core.rstrip("0").rstrip(".")
            if alt and alt in pdf_norm:
                result.matched_count += 1
            else:
                result.issues.append(
                    VerificationIssue(
                        kind="missing",
                        value=val,
                        context=ctx[:100],
                        message=f"报告中的数值「{val}」未在 PDF 原文中找到匹配",
                    )
                )

    if result.checked_count:
        result.score = result.matched_count / result.checked_count
    return result
