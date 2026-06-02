---
name: competitor-benchmark
description: 按统一维度对竞品进行跑分对比，生成结构化对比表与分析结论。
category: market-policy
inputTypes: [text, table]
outputFormat: comparison-table
status: scaffold
---

# 竞品跑分表对比分析

## 目标

按统一维度对竞品进行跑分对比，生成结构化对比表与分析结论。

## 输入

- 支持类型：text, table
- 请在用户提供足够上下文后开始分析

## 工作流

1. 确认输入完整性，缺失时向用户追问
2. 按领域知识进行结构化分析
3. 使用 `templates/` 下的输出模板组织结果
4. 给出可执行的结论与建议

## 输出格式

参考 [`templates/output-template.md`](templates/output-template.md)
