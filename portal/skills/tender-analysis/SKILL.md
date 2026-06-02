---
name: tender-analysis
description: >
  标书信息智能分析。登录剑鱼标讯抓取中标数据，或导入 Excel/CSV，完成清洗去重、
  维度提炼（行业/区域/机构/厂商/金额/产品）、15 项统计分析与 HTML 可视化报告。
  触发词：标书分析、招标分析、中标统计、竞品中标分析、抓取标书、剑鱼标讯。
category: market-policy
inputTypes: [pdf, text, csv]
outputFormat: markdown-report
status: scaffold
---

# 标书信息分析（剑鱼标讯 + 数据分析）

## 技能概述

支持两种数据来源：

- **模式 A（全自动）**：登录剑鱼标讯 → 关键词搜索 → 翻页抓取 → 去重分析 → 生成报告
- **模式 B（半自动）**：用户导出 Excel/CSV → 去重分析 → 生成报告

完整流程：**抓取（可选）→ 数据接入 → 清洗去重 → 信息提炼 → 统计分析与可视化**

> 与「标书信息获取」(`tender-info`) 的关系：门户上 `tender-info` 负责**快速查中标**；本 SKILL 负责**抓取 + 深度分析 + HTML 报告**。爬虫脚本在本目录 `scripts/` 下。

## 数据源

- 平台：**剑鱼标讯** https://www.jianyu360.com/（注意是 `.com`，不是 `.cn`）
- 账号：`portal/.env` 中 `JIANYU_PHONE`、`JIANYU_PASSWORD`

---

## 阶段零：剑鱼标讯自动抓取

脚本路径：`portal/skills/tender-analysis/scripts/`

### 环境准备（首次）

```powershell
cd e:\ccbaby\portal
pip install playwright pandas openpyxl
python -m playwright install chromium
```

### 探测页面（平台改版时）

```powershell
python skills/tender-analysis/scripts/probe_jianyu.py
# 输出 probe_homepage.png 等，据此更新 jianyu_crawler.py 中的 SELECTORS
```

### 抓取命令

```powershell
python skills/tender-analysis/scripts/jianyu_crawler.py "产品关键词" `
  --username %JIANYU_PHONE% --password %JIANYU_PASSWORD% `
  --max-pages 50 --output tender_raw_data
```

- 登录态保存在 `tender_raw_data/auth_state.json`，再次抓取可省略密码
- 默认有头浏览器，遇验证码有 60 秒人工处理窗口
- 输出：`jianyu_关键词_时间戳.csv` + `.json`

| 账号类型 | 建议 max-pages |
|---------|----------------|
| 免费    | 5–10           |
| VIP     | 50+            |

---

## 阶段一：数据接入

- Excel / CSV / 爬虫输出 CSV
- 读取后展示列名、前 3 行、总行数，确认字段映射
- 保留原始副本

## 阶段二：清洗去重

脚本：`scripts/data_cleaner.py`

- 同一项目多公告（招标/中标/废标）按主键合并
- 保留优先级：中标公告 > 成交公告 > 招标公告
- 金额统一为万元；地址标准化（见 `references/region_mapping.md`）

## 阶段三：维度提炼

脚本：`scripts/info_extractor.py` + 参考 `references/`

| 维度 | 说明 |
|------|------|
| 项目名称 | 行业分类（`industry_keywords.md`） |
| 项目地址 | 省-市 |
| 采购单位 | 机构类型（`org_type_rules.md`） |
| 中标单位 | 厂商品牌标准化 |
| 项目金额 | 万元数值 |
| 产品详情 | 型号、规格、数量 |

## 阶段四：统计分析（15 项）

区域分布、价格区间、厂商排名、厂商×区域/行业热力图等（见原 SKILL 模块列表）。

## 阶段五：HTML 报告

```powershell
python skills/tender-analysis/scripts/report_generator.py `
  --input tender_raw_data/jianyu_xxx.csv --output report.html --keyword "产品关键词"
```

---

## 门户入口

- 操作页：`/tender-analysis/`
- 快速检索：`/tender-info/`（轻量中标查询）
- API：`/api/tender-analysis/`（骨架，后续对接上述脚本）

## 执行约定

- 分阶段反馈进度；字段异常先标注存疑，不中断流程
- 超过 5000 条先抽样 500 条验证
- 最终交付：HTML 报告 + Excel 汇总表
