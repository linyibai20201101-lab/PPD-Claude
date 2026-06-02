---
name: patent-analysis
description: 分析专利文档或专利号，梳理技术布局、权利要求与竞争态势。
category: tech-rd
inputTypes: [text, pdf]
outputFormat: markdown-report
status: scaffold
---

# 专利技术分析

## 目标

分析专利文档或专利号，梳理技术布局、权利要求与竞争态势。

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
