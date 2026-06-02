#!/usr/bin/env python3
"""
每日工作门户 / 18 SKILL 智能体开发报告。
用法:
  python scripts/daily_agent_report.py              # 生成并打印
  python scripts/daily_agent_report.py --send       # 生成并发送邮件
  python scripts/daily_agent_report.py --send-only # 仅发送最近一份
"""

from __future__ import annotations

import argparse
import os
import smtplib
import ssl
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv

PORTAL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PORTAL_ROOT / "scripts"))

from agent_audit import LEVEL_LABELS, audit_all_skills, summarize  # noqa: E402

REPORT_DIR = PORTAL_ROOT / "reports" / "daily"
PROGRESS_PATH = PORTAL_ROOT / "skills" / "pm-progress-report" / "PROGRESS.md"


def _load_progress_excerpt(max_lines: int = 40) -> str:
    if not PROGRESS_PATH.is_file():
        return "（PROGRESS.md 尚未创建）"
    lines = PROGRESS_PATH.read_text(encoding="utf-8").splitlines()
    # 取最新全局汇报段
    start = 0
    for i, line in enumerate(lines):
        if "全局汇报" in line:
            start = i
            break
    chunk = lines[start : start + max_lines]
    return "\n".join(chunk)


def build_markdown_report() -> str:
    now = datetime.now()
    audits = audit_all_skills()
    stats = summarize(audits)
    business = [a for a in audits if a.id != "pm-progress-report"]

    lines = [
        f"# ccbaby 工作门户 · 智能体开发日报",
        "",
        f"**日期**：{now.strftime('%Y-%m-%d %H:%M')}  ",
        f"**视角**：18 个工作 SKILL 智能体（L0 占位 → L3 完整智能体）",
        "",
        "## 一、成熟度总览",
        "",
        f"| 指标 | 数量 |",
        f"|------|------|",
        f"| 业务 SKILL 总数 | {stats['total']} |",
        f"| L0 占位（无可用 Tool） | {stats['l0']} |",
        f"| L1 工具（API/脚本可用，无 NL 编排） | {stats['l1']} |",
        f"| L2 编排（模块联动 / 流程） | {stats['l2']} |",
        f"| L3 智能体（NL + 规划 + 解读） | {stats['l3']} |",
        f"| 后端 API 可用 | {stats['api_ready']} |",
        "",
        "> **治理结论**：标书线已达 **L2 编排**（获取→分析）；整体仍以 **L1 工具层** 为主，"
        "符合「先 Tools 后 Agent」规划；**L3 对话编排层尚未启动**。",
        "",
        "## 二、18 模块逐项检查",
        "",
        "| SKILL | 清单状态 | 智能体层级 | UI | API可用 | 偏离判断 | 能力缺口 | 下一步（Agent） |",
        "|-------|----------|------------|-----|---------|----------|----------|----------------|",
    ]

    for a in sorted(business, key=lambda x: (-x.agent_level, x.id)):
        ui = "Y" if a.ui else "—"
        api = "Y" if a.api_ready else "—"
        gap = a.agent_gap.replace("|", "/")[:40]
        nxt = a.next_for_agent.replace("|", "/")[:36]
        dev = a.deviation.replace("|", "/")[:28]
        lines.append(
            f"| {a.name} | {a.manifest_status} | {a.level_label} | {ui} | {api} | {dev} | {gap} | {nxt} |"
        )

    lines.extend(
        [
            "",
            "## 三、智能体建设优先级（建议）",
            "",
            "1. **标书 Agent MVP（Phase 2）**：对话入口 + function calling 调 `tender-info` / `tender-analysis` + LLM 解读报告",
            "2. **巩固 L1**：`tender-info` 筛选剑鱼页对齐、任务持久化；`tender-analysis` 报告解读",
            "3. **占位模块**：不并行开 15 个 scaffold，按业务优先级逐个升到 L1",
            "",
            "## 四、PROGRESS.md 摘要",
            "",
            "```",
            _load_progress_excerpt(),
            "```",
            "",
            "---",
            "本报告由 `portal/scripts/daily_agent_report.py` 自动生成 · pm-progress-report SKILL",
        ]
    )
    return "\n".join(lines)


def save_report(content: str) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    day = datetime.now().strftime("%Y%m%d")
    path = REPORT_DIR / f"agent_report_{day}.md"
    path.write_text(content, encoding="utf-8")
    latest = REPORT_DIR / "latest.md"
    latest.write_text(content, encoding="utf-8")
    return path


def send_email(content: str, subject: str) -> None:
    load_dotenv(PORTAL_ROOT / ".env")
    to_addr = os.getenv("REPORT_TO_EMAIL", "linyibai20201101@gmail.com").strip()
    from_addr = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()
    host = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
    port = int(os.getenv("SMTP_PORT", "465"))

    if not from_addr or not password:
        raise RuntimeError(
            "未配置邮件：请在 portal/.env 设置 SMTP_USER、SMTP_PASSWORD、REPORT_TO_EMAIL"
        )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr

    html_body = "<pre style='font-family:Consolas,Microsoft YaHei,sans-serif;white-space:pre-wrap;'>"
    html_body += content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    html_body += "</pre>"

    msg.attach(MIMEText(content, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(host, port, context=context) as server:
        server.login(from_addr, password)
        server.sendmail(from_addr, [to_addr], msg.as_string())
    print(f"[邮件] 已发送至 {to_addr}")


def main() -> int:
    parser = argparse.ArgumentParser(description="每日智能体开发报告")
    parser.add_argument("--send", action="store_true", help="生成后发送邮件")
    parser.add_argument("--send-only", action="store_true", help="只发送 latest.md")
    args = parser.parse_args()

    load_dotenv(PORTAL_ROOT / ".env")

    if args.send_only:
        latest = REPORT_DIR / "latest.md"
        if not latest.is_file():
            print("无 latest.md，请先运行不带 --send-only")
            return 1
        content = latest.read_text(encoding="utf-8")
    else:
        content = build_markdown_report()
        path = save_report(content)
        print(f"[报告] 已写入 {path}")

    if args.send or args.send_only:
        day = datetime.now().strftime("%Y-%m-%d")
        subject = os.getenv("REPORT_EMAIL_SUBJECT", f"[ccbaby] 智能体开发日报 {day}")
        try:
            send_email(content if args.send_only else content, subject)
        except Exception as e:
            print(f"[邮件] 发送失败: {e}")
            return 1

    if not args.send and not args.send_only:
        print(content[:2000])
        if len(content) > 2000:
            print("\n... (完整内容见 reports/daily/latest.md)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
