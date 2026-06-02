"""Audit projects with failed detail, no keyword hit, or attachment parse gaps."""

from __future__ import annotations

from typing import Any, Dict, List


def has_attachment(rec: dict) -> bool:
    if rec.get("附件列表"):
        return True
    flag = rec.get("有附件")
    return str(flag).lower() in ("true", "1", "yes") or flag is True


def build_unmatched_audit(records: List[dict]) -> List[Dict[str, Any]]:
    """Projects worth review: detail failure, no product lines, or attachment gap."""
    out: List[Dict[str, Any]] = []
    for rec in records or []:
        if not isinstance(rec, dict):
            continue
        reasons: List[str] = []
        detail = str(rec.get("详情抓取") or "")
        strategy = str(rec.get("匹配策略") or "")
        qty = int(rec.get("产品数量") or 0)
        has_url = bool(str(rec.get("详情链接") or rec.get("source_url") or "").strip())

        if detail.startswith("failed"):
            reasons.append(detail.replace("failed: ", "详情失败: ", 1))
        elif has_url and detail not in ("ok", "pending", ""):
            reasons.append(f"详情状态异常: {detail}")
        if strategy == "keyword_no_hit":
            reasons.append("关键词未命中正文/附件清单")
        if qty == 0 and strategy not in ("no_keyword", ""):
            reasons.append("未产出产品行")
        if has_attachment(rec):
            parsed = int(rec.get("附件解析数") or 0)
            downloads = rec.get("附件下载") or []
            if downloads and parsed == 0:
                reasons.append("附件已下载但未解析出产品")
            elif not downloads and qty == 0:
                reasons.append("有附件标记但未下载成功")

        if not reasons:
            continue

        out.append(
            {
                "项目名称": (rec.get("项目名称") or "")[:120],
                "详情链接": rec.get("详情链接") or rec.get("source_url") or "",
                "详情抓取": detail,
                "匹配策略": strategy,
                "产品数量": qty,
                "有附件": has_attachment(rec),
                "附件解析数": int(rec.get("附件解析数") or 0),
                "原因": "；".join(reasons),
            }
        )
    return out


def filter_for_retry(records: List[dict], retry_mode: str) -> List[dict]:
    """Select subset to re-fetch detail/attachments."""
    mode = (retry_mode or "failed").strip().lower()
    selected: List[dict] = []
    for rec in records:
        detail = str(rec.get("详情抓取") or "")
        strategy = str(rec.get("匹配策略") or "")
        qty = int(rec.get("产品数量") or 0)
        has_att = has_attachment(rec)
        parsed = int(rec.get("附件解析数") or 0)

        if mode in ("failed", "fail", "detail_failed"):
            if detail.startswith("failed") or (rec.get("详情链接") and detail != "ok"):
                selected.append(rec)
        elif mode in ("no_match", "unmatched", "nomatch"):
            if strategy == "keyword_no_hit" or qty == 0:
                selected.append(rec)
        elif mode in ("attachments", "attach", "attachment"):
            if has_att and (parsed == 0 or qty == 0):
                selected.append(rec)
        else:
            if detail.startswith("failed"):
                selected.append(rec)
    return selected
