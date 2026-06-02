---
name: product-design
description: 基于需求描述输出产品定位、功能规划与设计建议。
category: product-planning
inputTypes: [text]
outputFormat: markdown-report
status: scaffold
---

# 产品设计

## 目标

基于需求描述输出产品定位、功能规划与设计建议。

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
