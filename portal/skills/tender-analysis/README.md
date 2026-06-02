# 标讯分析

招标文件解析、剑鱼标讯抓取与中标数据深度分析。

## 状态

- **抓取脚本**：已从 `MD_list/tender-analysis.zip` 迁入 `scripts/`
- **门户 UI / API**：骨架阶段

## 能力矩阵

| 能力 | 脚本 | 说明 |
|------|------|------|
| 剑鱼登录抓取 | `scripts/jianyu_crawler.py` | Playwright，输出 CSV |
| 页面探测 | `scripts/probe_jianyu.py` | 平台改版时更新选择器 |
| 清洗去重 | `scripts/data_cleaner.py` | 金额/地址/去重 |
| 维度提炼 | `scripts/info_extractor.py` | 行业/机构/厂商 |
| HTML 报告 | `scripts/report_generator.py` | ECharts 仪表盘 |

## 访问

- 门户：`/tender-analysis/`
- 轻量查中标：`/tender-info/`
- SKILL：`portal/skills/tender-analysis/SKILL.md`

## 依赖

```powershell
pip install playwright pandas openpyxl
python -m playwright install chromium
```

账号：`portal/.env` → `JIANYU_PHONE`、`JIANYU_PASSWORD`
