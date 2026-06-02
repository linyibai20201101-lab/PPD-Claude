# tender-product-analysis

标书产品信息分析 SKILL：统筹 **项目统计（金额/数量）** 与 **附件 PDF/Word 参数解析**。

- 规范：`SKILL.md`
- 数据模型：`references/unified_schema.md`
- 缺口：`GAPS.md`
- 报告模板：`templates/output-template.md`

开发入口：`portal/tender_product_analysis/`（API/引擎）、`portal/tender-product-analysis/`（门户 UI）。

**阶段一（当前）**：接入 `tender-info` 任务 CSV → 可选剑鱼详情抓取 → `products_master.xlsx` + `stats_summary.json` + `report.md`。

**阶段二（规划）**：附件 PDF/Word 下载与参数抽取并入统筹表。
