"""Fetch Jianyu detail pages — keyword match + optional attachment download."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Callable, List, Optional

PORTAL_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PORTAL_ROOT / "skills" / "tender-analysis" / "scripts"
AUTH_GLOBAL = PORTAL_ROOT / "tender_raw_data" / "auth_state.json"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from jianyu_crawler import USER_AGENT, try_login  # noqa: E402
from playwright.sync_api import sync_playwright

from .attachment_fetcher import apply_attachment_products, download_attachments_on_page
from .product_matcher import enrich_project_products, extract_params_from_context

LOGIN_WALL_MARKERS = (
    "微信扫码登录",
    "验证码登录 密码登录",
    "欢迎来到剑鱼标讯",
    "免费查询招标采购信息",
    "未注册用户登录后将自动创建账号",
)


def _body_looks_like_login_wall(text: str) -> bool:
    if not text or len(text) < 80:
        return False
    hits = sum(1 for m in LOGIN_WALL_MARKERS if m in text)
    if hits >= 2:
        return True
    return "获取验证码" in text and "密码登录" in text and len(text) < 3500


def _page_body_text(page, limit: int = 4000) -> str:
    try:
        return (page.locator("body").inner_text(timeout=5000) or "")[:limit]
    except Exception:
        return ""


def _ensure_jianyu_login(page, username: str, password: str, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    if not try_login(page, username, password, out_dir):
        raise RuntimeError("剑鱼标讯登录失败，请先在标书信息获取完成登录，或检查 .env 的 JIANYU_PHONE/JIANYU_PASSWORD")
    try:
        auth_path = out_dir / "auth_state.json"
        page.context.storage_state(path=str(auth_path))
    except Exception:
        pass


def _project_attach_dir(root: Optional[Path], rec: dict, idx: int) -> Optional[Path]:
    if root is None:
        return None
    pid = str(rec.get("id") or rec.get("project_id") or f"p{idx + 1}")
    d = root / pid / "attachments"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _extract_detail_fields(
    page,
    item: dict,
    keyword: str = "",
    *,
    parse_attachments: bool = False,
    attach_dir: Optional[Path] = None,
) -> dict:
    full_text = ""
    for sel in (
        ".article-content",
        ".detail-content",
        ".content-body",
        ".article-body",
        "article",
        "body",
    ):
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=2000):
                full_text = el.inner_text(timeout=5000)
                if len(full_text) > 100:
                    break
        except Exception:
            continue

    item["详情正文"] = full_text[:120000] if full_text else ""

    for pat in (
        r"(?:预算金额|中标金额|成交金额|项目金额)[：:]\s*([\d,.]+)\s*(?:万?元?|万元)",
        r"总?金额[：:]\s*([\d,.]+)\s*(?:万?元?|万元)",
    ):
        m = re.search(pat, full_text)
        if m and not item.get("预算金额"):
            item["预算金额"] = m.group(1) + "万元"

    attachments = []
    try:
        links = page.locator(
            'a[href*="download"], a[href$=".pdf"], a[href$=".doc"], '
            'a[href$=".docx"], a[href*="attachment"], a[href*="file"]'
        ).all()
        for a in links[:12]:
            try:
                href = a.get_attribute("href", timeout=2000)
                text = a.inner_text(timeout=2000).strip()
                if href and not href.startswith("javascript"):
                    attachments.append({"name": text[:80] or "附件", "url": href})
            except Exception:
                continue
    except Exception:
        pass
    if attachments:
        item["附件列表"] = attachments

    if parse_attachments and attachments and attach_dir is not None:
        blocks = download_attachments_on_page(
            page,
            page.context,
            attachments,
            attach_dir,
            page_url=page.url,
        )
        item["附件下载"] = blocks
        if keyword:
            apply_attachment_products(item, keyword, blocks)
    if keyword and full_text and not item.get("产品明细"):
        enrich_project_products(item, keyword, body_text=full_text)
        if item.get("产品明细"):
            params = extract_params_from_context(full_text)
            if params:
                item["项目级参数"] = params
    else:
        item["匹配策略"] = "no_keyword" if not keyword else item.get("匹配策略", "")

    item["详情正文长度"] = len(full_text)
    return item


def fetch_details(
    records: List[dict],
    *,
    username: str,
    password: str,
    keyword: str = "",
    auth_dir: Optional[Path] = None,
    attach_root: Optional[Path] = None,
    parse_attachments: bool = False,
    headless: bool = False,
    on_progress: Optional[Callable[[int, int, str], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> List[dict]:
    """Visit 详情链接; extract products; optionally download/parse attachments."""
    todo = []
    for i, rec in enumerate(records):
        url = str(rec.get("详情链接") or rec.get("source_url") or "").strip()
        if url:
            todo.append((i, url))

    if not todo:
        return records

    out_dir = auth_dir or PORTAL_ROOT / "tender_raw_data"
    auth_path = (out_dir / "auth_state.json") if out_dir else AUTH_GLOBAL
    storage_state = auth_path if auth_path.is_file() else None

    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome",
            headless=headless,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        context_opts = {
            "user_agent": USER_AGENT,
            "viewport": {"width": 1920, "height": 1080},
            "locale": "zh-CN",
        }
        if storage_state:
            context_opts["storage_state"] = str(storage_state)
        context = browser.new_context(**context_opts)
        page = context.new_page()

        _ensure_jianyu_login(page, username, password, out_dir)

        total = len(todo)
        for n, (idx, url) in enumerate(todo, 1):
            if cancel_check and cancel_check():
                break
            if on_progress:
                on_progress(n, total, records[idx].get("项目名称", "")[:40])

            rec = records[idx]
            rec["详情抓取"] = "pending"
            att_dir = _project_attach_dir(attach_root, rec, idx) if parse_attachments else None
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(2500)
                body_preview = _page_body_text(page)
                if _body_looks_like_login_wall(body_preview):
                    _ensure_jianyu_login(page, username, password, out_dir)
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_timeout(2500)
                    body_preview = _page_body_text(page)
                    if _body_looks_like_login_wall(body_preview):
                        rec["详情抓取"] = "login_required"
                        rec["详情正文"] = ""
                        rec["匹配策略"] = "login_wall"
                        continue
                _extract_detail_fields(
                    page,
                    rec,
                    keyword=keyword,
                    parse_attachments=parse_attachments and bool(rec.get("有附件") or rec.get("附件列表")),
                    attach_dir=att_dir,
                )
                if _body_looks_like_login_wall(rec.get("详情正文") or ""):
                    rec["详情抓取"] = "login_required"
                    rec["详情正文"] = ""
                    rec["匹配策略"] = "login_wall"
                else:
                    rec["详情抓取"] = "ok"
            except Exception as e:
                rec["详情抓取"] = f"failed: {e}"

        browser.close()

    return records
