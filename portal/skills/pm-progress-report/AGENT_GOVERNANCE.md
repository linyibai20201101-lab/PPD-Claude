# 18 工作 SKILL 智能体治理规范

> 工作门户所有研发必须从此文档出发，判断「做的东西是不是智能体该做的」。

## 智能体成熟度（L0–L3）

| 层级 | 名称 | 用户感知 | 工程要求 |
|------|------|----------|----------|
| **L0** | 占位 | 只有说明页 | UI 占位 + API 501 |
| **L1** | 工具 | 填表/点按钮，结果确定 | `/run` API、可复用 Tools、SKILL.md 定义 I/O |
| **L2** | 编排 | 多步自动串联 | 模块间跳转、job 传递、固定工作流 |
| **L3** | 智能体 | 自然语言目标 → 规划 → 执行 → 解读 | NL 入口、function calling、LLM 结论 |

**当前阶段定位**：整体处于 **L0→L1 过渡**；标书线 L1 已具备，**L3 尚未启动**。

## 开发准入（每个 PR / 功能必答）

1. 服务哪个 SKILL id？属于 L 几？
2. 若为 L1：是否增加/完善 **Agent Tool**（可被对话层调用）？
3. 若为 L0：是否仅占位？是否阻塞更高优 L1？
4. 是否更新 `AGENT_OVERRIDES`（`scripts/agent_audit.py`）与 `PROGRESS.md`？
5. 是否偏离「先 Tools 后 Agent」？若只做 UI 无 API，视为 **偏离**。

## 18 模块与智能体关系

业务 SKILL **18 个**（不含 `pm-progress-report` 方法论模块）：

- **L1 工具已可用**：标书信息获取、企划 PPT（image-to-ppt）、标讯分析（部分）
- **L0 占位**：其余 15 个 — 不得假装「智能体已上线」

标书线目标路径：

```
L1 剑鱼 Tools（进行中）→ L2 获取↔分析编排（已部分）→ L3 标书对话 Agent
```

## 每日 8:00 开发报告

| 项 | 说明 |
|----|------|
| 脚本 | `portal/scripts/daily_agent_report.py` |
| 发送 | `portal/scripts/run_daily_report.bat` |
| 定时 | `portal/scripts/install_daily_report_task.bat`（Windows 计划任务） |
| 存档 | `portal/reports/daily/agent_report_YYYYMMDD.md` |
| 收件 | `REPORT_TO_EMAIL`（默认 linyibai20201101@gmail.com） |

### 邮件配置（portal/.env）

```env
REPORT_TO_EMAIL=linyibai20201101@gmail.com
SMTP_USER=linyibai20201101@gmail.com
SMTP_PASSWORD=Gmail应用专用密码
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
```

Gmail：Google 账户 → 安全 → 两步验证 → **应用专用密码**（16 位，非登录密码）。

## 审计命令

```powershell
cd portal
python scripts/daily_agent_report.py          # 本地生成
python scripts/daily_agent_report.py --send   # 生成并发邮件
```

## 与 PROGRESS.md 分工

| 文档 | 用途 |
|------|------|
| `PROGRESS.md` | 产品能力叙述、复盘、经验 |
| 本文件 | 智能体层级、准入、日报机制 |
| `reports/daily/` | 每日自动快照 |
