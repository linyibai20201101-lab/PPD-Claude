@echo off
chcp 65001 >nul
REM Register Windows Task Scheduler: daily 08:00 agent report email
set "SCRIPT=%~dp0run_daily_report.bat"
schtasks /Create /TN "CcbabyAgentDailyReport" /TR "\"%SCRIPT%\"" /SC DAILY /ST 08:00 /F
if errorlevel 1 (
  echo Failed to create scheduled task. Try running as Administrator.
  exit /b 1
)
echo Created task CcbabyAgentDailyReport - runs daily at 08:00
schtasks /Query /TN "CcbabyAgentDailyReport" /FO LIST
