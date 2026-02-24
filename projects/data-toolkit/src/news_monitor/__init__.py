"""
新闻监控模块 - News Monitor Module

功能：
1. 关键词抓取新闻
2. 自动生成日报
3. 简单情感分析

使用示例：
    from src.news_monitor.monitor import NewsMonitor
    
    monitor = NewsMonitor()
    monitor.add_keyword("人工智能")
    monitor.run()
"""

from .monitor import NewsMonitor
from .article import Article
from .sentiment_analyzer import SentimentAnalyzer
from .report_generator import ReportGenerator

__all__ = ["NewsMonitor", "Article", "SentimentAnalyzer", "ReportGenerator"]