#!/usr/bin/env python3
"""探测剑鱼标讯页面结构 - 生成截图和选择器建议"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("tender_raw_data")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(
        channel="chrome",
        headless=False,
        args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
    )
    
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    
    # 1. 探测首页/登录页
    print("[探测] 访问剑鱼标讯首页...")
    page.goto("https://www.jianyu360.com", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(3000)
    page.screenshot(path=str(OUTPUT_DIR / "probe_homepage.png"), full_page=False)
    print(f"[探测] 首页截图: {OUTPUT_DIR}/probe_homepage.png")
    
    # 打印页面标题和主要元素
    title = page.title()
    print(f"[探测] 页面标题: {title}")
    
    # 查找所有可能的登录入口
    login_btns = page.locator('a:has-text("登录"), button:has-text("登录"), span:has-text("登录"), div:has-text("登录")').all()
    print(f"[探测] 找到 {len(login_btns)} 个登录相关元素")
    for i, btn in enumerate(login_btns):
        try:
            text = btn.inner_text().strip()
            visible = btn.is_visible()
            tag = btn.evaluate("el => el.tagName")
            cls = btn.get_attribute("class") or ""
            print(f"  [{i}] {tag}.{cls[:50]} \"{text}\" visible={visible}")
        except Exception:
            pass
    
    # 2. 尝试点击登录链接
    try:
        login_link = page.locator('a:has-text("登录"), .login-btn, .login-link, [class*="login"]').first
        if login_link.is_visible(timeout=2000):
            login_link.click()
            print("[探测] 已点击登录入口")
            page.wait_for_timeout(3000)
            page.screenshot(path=str(OUTPUT_DIR / "probe_login_page.png"), full_page=False)
            print(f"[探测] 登录页截图: {OUTPUT_DIR}/probe_login_page.png")
    except Exception as e:
        print(f"[探测] 未找到登录入口: {e}")
    
    # 3. 查找所有输入框
    inputs = page.locator('input').all()
    print(f"\n[探测] 找到 {len(inputs)} 个输入框:")
    for i, inp in enumerate(inputs):
        try:
            name = inp.get_attribute("name") or ""
            placeholder = inp.get_attribute("placeholder") or ""
            type_ = inp.get_attribute("type") or "text"
            visible = inp.is_visible()
            cls = inp.get_attribute("class") or ""
            print(f"  [{i}] name=\"{name}\" type=\"{type_}\" placeholder=\"{placeholder}\" visible={visible} class=\"{cls[:60]}\"")
        except Exception:
            pass
    
    # 4. 查找所有按钮
    buttons = page.locator('button, a[class*="btn"], [type="submit"]').all()
    print(f"\n[探测] 找到 {len(buttons)} 个按钮:")
    for i, btn in enumerate(buttons):
        try:
            text = btn.inner_text().strip()
            visible = btn.is_visible()
            cls = btn.get_attribute("class") or ""
            if text:
                print(f"  [{i}] \"{text}\" visible={visible} class=\"{cls[:60]}\"")
        except Exception:
            pass
    
    # 5. 打印页面 HTML 关键部分
    print("\n[探测] 页面 body 前 2000 字符:")
    body_html = page.evaluate("() => document.body ? document.body.innerHTML.substring(0, 2000) : 'no body'")
    print(body_html)
    
    browser.close()
    print("\n[探测] 完成！")
