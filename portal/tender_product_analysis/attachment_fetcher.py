"""Download and parse attachments on Jianyu detail pages."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urljoin

from .attachment_parser import extract_text_from_file

ATTACHMENT_EXT = (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".zip")
MAX_FILES_PER_PROJECT = 5
MAX_FILE_BYTES = 25 * 1024 * 1024


def _safe_filename(name: str, fallback: str = "attachment") -> str:
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", (name or fallback).strip())
    return s[:120] or fallback


def _resolve_url(href: str, base_url: str) -> str:
    href = (href or "").strip()
    if not href or href.startswith("javascript"):
        return ""
    if href.startswith("//"):
        return "https:" + href
    if href.startswith("http"):
        return href
    return urljoin(base_url, href)


def _pick_extension(name: str, url: str, content_type: str = "") -> str:
    for src in (name, url):
        low = src.lower().split("?")[0]
        for ext in ATTACHMENT_EXT:
            if low.endswith(ext):
                return ext
    if "pdf" in content_type:
        return ".pdf"
    if "word" in content_type or "document" in content_type:
        return ".docx"
    return ".bin"


def download_attachments_on_page(
    page,
    context,
    attachments: List[dict],
    dest_dir: Path,
    *,
    page_url: str = "",
) -> List[Dict[str, Any]]:
    """
    Try to download attachment links on current detail page.
    Returns blocks: {name, path, text, status, size}.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    blocks: List[Dict[str, Any]] = []
    seen_urls: set[str] = set()

    for i, att in enumerate((attachments or [])[:MAX_FILES_PER_PROJECT]):
        url = _resolve_url(str(att.get("url") or ""), page_url)
        name = _safe_filename(str(att.get("name") or f"附件{i+1}"), f"附件{i+1}")
        if not url:
            continue
        if url in seen_urls:
            continue
        seen_urls.add(url)

        ext = _pick_extension(name, url)
        if not name.lower().endswith(ext):
            name = name + ext
        target = dest_dir / name
        if target.exists() and target.stat().st_size > 0:
            text = extract_text_from_file(target)
            blocks.append(
                {
                    "name": name,
                    "path": str(target),
                    "text": text,
                    "status": "cached",
                    "size": target.stat().st_size,
                }
            )
            continue

        status = "failed"
        try:
            frag = url.split("/")[-1][:24] if "/" in url else url[:24]
            link = page.locator(f'a[href*="{frag}"]').first
            with page.expect_download(timeout=20000) as dl_info:
                link.click(timeout=5000)
            download = dl_info.value
            download.save_as(target)
            status = "download_click"
        except Exception:
            try:
                resp = context.request.get(url, timeout=60000)
                if not resp.ok:
                    raise RuntimeError(f"HTTP {resp.status}")
                body = resp.body()
                if len(body) > MAX_FILE_BYTES:
                    raise RuntimeError("file too large")
                target.write_bytes(body)
                status = "download_request"
            except Exception as e:
                blocks.append(
                    {
                        "name": name,
                        "url": url,
                        "text": "",
                        "status": f"failed: {e}",
                        "size": 0,
                    }
                )
                continue

        if not target.is_file() or target.stat().st_size == 0:
            blocks.append({"name": name, "url": url, "text": "", "status": "empty", "size": 0})
            continue

        text = ""
        if target.suffix.lower() in (".pdf", ".docx", ".doc"):
            text = extract_text_from_file(target)

        blocks.append(
            {
                "name": name,
                "path": str(target),
                "url": url,
                "text": text,
                "status": status,
                "size": target.stat().st_size,
            }
        )

    return blocks


def apply_attachment_products(
    record: dict,
    keyword: str,
    blocks: List[Dict[str, Any]],
) -> None:
    """Re-run product enrichment with attachment text merged."""
    from .product_matcher import enrich_project_products

    record["附件解析文本"] = [
        {"name": b.get("name", ""), "text": b.get("text", ""), "status": b.get("status", "")}
        for b in blocks
    ]
    parsed_ok = sum(1 for b in blocks if b.get("text"))
    record["附件解析数"] = parsed_ok
    body = record.get("详情正文") or ""
    enrich_project_products(record, keyword, body_text=body)
