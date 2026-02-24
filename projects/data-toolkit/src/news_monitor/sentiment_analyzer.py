"""
情感分析器 - Sentiment Analyzer

基于关键词匹配的简单情感分析
可用于快速判断文本情感倾向
"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """
    情感分析器
    
    使用简单的关键词匹配进行情感分析
    适用于快速分析，如需精确分析建议使用专业NLP库
    
    Attributes:
        positive_words: 正面词列表
        negative_words: 负面词列表
    """
    
    # 默认正面词 / Default positive words
    DEFAULT_POSITIVE = [
        "增长", "突破", "成功", "创新", "利好", "优秀", "领先",
        "提升", "改善", "繁荣", "积极", "满意", "赞", "好消息",
        "growth", "breakthrough", "success", "innovation", "positive",
        "improve", "excellent", "leading", "boost", "prosperity"
    ]
    
    # 默认负面词 / Default negative words
    DEFAULT_NEGATIVE = [
        "下降", "亏损", "失败", "危机", "风险", "问题", "担忧",
        "负面", "恶化", "困难", "挑战", "不利", "批评", "坏消息",
        "decline", "loss", "failure", "crisis", "risk", "negative",
        "worsen", "difficult", "challenge", "criticism", "bad"
    ]
    
    def __init__(self, positive_words: List[str] = None, 
                 negative_words: List[str] = None):
        """
        初始化情感分析器
        
        Args:
            positive_words: 自定义正面词列表
            negative_words: 自定义负面词列表
        """
        self.positive_words = positive_words or self.DEFAULT_POSITIVE
        self.negative_words = negative_words or self.DEFAULT_NEGATIVE
        
        logger.info(f"SentimentAnalyzer initialized with "
                   f"{len(self.positive_words)} positive words, "
                   f"{len(self.negative_words)} negative words")
    
    def analyze(self, text: str) -> Dict:
        """
        分析文本情感
        
        Args:
            text: 待分析的文本
            
        Returns:
            包含情感结果的字典
            {
                'sentiment': 'positive'/'negative'/'neutral',
                'score': 情感分数 (-1 到 1),
                'positive_count': 正面词数量,
                'negative_count': 负面词数量
            }
        """
        if not text:
            return {
                'sentiment': 'neutral',
                'score': 0.0,
                'positive_count': 0,
                'negative_count': 0
            }
        
        text_lower = text.lower()
        
        # 统计词频
        positive_count = sum(1 for word in self.positive_words 
                           if word.lower() in text_lower)
        negative_count = sum(1 for word in self.negative_words 
                           if word.lower() in text_lower)
        
        # 计算情感分数
        total = positive_count + negative_count
        if total == 0:
            sentiment = 'neutral'
            score = 0.0
        else:
            score = (positive_count - negative_count) / total
            if score > 0.1:
                sentiment = 'positive'
            elif score < -0.1:
                sentiment = 'negative'
            else:
                sentiment = 'neutral'
        
        return {
            'sentiment': sentiment,
            'score': round(score, 3),
            'positive_count': positive_count,
            'negative_count': negative_count
        }
    
    def analyze_batch(self, texts: List[str]) -> List[Dict]:
        """
        批量分析文本情感
        
        Args:
            texts: 文本列表
            
        Returns:
            情感分析结果列表
        """
        return [self.analyze(text) for text in texts]
    
    def get_summary(self, results: List[Dict]) -> Dict:
        """
        获取批量分析汇总
        
        Args:
            results: 分析结果列表
            
        Returns:
            汇总统计
        """
        if not results:
            return {}
        
        total = len(results)
        positive = sum(1 for r in results if r['sentiment'] == 'positive')
        negative = sum(1 for r in results if r['sentiment'] == 'negative')
        neutral = sum(1 for r in results if r['sentiment'] == 'neutral')
        
        avg_score = sum(r['score'] for r in results) / total
        
        return {
            'total': total,
            'positive': positive,
            'negative': negative,
            'neutral': neutral,
            'positive_ratio': round(positive / total * 100, 2),
            'negative_ratio': round(negative / total * 100, 2),
            'neutral_ratio': round(neutral / total * 100, 2),
            'average_score': round(avg_score, 3)
        }