# 标书信息获取

通过剑鱼标讯查询产品或企业的中标情况。

- 门户入口：`/tender-info/`
- 数据源：[剑鱼标讯](https://www.jianyu360.cn/)
- 账号：在 `portal/.env` 配置 `JIANYU_PHONE`、`JIANYU_PASSWORD`

## 查询类型

1. **产品** — 关键词为产品/品类，看谁家中标、在哪些区域
2. **企业** — 关键词为企业名，看该企业近期中标项目

## API

- `GET /api/tender-info/status` — 剑鱼账号是否已配置
- `POST /api/tender-info/run` — 发起检索（开发中）
