#!/usr/bin/env python3
"""
在 CC-Switch 中为 Claude Code 添加 / 更新 DeepSeek 供应商。

用法:
  # 从环境变量或 portal/.env 读取 DEEPSEEK_API_KEY
  python scripts/setup_cc_switch_deepseek.py

  # 显式传入 Key 并设为当前供应商
  python scripts/setup_cc_switch_deepseek.py --api-key sk-xxx --activate

  # 仅查看已有 Claude 供应商
  python scripts/setup_cc_switch_deepseek.py --list

DeepSeek 官方 Claude Code 接入:
  https://api-docs.deepseek.com/guides/agent_integrations/claude_code
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import time
import uuid
from pathlib import Path

from dotenv import load_dotenv

PORTAL_ROOT = Path(__file__).resolve().parent.parent
CC_SWITCH_DB = Path(os.environ.get("CC_SWITCH_DB", Path.home() / ".cc-switch" / "cc-switch.db"))
CLAUDE_SETTINGS = Path(os.environ.get("CLAUDE_SETTINGS", Path.home() / ".claude" / "settings.json"))

DEEPSEEK_BASE_URL = "https://api.deepseek.com/anthropic"
DEEPSEEK_WEBSITE = "https://platform.deepseek.com"
PROVIDER_NAME = "DeepSeek"
APP_TYPE = "claude"

DEFAULT_MODELS = {
    "ANTHROPIC_MODEL": "deepseek-v4-pro[1m]",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "deepseek-v4-pro[1m]",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "deepseek-v4-pro[1m]",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "deepseek-v4-flash",
    "CLAUDE_CODE_SUBAGENT_MODEL": "deepseek-v4-flash",
    "CLAUDE_CODE_EFFORT_LEVEL": "max",
}


def _load_api_key(explicit: str | None) -> str:
    if explicit and explicit.strip():
        return explicit.strip()
    load_dotenv(PORTAL_ROOT / ".env")
    key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if key:
        return key
    raise SystemExit(
        "未找到 DeepSeek API Key。请任选其一：\n"
        "  1) python setup_cc_switch_deepseek.py --api-key sk-你的Key\n"
        "  2) 在 portal/.env 添加 DEEPSEEK_API_KEY=sk-...\n"
        "  3) 设置环境变量 DEEPSEEK_API_KEY\n"
        "Key 获取: https://platform.deepseek.com"
    )


def _build_settings_config(api_key: str) -> dict:
    env = {
        "ANTHROPIC_BASE_URL": DEEPSEEK_BASE_URL,
        "ANTHROPIC_AUTH_TOKEN": api_key,
        **DEFAULT_MODELS,
    }
    return {"env": env}


def _build_meta() -> dict:
    now_ms = int(time.time() * 1000)
    return {
        "apiFormat": "anthropic",
        "authTokenField": "ANTHROPIC_AUTH_TOKEN",
        "baseUrl": DEEPSEEK_BASE_URL,
        "custom_endpoints": {
            DEEPSEEK_BASE_URL: {
                "url": DEEPSEEK_BASE_URL,
                "added_at": now_ms,
                "last_used": None,
            }
        },
    }


def _backup_db() -> Path:
    if not CC_SWITCH_DB.is_file():
        raise SystemExit(f"未找到 CC-Switch 数据库: {CC_SWITCH_DB}")
    backup = CC_SWITCH_DB.with_suffix(f".db.bak-{int(time.time())}")
    shutil.copy2(CC_SWITCH_DB, backup)
    return backup


def list_providers(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        "SELECT name, app_type, is_current, settings_config FROM providers WHERE app_type = ?",
        (APP_TYPE,),
    ).fetchall()
    if not rows:
        print("（无 Claude Code 供应商）")
        return
    for name, app_type, is_current, settings_config in rows:
        base = ""
        try:
            env = json.loads(settings_config or "{}").get("env", {})
            base = env.get("ANTHROPIC_BASE_URL", "")
        except json.JSONDecodeError:
            base = "?"
        mark = " [当前]" if is_current else ""
        print(f"  - {name}{mark} · {base}")


def upsert_deepseek(conn: sqlite3.Connection, api_key: str, activate: bool) -> str:
    settings_json = json.dumps(_build_settings_config(api_key), ensure_ascii=False)
    meta_json = json.dumps(_build_meta(), ensure_ascii=False)
    now_ms = int(time.time() * 1000)

    row = conn.execute(
        "SELECT id FROM providers WHERE app_type = ? AND name = ?",
        (APP_TYPE, PROVIDER_NAME),
    ).fetchone()

    if row:
        provider_id = row[0]
        conn.execute(
            """
            UPDATE providers SET
              settings_config = ?,
              meta = ?,
              website_url = ?,
              category = 'preset',
              icon = 'deepseek',
              provider_type = 'anthropic'
            WHERE id = ?
            """,
            (settings_json, meta_json, DEEPSEEK_WEBSITE, provider_id),
        )
        print(f"[更新] 供应商「{PROVIDER_NAME}」id={provider_id}")
    else:
        provider_id = str(uuid.uuid4())
        max_sort = conn.execute(
            "SELECT COALESCE(MAX(sort_index), -1) FROM providers WHERE app_type = ?",
            (APP_TYPE,),
        ).fetchone()[0]
        conn.execute(
            """
            INSERT INTO providers (
              id, app_type, name, settings_config, website_url, category,
              created_at, sort_index, notes, icon, icon_color, meta,
              is_current, in_failover_queue, cost_multiplier
            ) VALUES (?, ?, ?, ?, ?, 'preset', ?, ?, '', 'deepseek', NULL, ?, 0, 0, '1.0')
            """,
            (
                provider_id,
                APP_TYPE,
                PROVIDER_NAME,
                settings_json,
                DEEPSEEK_WEBSITE,
                now_ms,
                max_sort + 1,
                meta_json,
            ),
        )
        print(f"[新增] 供应商「{PROVIDER_NAME}」id={provider_id}")

    conn.execute(
        "DELETE FROM provider_endpoints WHERE provider_id = ? AND app_type = ?",
        (provider_id, APP_TYPE),
    )
    conn.execute(
        """
        INSERT INTO provider_endpoints (provider_id, app_type, url, added_at)
        VALUES (?, ?, ?, ?)
        """,
        (provider_id, APP_TYPE, DEEPSEEK_BASE_URL, now_ms),
    )

    if activate:
        conn.execute(
            "UPDATE providers SET is_current = 0 WHERE app_type = ?",
            (APP_TYPE,),
        )
        conn.execute(
            "UPDATE providers SET is_current = 1 WHERE id = ?",
            (provider_id,),
        )
        print(f"[启用] 已将「{PROVIDER_NAME}」设为 Claude Code 当前供应商")

    return provider_id


def write_claude_settings(api_key: str) -> None:
    CLAUDE_SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    data = {"env": _build_settings_config(api_key)["env"]}
    if CLAUDE_SETTINGS.is_file():
        backup = CLAUDE_SETTINGS.with_suffix(".json.bak")
        shutil.copy2(CLAUDE_SETTINGS, backup)
        print(f"[备份] {backup}")
    CLAUDE_SETTINGS.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[写入] {CLAUDE_SETTINGS}")


def main() -> int:
    parser = argparse.ArgumentParser(description="CC-Switch 接入 DeepSeek（Claude Code）")
    parser.add_argument("--api-key", help="DeepSeek API Key (sk-...)")
    parser.add_argument("--activate", action="store_true", help="设为当前供应商并写入 ~/.claude/settings.json")
    parser.add_argument("--list", action="store_true", help="仅列出 Claude 供应商")
    parser.add_argument("--no-backup", action="store_true", help="不备份 cc-switch.db")
    args = parser.parse_args()

    if not CC_SWITCH_DB.is_file():
        print(f"请先安装 CC-Switch: https://ccswitch.io\n数据库路径: {CC_SWITCH_DB}")
        return 1

    conn = sqlite3.connect(CC_SWITCH_DB)
    try:
        if args.list:
            print(f"CC-Switch Claude 供应商 ({CC_SWITCH_DB}):")
            list_providers(conn)
            return 0

        if not args.no_backup:
            bak = _backup_db()
            print(f"[备份] {bak}")

        api_key = _load_api_key(args.api_key)
        upsert_deepseek(conn, api_key, activate=args.activate)
        conn.commit()

        print("\n当前 Claude 供应商:")
        list_providers(conn)

        if args.activate:
            write_claude_settings(api_key)
            print("\n请关闭并重新打开终端，再运行 claude 测试。")
        else:
            print(
                "\n下一步：在 CC-Switch 界面启用「DeepSeek」，或运行:\n"
                "  python scripts/setup_cc_switch_deepseek.py --activate"
            )
            print("（--activate 会从 .env 再次读取 DEEPSEEK_API_KEY）")
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
