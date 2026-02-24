import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import yaml
import re
from collections import defaultdict


@dataclass
class NewsArticle:
    """新闻文章数据类"""
    title: str
    url: str
    source: str
    publish_time: str
    summary: str
    keywords: List[str]


class NewsMonitor:
    """新闻/舆情监控器 - 关键词抓取与日报生成"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self.data_dir = self.config.get('data_dir', 'data/news')
        self.history_file = os.path.join(self.data_dir, 'news_history.json')
        self._ensure_data_dir()
        self.news_history = self._load_history()
        
    def _load_config(self, path: str) -> dict:
        """加载配置文件"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"配置文件 {path} 未找到，使用默认配置")
            return self._default_config()
    
    def _default_config(self) -> dict:
        """默认配置"""
        return {
            'data_dir': 'data/news',
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0'
            },
            'keywords': ['科技', '人工智能', 'AI'],
            'sources': [
                {
                    'name': '示例新闻源',
                    'url': 'https://example.com/news',
                    'enabled': False  # 需要用户配置真实源
                }
            ],
            'max_articles_per_source': 10,
            'summary_length': 200
        }
    
    def _ensure_data_dir(self):
        """确保数据目录存在"""
        os.makedirs(self.data_dir, exist_ok=True)
    
    def _load_history(self) -> List[Dict]:
        """加载历史新闻"""
        if os.path.exists(self.history_file):
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def _save_history(self):
        """保存新闻历史"""
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(self.news_history, f, ensure_ascii=False, indent=2)
    
    def fetch_from_rss(self, rss_url: str) -> List[NewsArticle]:
        """
        从RSS源抓取新闻
        
        Args:
            rss_url: RSS订阅地址
            
        Returns:
            新闻文章列表
        """
        import feedparser
        
        articles = []
        try:
            feed = feedparser.parse(rss_url)
            
            for entry in feed.entries[:self.config.get('max_articles_per_source', 10)]:
                # 提取关键词
                content = f"{entry.get('title', '')} {entry.get('summary', '')}"
                keywords = self._extract_keywords(content)
                
                # 解析发布时间
                published = entry.get('published', '')
                if not published:
                    published = datetime.now().isoformat()
                
                article = NewsArticle(
                    title=entry.get('title', '无标题'),
                    url=entry.get('link', ''),
                    source=feed.feed.get('title', '未知来源'),
                    publish_time=published,
                    summary=entry.get('summary', '')[:self.config.get('summary_length', 200)],
                    keywords=keywords
                )
                articles.append(article)
                
        except Exception as e:
            print(f"RSS抓取失败 {rss_url}: {e}")
            
        return articles
    
    def fetch_from_web(self, url: str, selectors: Dict[str, str]) -> List[NewsArticle]:
        """
        从网页抓取新闻列表
        
        Args:
            url: 新闻列表页URL
            selectors: CSS选择器配置
                {
                    'container': '文章容器选择器',
                    'title': '标题选择器',
                    'link': '链接选择器',
                    'time': '时间选择器',
                    'summary': '摘要选择器'
                }
        
        Returns:
            新闻文章列表
        """
        headers = self.config.get('headers', {})
        articles = []
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            container_selector = selectors.get('container', 'article')
            containers = soup.select(container_selector)
            
            for container in containers[:self.config.get('max_articles_per_source', 10)]:
                try:
                    # 提取标题
                    title_elem = container.select_one(selectors.get('title', 'h2'))
                    title = title_elem.get_text(strip=True) if title_elem else "无标题"
                    
                    # 提取链接
                    link_elem = container.select_one(selectors.get('link', 'a'))
                    link = link_elem.get('href', '') if link_elem else ''
                    if link and not link.startswith('http'):
                        # 相对路径转绝对路径
                        from urllib.parse import urljoin
                        link = urljoin(url, link)
                    
                    # 提取时间
                    time_elem = container.select_one(selectors.get('time', 'time'))
                    publish_time = time_elem.get_text(strip=True) if time_elem else datetime.now().isoformat()
                    
                    # 提取摘要
                    summary_elem = container.select_one(selectors.get('summary', '.summary, .desc'))
                    summary = summary_elem.get_text(strip=True)[:self.config.get('summary_length', 200)] if summary_elem else ""
                    
                    # 提取关键词
                    keywords = self._extract_keywords(f"{title} {summary}")
                    
                    article = NewsArticle(
                        title=title,
                        url=link,
                        source=url,
                        publish_time=publish_time,
                        summary=summary,
                        keywords=keywords
                    )
                    articles.append(article)
                    
                except Exception as e:
                    continue
                    
        except requests.RequestException as e:
            print(f"请求失败 {url}: {e}")
            
        return articles
    
    def _extract_keywords(self, text: str) -> List[str]:
        """从文本中提取匹配的关键词"""
        monitor_keywords = self.config.get('keywords', [])
        found_keywords = []
        
        text_lower = text.lower()
        for keyword in monitor_keywords:
            if keyword.lower() in text_lower:
                found_keywords.append(keyword)
                
        return found_keywords
    
    def filter_by_keywords(self, articles: List[NewsArticle]) -> List[NewsArticle]:
        """根据关键词过滤文章"""
        keywords = self.config.get('keywords', [])
        if not keywords:
            return articles
            
        filtered = []
        for article in articles:
            if article.keywords:  # 文章包含至少一个监控关键词
                filtered.append(article)
                
        return filtered
    
    def is_duplicate(self, article: NewsArticle) -> bool:
        """检查文章是否已存在"""
        for history in self.news_history:
            if history['url'] == article.url:
                return True
            # 标题相似度检查（简单实现）
            if self._title_similarity(history['title'], article.title) > 0.8:
                return True
        return False
    
    def _title_similarity(self, title1: str, title2: str) -> float:
        """计算标题相似度（简单实现）"""
        # 使用简单的字符集合相似度
        set1 = set(title1.lower())
        set2 = set(title2.lower())
        if not set1 or not set2:
            return 0.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0
    
    def collect_news(self) -> List[NewsArticle]:
        """收集所有配置源的新闻"""
        all_articles = []
        sources = self.config.get('sources', [])
        
        for source in sources:
            if not source.get('enabled', True):
                continue
                
            source_type = source.get('type', 'web')
            url = source.get('url')
            
            if not url:
                continue
                
            print(f"正在抓取: {source.get('name', url)}")
            
            if source_type == 'rss':
                articles = self.fetch_from_rss(url)
            else:
                selectors = source.get('selectors', {})
                articles = self.fetch_from_web(url, selectors)
            
            # 关键词过滤
            articles = self.filter_by_keywords(articles)
            
            # 去重
            new_articles = [a for a in articles if not self.is_duplicate(a)]
            
            print(f"  找到 {len(articles)} 篇相关文章，{len(new_articles)} 篇新文章")
            all_articles.extend(new_articles)
        
        # 保存到历史
        for article in all_articles:
            self.news_history.append(asdict(article))
        
        # 限制历史记录数量
        max_history = self.config.get('max_history', 1000)
        self.news_history = self.news_history[-max_history:]
        self._save_history()
        
        return all_articles
    
    def generate_daily_report(self, date: datetime = None) -> str:
        """
        生成日报
        
        Args:
            date: 指定日期，None则使用今天
            
        Returns:
            日报文本
        """
        if date is None:
            date = datetime.now()
        
        # 获取当天的文章
        date_str = date.strftime('%Y-%m-%d')
        day_articles = []
        
        for article in self.news_history:
            try:
                article_date = article['publish_time'][:10]  # 提取日期部分
                if article_date == date_str:
                    day_articles.append(article)
            except:
                continue
        
        # 按关键词分组统计
        keyword_stats = defaultdict(int)
        for article in day_articles:
            for kw in article.get('keywords', []):
                keyword_stats[kw] += 1
        
        # 生成报告
        lines = [
            "=" * 60,
            f"📰 舆情监控日报 - {date_str}",
            "=" * 60,
            "",
            f"📊 今日共监控到 {len(day_articles)} 篇相关文章",
            "",
            "🔍 关键词热度:",
        ]
        
        for kw, count in sorted(keyword_stats.items(), key=lambda x: -x[1]):
            lines.append(f"   • {kw}: {count} 篇")
        
        lines.extend(["", "📋 文章列表:", "-" * 60])
        
        for i, article in enumerate(day_articles[:20], 1):  # 最多显示20篇
            lines.extend([
                f"\n{i}. {article['title']}",
                f"   来源: {article['source']}",
                f"   关键词: {', '.join(article.get('keywords', []))}",
                f"   链接: {article['url']}",
            ])
            if article.get('summary'):
                lines.append(f"   摘要: {article['summary'][:100]}...")
        
        if len(day_articles) > 20:
            lines.append(f"\n... 还有 {len(day_articles) - 20} 篇文章未显示")
        
        lines.extend(["", "=" * 60, "报告生成时间: " + datetime.now().isoformat()])
        
        return "\n".join(lines)
    
    def save_daily_report(self, date: datetime = None):
        """保存日报到文件"""
        report = self.generate_daily_report(date)
        
        if date is None:
            date = datetime.now()
        
        filename = f"daily_report_{date.strftime('%Y%m%d')}.txt"
        filepath = os.path.join(self.data_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"📄 日报已保存: {filepath}")
        return filepath
    
    def get_keyword_trend(self, days: int = 7) -> Dict[str, List[int]]:
        """
        获取关键词趋势
        
        Args:
            days: 统计最近N天
            
        Returns:
            关键词 -> 每日数量列表
        """
        keywords = self.config.get('keywords', [])
        trend = {kw: [0] * days for kw in keywords}
        
        today = datetime.now().date()
        
        for article in self.news_history:
            try:
                article_date = datetime.fromisoformat(article['publish_time'].replace('Z', '+00:00').replace('+00:00', '')).date()
                day_diff = (today - article_date).days
                
                if 0 <= day_diff < days:
                    for kw in article.get('keywords', []):
                        if kw in trend:
                            trend[kw][days - 1 - day_diff] += 1
            except:
                continue
        
        return trend


def main():
    """主函数"""
    monitor = NewsMonitor()
    
    print("🔍 开始新闻监控...")
    articles = monitor.collect_news()
    
    print(f"\n✅ 成功收集 {len(articles)} 篇新文章")
    
    # 生成日报
    print("\n📄 生成日报...")
    report_path = monitor.save_daily_report()
    
    # 打印摘要
    print("\n" + monitor.generate_daily_report())
    
    # 显示关键词趋势
    print("\n📈 关键词趋势（最近7天）:")
    trend = monitor.get_keyword_trend(7)
    for kw, counts in trend.items():
        print(f"   {kw}: {' '.join(str(c) for c in counts)}")


if __name__ == "__main__":
    main()
