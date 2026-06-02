# 标书产品信息分析 · 能力缺口与建设清单

> 项目经理维护。目标：**统计（金额/数量/产品）+ 附件原文 PDF/Word 参数** 统筹到同一导出与分析链路。

## P0 — 能跑通闭环

| # | 能力 | 状态 | 说明 |
|---|------|------|------|
| 1 | SKILL 定义 + 统一数据模型 | [x] | `SKILL.md`、`references/unified_schema.md` |
| 2 | 接入 tender-info job / CSV | [x] | `source_job_id` 读取 `tender_raw_data/{id}/` |
| 3 | 关键词+属性匹配正文/附件清单 | [x] | `product_matcher.py`（非硬编码型号） |
| 4 | 附件下载（剑鱼站内直链） | [x] | `attachment_fetcher.py` 详情页同会话下载 |
| 5 | PDF/Word 文本与表格抽取 | [x] | `attachment_parser.py` PyMuPDF + python-docx |
| 6 | 合并 L1/L2/L3 → `products_master.xlsx` | [x] | `product_lines.py` + export |
| 7 | 基础统计 `stats_summary.json` | [x] | `stats.py` 金额/数量/产品 TOP |
| 8 | `POST /run` + job 进度 + 存储目录 | [x] | `tender_product_data/` |
| 9 | 门户页（可运行+页内表） | [x] | `/tender-product-analysis/` |

## P1 — 好用与深度

| # | 能力 | 状态 | 说明 |
|---|------|------|------|
| 10 | 跳转原文站（政采云等） | [ ] | 多模板选择器 |
| 11 | ZIP 解压、扫描件 OCR | [ ] | 复用 annual_report OCR |
| 12 | 参数键值 LLM 增强 + 报告 MD | [ ] | 按 output-template |
| 13 | tender-info 一键「产品深度分析」 | [x] | 结果区「产品分析」+ 任务 ID 展示 |
| 14 | 失败重跑、仅附件队列 | [x] | `from_report_id` + failed/no_match |
| 15 | 智能体工作台 UI（轨迹） | [ ] | 参考 annual-report |

## P2 — 智能体

| # | 能力 | 状态 | 说明 |
|---|------|------|------|
| 16 | 对话触发 run + 解读 | [ ] | |
| 17 | 我司产品库对标 | [ ] | 竞品/产品库字段 |

## 成熟度

- **当前：L1+** 统计+详情+附件解析；S2 未命中/重跑；S3 标讯摘要+CSV 上传；**S1.7** 见 `S17_ACCEPTANCE.md`
- **目标：L2** 一站式向导 + 智能体轨迹（S4）
- **L2**：tender-info → 本模块一键串联

## 与 tender-analysis 边界

- **不替代** 标讯分析的市场 HTML 大盘；统计结果可复用部分逻辑，但导出主表是 **产品行宽表**。
- 本模块 **必须** 解析有附件项目的招标文件（用户明确要求）。
