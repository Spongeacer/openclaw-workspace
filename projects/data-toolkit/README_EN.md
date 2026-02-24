# Data Toolkit - Data Scraping & Processing Toolkit

A Python sample project for data scraping, monitoring, and processing, demonstrating automation capabilities and best practices.

## Features

### 1. E-commerce Price Monitor (price_monitor/)
- Scrape product historical price data
- Generate price trend charts
- Support price alert notifications

### 2. News/Sentiment Monitor (news_monitor/)
- Keyword-based news scraping
- Auto-generate daily reports
- Sentiment analysis support

### 3. Excel Data Processor (excel_processor/)
- Merge multiple sheets
- Auto-generate reports
- Data cleaning and formatting

## Project Structure

```
data-toolkit/
├── config/                 # Configuration directory
│   ├── config.yaml        # Main configuration file
│   └── .env.example       # Environment variables example
├── src/                   # Source code directory
│   ├── __init__.py
│   ├── price_monitor/     # Price monitoring module
│   ├── news_monitor/      # News monitoring module
│   └── excel_processor/   # Excel processing module
├── data/                  # Data directory
│   ├── raw/              # Raw data
│   └── processed/        # Processed data
├── output/               # Output directory
│   ├── charts/          # Chart outputs
│   └── reports/         # Report outputs
├── tests/               # Test directory
├── requirements.txt     # Dependencies
├── README.md           # Chinese documentation
└── README_EN.md        # English documentation
```

## Quick Start

### 1. Environment Setup

```bash
# Clone the project
git clone https://github.com/yourusername/data-toolkit.git
cd data-toolkit

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy environment variables example
cp config/.env.example config/.env

# Edit configuration files
# Modify parameters in config/config.yaml
# Modify sensitive info (e.g., API Keys) in config/.env
```

### 3. Run Examples

```bash
# Run price monitor demo
python -m src.price_monitor.demo

# Run news monitor demo
python -m src.news_monitor.demo

# Run Excel processor demo
python -m src.excel_processor.demo
```

## Compliance Statement

⚠️ **This project is for educational purposes only. All data scraping targets publicly available data:**

1. **Follow Robots.txt** - All scrapers respect target website's robots.txt rules
2. **Control Request Rate** - Built-in request intervals to avoid server pressure
3. **Public Data Only** - Do not scrape private data requiring login or payment
4. **Respect Copyright** - Scraped data is for personal learning only, not commercial use

When using this project, please comply with:
- Target website's Terms of Service
- Relevant laws and regulations
- Data privacy protection regulations

## Tech Stack

- Python 3.8+
- requests / aiohttp - HTTP requests
- BeautifulSoup4 / lxml - HTML parsing
- pandas - Data processing
- openpyxl - Excel operations
- matplotlib / plotly - Data visualization
- schedule - Scheduled tasks

## Contributing

Issues and Pull Requests are welcome!

## License

MIT License - See [LICENSE](LICENSE) file for details

## Contact

For questions or suggestions, please contact:
- GitHub Issues
- Email: your.email@example.com

---

**Disclaimer**: This project is for educational purposes only. Users assume all risks associated with its use.