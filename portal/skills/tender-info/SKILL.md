---
name: tender-info
description: 登录剑鱼标讯，按关键词快速查询某产品或企业的中标情况。深度分析见 tender-analysis。触发词：标书获取、剑鱼标讯、中标查询。
category: market-policy
inputTypes: [text]
outputFormat: markdown-report
status: ready
---

# 标书信息获取（剑鱼标讯 · 轻量查询）

## 目标

登录 **剑鱼标讯**（https://www.jianyu360.com/），用关键词快速查看**产品**或**企业**的中标记录。

## 与 tender-analysis 的分工

| 模块 | 用途 |
|------|------|
| **tender-info**（本 SKILL） | 门户快速检索，看中标列表 |
| **tender-analysis** | 爬虫批量抓取 + 去重 + 15 项统计 + HTML 报告 |

批量抓取请直接用：

```powershell
python portal/skills/tender-analysis/scripts/jianyu_crawler.py "关键词" --username ... --password ...
```

## 输入

- `query_type`：`product`（产品）/ `enterprise`（企业）
- `keywords`：产品名或企业名
- 可选：地区、日期范围

## 账号

`portal/.env` → `JIANYU_PHONE`、`JIANYU_PASSWORD`

## 门户

- `/tender-info/` — 轻量查询 UI
- `/tender-analysis/` — 完整分析
