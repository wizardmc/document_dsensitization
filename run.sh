#!/bin/bash

# 配置区 ===========================================
PYTHON_RECOMMENDED_VERSION="3.10"
PYTHON_DOWNLOAD_URL="https://www.python.org/downloads/"
VENV_DIR="venv"
REQUIREMENTS="requirements.txt"
APP_ENTRY="Data_Masking/ui/gui_app.py"
# ================================================

# 检测Python是否存在
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未检测到Python环境"
    echo "请安装Python ${PYTHON_RECOMMENDED_VERSION} 或更高版本"
    echo "下载链接: ${PYTHON_DOWNLOAD_URL}"
    echo "按任意键退出..."
    read -n 1
    open "${PYTHON_DOWNLOAD_URL}"
    exit 1
fi

# 显示当前Python版本（仅信息）
python3 --version
echo ""

# 虚拟环境管理
if [ ! -d "${VENV_DIR}" ]; then
    echo "正在创建虚拟环境..."
    python3 -m venv "${VENV_DIR}"
    if [ $? -ne 0 ]; then
        echo "[错误] 虚拟环境创建失败"
        read -p "按回车键继续..."
        exit 1
    fi
fi

# 激活虚拟环境
source "${VENV_DIR}/bin/activate"
if [ $? -ne 0 ]; then
    echo "[错误] 虚拟环境激活失败"
    read -p "按回车键继续..."
    exit 1
fi

# 智能依赖安装 ===================================
echo "正在检查依赖项..."

# 生成requirements.txt（如果不存在）
if [ ! -f "${REQUIREMENTS}" ]; then
    cat > "${REQUIREMENTS}" << EOF
modelscope
numpy
packaging
addict
datasets==2.16.1
torch
Pillow
simplejson
sortedcontainers
PyQt5
pyinstaller

--extra-index-url=https://wheels.myhloli.com
-i https://mirrors.aliyun.com/pypi/simple
magic-pdf[full]
EOF
fi

# 检查是否需要安装依赖
MISSING_DEPS=0
while IFS= read -r line || [[ -n "$line" ]]; do
    # 跳过空行和以-开头的行（如-i和--extra-index-url）
    if [[ -n "$line" && ! "$line" =~ ^- ]]; then
        # 提取包名（去除版本号）
        package=$(echo "$line" | cut -d'[' -f1 | cut -d'=' -f1 | xargs)
        if [[ -n "$package" ]]; then
            if ! pip show "$package" &> /dev/null; then
                echo "[未安装] $package"
                MISSING_DEPS=1
            fi
        fi
    fi
done < "${REQUIREMENTS}"

if [ $MISSING_DEPS -eq 1 ]; then
    echo "正在安装依赖项..."
    pip install -r "${REQUIREMENTS}"
    if [ $? -ne 0 ]; then
        echo "[错误] 依赖安装失败"
        read -p "按回车键继续..."
        exit 1
    fi
else
    echo "所有依赖已安装"
fi

# 启动应用 =======================================
if [ -f "${APP_ENTRY}" ]; then
    echo "正在启动应用程序..."
    python "${APP_ENTRY}"
else
    echo "[错误] 应用程序入口不存在: ${APP_ENTRY}"
    echo "预期路径: $(pwd)/${APP_ENTRY}"
fi

read -p "按回车键继续..."