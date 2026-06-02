---
name: leader-analysis
description: 分析行业龙头企业的战略、产品、财务与市场地位。
category: market-policy
inputTypes: [text]
outputFormat: markdown-report
status: scaffold
---

# 龙头分析

## 目标

分析行业龙头企业的战略、产品、财务与市场地位。

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
