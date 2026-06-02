#!/bin/bash
# 剑鱼标讯抓取环境安装脚本
# 运行方式：bash scripts/setup_crawler.sh

PYTHON="C:/Users/zenglb/.workbuddy/binaries/python/versions/3.13.12/python.exe"
VENV_DIR="C:/Users/zenglb/.workbuddy/binaries/python/envs/tender"

echo "=== 剑鱼标讯爬虫环境安装 ==="

# 创建虚拟环境
echo "1/3 创建Python虚拟环境..."
"$PYTHON" -m venv "$VENV_DIR"

# 安装依赖
echo "2/3 安装依赖包..."
"$VENV_DIR/Scripts/pip.exe" install playwright pandas openpyxl

# 安装Playwright浏览器
echo "3/3 安装Playwright浏览器（Chromium）..."
"$VENV_DIR/Scripts/python.exe" -m playwright install chromium

echo ""
echo "✅ 安装完成！"
echo ""
echo "使用方式："
echo "  首次探测页面结构："
echo "    $VENV_DIR/Scripts/python.exe scripts/probe_jianyu.py"
echo ""
echo "  抓取标书数据："
echo "    $VENV_DIR/Scripts/python.exe scripts/jianyu_crawler.py 工业相机 -u 手机号 -p 密码"
echo ""
echo "  使用已保存的登录态（无需重新登录）："
echo "    $VENV_DIR/Scripts/python.exe scripts/jianyu_crawler.py 工业相机"
echo "    （会自动读取 tender_raw_data/auth_state.json）"
