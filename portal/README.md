# ccbaby Portal — 工作门户

独立仓库：18+ 业务 SKILL 的 Web 工作台（FastAPI + 静态前端 + Playwright 标书线等）。

## 快速开始

1. 复制 `.env.example` 为 `.env`，填入 API Key 与剑鱼账号（标书模块需要）
2. 安装依赖并启动：

```bash
pip install -r requirements.txt
playwright install chromium   # 标书信息获取 / 产品分析需要
python server.py
```

或双击 **`start-portal.bat`** / **`run-portal.bat`**，浏览器打开 http://localhost:8080

## 目录结构

```
├── server.py              # FastAPI 入口
├── index.html             # 开发工作台首页
├── work/                  # 工作门户首页
├── skills/                # SKILL 定义（manifest + SKILL.md）
├── {skill-slug}/          # 各 SKILL 前端（kebab-case）
├── {skill_slug}/          # 各 SKILL 后端 API（snake_case）
├── image-to-ppt/          # 企划 PPT 排版 UI
├── image_to_ppt/          # 企划 PPT 后端
├── tender-info/           # 标书信息获取
├── tender-analysis/       # 标讯分析
├── tender-product-analysis/
├── requirements.txt
├── .env.example
├── tender_raw_data/       # 运行时（git 忽略，见 README）
├── tender_product_data/
└── annual_report_data/
```

## 主要入口

| 地址 | 说明 |
|------|------|
| `/` | 工作门户首页 |
| `/chat/` | 网页对话 |
| `/tender-info/` | 标书信息获取（剑鱼） |
| `/tender-analysis/` | 标讯分析 |
| `/tender-product-analysis/` | 标书产品分析 |
| `/image-to-ppt/` | 企划 PPT 排版 |
| `/skills/manifest.json` | SKILL 元数据 |

## 环境变量

见 `.env.example`：`ANTHROPIC_*`（对话）、`JIANYU_PHONE` / `JIANYU_PASSWORD`（标书线）、年报与邮件等可选项。

## 开发说明

- 修改 Python 路由后需**重启** `python server.py`
- 标书线路线图：`skills/pm-progress-report/TENDER_LINE_PLAN.md`
- 单元测试：`python -m pytest tests/`（需安装 pytest）

## 从 monorepo 拆出

本目录原为 `ccbaby` 仓库下的 `portal/` 子项目；运行时数据目录已在 `.gitignore` 中排除，克隆后需重新执行标书检索或导入数据。
