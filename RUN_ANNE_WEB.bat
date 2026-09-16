@echo off
setlocal
cd /d "%~dp0"

echo ==============================================
echo   ANNE AI V1 - Web Tinker
echo ==============================================
echo Ollama is NOT used as the V1 cognitive engine.
echo Prefer START_ANNE.bat for first-run setup.
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] .venv bulunamadi. Once START_ANNE.bat calistirin.
    pause
    exit /b 1
)

if exist "anne_config.env" (
    for /f "usebackq tokens=1,* delims== eol=#" %%A in ("anne_config.env") do (
        if not "%%A"=="" if not "%%B"=="" if not defined %%A set "%%A=%%B"
    )
)

if "%ANNE_WEB_PROVIDER%"=="" set "ANNE_WEB_PROVIDER=openai"
if "%ANNE_WEB_PORT%"=="" set "ANNE_WEB_PORT=8000"
if "%ANNE_WEB_MAX_QUEUE%"=="" set "ANNE_WEB_MAX_QUEUE=32"

echo Provider: %ANNE_WEB_PROVIDER%
echo URL     : http://127.0.0.1:%ANNE_WEB_PORT%
echo.

".venv\Scripts\python.exe" -m uvicorn anne.api.web_tinker:app --host 127.0.0.1 --port %ANNE_WEB_PORT%
if errorlevel 1 (
    echo [ERROR] Web Tinker durdu.
    pause
)
