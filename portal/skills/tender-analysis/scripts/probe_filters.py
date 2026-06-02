#!/usr/bin/env python3
"""探测剑鱼筛选区 DOM 结构（登录后）"""
import json
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).parent))
from jianyu_crawler import BASE_URL, try_login, _close_popups, do_search  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "tender_raw_data" / "probe_filters"
OUT.mkdir(parents=True, exist_ok=True)

phone = os.getenv("JIANYU_PHONE", "")
password = os.getenv("JIANYU_PASSWORD", "")

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True)
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    try_login(page, phone, password, OUT)
    do_search(page, "工业相机", OUT, filters={})
    page.wait_for_timeout(2000)
    page.screenshot(path=str(OUT / "after_search.png"), full_page=False)

    info = page.evaluate(
        """() => {
        const texts = [];
        document.querySelectorAll('span, label, a, button, div').forEach(el => {
          const t = (el.innerText || '').trim();
          if (/近|最近|发布时间|搜索范围|标题|正文|全部/.test(t) && t.length < 20) {
            const r = el.getBoundingClientRect();
            if (r.width > 0 && r.height > 0 && r.top < 600) {
              texts.push({ tag: el.tagName, cls: (el.className||'').slice(0,80), text: t, top: Math.round(r.top) });
            }
          }
        });
        const uniq = [];
        const seen = new Set();
        texts.sort((a,b) => a.top - b.top);
        for (const x of texts) {
          const k = x.text + x.top;
          if (!seen.has(k)) { seen.add(k); uniq.push(x); }
        }
        return uniq.slice(0, 60);
    }"""
    )
    (OUT / "filter_texts.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(info[:30], ensure_ascii=False, indent=2))
    browser.close()
