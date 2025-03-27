@echo off
chcp 936 >nul
setlocal enabledelayedexpansion

:: ===== CONFIGURATION =====
set PYTHON_URL=https://mirrors.aliyun.com/python-release/windows/python-3.10.9-amd64.exe
set VENV_DIR=venv
set APP_ENTRY=Data_Masking\ui\gui_app.py

:: Mirror settings
set PRIMARY_SOURCE=https://pypi.tuna.tsinghua.edu.cn/simple
set SECONDARY_SOURCE=https://mirrors.aliyun.com/pypi/simple
set MAGIC_PDF_SOURCE=https://wheels.myhloli.com
:: ========================

:: Check Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found!
    echo Please download from:
    echo %PYTHON_URL%
    echo Remember to check "Add Python to PATH"
    timeout /t 15
    start "" "%PYTHON_URL%"
    exit /b 1
)

:: Show Python version
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PY_VER=%%v
echo Detected Python: !PY_VER!

:: Create virtual environment
if not exist "%VENV_DIR%\" (
    echo Creating virtual environment...
    python -m venv "%VENV_DIR%"
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create venv
        pause
        exit /b 1
    )
)

:: Activate venv
call "%VENV_DIR%\Scripts\activate.bat"
if %errorlevel% neq 0 (
    echo [ERROR] Failed to activate venv
    pause
    exit /b 1
)

:: Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip --index-url="%PRIMARY_SOURCE%" --retries 3 --timeout 60
if %errorlevel% neq 0 (
    echo [WARNING] Retrying with secondary mirror...
    python -m pip install --upgrade pip --index-url="%SECONDARY_SOURCE%" --retries 2 --timeout 90
)

:: Install dependencies
echo Installing dependencies...
call :install_deps numpy packaging addict simplejson sortedcontainers
call :install_deps datasets==2.16.1 torch Pillow PyQt5 pyinstaller

:: Install magic-pdf
echo Installing magic-pdf...
pip install -U "magic-pdf[full]" ^
    --extra-index-url="%MAGIC_PDF_SOURCE%" ^
    --index-url="%PRIMARY_SOURCE%" ^
    --retries 5 ^
    --timeout 600
if %errorlevel% neq 0 (
    echo [ERROR] magic-pdf installation failed!
    echo Possible solutions:
    echo 1. Check network connection to !MAGIC_PDF_SOURCE!
    echo 2. Disable firewall temporarily
    pause
    exit /b 1
)

:: Verify installation
pip list --format=columns | findstr /i "magic-pdf torch"

:: Launch application
if exist "%APP_ENTRY%" (
    echo Starting application...
    python "%APP_ENTRY%"
) else (
    echo [ERROR] App entry not found: %APP_ENTRY%
    echo Directory listing:
    dir /b "%cd%\Data_Masking\ui\*.py"
    pause
)
exit /b

:: ===== FUNCTIONS =====
:install_deps
echo Installing: %*
pip install %* ^
    --index-url="%PRIMARY_SOURCE%" ^
    --retries 3 ^
    --timeout 120
if %errorlevel% neq 0 (
    echo [WARNING] Retrying with secondary mirror...
    pip install %* ^
        --index-url="%SECONDARY_SOURCE%" ^
        --retries 2 ^
        --timeout 180
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install: %*
        pause
        exit /b 1
    )
)
exit /b 0