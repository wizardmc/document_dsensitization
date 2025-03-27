@echo off
setlocal enabledelayedexpansion

:: ================= 配置区 =================
set PYTHON_MIN_VERSION=3.8  :: 最低要求版本
set PYTHON_RECOMMENDED_URL=https://mirrors.aliyun.com/python-release/windows/python-3.10.9-amd64.exe
set VENV_DIR=venv
set APP_ENTRY=Data_Masking/ui/gui_app.py

:: 定义依赖源（阿里云标准源 + myhloli私有源）
set DEFAULT_INDEX_URL=https://mirrors.aliyun.com/pypi/simple
set MAGIC_PDF_EXTRA_INDEX=https://wheels.myhloli.com
:: =========================================

:: 检测Python主环境
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python未安装
    echo 请下载推荐版本: %PYTHON_RECOMMENDED_URL%
    echo 安装时务必勾选 "Add Python to PATH"
    timeout /t 5
    start "" "%PYTHON_RECOMMENDED_URL%"
    exit /b 1
)

:: 验证Python版本
for /f "tokens=2 delims==" %%v in ('python -c "import sys; print(sys.version.split()[0])"') do (
    set PYTHON_VERSION=%%v
)
echo 检测到Python版本: !PYTHON_VERSION!

:: 创建/激活虚拟环境
if not exist "%VENV_DIR%\" (
    echo 正在创建虚拟环境...
    python -m venv "%VENV_DIR%"
    if %errorlevel% neq 0 (
        echo [ERROR] 虚拟环境创建失败
        pause
        exit /b 1
    )
)
call "%VENV_DIR%\Scripts\activate.bat"

:: ===== 分源安装依赖 =====
echo 正在安装基础依赖（阿里云源）...
pip install ^
    modelscope ^
    numpy ^
    packaging ^
    addict ^
    datasets==2.16.1 ^
    torch ^
    Pillow ^
    simplejson ^
    sortedcontainers ^
    PyQt5 ^
    pyinstaller ^
    --index-url "%DEFAULT_INDEX_URL%" ^
    --trusted-host mirrors.aliyun.com

if %errorlevel% neq 0 (
    echo [ERROR] 基础依赖安装失败
    pause
    exit /b 1
)

echo 正在安装magic-pdf（强制myhloli源）...
pip install -U "magic-pdf[full]" ^
    --extra-index-url "%MAGIC_PDF_EXTRA_INDEX%" ^
    --index-url "%DEFAULT_INDEX_URL%" ^
    --trusted-host wheels.myhloli.com

if %errorlevel% neq 0 (
    echo [ERROR] magic-pdf安装失败
    echo 请检查网络或私有源可用性
    pause
    exit /b 1
)

:: 启动应用
if exist "%APP_ENTRY%" (
    echo 正在启动应用...
    python "%APP_ENTRY%"
) else (
    echo [ERROR] 应用入口不存在: %APP_ENTRY%
    dir /s /b Data_Masking\*.py
    pause
)