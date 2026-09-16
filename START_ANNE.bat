@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ==============================================
echo   ANNE AI V1 - One-Click Windows Starter
echo ==============================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python bulunamadi. Python 3.12+ kurun ve "Add to PATH" secin.
    pause
    exit /b 1
)

python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,12) else 1)"
if errorlevel 1 (
    echo [ERROR] ANNE Python 3.12+ ister.
    python --version
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [SETUP] Sanal ortam olusturuluyor...
    python -m venv .venv
    if errorlevel 1 goto :fail
)

echo [SETUP] Bagimliliklar kontrol ediliyor...
".venv\Scripts\python.exe" -m pip install -q -U pip
".venv\Scripts\python.exe" -m pip install -q -e ".[api]"
if errorlevel 1 (
    echo [WARN] pip install -e ".[api]" basarisiz, dev extras denenecek...
    ".venv\Scripts\python.exe" -m pip install -q -e ".[dev]"
    if errorlevel 1 goto :fail
)

if not exist "anne_config.env" (
    if exist "anne_config.env.example" (
        copy /Y "anne_config.env.example" "anne_config.env" >nul
        echo [SETUP] anne_config.env olusturuldu. API anahtarlarini duzenleyin.
    )
)

echo [SETUP] ANNE Self-Setup calisiyor...
".venv\Scripts\python.exe" -m anne.setup.self_setup

if not exist "anne_config.env" (
    echo.
    echo [ERROR] anne_config.env yok. Ornek dosyadan kopyalayip OPENAI_API_KEY veya XAI_API_KEY girin.
    pause
    exit /b 1
)

for /f "usebackq tokens=1,* delims== eol=#" %%A in ("anne_config.env") do (
    if not "%%A"=="" if not "%%B"=="" if not defined %%A set "%%A=%%B"
)

if "%ANNE_WEB_PROVIDER%"=="" set "ANNE_WEB_PROVIDER=openai"
if "%ANNE_WEB_PORT%"=="" set "ANNE_WEB_PORT=8000"
if "%ANNE_WEB_DB%"=="" set "ANNE_WEB_DB=anne_data\anne_web.db"
if "%ANNE_WEB_MAX_QUEUE%"=="" set "ANNE_WEB_MAX_QUEUE=32"
set "ANNE_GITHUB_REGISTER=1"
if "%ANNE_VERSION%"=="" set "ANNE_VERSION=0.1.0"

echo [SETUP] Optional GitHub installation registration...
".venv\Scripts\python.exe" -m anne.setup.installation_registration
if errorlevel 1 (
    echo [WARN] GitHub registration skipped; ANNE continues normally.
)

echo.
echo Provider : %ANNE_WEB_PROVIDER%
echo Port     : %ANNE_WEB_PORT%
echo Memory   : %ANNE_WEB_DB%
echo.
echo Chrome: http://127.0.0.1:%ANNE_WEB_PORT%
echo.

start "" cmd /c "timeout /t 3 /nobreak >nul && start http://127.0.0.1:%ANNE_WEB_PORT%/"

echo [RUN] ANNE Web Interface baslatiliyor...
".venv\Scripts\python.exe" -m uvicorn anne.api.web_tinker:app --host 127.0.0.1 --port %ANNE_WEB_PORT%
if errorlevel 1 goto :fail
exit /b 0

:fail
echo.
echo [ERROR] ANNE baslatilamadi. Yukaridaki mesaji kontrol edin.
pause
exit /b 1
