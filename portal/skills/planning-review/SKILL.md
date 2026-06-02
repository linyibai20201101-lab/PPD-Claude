---
name: planning-review
description: 审核企划文稿的内容完整性、逻辑性与合规性，给出修改建议。
category: product-planning
inputTypes: [text, pdf]
outputFormat: markdown-report
status: scaffold
---

# 企划内容审核

## 目标

审核企划文稿的内容完整性、逻辑性与合规性，给出修改建议。

## 输入

- 支持类型：text, pdf
- 请在用户提供足够上下文后开始分析

## 工作流

1. 确认输入完整性，缺失时向用户追问
2. 按领域知识进行结构化分析
3. 使用 `templates/` 下的输出模板组织结果
4. 给出可执行的结论与建议

## 输出格式

参考 [`templates/output-template.md`](templates/output-template.md)
