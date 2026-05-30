@echo off
chcp 65001 >nul
title Claude Code - ccbaby
cd /d "%~dp0"

set "PATH=C:\Program Files\nodejs;C:\Users\%USERNAME%\AppData\Roaming\npm;C:\Windows\System32;C:\Windows;%PATH%"
set "CLAUDE_CMD=%APPDATA%\npm\claude.cmd"

if not exist "%CLAUDE_CMD%" (
    echo [错误] 未找到 claude.cmd
    echo 请先运行: npm install -g @anthropic-ai/claude-code@latest
    pause
    exit /b 1
)

if exist "C:\Program Files\PowerShell\7\pwsh.exe" (
    "C:\Program Files\PowerShell\7\pwsh.exe" -NoExit -NoProfile -ExecutionPolicy Bypass -File "%~dp0run-claude.ps1"
    exit /b 0
)

set "GIT_BASH="
if exist "F:\Git\bin\bash.exe" set "GIT_BASH=F:\Git\bin\bash.exe"
if exist "C:\Program Files\Git\bin\bash.exe" set "GIT_BASH=C:\Program Files\Git\bin\bash.exe"
if exist "C:\Program Files (x86)\Git\bin\bash.exe" set "GIT_BASH=C:\Program Files (x86)\Git\bin\bash.exe"

if defined GIT_BASH (
    set "CLAUDE_CODE_GIT_BASH_PATH=%GIT_BASH%"
    call "%CLAUDE_CMD%"
    if errorlevel 1 pause
    exit /b 0
)

echo.
echo ========================================
echo   Claude Code 缺少运行依赖
echo ========================================
echo.
echo Claude Code 在 Windows 上需要以下之一:
echo   1. Git for Windows  ^(推荐^)
echo   2. PowerShell 7
echo.
echo 请双击运行 install-git.bat 安装 Git，
echo 或手动下载:
echo   https://git-scm.com/download/win
echo.
echo 安装完成后重新运行本脚本即可。
echo.
pause
exit /b 1
