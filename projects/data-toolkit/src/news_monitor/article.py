"""
新闻文章数据模型 - Article Data Model

定义新闻文章的数据结构
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
import hashlib


@dataclass
class Article:
    """
    新闻文章类
    
    Attributes:
        title: 文章标题
        url: 文章链接
        source: 来源网站
        publish_time: 发布时间
        content: 文章内容摘要
        keywords: 匹配的关键词列表
        sentiment: 情感分析结果
    """
    title: str
    url: str
    source: str
    publish_time: Optional[datetime] = None
    content: str = ""
    keywords: List[str] = field(default_factory=list)
    sentiment: Optional[str] = None  # 'positive', 'negative', 'neutral'
    sentiment_score: float = 0.0
    
    def __post_init__(self):
        """初始化后处理"""
        if self.publish_time is None:
            self.publish_time = datetime.now()
    
    @property
    def id(self) -> str:
        """生成文章唯一ID"""
        return hashlib.md5(f"{self.title}{self.url}".encode()).hexdigest()[:12]
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "publish_time": self.publish_time.isoformat() if self.publish_time else None,
            "content": self.content[:200] + "..." if len(self.content) > 200 else self.content,
            "keywords": self.keywords,
            "sentiment": self.sentiment,
            "sentiment_score": self.sentiment_score
        }
    
    def __str__(self) -> str:
        return f"[{self.source}] {self.title}"