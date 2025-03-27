@echo off
setlocal enabledelayedexpansion

:: 配置区 ===========================================
set PYTHON_RECOMMENDED_VERSION=3.10.16
set PYTHON_DOWNLOAD_URL=https://www.python.org/ftp/python/3.10.16/python-3.10.16-amd64.exe
set VENV_DIR=venv
set REQUIREMENTS=requirements.txt
set APP_ENTRY=Data_Masking/ui/gui_app.py
:: ================================================

:: 检测Python是否存在
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到Python环境
    echo 请安装Python %PYTHON_RECOMMENDED_VERSION% 并确保勾选"Add to PATH"
    echo 下载链接: %PYTHON_DOWNLOAD_URL%
    echo 按任意键退出...
    pause >nul
    start "" "%PYTHON_DOWNLOAD_URL%"
    exit /b 1
)

:: 显示当前Python版本（仅信息）
python --version
echo.

:: 虚拟环境管理
if not exist "%VENV_DIR%\" (
    echo 正在创建虚拟环境...
    python -m venv "%VENV_DIR%"
    if %errorlevel% neq 0 (
        echo [错误] 虚拟环境创建失败
        pause
        exit /b 1
    )
)

:: 激活虚拟环境
call "%VENV_DIR%\Scripts\activate.bat"
if %errorlevel% neq 0 (
    echo [错误] 虚拟环境激活失败
    pause
    exit /b 1
)

:: 智能依赖安装 ===================================
echo 正在检查依赖项...

:: 生成requirements.txt（如果不存在）
if not exist "%REQUIREMENTS%" (
    (
        echo modelscope
        echo numpy
        echo packaging
        echo addict
        echo datasets==2.16.1
        echo torch
        echo Pillow
        echo simplejson
        echo sortedcontainers
        echo PyQt5
        echo pyinstaller
        echo.
        echo --extra-index-url=https://wheels.myhloli.com
        echo -i https://mirrors.aliyun.com/pypi/simple
        echo magic-pdf[full]
    ) > "%REQUIREMENTS%"
)

:: 检查是否需要安装依赖
set MISSING_DEPS=0
for /f "tokens=1 delims==" %%p in (%REQUIREMENTS%) do (
    if "%%p" neq "" (
        if /i "%%p" neq "--extra-index-url" (
            if /i "%%p" neq "-i" (
                pip show "%%p" >nul 2>&1
                if %errorlevel% neq 0 (
                    echo [未安装] %%p
                    set MISSING_DEPS=1
                )
            )
        )
    )
)

if %MISSING_DEPS% equ 1 (
    echo 正在安装依赖项...
    pip install -r "%REQUIREMENTS%"
    if %errorlevel% neq 0 (
        echo [错误] 依赖安装失败
        pause
        exit /b 1
    )
) else (
    echo 所有依赖已安装
)

:: 启动应用 =======================================
if exist "%APP_ENTRY%" (
    echo 正在启动应用程序...
    python "%APP_ENTRY%"
) else (
    echo [错误] 应用程序入口不存在: %APP_ENTRY%
    echo 预期路径: %cd%\%APP_ENTRY%
)

pause