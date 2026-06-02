@echo off
setlocal
set "PORT=%PORTAL_PORT%"
if not defined PORT set "PORT=8080"
if not defined PORTAL_PYTHON set "PORTAL_PYTHON=python"
set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"

ping 127.0.0.1 -n 3 >nul

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%PORT% " ^| findstr LISTENING') do (
  taskkill /F /PID %%a >nul 2>&1
)

ping 127.0.0.1 -n 2 >nul
cd /d "%ROOT%"
start "" /D "%ROOT%" "%PORTAL_PYTHON%" server.py
