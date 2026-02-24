# File Toolkit - 文件处理工具箱

一个简单易用的文件批量处理工具，支持重命名、图片处理、文件整理、压缩解压等功能。

## 功能特性

- 📝 **批量重命名** - 支持按序号、日期、正则表达式重命名
- 🖼️ **图片处理** - 格式转换、尺寸调整
- 📂 **文件整理** - 按日期或类型自动分类文件
- 📦 **压缩解压** - 支持 ZIP、TAR 等多种格式

## 安装

### 环境要求

- Python 3.7+
- Windows / macOS / Linux

### 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方式

### 1. 图形界面（推荐）

双击运行或命令行启动：

```bash
python gui.py
```

界面简洁直观，适合非技术用户：
- 选择目录 → 设置选项 → 预览 → 执行

### 2. 命令行

```bash
# 批量重命名（按序号）
python cli.py rename sequence -d ./photos -p "vacation_" --start 1 --padding 3 --execute

# 批量转换图片格式
python cli.py image convert -d ./photos -f webp -q 90 --execute

# 按日期整理文件
python cli.py organize date -d ./downloads --format "%Y-%m" --execute

# 压缩文件
python cli.py archive compress -i ./folder -o output.zip

# 解压文件
python cli.py archive extract -i archive.zip -o ./output
```

## 详细功能说明

### 批量重命名

| 模式 | 说明 | 示例 |
|------|------|------|
| 按序号 | 添加数字序号 | file_001.jpg, file_002.jpg |
| 按日期 | 使用文件日期 | 20240224_153045.jpg |
| 正则替换 | 正则表达式替换 | 替换特定字符 |

### 图片处理

| 功能 | 说明 |
|------|------|
| 格式转换 | jpg ↔ png ↔ webp ↔ gif |
| 尺寸调整 | 按比例缩放或指定宽高 |

### 文件整理

| 方式 | 说明 |
|------|------|
| 按日期 | 按年月分类到不同文件夹 |
| 按类型 | 按文件类型分类（图片/视频/文档等）|

### 压缩解压

支持格式：ZIP、TAR、TAR.GZ、TAR.BZ2

---

# File Toolkit

A simple and easy-to-use file batch processing tool supporting rename, image processing, file organization, compression and decompression.

## Features

- 📝 **Batch Rename** - Support sequential, date-based, and regex renaming
- 🖼️ **Image Processing** - Format conversion, resize
- 📂 **File Organization** - Auto-organize files by date or type
- 📦 **Archive** - Support ZIP, TAR and more formats

## Installation

### Requirements

- Python 3.7+
- Windows / macOS / Linux

### Install Dependencies

```bash
pip install -r requirements.txt
```

## Usage

### 1. GUI (Recommended)

Double-click or run from command line:

```bash
python gui.py
```

Simple workflow: Select directory → Set options → Preview → Execute

### 2. Command Line

```bash
# Batch rename (sequential)
python cli.py rename sequence -d ./photos -p "vacation_" --start 1 --padding 3 --execute

# Batch convert images
python cli.py image convert -d ./photos -f webp -q 90 --execute

# Organize by date
python cli.py organize date -d ./downloads --format "%Y-%m" --execute

# Compress
python cli.py archive compress -i ./folder -o output.zip

# Extract
python cli.py archive extract -i archive.zip -o ./output
```

## Detailed Features

### Batch Rename

| Mode | Description | Example |
|------|-------------|---------|
| Sequential | Add number suffix | file_001.jpg, file_002.jpg |
| Date-based | Use file date | 20240224_153045.jpg |
| Regex | Pattern replacement | Replace specific characters |

### Image Processing

| Feature | Description |
|---------|-------------|
| Convert | jpg ↔ png ↔ webp ↔ gif |
| Resize | Scale by ratio or specify dimensions |

### File Organization

| Method | Description |
|--------|-------------|
| By Date | Organize by year/month folders |
| By Type | Organize by file type (Images/Videos/Documents) |

### Compression

Supported formats: ZIP, TAR, TAR.GZ, TAR.BZ2

## Project Structure

```
file-toolkit/
├── cli.py              # Command line interface
├── gui.py              # Graphical user interface
├── core.py             # Core functionality
├── requirements.txt    # Dependencies
├── config.example.json # Example configuration
└── README.md           # Documentation
```

## License

MIT License
