---
name: annual-report
description: 分析年报与财务报表，解读经营状况、财务指标与趋势变化。
category: finance
inputTypes: [pdf]
outputFormat: markdown-report
status: ready
---

# 年报财报分析

## 目标

分析年报与财务报表，解读经营状况、财务指标与趋势变化。

## 能力清单

详见 [`GAPS.md`](GAPS.md) — 项目经理维护的缺口与完成状态。

## 工作流

1. 上传年报 PDF（可选自定义 `.md` 模板）
2. 选择分章分析 / 强制 OCR
3. `POST /api/annual-report/run` 提交异步任务
4. 轮询 `GET /api/annual-report/jobs/{job_id}` 获取进度
5. 报告持久化至 `portal/annual_report_data/`，可通过历史列表回看

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/annual-report/status` | 服务状态（含 OCR） |
| GET | `/api/annual-report/template` | 默认分析模板 |
| POST | `/api/annual-report/run` | **推荐** 异步分析 |
| GET | `/api/annual-report/jobs/{job_id}` | 任务进度 |
| GET | `/api/annual-report/reports` | 历史报告列表 |
| GET | `/api/annual-report/reports/{id}` | 读取报告 |
| POST | `/api/annual-report/analyze` | 同步分析（易超时） |

## 配置

需在 `portal/.env` 配置 `ANTHROPIC_API_KEY`。扫描版 PDF 需安装 OCR：`pip install rapidocr-onnxruntime`。

## 输出格式

参考 [`templates/output-template.md`](templates/output-template.md)
