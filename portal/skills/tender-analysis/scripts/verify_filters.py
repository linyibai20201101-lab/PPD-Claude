#!/usr/bin/env python3
"""验证筛选是否在剑鱼页面生效"""
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(Path(__file__).parent))
from jianyu_crawler import try_login, do_search, _wait_for_filter_panel, _get_filter_panel, _scope_item_checked  # noqa: E402

OUT = ROOT / "tender_raw_data" / "probe_filters"
OUT.mkdir(parents=True, exist_ok=True)

filters = {
    "publish_time_preset": "30d",
    "search_scopes": ["title"],  # 仅标题，取消正文
    "info_types": [],
    "region": "全国",
}

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True)
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    try_login(page, os.getenv("JIANYU_PHONE", ""), os.getenv("JIANYU_PASSWORD", ""), OUT)
    ok = do_search(page, "工业相机", OUT, filters=filters)
    page.wait_for_timeout(2000)
    page.screenshot(path=str(OUT / "after_filter_fix.png"))

    state = page.evaluate(
        """() => {
        const time = document.querySelector('.search-time-scope-selector .j-button-item.active');
        const scopes = [...document.querySelectorAll('.checkbox-item')].map(el => ({
          label: el.querySelector('.checkbox-item-label')?.innerText?.trim(),
          checked: el.querySelector('.j-checkbox')?.classList.contains('checked')
        }));
        const count = document.body.innerText.match(/搜索到\\s*(\\d+)\\s*条/);
        return {
          activeTime: time?.innerText?.trim(),
          scopes,
          resultCount: count ? count[1] : null
        };
    }"""
    )
    (OUT / "filter_verify.json").write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    browser.close()
    print("search_ok", ok)
    print(json.dumps(state, ensure_ascii=False))
