@echo off
cd /d "%~dp0"
set "PATH=C:\Program Files\nodejs;%PATH%"

python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found. Install from https://www.python.org/downloads/
    pause
    exit /b 1
)

pip show fastapi >nul 2>&1
if errorlevel 1 (
    pip install -r requirements.txt
)

echo Starting portal at http://localhost:8080
start "" "http://localhost:8080"
python server.py
pause
