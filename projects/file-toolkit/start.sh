#!/bin/bash
# File Toolkit 启动脚本
# File Toolkit Launcher Script

cd "$(dirname "$0")"

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 Python3，请先安装 Python 3.7+"
    echo "Error: Python3 not found. Please install Python 3.7+"
    exit 1
fi

# 安装依赖（如果需要）
if [ "$1" == "--install" ]; then
    echo "正在安装依赖..."
    pip3 install -r requirements.txt
    exit 0
fi

# 启动 GUI
echo "正在启动文件处理工具箱..."
echo "Starting File Toolkit..."
python3 gui.py
