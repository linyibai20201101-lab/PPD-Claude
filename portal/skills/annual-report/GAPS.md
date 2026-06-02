# 年报财报分析 · 能力缺口与建设清单

> 项目经理维护。全部 P0/P1/P2 项已完成（2026-06-01）。

## P0 — 能否稳定使用

| # | 能力 | 状态 | 实现位置 |
|---|------|------|----------|
| 1 | 扫描版 PDF / OCR 兜底 | [x] | `pdf_extractor.py` |
| 2 | 长年报分章分析 | [x] | `template_sections.py` + `engine.py` |
| 3 | 异步任务 + 进度查询 | [x] | `jobs.py` + `POST /run` |
| 4 | 报告持久化与历史 | [x] | `storage.py` |
| 5 | 数据引用页码 | [x] | `analyzer.py` |
| 6 | 统一 `POST /run` | [x] | `router.py` |

## P1 — 好用与可信

| # | 能力 | 状态 | 实现位置 |
|---|------|------|----------|
| 7 | 前端任务进度与历史 | [x] | `annual-report/app.js` |
| 8 | 关键指标 JSON | [x] | `metrics_extractor.py` → `metrics.json` |
| 9 | 多年报对比 | [x] | `POST /run` + `extra_files` |
| 10 | 分章单独重跑 | [x] | `POST /reports/{id}/sections/{sid}/rerun` |
| 11 | Word/PDF/Excel 导出 | [x] | `exporter.py` + `GET .../export?format=` |
| 12 | 同行业外部数据 | [x] | `competitor_context.py` + 竞品表单字段 |

## P2 — 智能体路线

| # | 能力 | 状态 | 实现位置 |
|---|------|------|----------|
| 13 | L2 竞品/行业串联 | [x] | `GET /links` + competitor-benchmark URL 预填 |
| 14 | L3 对话 Agent | [x] | `agent.py` + `POST /agent/query` |
| 15 | 单元测试 | [x] | `tests/test_annual_report.py` |
| 16 | 数字回查校验 | [x] | `verifier.py` → `verification.json` |

## 成熟度

- **当前：L1 生产可用 / L2 入口就绪**
- **后续增强**：竞品模块完整分析能力、chat 页原生 tool calling
