@echo off
setlocal
cd /d "%~dp0"

echo ==============================================
echo   ANNE AI - Windows Local Starter
 echo ==============================================

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python was not found in PATH.
    echo Install Python 3.12+ and enable "Add Python to PATH".
    pause
    exit /b 1
)

python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,12) else 1)"
if errorlevel 1 (
    echo [ERROR] ANNE requires Python 3.12 or newer.
    python --version
    pause
    exit /b 1
)

echo [1/4] Checking virtual environment...
if not exist ".venv\Scripts\python.exe" (
    echo [2/4] Creating .venv...
    python -m venv .venv
    if errorlevel 1 goto :fail
) else (
    echo [2/4] Existing .venv found.
)

echo [3/4] Installing ANNE in editable mode...
call ".venv\Scripts\python.exe" -m pip install -e ".[dev]"
if errorlevel 1 goto :fail

echo [4/4] Starting ANNE desktop...
echo.
".venv\Scripts\python.exe" -m anne.desktop
if errorlevel 1 goto :fail
exit /b 0

:fail
echo.
echo [ERROR] ANNE could not be started.
echo See the message above for the failing step.
pause
exit /b 1
