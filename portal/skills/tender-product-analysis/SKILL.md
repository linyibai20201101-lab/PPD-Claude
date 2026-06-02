---
name: tender-product-analysis
description: >
  标书产品信息分析：列表/详情/原文附件全链路抓取，统筹项目级统计与产品行级参数，
  解析 PDF/Word 招标文件并输出 Excel+MD 报告。触发词：标书产品分析、附件解析、招标参数。
category: market-policy
inputTypes: [csv, pdf, docx, url]
outputFormat: markdown-report
status: ready
---

# 标书产品信息分析

## 目标

在标书/中标数据基础上，**把能爬到的信息统筹到一张产品分析库**：

1. **项目级**：金额、数量、区域、采购单位、中标单位（与标讯统计一致，但服务于产品视角）
2. **详情页级**：剑鱼详情正文中的产品表、简要规格
3. **附件级（核心）**：有附件的中标项目 → 跳转原文 → 下载 PDF/Word → 技术参数深度解析

最终输出：**统一 Excel 产品总表 + 统计摘要 + MD 分析报告**。

## 与兄弟模块分工

| 模块 | 职责 |
|------|------|
| `tender-info` | 剑鱼检索，快速列表 CSV |
| `tender-analysis` | 市场大盘：区域/行业/厂商 15 项 HTML 统计 |
| **`tender-product-analysis`（本模块）** | **产品+金额+数量+附件参数** 统筹分析 |

推荐串联：`tender-info` 提交检索 → 本模块 `POST /run` 传入 `source_job_id` 做深度分析。

## 统一数据模型

见 [`references/unified_schema.md`](references/unified_schema.md)。

三层合并为导出表：

- **L1 项目**：一条中标/成交记录
- **L2 产品行**：从详情或附件解析出的 SKU/明细行（含数量、单价、金额）
- **L3 参数**：规格键值（分辨率、量程、品牌、型号等）

统计层在 L1/L2 上聚合：金额 SUM、数量 SUM、产品/型号 TOP、厂商×产品交叉表。

## 处理流程

```
列表(CSV/job) → 筛选有附件(可选) → 剑鱼详情
    → **关键词+产品属性** 匹配正文产品清单 → 金额/数量/参数
    → 附件名线索 +（P1）PDF/Word 全文清单匹配
    → 原文跳转 → 下载附件(PDF/DOC/DOCX)
    → 文档解析 → 参数表
    → 与 L1/L2 合并去重
    → 统计 + LLM 解读 → 报告
```

## 输入

- `source_job_id`：`tender-info` 任务 ID（推荐）
- 或上传 CSV（须含 `详情链接`，建议含 `有附件`）
- `keywords`：检索词（用于参数匹配、报告标题）
- `only_with_attachment`：是否仅处理有附件项目（默认 true 可配置）
- `fetch_original`：是否跟跳原文站（P1）
- `parse_attachments`：是否下载并解析 PDF/Word（默认 true）

## 输出

- `tender_product_data/{job_id}/projects/...` 原始附件与中间 JSON
- `products_master.xlsx`：统筹总表（项目+产品+参数列）
- `stats_summary.json`：金额/数量/产品 TOP 等统计
- `report.md`：按 [`templates/output-template.md`](templates/output-template.md)

## 账号与依赖

- 剑鱼：`portal/.env` → `JIANYU_PHONE`、`JIANYU_PASSWORD`
- 文档：`pymupdf`、`python-docx`；扫描件 `rapidocr-onnxruntime`（可选）
- LLM：解读章节用 `portal/.env` MiMo/Anthropic（可选 P1）

## API（规划）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/tender-product-analysis/status` | 状态 |
| POST | `/api/tender-product-analysis/run` | 异步深度分析 |
| GET | `/api/tender-product-analysis/jobs/{id}` | 进度 |
| GET | `/api/tender-product-analysis/reports` | 历史 |

## 门户

- `/tender-product-analysis/` — 产品分析工作台（统计+详情，阶段一已就绪）
