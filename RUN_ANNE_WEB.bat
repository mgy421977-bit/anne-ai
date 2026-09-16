@echo off
setlocal
cd /d "%~dp0"

echo ==============================================
echo   ANNE AI - Laptop Web Tinker
 echo ==============================================

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] .venv not found. Run START_ANNE.bat first.
    pause
    exit /b 1
)

if "%ANNE_LOCAL_BACKEND%"=="" set "ANNE_LOCAL_BACKEND=ollama"
if "%ANNE_LOCAL_MODEL%"=="" set "ANNE_LOCAL_MODEL=qwen2.5:3b"
if "%ANNE_WEB_MAX_QUEUE%"=="" set "ANNE_WEB_MAX_QUEUE=32"

 echo Backend: %ANNE_LOCAL_BACKEND%
 echo Model  : %ANNE_LOCAL_MODEL%
 echo Queue  : %ANNE_WEB_MAX_QUEUE%
 echo.
echo Web Tinker: http://127.0.0.1:8000
 echo LAN access is intentionally not enabled by default.
echo.

".venv\Scripts\python.exe" -m uvicorn anne.api.web_tinker:app --host 127.0.0.1 --port 8000
if errorlevel 1 (
    echo.
    echo [ERROR] Web Tinker stopped.
    pause
)
