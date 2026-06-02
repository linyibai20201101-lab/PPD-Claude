@echo off
chcp 65001 >nul
cd /d "%~dp0.."
python scripts\daily_agent_report.py --send
if errorlevel 1 (
  echo Email send failed. Report saved to reports\daily\latest.md
  exit /b 1
)
