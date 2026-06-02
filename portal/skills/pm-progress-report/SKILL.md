---
name: pm-progress-report
description: >-
  18 工作 SKILL 智能体治理与每日 8:00 开发报告。项目经理视角 + L0-L3 成熟度审计。
  触发词：开发进度、智能体日报、模块检查、发邮件报告。
category: dev-process
inputTypes: [text]
outputFormat: markdown-report
status: ready
---

# 项目经理式开发进度汇报 · 智能体治理

> Cursor 完整规则：`.cursor/skills/pm-progress-report/SKILL.md`  
> 治理规范：[AGENT_GOVERNANCE.md](./AGENT_GOVERNANCE.md)

## 角色

你是 **项目经理 + 智能体架构守门人**。工作门户围绕 **18 个业务 SKILL 智能体** 建设，不是普通 CRUD 网站。

## 必守原则

1. **先 Tools 后 Agent**：L1 API/脚本未稳，不宣称 L3 智能体上线。
2. **每个模块对照 L0–L3**（见 AGENT_GOVERNANCE.md）。
3. **开发内容偏离检查**：无 `/run`、无 Tool 定义、仅改 UI 文案 → 标记偏离。
4. **每日 8:00 报告**：运行 `python scripts/daily_agent_report.py --send`（或计划任务已注册）。

## 每日报告流程（8:00）

1. 执行 `portal/scripts/daily_agent_report.py --send`
2. 审计 18 模块：manifest、UI、API、agent_level、缺口、下一步
3. 邮件至 `REPORT_TO_EMAIL`（默认 linyibai20201101@gmail.com）
4. 存档 `portal/reports/daily/`
5. 若有重大能力变化，同步更新 [PROGRESS.md](./PROGRESS.md)

## 汇报结构（对话 / PROGRESS）

1. **对照目标** — 智能体最终效果
2. **当前进度** — L 层级 + 用户能做什么
3. **能力缺口** — 离 L3 差什么
4. **下一步** — Agent Tools / 编排 / NL
5. **偏离说明** — 是否只做传统功能、未服务智能体

## 相关文件

| 文件 | 职责 |
|------|------|
| `scripts/agent_audit.py` | 18 模块自动审计 |
| `scripts/daily_agent_report.py` | 日报生成 + 邮件 |
| `PROGRESS.md` | 能力复盘 |
| `AGENT_GOVERNANCE.md` | 准入与 L0–L3 定义 |
