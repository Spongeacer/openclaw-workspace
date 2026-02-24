# Data Toolkit - 数据抓取工具集

[English Version Below](#data-toolkit---data-scraping-toolkit)

---

## 📋 项目简介

Data Toolkit 是一个实用的数据抓取与处理工具集，包含三个核心模块：

1. **电商价格监控** (`monitor.py`) - 监控商品价格变动，生成趋势图
2. **新闻舆情监控** (`news_monitor.py`) - 抓取关键词相关新闻，生成日报
3. **Excel数据处理** (`excel_processor.py`) - 自动化处理Excel表格

## ⚖️ 合规声明

**本工具仅用于抓取公开可访问的数据。**

使用本工具时，请遵守以下原则：

1. ✅ **遵守 robots.txt** - 尊重目标网站的爬虫协议
2. ✅ **遵守服务条款** - 遵循目标网站的使用条款
3. ✅ **数据保护法规** - 遵守适用的数据保护法规（如 GDPR、CCPA 等）
4. ✅ **访问频率限制** - 使用合理的请求间隔，避免对目标网站造成过大负载

**禁止用于：**

- ❌ 抓取非公开数据或需要登录的私有数据
- ❌ 绕过反爬虫机制
- ❌ 抓取个人隐私信息
- ❌ 对目标网站造成过大负载

**使用本工具即表示您同意仅将其用于合法、合规的目的。**

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置

复制 `config.yaml` 并根据需要修改配置：

```bash
cp config.yaml my_config.yaml
# 编辑 my_config.yaml
```

### 3. 运行

```bash
# 价格监控
python monitor.py

# 新闻监控
python news_monitor.py

# Excel处理
python excel_processor.py
```

## 📦 模块说明

### 1. 电商价格监控 (monitor.py)

监控多个商品价格，记录历史价格，生成趋势图。

**功能：**
- 支持多个商品URL配置
- 自动记录价格历史
- 价格变动提醒（超过阈值时）
- 生成价格趋势图
- 价格摘要报告

**配置示例：**
```yaml
products:
  - name: "商品名称"
    url: "https://example.com/product/123"
    enabled: true
    selectors:
      name: "h1.product-title"
      price: ".price .amount"
      currency: ".currency-symbol"
```

### 2. 新闻舆情监控 (news_monitor.py)

监控关键词相关新闻，自动生成日报。

**功能：**
- 支持 RSS 和网页抓取
- 关键词过滤
- 自动去重
- 生成日报报告
- 关键词趋势统计

**配置示例：**
```yaml
keywords:
  - 人工智能
  - AI
  - 机器学习

sources:
  - name: "科技新闻"
    type: rss
    url: "https://example.com/rss"
    enabled: true
```

### 3. Excel数据处理 (excel_processor.py)

自动化处理Excel表格，支持合并、清洗、报表生成。

**功能：**
- 读取多个Excel文件
- 合并多个表格
- 按关键联合并
- 数据清洗（去重、填充空值）
- 生成数据透视表
- 批量处理
- 多工作表导出

**使用示例：**
```python
from excel_processor import ExcelProcessor

processor = ExcelProcessor()

# 合并多个文件
merged = processor.merge_sheets(['file1.xlsx', 'file2.xlsx'])

# 创建透视表
pivot = processor.create_pivot_table(merged, values='销量', index='产品')

# 生成报表
processor.generate_report(merged, "report")
```

## 📁 项目结构

```
data-toolkit/
├── monitor.py           # 电商价格监控
├── news_monitor.py      # 新闻舆情监控
├── excel_processor.py   # Excel数据处理
├── config.yaml          # 配置文件模板
├── requirements.txt     # Python依赖
├── README.md           # 本文件
└── data/               # 数据存储目录
    ├── price/          # 价格数据
    ├── news/           # 新闻数据
    └── excel/          # Excel数据
```

## 🔧 配置说明

所有模块共享 `config.yaml` 配置文件：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `data_dir` | 数据存储目录 | `data` |
| `output_dir` | 输出目录 | `output` |
| `headers` | HTTP请求头 | - |
| `price_threshold` | 价格变化阈值 | `0.05` |
| `products` | 监控商品列表 | `[]` |
| `keywords` | 监控关键词列表 | `[]` |
| `sources` | 新闻源配置 | `[]` |

## 📝 注意事项

1. **选择器配置** - 不同网站的HTML结构不同，需要根据实际网站调整CSS选择器
2. **请求频率** - 建议设置适当的延迟，避免被封禁
3. **数据备份** - 定期备份 `data/` 目录中的重要数据

## 📄 许可证

MIT License - 详见 LICENSE 文件

---

# Data Toolkit - Data Scraping Toolkit

## 📋 Overview

Data Toolkit is a practical data scraping and processing toolkit with three core modules:

1. **E-commerce Price Monitor** (`monitor.py`) - Monitor product prices and generate trend charts
2. **News Monitor** (`news_monitor.py`) - Scrape keyword-related news and generate daily reports
3. **Excel Processor** (`excel_processor.py`) - Automate Excel data processing

## ⚖️ Compliance Statement

**This tool is for scraping publicly accessible data only.**

When using this tool, please comply with:

1. ✅ **robots.txt** - Respect the target website's robots.txt rules
2. ✅ **Terms of Service** - Follow the target website's Terms of Service
3. ✅ **Data Protection** - Comply with applicable data protection regulations (GDPR, CCPA, etc.)
4. ✅ **Rate Limiting** - Use reasonable request intervals to avoid excessive load

**Prohibited uses:**

- ❌ Scraping non-public or private data requiring login
- ❌ Bypassing anti-scraping mechanisms
- ❌ Scraping personal private information
- ❌ Causing excessive load on target websites

**By using this tool, you agree to use it only for legal and compliant purposes.**

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configuration

Copy `config.yaml` and modify as needed:

```bash
cp config.yaml my_config.yaml
# Edit my_config.yaml
```

### 3. Run

```bash
# Price monitoring
python monitor.py

# News monitoring
python news_monitor.py

# Excel processing
python excel_processor.py
```

## 📦 Module Documentation

### 1. Price Monitor (monitor.py)

Monitor multiple product prices, record history, and generate trend charts.

**Features:**
- Support multiple product URL configuration
- Automatic price history recording
- Price change alerts (when exceeding threshold)
- Generate price trend charts
- Price summary reports

**Configuration Example:**
```yaml
products:
  - name: "Product Name"
    url: "https://example.com/product/123"
    enabled: true
    selectors:
      name: "h1.product-title"
      price: ".price .amount"
      currency: ".currency-symbol"
```

### 2. News Monitor (news_monitor.py)

Monitor keyword-related news and auto-generate daily reports.

**Features:**
- Support RSS and web scraping
- Keyword filtering
- Automatic deduplication
- Generate daily reports
- Keyword trend statistics

**Configuration Example:**
```yaml
keywords:
  - Artificial Intelligence
  - AI
  - Machine Learning

sources:
  - name: "Tech News"
    type: rss
    url: "https://example.com/rss"
    enabled: true
```

### 3. Excel Processor (excel_processor.py)

Automate Excel data processing with merge, clean, and report generation.

**Features:**
- Read multiple Excel files
- Merge multiple sheets
- Merge by key columns
- Data cleaning (deduplication, fill NA)
- Generate pivot tables
- Batch processing
- Multi-sheet export

**Usage Example:**
```python
from excel_processor import ExcelProcessor

processor = ExcelProcessor()

# Merge multiple files
merged = processor.merge_sheets(['file1.xlsx', 'file2.xlsx'])

# Create pivot table
pivot = processor.create_pivot_table(merged, values='sales', index='product')

# Generate report
processor.generate_report(merged, "report")
```

## 📁 Project Structure

```
data-toolkit/
├── monitor.py           # E-commerce price monitor
├── news_monitor.py      # News monitor
├── excel_processor.py   # Excel processor
├── config.yaml          # Configuration template
├── requirements.txt     # Python dependencies
├── README.md           # This file
└── data/               # Data storage
    ├── price/          # Price data
    ├── news/           # News data
    └── excel/          # Excel data
```

## 🔧 Configuration

All modules share the `config.yaml` configuration file:

| Option | Description | Default |
|--------|-------------|---------|
| `data_dir` | Data storage directory | `data` |
| `output_dir` | Output directory | `output` |
| `headers` | HTTP request headers | - |
| `price_threshold` | Price change threshold | `0.05` |
| `products` | Products to monitor | `[]` |
| `keywords` | Keywords to monitor | `[]` |
| `sources` | News sources | `[]` |

## 📝 Notes

1. **Selector Configuration** - Different websites have different HTML structures; adjust CSS selectors accordingly
2. **Request Frequency** - Set appropriate delays to avoid being blocked
3. **Data Backup** - Regularly backup important data in the `data/` directory

## 📄 License

MIT License - See LICENSE file
