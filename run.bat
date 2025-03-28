@echo off
setlocal enabledelayedexpansion

echo ===================================================
echo Document AI Desensitization Tool Installation Script
echo ===================================================

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python not detected. Please install Python 3.10.9
    echo Opening Python download link...
    start https://mirrors.aliyun.com/python-release/windows/python-3.10.9-amd64.exe
    echo After installation, please run this script again
    pause
    exit /b 1
)

:: Check Python version
for /f "tokens=2" %%a in ('python --version 2^>^&1') do set "pyver=%%a"
echo Detected Python version: %pyver%

:: Check if virtual environment exists
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo Failed to create virtual environment. Please check your Python installation
        pause
        exit /b 1
    )
    echo Virtual environment created successfully
) else (
    echo Existing virtual environment detected
)

:: Activate virtual environment
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo Failed to activate virtual environment
    pause
    exit /b 1
)
echo Virtual environment activated

:: Check if dependencies are installed
set "need_install=0"
python -c "import modelscope" 2>nul || set "need_install=1"
python -c "import numpy" 2>nul || set "need_install=1"
python -c "import packaging" 2>nul || set "need_install=1"
python -c "import addict" 2>nul || set "need_install=1"
python -c "import datasets" 2>nul || set "need_install=1"
python -c "import torch" 2>nul || set "need_install=1"
python -c "import PIL" 2>nul || set "need_install=1"
python -c "import simplejson" 2>nul || set "need_install=1"
python -c "import sortedcontainers" 2>nul || set "need_install=1"
python -c "import PyQt5" 2>nul || set "need_install=1"
python -c "import magic_pdf" 2>nul || set "need_install=1"

if "%need_install%"=="1" (
    echo Installing dependencies...
    
    :: Try using Aliyun mirror
    echo Trying to install regular dependencies using Aliyun mirror...
    pip install -U pip -i https://mirrors.aliyun.com/pypi/simple/
    pip install modelscope numpy packaging addict "datasets==2.16.1" torch Pillow simplejson sortedcontainers PyQt5 -i https://mirrors.aliyun.com/pypi/simple/
    
    if %errorlevel% neq 0 (
        echo Aliyun mirror installation failed, trying Tsinghua mirror...
        pip install modelscope numpy packaging addict "datasets==2.16.1" torch Pillow simplejson sortedcontainers PyQt5 -i https://pypi.tuna.tsinghua.edu.cn/simple/
        
        if %errorlevel% neq 0 (
            echo Tsinghua mirror installation failed, trying default source...
            pip install modelscope numpy packaging addict "datasets==2.16.1" torch Pillow simplejson sortedcontainers PyQt5
            
            if %errorlevel% neq 0 (
                echo Failed to install dependencies. Please check your network connection
                pause
                exit /b 1
            )
        )
    )
    
    :: Install special dependency magic-pdf
    echo Installing special dependency magic-pdf...
    pip install -U "magic-pdf[full]" --extra-index-url https://wheels.myhloli.com -i https://mirrors.aliyun.com/pypi/simple
    
    if %errorlevel% neq 0 (
        echo Trying alternative method to install magic-pdf...
        pip install -U "magic-pdf[full]" --extra-index-url https://wheels.myhloli.com -i https://pypi.tuna.tsinghua.edu.cn/simple/
        
        if %errorlevel% neq 0 (
            echo Failed to install magic-pdf. Please install manually
            echo Recommended command: pip install -U "magic-pdf[full]" --extra-index-url https://wheels.myhloli.com
            pause
            exit /b 1
        )
    )
    
    echo Dependencies installation completed
) else (
    echo All dependencies are already installed
)

:: Launch the application
echo Launching application...
python Data_Masking/ui/gui_app.py

:: If application exits abnormally, keep the window open
if %errorlevel% neq 0 (
    echo Application exited abnormally with error code: %errorlevel%
    pause
)

:: Deactivate virtual environment
call venv\Scripts\deactivate.bat
echo Virtual environment deactivated

pause