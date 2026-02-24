@echo off
chcp 65001 >nul
REM File Toolkit 启动脚本 (Windows)
REM File Toolkit Launcher Script (Windows)

cd /d "%~dp0"

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到 Python，请先安装 Python 3.7+
    echo Error: Python not found. Please install Python 3.7+
    pause
    exit /b 1
)

REM 安装依赖
if "%1"=="--install" (
    echo 正在安装依赖...
    pip install -r requirements.txt
    pause
    exit /b 0
)

REM 启动 GUI
echo 正在启动文件处理工具箱...
echo Starting File Toolkit...
python gui.py

pause
