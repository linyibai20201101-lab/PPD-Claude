---
name: policy-analysis
description: 解读政策文件，分析政策背景、核心条款、影响范围与应对建议。
category: market-policy
inputTypes: [pdf, text, url]
outputFormat: markdown-report
status: scaffold
---

# 政策分析

## 目标

解读政策文件，分析政策背景、核心条款、影响范围与应对建议。

## 输入

- 支持类型：pdf, text, url
- 请在用户提供足够上下文后开始分析

## 工作流

1. 确认输入完整性，缺失时向用户追问
2. 按领域知识进行结构化分析
3. 使用 `templates/` 下的输出模板组织结果
4. 给出可执行的结论与建议

## 输出格式

参考 [`templates/output-template.md`](templates/output-template.md)
