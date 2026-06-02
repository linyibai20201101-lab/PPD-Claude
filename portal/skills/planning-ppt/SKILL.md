---
name: planning-ppt
description: 上传图片或 PDF，OCR 识别文字与形状，导出可编辑 .pptx。
category: product-planning
inputTypes: [image, pdf]
outputFormat: pptx
status: ready
---

# 企划PPT排版

## 目标

上传图片或 PDF，OCR 识别文字与形状，导出可编辑 .pptx。

## 输入

- 支持类型：image, pdf
- 请在用户提供足够上下文后开始分析

## 工作流

1. 确认输入完整性，缺失时向用户追问
2. 按领域知识进行结构化分析
3. 使用 `templates/` 下的输出模板组织结果
4. 给出可执行的结论与建议

## 输出格式

参考 [`templates/output-template.md`](templates/output-template.md)
