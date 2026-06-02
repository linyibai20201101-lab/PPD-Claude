# 产品开发进度总览

> 由 **pm-progress-report** SKILL 维护。每次能力变更后追加「最新汇报」，不删除历史。
> 汇报语言：**产品能力**，不是代码清单。

---

## 全局汇报 · 2026-06-02（最新）

### 对照目标

建设 **18 个工作 SKILL 智能体** 的工作门户：L1 工具 → L2 编排 → L3 对话 Agent。当前 Phase 1 以 Tools 为主，年报模块正推进 **L2 智能体工作台** 展示形态。

### 当前进度（平台层）

| 层级 | 状态 |
|------|------|
| 工作台首页 | 可用：18 业务 SKILL + 开发方法论卡片 |
| 智能体治理 | `AGENT_GOVERNANCE.md` + `agent_audit.py` 每日审计 |
| 每日 8:00 报告 | 脚本就绪；邮件需 `SMTP_PASSWORD`（应用专用密码） |
| **L1 工具** | 企划 PPT、**年报财报分析**（分章/OCR/校验/导出） |
| **L2 编排** | 标书获取 ↔ 标讯分析；年报 ↔ 竞品对标 URL 预填 |
| **L2+ 展示** | 年报模块已改为三栏智能体工作台（对话/轨迹/交付物） |
| **L0 占位** | 其余约 13 个 scaffold 模块 |

### 本周期重点交付（2026-06-01 ~ 06-02）

1. **年报财报分析**：GAPS P0–P2 全部完成；申菱 175 页年报实测；按章节分读 PDF（取消全文 12 万字截断）；智能体工作台 UI。
2. **标书线**：tender-info 筛选/日期/中标默认；tender-analysis 联动分析。
3. **方法论**：pm-progress-report 日报脚本 + PROGRESS 复盘机制。

### 能力缺口（平台）

- L3 对话层：年报仅有轻量 `agent/query`，尚不能对话内全自动调 `/run`
- 复盘闭环：前端复盘面板已有，后端 `reflect` / 一键优化重跑未接
- 邮件日报：`.env` 未配置 `SMTP_PASSWORD` 时无法发信
- 竞品对标等 13+ 模块仍为 scaffold

### 下一步建设

1. **标书线**：S2 完成；**S3.4–3.5 + S4.1 入口** 已落地（标讯 LLM/规则摘要、CSV 上传、首页一站式关键词）；待 **S1.7 业务验收** 与 S4 轨迹 UI
2. 配置 Gmail 应用专用密码 → 启用每日 8:00 自动邮件
3. 年报 Phase 2：对话 Tool 调用 `/run` + 复盘自动重跑章节
4. 标书 Agent MVP（S5）：chat Tool 调三条 `/run`
5. 竞品 benchmark 模块从 scaffold 升到 L1

---

## 全局汇报 · 2026-06-01（历史）

### 对照目标

建设 **18 个工作 SKILL 智能体** 的工作门户：L1 工具 → L2 编排 → L3 对话 Agent。当前 Phase 1 以 Tools 为主，不偏离智能体路线图。

### 当前进度（平台层）

| 层级 | 状态 |
|------|------|
| 工作台首页 | 可用：18 业务 SKILL + 开发方法论卡片 |
| 智能体治理 | `AGENT_GOVERNANCE.md` + `agent_audit.py` 每日审计 |
| 每日 8:00 报告 | 脚本就绪；邮件需配置 `portal/.env` SMTP |
| **L1 工具** | 企划 PPT（image-to-ppt） |
| **L2 编排** | 标书信息获取 ↔ 标讯分析（抓取→分析跳转） |
| **L0 占位** | 其余 15 个 scaffold 模块 |

### 能力缺口（平台）

- L3 对话 Agent 尚未启动（无 NL 入口、无 function calling 编排）
- 15 个模块仅占位，不得对外宣称「智能体已上线」
- 日报邮件依赖 Gmail 应用专用密码

### 下一步建设

1. **配置 SMTP** → 注册计划任务 `install_daily_report_task.bat`
2. **标书 Agent MVP（Phase 2）**：对话 + 调 tender-info / tender-analysis + LLM 解读
3. **巩固 L2**：任务持久化、剑鱼筛选稳定性

---

## 全局汇报 · 2026-06-02（历史）

### 对照目标

建设 **ccbaby 工作门户**：在一个入口里聚合多个业务 SKILL（标书、图片转 PPT、行业调研等），用户打开网页即可完成查询、转换、分析，无需记命令行。

### 当前进度（平台层）

| 层级 | 状态 |
|------|------|
| 工作台首页 | 可用：18 个 SKILL 卡片、对话 API、一键重启 8080 |
| 开发方法论 | 已建立 `pm-progress-report`：产品能力式汇报 + PROGRESS.md 复盘 |
| **已可用模块** | 标书信息获取、图片结构转 PPT |
| **部分可用** | 标讯分析（脚本在，网页一键分析未接） |
| **待开发** | manifest 中其余 15+ scaffold 模块 |

> **运行态**：当前 8080 portal 未启动，需 `start-portal.bat` 或 `cd portal && python server.py` 后各模块才可访问。

### 能力缺口（平台）

- 多数 SKILL 仅有占位页，尚无实际业务能力
- 模块间跳转有链接，但缺少「查完标书 → 一键深度分析」等产品闭环
- 账号/配置分散（剑鱼需页面或 .env），新用户上手成本偏高

### 下一步建设（建议优先级）

1. **标书信息获取** — 打磨到「日常可用」（见下模块节）
2. **标讯分析** — 接上 CSV 上传 → HTML 报告
3. **按需启动** — 你指定下一个要高优的 SKILL（行业调研 / 政策分析等）

---

## 模块：标书信息获取（tender-info）

### 产品目标

用户登录剑鱼标讯，按**产品**或**企业**关键词快速查看中标情况：填账号 → 设条件 → 执行任务 → 看列表 + 下载 CSV。与 tender-analysis 分工：本模块轻量查询，不做深度统计报告。

### 最新汇报 · 2026-06-02（打磨）

- **进度**
  - **默认只展示已中标/成交**，统计 chips 显示匹配/已中标/预告数量
  - **日期筛选**已生效（支持「05-28」「N小时前」等剑鱼格式）
  - 结果表新增**类型标签**、**剑鱼详情链接**、**Markdown 报告预览**
  - 可选「包含招标/预告」；CSV 下载为**筛选后**结果
  - 登录态全局复用（`tender_raw_data/auth_state.json`）；翻页选择器增强
- **缺口**
  - 翻页仍须在真实多页场景下验收
  - 产品维度仍依赖列表页（未开详情时无产品明细）
  - 任务仍存内存
- **下一步**
  1. 多页抓取实测与翻页微调
  2. tender-info → tender-analysis 一键深度分析
  3. 可选：任务历史持久化

### 技术复盘

- 剑鱼域名：`jianyu360.com`（非 .cn）；Playwright 无头可登录，验证码需有头
- 爬虫 subprocess 首次约 2 分钟；任务进行中勿重启 portal
- 重启 8080 用 `restart_portal_worker.py` 可靠

### 经验复用

- 联调前先直连跑 `jianyu_crawler.py`，再走 portal API
- 演示用「工业相机」；首次使用关闭无头、勾选「仅抓列表」

---

## 模块：标讯分析（tender-analysis）

### 产品目标

批量抓取 → 清洗去重 → 15 项统计 → HTML 报告。门户 UI 偏说明型，主流程在脚本。

### 最新汇报 · 2026-06-01

- **进度**
  - 门户页可接收 `job_id` 自动分析（6+ 维度 HTML 报告 + 下载）
  - 标书获取结果页「标讯分析」一键跳转
  - manifest 状态已更新为 `ready`
- **缺口**
  - 缺 LLM 对报告的竞争格局文字解读
  - 无对话式选参与追问
- **下一步**
  - Phase 2：Agent function calling 调 `/api/tender-analysis/run`
  - LLM 生成执行摘要段落

### 最新汇报 · 2026-06-02（历史）

- **进度**：爬虫脚本可用；与 tender-info 共用爬虫；门户有说明页与交叉链接
- **缺口**：网页无法「上传 CSV → 出报告」；与轻量查询的边界用户易混淆
- **下一步**：CSV 上传 + report_generator；或 tender-info 结果一键「深度分析」

### 技术复盘

- 改 `jianyu_crawler.py` 须同时评估 tender-info 与 tender-analysis

### 经验复用

- 轻量查询 → tender-info；统计报告 → tender-analysis

---

## 模块：标书产品信息分析（tender-product-analysis）

### 产品目标

在 tender-info 检索结果上，按**关键词+产品属性**匹配正文/附件中的产品清单，统筹**金额、数量、参数**到产品宽表；与标讯分析（市场大盘）分工。

### 最新汇报 · 2026-06-02

- **进度（L1 阶段一）**
  - API 异步 run、关键词+政采表解析、项目/产品去重
  - 门户：产品分析一键跳转、页内统计卡片+产品表+报告 Tab
  - 详见 `tender-product-analysis/PM_REVIEW.md`
- **缺口（见 GAPS + TENDER_LINE_PLAN S1）**
  - **附件 PDF/Word 下载与解析**（用户核心诉求，未做）
  - 未命中抽检、失败重跑、属性词典外置、智能体工作台
- **下一步**
  1. **S1（1–2 周）**：附件闭环 → L1+
  2. S2：低分抽检 + 重跑 + 词典配置
  3. S4：三栏工作台（对齐年报）

### 开发计划

全线路线图：**[`TENDER_LINE_PLAN.md`](TENDER_LINE_PLAN.md)**

---

## 模块：图片结构转 PPT（image-to-ppt）

### 产品目标

上传图片/PDF → OCR + 形状识别 → 可编辑 PPT；可选 Vision 增强。

### 最新汇报 · 2026-06-02

- **进度**：四阶段 MVP 完成 — 多图/PDF 上传、图层预览、OCR+形状、Vision 增强、PPT 导出
- **缺口**：真实复杂版式/扫描件效果待你业务侧验收；MiMo Key 未配时 Vision 不可用
- **下一步**：按你实际样张做识别率与编辑体验迭代

---

## 模块：开发进度汇报（pm-progress-report）

### 产品目标

全模块开发统一用「项目经理视角」做能力进度汇报与技术/经验复盘。

### 最新汇报 · 2026-06-01

- **进度**
  - 智能体治理体系：`AGENT_GOVERNANCE.md`、`agent_audit.py`、`daily_agent_report.py`
  - Windows 计划任务脚本 `install_daily_report_task.bat`（每天 08:00）
  - 收件邮箱默认 linyibai20201101@gmail.com（Gmail）
- **缺口**
  - 用户须在 `portal/.env` 配置 Gmail 应用专用密码后 `--send` 才生效
- **下一步**
  - 运行 `install_daily_report_task.bat` 注册定时任务
  - 每次能力变更同步 PROGRESS 与 AGENT_OVERRIDES

### 最新汇报 · 2026-06-02（历史）

- **进度**：SKILL 已注册（Cursor + 门户 manifest）；本 PROGRESS.md 为唯一进度源
- **缺口**：其余 scaffold 模块尚未写入专节
- **下一步**：每完成一轮能力交付自动追加汇报

---

## 跨模块经验

| 主题 | 结论 |
|------|------|
| Portal 热更新 | 改 Python 路由需重启 8080；首页「↻ 重启服务」 |
| SKILL 注册 | `manifest.json` + `portal/{slug}/` UI + `{slug_pkg}/router.py` |
| 进度汇报 | 能力变更 → 五段汇报 → 更新本文件 |

---

## 年报财报分析 · 最新汇报 · 2026-06-02

### 对照目标

用户以**智能体**方式完成上市公司年报分析：对话定目标 → 可见执行轨迹 → 交付报告与指标 → 自我复盘并建议优化。

### 当前进度

| 能力 | 状态 |
|------|------|
| PDF 全页提取（至 250 页） | ✅ 申菱 175 页实测通过 |
| 按章节分读 PDF | ✅ 每章独立选页 ~4.5 万字 |
| 分章 LLM + 校验 + 导出 | ✅ MD/DOCX/PDF/XLSX |
| 智能体工作台 UI | ✅ 对话 / 执行轨迹 / 交付物 / 复盘面板 |
| L3 轻量对话 | ✅ `POST /agent/query`（问答、历史列表） |
| 对话触发分析 | ⚠ 前端支持「开始分析」，未接 Tool Router |

**成熟度：L1 生产可用 · L2 编排（竞品跳转）· L2+ 智能体展示（非完整 L3）**

### 能力缺口

- 对话层不能全自动规划并调用 `/run`（缺 function calling）
- 复盘「一键优化重跑」仅 UI 提示，无 `reflect`/`optimize` API
- 竞品 benchmark 模块仍为 scaffold

### 下一步建设

1. Phase 2：`reflect` + 低分校验自动重跑财务章
2. chat 页注册 annual-report tools
3. 竞品模块 L1 对标表

### 偏离说明

- 界面已按智能体形态改造；执行层仍以确定性 Tools + LLM 为主，符合「先 Tools 后 Agent」。

---

## 年报财报分析 · 历史汇报 · 2026-06-01

（GAPS P0–P2 首次全部完成；见 `skills/annual-report/GAPS.md`）

---

## 待登记模块

以下模块在 manifest 中为 scaffold，首次开发能力时在此追加章节：

`industry-research` · `policy-analysis` · `policy-tracking` · `competitor-benchmark` · `product-design` · `planning-ppt` · `planning-review` · `product-ecosystem` · `tech-advancement` · `patent-analysis` · `rd-manpower` · `leader-analysis` · `prospectus-analysis` · `ecommerce-review` · `exhibition-info`
