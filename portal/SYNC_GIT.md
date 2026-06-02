# Portal 独立 Git 仓库说明

## 本地独立副本

完整可推送的独立项目在：

```
E:\ccbaby-portal
```

已执行 `git init`、首次提交（约 301 个源码文件），**未包含**运行时数据（`tender_raw_data/`、抓取截图、`.env` 等）。

## 推送到 GitHub（首次）

1. 在 GitHub 组织 `linyibai20201101-lab` 下新建**空仓库**，名称建议：`ccbaby-portal`（不要勾选 README）。
2. 在本机执行：

```powershell
cd E:\ccbaby-portal
git remote set-url origin git@github.com:linyibai20201101-lab/ccbaby-portal.git
git push -u origin main
```

若使用 HTTPS：

```powershell
git remote set-url origin https://github.com/linyibai20201101-lab/ccbaby-portal.git
git push -u origin main
```

## 日常同步

```powershell
cd E:\ccbaby-portal
# 从 monorepo 同步最新 portal 源码（排除运行时目录）后：
git add -A
git commit -m "你的提交说明"
git push
```

从 `E:\ccbaby\portal` 更新到独立仓库可用 robocopy（勿覆盖 `.git`）：

```powershell
robocopy E:\ccbaby\portal E:\ccbaby-portal /E /XD __pycache__ .git .venv venv /XF .env
```

## 与 monorepo 的关系

- `E:\ccbaby` → 原仓库 `PPD-Claude`，`portal/` 为子目录
- `E:\ccbaby-portal` → 仅 Portal 的独立仓库根目录
