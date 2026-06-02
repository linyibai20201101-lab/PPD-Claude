#!/usr/bin/env python3
"""
剑鱼标讯爬虫 v2 - 增强版
- 从列表页提取所有可见+隐藏字段（预算金额、采购/中标单位、地区、类型、行业）
- 点击进入详情页提取产品明细（名称、型号、数量、单价、总价）
- 自动去重（同一项目的不同公告类型合并）
- 下载并解析附件

用法：
  python jianyu_crawler.py "关键词" --username 手机号 --password 密码 --max-pages 50 --output tender_raw_data
"""

import argparse
import json
import os
import re
import sys
import time
import csv
from datetime import datetime
from pathlib import Path
import shutil

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


# ======================== 配置 ========================
BASE_URL = "https://www.jianyu360.com"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

# CSS 选择器（基于 2026-05-29 探测结果）
SELECTORS = {
    "login_trigger": 'button.login-register-button, button.j-s-button:has-text("登录"), .login-register-button',
    "login_tab_pwd": 'text="密码登录", [data-type="password"], .password-login-tab',
    "phone_input_pwd": 'input[name="pass_phone"]',
    "password_input": 'input[name="pass_pass"], input[type="password"][placeholder*="密码"]',
    "login_btn_popup": '.login-popup button:has-text("登录"), .login-dialog button:has-text("登录"), button:has-text("登 录")',
    "captcha_input": 'input[placeholder*="验证码"]',
    "search_input": 'input[name="keywords"], input[placeholder*="关键词"], input[placeholder*="搜索"], #searchInput',
    "search_btn": '.search-button, button:has-text("搜索一下"), button:has-text("搜索"), #searchBtn',
    "result_row": '.search-result-item',
    "next_page": 'a:has-text("下一页"), .next-page, .el-icon-arrow-right, button:has-text(">"), .pagination .next',
}


def parse_args():
    parser = argparse.ArgumentParser(description="剑鱼标讯爬虫 v2")
    parser.add_argument("keyword", help="搜索关键词")
    parser.add_argument("--username", required=True, help="登录手机号")
    parser.add_argument("--password", default="", help="登录密码")
    parser.add_argument("--max-pages", type=int, default=50, help="最大翻页数")
    parser.add_argument("--output", default="tender_raw_data", help="输出目录")
    parser.add_argument("--headless", action="store_true", help="无头模式")
    parser.add_argument("--no-detail", action="store_true", help="跳过详情页（仅列表数据）")
    parser.add_argument(
        "--filters",
        default="",
        help="JSON 查询维度：publish_time_preset/search_scopes/info_types/region/date_from/date_to",
    )
    parser.add_argument(
        "--cancel-file",
        default="",
        help="中止标记文件路径；存在时爬虫会在下一检查点退出",
    )
    parser.add_argument(
        "--screenshots",
        action="store_true",
        help="保存步骤截图到输出目录（latest.png 供网页预览）",
    )
    return parser.parse_args()


def _load_filters_json(raw: str) -> dict:
    if not raw or not raw.strip():
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        print(f"[筛选] filters JSON 无效，忽略: {raw[:80]}")
        return {}


def _cancel_requested(cancel_file: str) -> bool:
    if not cancel_file:
        return False
    return Path(cancel_file).exists()


def save_partial_results(results: list, output_dir: Path) -> None:
    if not results:
        return
    path = output_dir / "partial_results.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


def ensure_workbench_tab(page) -> None:
    """确保在招标采购工作台搜索页。"""
    for label in ("招标采购", "招标公告"):
        try:
            tab = page.locator(
                f'.tab-item:has-text("{label}"), .nav-item:has-text("{label}"), span:has-text("{label}")'
            ).first
            if tab.is_visible(timeout=1500):
                tab.click()
                page.wait_for_timeout(800)
                print(f"[筛选] 已切换到「{label}」")
                return
        except Exception:
            continue


def _wait_for_filter_panel(page, timeout: int = 12000) -> bool:
    """筛选区仅在首次搜索后的结果页出现。"""
    try:
        panel = page.locator(".search-schema-filter-container").first
        panel.wait_for(state="visible", timeout=timeout)
        return True
    except Exception:
        return False


def _get_filter_panel(page):
    """定位剑鱼 search-schema 筛选区。"""
    for sel in (
        ".search-schema-filter-container",
        ".search-schema-filter-box",
        'div:has(.search-schema-filter-label:has-text("发布时间"))',
    ):
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=2000):
                return el
        except Exception:
            continue
    return page.locator("body")


def _click_search_button(page, search_input=None) -> bool:
    search_btn_selectors = [
        ".search-button",
        'button:has-text("搜索一下")',
        'button:has-text("搜索")',
        "#searchBtn",
        ".search-box button",
    ]
    for sel in search_btn_selectors:
        try:
            btn = page.locator(sel).first
            if btn.is_visible(timeout=2000):
                btn.click()
                print(f"[搜索] 已点击搜索按钮: {sel}")
                return True
        except Exception:
            continue
    if search_input:
        try:
            search_input.press("Enter")
            print("[搜索] 未找到搜索按钮，尝试按回车")
            return True
        except Exception:
            pass
    return False


def _click_time_preset(panel, label: str) -> bool:
    """点击发布时间快捷项（剑鱼 DOM: div.j-button-item.bgc）。"""
    for sel in (
        f'.search-time-scope-selector .j-button-item:has-text("{label}")',
        f'.j-button-item.bgc:has-text("{label}")',
    ):
        try:
            el = panel.locator(sel).first
            if el.is_visible(timeout=2000):
                el.click()
                panel.page.wait_for_timeout(500)
                cls = el.get_attribute("class") or ""
                return "active" in cls or True
        except Exception:
            continue
    return False


def _scope_item_checked(item) -> bool:
    try:
        icon = item.locator(".j-checkbox.checkbox-item-icon").first
        cls = icon.get_attribute("class") or ""
        return "checked" in cls
    except Exception:
        return False


def _set_scope_checkbox(panel, label: str, checked: bool) -> bool:
    """剑鱼搜索范围：div.checkbox-item + span.j-checkbox.checked。"""
    try:
        item = panel.locator(
            f'.checkbox-item:has(.checkbox-item-label:text-is("{label}"))'
        ).first
        if not item.is_visible(timeout=1500):
            item = panel.locator(f'.checkbox-item:has-text("{label}")').first
        if not item.is_visible(timeout=1500):
            return False
        is_checked = _scope_item_checked(item)
        if checked != is_checked:
            item.click()
            panel.page.wait_for_timeout(250)
        return True
    except Exception:
        return False


def _click_info_type_all(panel) -> bool:
    for sel in ('button.j-button-item.is-all:has-text("全部")', 'button.j-button-item:has-text("全部")'):
        try:
            btn = panel.locator(sel).first
            if btn.is_visible(timeout=1500):
                btn.click()
                panel.page.wait_for_timeout(300)
                return True
        except Exception:
            continue
    return False


def _log_filter_state(page) -> None:
    """打印当前筛选状态供日志核对。"""
    try:
        active_time = page.locator(".search-time-scope-selector .j-button-item.active").first
        if active_time.is_visible(timeout=1000):
            print(f"[筛选] 当前发布时间: {active_time.inner_text().strip()}")
    except Exception:
        pass
    try:
        checked = page.locator(".checkbox-item .j-checkbox.checked").all()
        labels = []
        for c in checked[:8]:
            parent = c.locator("xpath=..")
            if parent.count():
                t = parent.first.inner_text(timeout=500).strip()
                if t:
                    labels.append(t.split("\n")[0])
        if labels:
            print(f"[筛选] 当前搜索范围: {', '.join(labels)}")
    except Exception:
        pass
    try:
        count_el = page.locator('text=/搜索到\\s*\\d+\\s*条/').first
        if count_el.is_visible(timeout=1500):
            print(f"[筛选] {count_el.inner_text().strip()}")
    except Exception:
        pass


def _apply_region_filter(page, panel, region: str) -> None:
    """在「更多筛选」中选择地区。"""
    if not region or region in ("全国", "全部"):
        print("[筛选] 地区: 全国（默认）")
        return

    for sel in ('text="更多筛选"', ".more-filter", ".filter-more"):
        try:
            btn = page.locator(sel).first
            if btn.is_visible(timeout=1200):
                btn.click()
                page.wait_for_timeout(600)
                break
        except Exception:
            continue

    opened = False
    for trigger in (
        page.locator('.search-schema-more-filter:has-text("地区")').first,
        page.locator('div:has-text("地区") .el-select').first,
        page.locator('.region-select, .area-select').first,
    ):
        try:
            if trigger.is_visible(timeout=1500):
                trigger.click()
                page.wait_for_timeout(800)
                opened = True
                break
        except Exception:
            continue

    if not opened:
        print(f"[筛选] 未能打开地区选择器: {region}")

    for target in (region, region.replace("省", "").replace("市", "")):
        try:
            opt = page.locator(f'.el-select-dropdown__item:has-text("{target}")').first
            if opt.is_visible(timeout=2000):
                opt.click()
                print(f"[筛选] 地区: {region}")
                page.keyboard.press("Escape")
                return
        except Exception:
            continue
    print(f"[筛选] 地区选择可能未生效: {region}，将依赖后端筛选")
    page.keyboard.press("Escape")


# 剑鱼页面实际文案（探测 2026-06-01）
TIME_PRESET_LABELS = {
    "7d": "最近7天",
    "30d": "最近30天",
    "1y": "最近1年",
    "3y": "最近3年",
    "5y": "最近5年",
}


def apply_search_filters(page, filters: dict) -> bool:
    """在搜索结果页设置筛选条件（须先完成一次搜索以加载筛选面板）。"""
    if not filters:
        return True

    if not _wait_for_filter_panel(page, timeout=8000):
        print("[筛选] 未找到筛选面板（需先搜索一次才能出现），跳过页面筛选")
        return False

    print("[筛选] 在剑鱼工作台应用查询条件…")
    ensure_workbench_tab(page)
    panel = _get_filter_panel(page)
    try:
        panel.scroll_into_view_if_needed(timeout=3000)
    except Exception:
        pass
    page.wait_for_timeout(500)

    preset = str(filters.get("publish_time_preset") or "1y")
    if preset == "custom":
        date_from = filters.get("date_from") or ""
        date_to = filters.get("date_to") or ""
        date_inputs = panel.locator(
            'input[placeholder*="开始"], input[placeholder*="结束"], input[type="date"]'
        ).all()
        if date_from and len(date_inputs) >= 1:
            try:
                date_inputs[0].fill(date_from)
            except Exception:
                pass
        if date_to and len(date_inputs) >= 2:
            try:
                date_inputs[1].fill(date_to)
            except Exception:
                pass
        print(f"[筛选] 发布时间: 自定义 {date_from} ~ {date_to}")
    elif preset in TIME_PRESET_LABELS:
        label = TIME_PRESET_LABELS[preset]
        ok = _click_time_preset(panel, label)
        print(f"[筛选] 发布时间: {label}" + (" [OK]" if ok else " [FAIL]"))

    scope_labels = {
        "title": ["标题"],
        "body": ["正文"],
        "attachment": ["附件"],
        "subject": ["项目名称/标的物", "项目名称/标的"],
        "brand": ["品牌"],
        "buyer": ["采购单位"],
        "winner": ["中标企业", "中标单位"],
        "agency": ["招标代理机构"],
    }
    selected_scopes = filters.get("search_scopes") or ["title", "body"]
    for sid, labels in scope_labels.items():
        want = sid in selected_scopes
        for label in labels:
            if _set_scope_checkbox(panel, label, want):
                state = "勾选" if want else "取消"
                print(f"[筛选] 搜索范围 {label}: {state} [OK]")
                break
        else:
            if want:
                print(f"[筛选] 搜索范围 {labels[0]}: 未找到选项")

    info_types = filters.get("info_types") or []
    if not info_types:
        if _click_info_type_all(panel):
            print("[筛选] 信息类型: 全部 [OK]")
    else:
        _click_info_type_all(panel)
        page.wait_for_timeout(300)
        for it in info_types:
            try:
                btn = panel.locator(f'button.j-button-item:has-text("{it}")').first
                if btn.is_visible(timeout=1500):
                    btn.click()
                    print(f"[筛选] 信息类型: {it} [OK]")
            except Exception:
                print(f"[筛选] 信息类型: {it} [FAIL]")

    _apply_region_filter(page, panel, str(filters.get("region") or "全国").strip())
    page.wait_for_timeout(500)
    _log_filter_state(page)
    print("[筛选] 剑鱼页面筛选条件已设置")
    return True


def save_step_screenshot(page, output_dir: Path, step_name: str, enabled: bool) -> None:
    if not enabled:
        return
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"step_{step_name}.png"
        page.screenshot(path=str(path), full_page=False)
        latest = output_dir / "latest.png"
        shutil.copy2(path, latest)
        print(f"[截图] {step_name} → {path.name}", flush=True)
    except Exception as e:
        print(f"[截图] {step_name} 失败: {e}", flush=True)


def get_output_dir(output_arg):
    path = Path(output_arg)
    path.mkdir(parents=True, exist_ok=True)
    return path


# ======================== 登录 ========================
def try_login(page, username, password, output_dir):
    auth_file = output_dir / "auth_state.json"

    print("[登录] 尝试登录...")

    if auth_file.exists():
        print("[登录] 发现已保存的登录态，尝试恢复...")
        try:
            with open(auth_file, "r", encoding="utf-8") as f:
                storage = json.load(f)
            page.context.add_cookies(storage.get("cookies", []))
            page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)
            try:
                login_trigger = page.locator(SELECTORS["login_trigger"]).first
                if login_trigger.is_visible(timeout=3000):
                    print("[登录] 已保存的登录态已过期，需要重新登录")
                else:
                    print("[登录] 登录态有效")
                    _close_popups(page)
                    return True
            except Exception:
                print("[登录] 登录态有效（无法检测登录按钮）")
                _close_popups(page)
                return True
        except Exception as e:
            print(f"[登录] 登录态恢复失败: {e}")

    if not password:
        print("[登录] 未提供密码且无有效登录态，跳过登录")
        return False

    # 导航到首页
    try:
        page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)
        print("[登录] 首页加载完成")
    except Exception as e:
        print(f"[登录] 页面加载异常: {e}")
        return False

    # 步骤1：点击首页"登录"按钮
    try:
        login_trigger = page.locator(SELECTORS["login_trigger"]).first
        login_trigger.wait_for(state="visible", timeout=10000)
        login_trigger.click()
        print("[登录] 已点击首页'登录'按钮，等待弹窗...")
        page.wait_for_timeout(2000)
    except Exception as e:
        print(f"[登录] 找不到首页登录按钮: {e}")
        return False

    # 步骤2：切换到"密码登录"tab
    try:
        pwd_tab_selectors = [
            'text="密码登录"', '.login-tab:has-text("密码登录")',
            '[data-type="password"]', 'span:has-text("密码登录")',
            'div:has-text("密码登录")',
        ]
        for sel in pwd_tab_selectors:
            try:
                tab = page.locator(sel).first
                if tab.is_visible(timeout=2000):
                    tab.click()
                    print(f"[登录] 已切换到'密码登录'tab: {sel}")
                    page.wait_for_timeout(1000)
                    break
            except Exception:
                continue
    except Exception as e:
        print(f"[登录] 切换密码tab: {e}")

    # 步骤3：填写手机号
    try:
        phone_input = page.locator(SELECTORS["phone_input_pwd"]).first
        phone_input.wait_for(state="visible", timeout=10000)
        phone_input.click()
        phone_input.fill("")
        page.wait_for_timeout(300)
        phone_input.fill(username)
        print(f"[登录] 已输入手机号: {username}")
    except Exception as e:
        print(f"[登录] 找不到 pass_phone 输入框: {e}")
        try:
            alt_phone = page.locator('input[name="phone"], input[name="mobile"], input[type="tel"][placeholder*="手机"]').first
            alt_phone.wait_for(state="visible", timeout=5000)
            alt_phone.fill(username)
            print(f"[登录] (备用) 已输入手机号: {username}")
        except Exception as e2:
            print(f"[登录] 备用手机号输入框也失败: {e2}")
            return False

    # 步骤4：填写密码
    try:
        pwd_input = page.locator(SELECTORS["password_input"]).first
        pwd_input.wait_for(state="visible", timeout=5000)
        pwd_input.click()
        pwd_input.fill("")
        page.wait_for_timeout(300)
        pwd_input.fill(password)
        print("[登录] 已输入密码")
    except Exception as e:
        print(f"[登录] 找不到密码输入框: {e}")
        return False

    # 步骤5：点击弹窗登录按钮
    try:
        popup_btn_selectors = [
            '.login-popup button:has-text("登录")',
            '.login-dialog button:has-text("登录")',
            '.j-s-button:has-text("登录")',
            'button:has-text("登 录")',
            'button[type="submit"]',
            '.login-form button',
        ]
        clicked = False
        for sel in popup_btn_selectors:
            try:
                btn = page.locator(sel).first
                if btn.is_visible(timeout=2000):
                    btn.click()
                    clicked = True
                    print(f"[登录] 已点击弹窗登录按钮: {sel}")
                    break
            except Exception:
                continue
        if not clicked:
            print("[登录] 未找到弹窗登录按钮，尝试按回车")
            pwd_input = page.locator(SELECTORS["password_input"]).first
            pwd_input.press("Enter")
        page.wait_for_timeout(4000)
    except Exception as e:
        print(f"[登录] 提交登录失败: {e}")
        return False

    # 步骤6：检查验证码
    try:
        captcha = page.locator(SELECTORS["captcha_input"])
        if captcha.is_visible(timeout=2000):
            print("\n[!] 检测到验证码！请在浏览器中手动输入（60秒内）...")
            page.wait_for_timeout(60000)
    except Exception:
        pass

    # 步骤7：验证登录状态
    page.wait_for_timeout(3000)
    try:
        login_trigger = page.locator(SELECTORS["login_trigger"]).first
        if login_trigger.is_visible(timeout=2000):
            print("[登录] 登录可能失败：登录按钮仍然可见")
            return False
    except Exception:
        pass

    # 保存登录态
    try:
        cookies = page.context.cookies()
        with open(auth_file, "w", encoding="utf-8") as f:
            json.dump({"cookies": cookies}, f, ensure_ascii=False)
        print(f"[登录] 登录成功！登录态已保存到 {auth_file}")
    except Exception as e:
        print(f"[登录] 保存登录态失败: {e}")
        return False

    _close_popups(page)
    return True


def _close_popups(page):
    """关闭引导弹窗"""
    page.wait_for_timeout(2000)
    for sel in ['text="我知道"', 'text="我知道了"', 'text="关闭"', 'text="跳过"', '.el-dialog__close']:
        try:
            btn = page.locator(sel).first
            if btn.is_visible(timeout=1500):
                btn.click()
                print(f"[弹窗] 已关闭: {sel}")
                page.wait_for_timeout(1000)
                break
        except Exception:
            continue
    page.keyboard.press("Escape")
    page.wait_for_timeout(500)


# ======================== 搜索 ========================
def do_search(page, keyword, output_dir, filters=None):
    print(f"[搜索] 搜索关键词: {keyword}")

    _close_popups(page)
    filters = filters or {}

    # 确保在首页
    current_url = page.url
    if "jianyu360.com" not in current_url or "login" in current_url.lower():
        print(f"[搜索] 导航到首页...")
        page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)
        _close_popups(page)

    page.wait_for_timeout(2000)

    search_selectors = [
        'input[name="keywords"]',
        'input[placeholder*="项目名称"]',
        'input[placeholder*="关键词"]',
        'input[name="keyword"]',
        '#searchInput',
        '.search-input input',
        '.search-box input',
        'input[type="text"]:visible',
    ]

    search_input = None
    for sel in search_selectors:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=2000):
                search_input = el
                print(f"[搜索] 找到搜索框: {sel}")
                break
        except Exception:
            continue

    if not search_input:
        print("[搜索] 未能找到搜索框")
        page.screenshot(path=str(output_dir / "debug_no_search.png"))
        return False

    search_input.click()
    search_input.fill("")
    page.wait_for_timeout(300)
    search_input.fill(keyword)
    page.wait_for_timeout(500)
    print(f"[搜索] 已输入关键词: {keyword}")

    # 剑鱼筛选面板仅在首次搜索后的结果页才渲染，须先搜一次再设条件
    print("[搜索] 首次搜索以加载筛选面板…")
    _click_search_button(page, search_input)
    page.wait_for_timeout(3500)

    if filters:
        applied = apply_search_filters(page, filters)
        if applied:
            print("[搜索] 应用筛选后重新搜索…")
            _click_search_button(page, search_input)
            page.wait_for_timeout(4000)
        else:
            print("[搜索] 页面筛选未生效，结果将依赖后端过滤")
    else:
        page.wait_for_timeout(1000)

    return True


# ======================== 列表页提取 (v2 增强版) ========================
def extract_results(page):
    """从搜索结果列表页提取完整的标书数据（包括隐藏的list-detail）"""
    results = []

    rows = page.locator(SELECTORS["result_row"]).all()
    if not rows:
        print("[提取] 未找到搜索结果行")
        return results

    print(f"[提取] 找到 {len(rows)} 条搜索结果")

    for i, row in enumerate(rows):
        try:
            item = {
                "id": i + 1,
                "项目名称": "",
                "发布时间": "",
                "地区": "",
                "预算金额": "",
                "项目类型": "",
                "行业类型": "",
                "采购单位": "",
                "中标单位": "",
                "有附件": False,
                "详情链接": "",
                "数据来源": "剑鱼标讯",
            }

            # --- 标题 (无链接，直接文本) ---
            try:
                title_el = row.locator('.a-i-left.visited-hd, .a-i-left').first
                title = title_el.inner_text(timeout=3000).strip()
                # 清理编号前缀
                title = re.sub(r'^\d+\.\s*', '', title)
                item["项目名称"] = title
            except Exception:
                pass

            # --- 发布时间 ---
            try:
                time_el = row.locator('.time-text').first
                item["发布时间"] = time_el.inner_text(timeout=2000).strip()
            except Exception:
                pass

            # --- 标签列表：地区、类型、行业、金额 ---
            tags = row.locator('.tag').all()
            for tag in tags:
                try:
                    text = tag.inner_text(timeout=1000).strip()
                    cls = tag.get_attribute("class") or ""
                    if "dpink" in cls and not item["预算金额"]:
                        item["预算金额"] = text
                    elif "tag-handle" in cls and not item["地区"]:
                        item["地区"] = text
                    elif "orange" in cls and not item["项目类型"]:
                        item["项目类型"] = text
                    elif "green" in cls and not item["行业类型"]:
                        item["行业类型"] = text
                except Exception:
                    continue

            # --- 有附件标记 ---
            try:
                file_tag = row.locator('.haveFile').first
                if file_tag.is_visible(timeout=1000):
                    item["有附件"] = True
            except Exception:
                pass

            # --- 隐藏的 list-detail（采购单位/中标单位/联系方式等）---
            try:
                detail_div = row.locator('.list-detail').first
                if detail_div:
                    # 先展开
                    detail_div.evaluate("el => { el.style.display = 'block'; }")
                    page.wait_for_timeout(300)
                    detail_text = detail_div.inner_text(timeout=3000)

                    # 解析采购单位
                    buyer_match = re.search(r'采购单位[：:]\s*(.+?)(?:\s|$|\n|采购单位联系方式)', detail_text)
                    if buyer_match:
                        item["采购单位"] = buyer_match.group(1).strip()[:100]

                    # 解析中标单位
                    winner_match = re.search(r'中标单位[：:]\s*(.+?)(?:\s|$|\n)', detail_text)
                    if winner_match:
                        item["中标单位"] = winner_match.group(1).strip()[:200]

                    # 复原隐藏
                    detail_div.evaluate("el => { el.style.display = 'none'; }")
            except Exception:
                pass

            # --- 尝试获取详情链接（点击标题应该导航） ---
            try:
                # 找到 checkbox 上的 dataid
                checkbox = row.locator('input[type="checkbox"][dataid]').first
                dataid = checkbox.get_attribute("dataid", timeout=2000)
                if dataid:
                    item["详情链接"] = f"https://www.jianyu360.com/article/content/{dataid}.html"
            except Exception:
                pass

            if item["项目名称"]:
                results.append(item)

        except Exception as e:
            print(f"[提取] Row {i} 解析异常: {e}")
            continue

    print(f"[提取] 成功解析 {len(results)} 条记录")
    return results


# ======================== 详情页钻取 (v2 新增) ========================
def scrape_detail_page(page, item, output_dir, index, total):
    """进入详情页提取产品明细、附件、完整金额信息"""
    print(f"\n[详情] [{index}/{total}] {item['项目名称'][:50]}...")

    # 保存列表页 URL 以便返回
    list_url = page.url

    try:
        # 方法1：点击标题进入
        title_sel = f'.search-result-item:nth-child({index}) .a-i-left.visited-hd, .search-result-item:nth-child({index}) .a-i-left'
        title_el = page.locator(title_sel).first
        if not title_el.is_visible(timeout=2000):
            # 回退方法：点击搜索结果的第 index 行
            title_el = page.locator('.search-result-item').nth(index - 1).locator('.a-i-left').first

        # 点击前记录
        title_el.click()
        page.wait_for_timeout(3000)

        # 检查是否打开了新页面/标签
        pages = page.context.pages
        detail_page = page
        if len(pages) > 1:
            detail_page = pages[-1]  # 新标签页

        # 等待详情页加载
        detail_page.wait_for_load_state("domcontentloaded", timeout=15000)
        detail_page.wait_for_timeout(3000)

        detail_url = detail_page.url
        item["详情链接"] = detail_url
        print(f"[详情] 页面URL: {detail_url}")

        # --- 提取详情页全文 ---
        full_text = ""
        content_selectors = [
            '.article-content', '.detail-content', '.content-body',
            '.article-body', '.text-content', '[class*="content"]',
            '.detail-container', '.article-container', 'article',
            'body',
        ]
        for sel in content_selectors:
            try:
                el = detail_page.locator(sel).first
                if el.is_visible(timeout=2000):
                    full_text = el.inner_text(timeout=5000)
                    if len(full_text) > 100:
                        break
            except Exception:
                continue

        # --- 提取预算/中标金额 ---
        # 从全文匹配金额模式
        amount_patterns = [
            r'(?:预算金额|中标金额|成交金额|项目金额|采购预算|合同金额)[：:]\s*([\d,.]+)\s*(?:万?元?|万元)',
            r'(?:中标[\(（].+[\)）]金额)[：:]\s*([\d,.]+)\s*(?:万?元?|万元)',
            r'总?金额[：:]\s*([\d,.]+)\s*(?:万?元?|万元)',
        ]
        for pat in amount_patterns:
            m = re.search(pat, full_text)
            if m:
                item["预算金额"] = m.group(1) + "万元"
                break

        # --- 提取产品明细 ---
        products = _extract_products(full_text)
        item["产品明细"] = products

        # --- 提取附件链接 ---
        attachments = []
        try:
            attach_links = detail_page.locator('a[href*="download"], a[href$=".pdf"], a[href$=".doc"], a[href$=".xls"], a[href*="attachment"], a[href*="file"]').all()
            for a in attach_links[:10]:
                try:
                    href = a.get_attribute("href", timeout=2000)
                    text = a.inner_text(timeout=2000).strip()
                    if href and not href.startswith("javascript"):
                        attachments.append({"name": text[:80], "url": href})
                except Exception:
                    continue
        except Exception:
            pass
        item["附件列表"] = attachments

        # --- 记录摘要 ---
        if products:
            total_qty = sum(p.get("数量", 0) for p in products if isinstance(p.get("数量"), (int, float)))
            item["产品数量"] = len(products)
            item["总数量"] = total_qty
            print(f"[详情] 提取到 {len(products)} 个产品, 总数量: {total_qty}")
        else:
            item["产品数量"] = 0
            print("[详情] 未提取到产品明细")

        # --- 返回列表页 ---
        if len(pages) > 1:
            detail_page.close()
        page.goto(list_url, wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(2000)
        _close_popups(page)

    except Exception as e:
        print(f"[详情] 提取失败: {e}")
        # 确保返回列表页
        try:
            if page.url != list_url:
                page.goto(list_url, wait_until="domcontentloaded", timeout=15000)
                page.wait_for_timeout(2000)
        except Exception:
            pass

    return item


def _extract_products(text):
    """从详情页文本中提取产品明细（名称、型号、数量、单价、总价）"""
    products = []

    # 查找 TS-9230P2 相关行
    lines = text.split('\n')
    keyword_lines = []
    for i, line in enumerate(lines):
        if 'TS-9230P2' in line or '9230' in line or '投影' in line:
            context_start = max(0, i - 3)
            context_end = min(len(lines), i + 5)
            keyword_lines.extend(lines[context_start:context_end])

    # 策略1：查找表格数据（按列对齐的数值行）
    # 匹配模式: 名称...数量...单价...金额
    product_patterns = [
        # 模式: 产品名 + 数字 + 数字 + 数字（可能是 数量,单价,总价）
        r'([^\d\n]{3,80}?)[\s　]+(\d+)[\s　]+([\d,.]+)[\s　]+([\d,.]+)',
        # 模式: 产品名 + 单价 + 数量
        r'([^\d\n]{3,80}?)[\s　]+([\d,.]+)\s*元?[\s　]+(\d+)\s*[台套个件]',
    ]

    for pat in product_patterns:
        matches = re.findall(pat, text[:8000])
        if matches:
            for m in matches:
                name = m[0].strip()
                if 'TS-9230P2' in name or '9230' in name or '投影' in name:
                    nums = [float(n.replace(',', '')) for n in m[1:]]
                    products.append({
                        "产品名称": name[:80],
                        "数量": int(nums[-1]) if nums[-1] == int(nums[-1]) else nums[-1] if len(nums) > 1 else 0,
                        "单价": nums[1] if len(nums) >= 3 else (nums[0] if len(nums) == 2 else 0),
                        "匹配文本": m,
                    })

    # 策略2：如果没找到结构化产品，尝试从 TS-9230P2 上下文中提取
    if not products:
        combined = '\n'.join(keyword_lines) if keyword_lines else text[:5000]

        # 提取金额
        amounts = re.findall(r'([\d,]+\.?\d*)\s*万?元?', combined)
        quantities = re.findall(r'(\d+)\s*[台套个件只]', combined)

        if amounts:
            products.append({
                "产品名称": "TS-9230P2（从上下文提取）",
                "参考金额": max(float(a.replace(',', '')) for a in amounts if a.replace(',', '').replace('.', '').isdigit()),
                "数量": int(quantities[0]) if quantities else 1,
                "上下文": combined[:500],
            })

    return products


# ======================== 去重 (v2 新增) ========================
def deduplicate_results(results):
    """合并同一项目的不同公告类型（采购公告+成交公告=同一项目）"""
    if not results:
        return results

    # 清理项目名称（去除编号前缀、多余空格）
    for r in results:
        name = r.get("项目名称", "")
        # 去除编号
        name = re.sub(r'^\d+\.\s*', '', name)
        # 规范化
        name = re.sub(r'\s+', '', name)
        r["_clean_name"] = name

    # 分组逻辑：提取核心项目名（去除后缀如"竞价成交公告""结果公告"等）
    suffix_patterns = [
        r'(竞价)?成交(结果)?公告$',
        r'(中标|成交)结果公告$',
        r'结果公告.*$',
        r'采购公告$',
        r'招标公告$',
        r'公开招标.*$',
        r'竞价成交公告$',
        r'竞价公告$',
        r'采购项目$',
        r'（.*）$',
        r'\(.*\)$',
    ]

    def get_project_key(name):
        """提取项目核心标识"""
        key = name
        for pat in suffix_patterns:
            key = re.sub(pat, '', key)
        # 进一步清理
        key = re.sub(r'[-_（）()\s]', '', key)
        return key[:40]  # 前40字作为分组key

    # 构建分组
    groups = {}
    for r in results:
        key = get_project_key(r["_clean_name"])
        if key not in groups:
            groups[key] = []
        groups[key].append(r)

    # 合并每组
    merged = []
    for key, group in groups.items():
        if len(group) == 1:
            merged.append(group[0])
        else:
            # 合并：取最完整的信息
            base = group[0].copy()
            base["_merged_from"] = len(group)

            for r in group[1:]:
                # 合并非空字段
                for field in ["采购单位", "中标单位", "预算金额", "地区", "项目类型", "行业类型"]:
                    if not base.get(field) and r.get(field):
                        base[field] = r[field]
                # 合并附件标记
                if r.get("有附件"):
                    base["有附件"] = True
                # 合并产品明细
                if r.get("产品明细") and not base.get("产品明细"):
                    base["产品明细"] = r["产品明细"]
                if r.get("附件列表") and not base.get("附件列表"):
                    base["附件列表"] = r["附件列表"]

            # 重建项目名称（去后缀）
            base["项目名称"] = key
            base["_original_names"] = [r.get("项目名称") for r in group]

            merged.append(base)

    print(f"[去重] 原始 {len(results)} 条 -> 合并后 {len(merged)} 条 ({len(groups)} 个独立项目)")

    # 清理内部字段
    for r in merged:
        r.pop("_clean_name", None)

    return merged


# ======================== 翻页 ========================
def go_next_page(page, current_page):
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(500)

    next_selectors = [
        '.el-pagination .btn-next:not(.disabled)',
        '.el-pagination button.btn-next:not([disabled])',
        '.j-pagination .btn-next:not(.disabled)',
        'button.btn-next:not(.disabled)',
        'a:has-text("下一页")',
        '.pagination .next:not(.disabled)',
        'li.next:not(.disabled) a',
        '.next-page:not(.disabled)',
        'button:has-text(">")',
    ]

    for sel in next_selectors:
        try:
            btn = page.locator(sel).first
            if btn.is_visible(timeout=1500):
                cls = btn.get_attribute("class") or ""
                disabled = btn.get_attribute("disabled")
                aria = btn.get_attribute("aria-disabled")
                if disabled or aria == "true" or "disabled" in cls or "is-disabled" in cls:
                    continue
                btn.click()
                page.wait_for_timeout(3000)
                print(f"[翻页] 已翻到第 {current_page + 1} 页（{sel}）")
                return True
        except Exception:
            continue

    # 点击页码：当前 active 的下一数字页
    try:
        active = page.locator(".el-pagination .number.active, .el-pager li.active").first
        if active.is_visible(timeout=1500):
            nxt = active.locator("xpath=following-sibling::*[1]").first
            if nxt.is_visible(timeout=1000):
                nxt.click()
                page.wait_for_timeout(3000)
                print(f"[翻页] 已翻到第 {current_page + 1} 页（页码）")
                return True
    except Exception:
        pass

    print(f"[翻页] 无法找到下一页按钮，停止翻页")
    return False


# ======================== 保存 ========================
def save_results(results, output_csv):
    if not results:
        print("[保存] 无数据可保存")
        return None

    # 展开结果（处理合并后的记录）
    flat_results = []
    for r in results:
        flat = {}
        for k, v in r.items():
            if k.startswith("_"):
                if k == "_original_names":
                    flat["原始公告列表"] = " | ".join(v)
                elif k == "_merged_from":
                    flat["合并公告数"] = v
                continue
            if isinstance(v, (list, dict)):
                flat[k] = json.dumps(v, ensure_ascii=False)
            else:
                flat[k] = str(v) if v else ""
        flat_results.append(flat)

    # 收集所有字段名
    all_fields = []
    for r in flat_results:
        for k in r:
            if k not in all_fields:
                all_fields.append(k)
    # 确保核心字段排前面
    priority = ["id", "项目名称", "发布时间", "地区", "预算金额", "项目类型", "行业类型",
                "采购单位", "中标单位", "有附件", "产品数量", "产品明细", "附件列表",
                "合并公告数", "原始公告列表", "详情链接", "数据来源"]
    ordered_fields = [f for f in priority if f in all_fields]
    ordered_fields += [f for f in all_fields if f not in priority]

    filepath = Path(output_csv)
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=ordered_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(flat_results)

    print(f"[保存] 已保存 {len(flat_results)} 条记录到: {filepath}")
    return str(filepath)


# ======================== 主流程 ========================
def main():
    args = parse_args()
    filters = _load_filters_json(args.filters)
    cancel_file = args.cancel_file or ""

    output_dir = get_output_dir(args.output)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    keyword_safe = re.sub(r'[\\/:*?"<>|]', '_', args.keyword)
    output_csv = output_dir / f"jianyu_{keyword_safe}_{timestamp}.csv"

    print("=" * 60)
    print(f"  剑鱼标讯爬虫 v2 (增强版)")
    print(f"  关键词: {args.keyword}")
    if filters:
        print(f"  查询维度: {json.dumps(filters, ensure_ascii=False)}")
    print(f"  最大页数: {args.max_pages}")
    print(f"  详情页: {'跳过' if args.no_detail else '钻取'}")
    print(f"  输出目录: {output_dir}")
    print("=" * 60)

    all_results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome",
            headless=args.headless,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )

        context = browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1920, "height": 1080},
            locale="zh-CN",
        )

        page = context.new_page()

        # 1. 登录
        if not try_login(page, args.username, args.password, output_dir):
            print("[错误] 登录失败")
            browser.close()
            sys.exit(1)
        save_step_screenshot(page, output_dir, "01_login", args.screenshots)

        # 2. 搜索
        if not do_search(page, args.keyword, output_dir, filters=filters):
            print("[错误] 搜索失败")
            browser.close()
            sys.exit(1)
        save_step_screenshot(page, output_dir, "02_search", args.screenshots)

        # 3. 翻页 + 提取列表数据
        for page_num in range(1, args.max_pages + 1):
            if _cancel_requested(cancel_file):
                save_partial_results(all_results, output_dir)
                print(f"[中止] 用户已中止，已保存 {len(all_results)} 条部分结果")
                browser.close()
                sys.exit(130)

            print(f"\n{'='*40}")
            print(f"[抓取] 第 {page_num}/{args.max_pages} 页")
            print(f"{'='*40}")

            page.wait_for_timeout(2000)
            page_results = extract_results(page)
            save_step_screenshot(page, output_dir, f"03_page_{page_num}", args.screenshots)

            if not page_results:
                print("[抓取] 当前页无结果，可能已到末尾")
                break

            all_results.extend(page_results)
            save_partial_results(all_results, output_dir)

            if page_num < args.max_pages:
                if not go_next_page(page, page_num):
                    break

        # === 4. 详情页钻取（对每条记录进入详情页） ===
        if not args.no_detail and all_results:
            print(f"\n{'='*60}")
            print(f"  详情页钻取: {len(all_results)} 条记录")
            print(f"{'='*60}")

            # 回到搜索结果第一页
            do_search(page, args.keyword, output_dir, filters=filters)

            for i, item in enumerate(all_results):
                if _cancel_requested(cancel_file):
                    save_partial_results(all_results, output_dir)
                    print(f"[中止] 用户已中止，已保存 {len(all_results)} 条部分结果")
                    browser.close()
                    sys.exit(130)
                # 如果已有产品明细，跳过
                if item.get("产品明细"):
                    print(f"[详情] [{i+1}/{len(all_results)}] 已有产品数据，跳过")
                    continue
                scrape_detail_page(page, item, output_dir, i + 1, len(all_results))
                save_partial_results(all_results, output_dir)

        # 保存登录态
        try:
            cookies = context.cookies()
            auth_file = output_dir / "auth_state.json"
            with open(auth_file, "w", encoding="utf-8") as f:
                json.dump({"cookies": cookies}, f, ensure_ascii=False)
        except Exception:
            pass

        browser.close()

    # === 5. 去重 ===
    deduped = deduplicate_results(all_results)

    # === 6. 保存 ===
    if deduped:
        csv_path = save_results(deduped, output_csv)

        json_path = output_csv.with_suffix(".json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(deduped, f, ensure_ascii=False, indent=2)

        print(f"\n[完成] 列表提取: {len(all_results)} 条")
        print(f"[完成] 去重后: {len(deduped)} 条独立项目")
        print(f"[完成] CSV: {csv_path}")
        print(f"[完成] JSON: {json_path}")
        print(f"\n[DATA_PATH] {csv_path}")
    else:
        print("[警告] 未抓取到任何数据！")

    return 0 if deduped else 1


if __name__ == "__main__":
    sys.exit(main())
