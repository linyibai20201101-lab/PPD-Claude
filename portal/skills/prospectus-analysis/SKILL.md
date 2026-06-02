---
name: prospectus-analysis
description: 解析招股说明书，提取业务概况、财务数据、风险因素与估值要点。
category: finance
inputTypes: [pdf]
outputFormat: markdown-report
status: scaffold
---

# 招股书分析

## 目标

解析招股说明书，提取业务概况、财务数据、风险因素与估值要点。

## 输入

- 支持类型：pdf
- 请在用户提供足够上下文后开始分析

## 工作流

1. 确认输入完整性，缺失时向用户追问
2. 按领域知识进行结构化分析
3. 使用 `templates/` 下的输出模板组织结果
4. 给出可执行的结论与建议

## 输出格式

参考 [`templates/output-template.md`](templates/output-template.md)
