@echo off
chcp 65001 >nul
title 安装 Git for Windows
echo.
echo 正在打开 Git for Windows 下载页面...
echo 请下载并安装，安装时保持默认选项即可。
echo 安装完成后重新运行 run-claude.bat
echo.
start https://git-scm.com/download/win
echo.
echo 如果 Git 已安装到默认路径，安装完成后可直接关闭本窗口。
pause
