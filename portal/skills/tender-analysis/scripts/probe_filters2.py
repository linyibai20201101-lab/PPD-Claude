#!/usr/bin/env python3
"""探测剑鱼筛选区完整 DOM"""
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(Path(__file__).parent))
from jianyu_crawler import try_login, do_search, _close_popups  # noqa: E402

OUT = ROOT / "tender_raw_data" / "probe_filters"
OUT.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True)
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    try_login(page, os.getenv("JIANYU_PHONE", ""), os.getenv("JIANYU_PASSWORD", ""), OUT)
    do_search(page, "工业相机", OUT, filters={})
    page.wait_for_timeout(2000)

    info = page.evaluate(
        """() => {
        const scopes = [...document.querySelectorAll('.checkbox-item')].map(el => ({
          text: el.innerText.trim(),
          cls: el.className,
          checked: el.classList.contains('active') || el.classList.contains('checked') || el.querySelector('input')?.checked
        }));
        const times = [...document.querySelectorAll('.j-button-item')].map(el => ({
          text: el.innerText.trim(),
          cls: el.className,
          tag: el.tagName
        })).filter(x => x.text.includes('最近') || x.text.includes('近'));
        const panel = document.querySelector('.search-schema-filter, .search-filter-schema, [class*="search-schema"]');
        return {
          panelClass: panel?.className || null,
          panelHtml: panel?.outerHTML?.slice(0, 500) || null,
          scopes,
          times: times.slice(0, 10),
          parentOfTime: document.querySelector('.search-schema-filter-label')?.parentElement?.className || null
        };
    }"""
    )
    (OUT / "filter_dom.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    browser.close()

print("written filter_dom.json")
