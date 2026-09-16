@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo ANNE is not installed yet.
    echo Run START_ANNE.bat once first.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m anne.desktop
if errorlevel 1 (
    echo.
    echo [ERROR] ANNE stopped with an error.
    pause
    exit /b 1
)
