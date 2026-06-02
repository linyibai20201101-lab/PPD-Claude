---
name: industry-research
description: 对指定行业进行系统性调研，输出市场规模、趋势、竞争格局与机会点分析。
category: market-policy
inputTypes: [text]
outputFormat: markdown-report
status: scaffold
---

# 行业调研

## 目标

对指定行业进行系统性调研，输出市场规模、趋势、竞争格局与机会点分析。

## 输入

- 支持类型：text
- 请在用户提供足够上下文后开始分析

## 工作流

1. 确认输入完整性，缺失时向用户追问
2. 按领域知识进行结构化分析
3. 使用 `templates/` 下的输出模板组织结果
4. 给出可执行的结论与建议

## 输出格式

参考 [`templates/output-template.md`](templates/output-template.md)
