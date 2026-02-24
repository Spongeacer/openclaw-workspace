"""
商品数据模型 - Product Data Model

定义商品的数据结构，包括名称、URL、价格历史等信息
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class PricePoint:
    """
    价格数据点
    
    Attributes:
        price: 价格数值
        timestamp: 记录时间
        currency: 货币单位（默认CNY）
    """
    price: float
    timestamp: datetime = field(default_factory=datetime.now)
    currency: str = "CNY"
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "price": self.price,
            "timestamp": self.timestamp.isoformat(),
            "currency": self.currency
        }


@dataclass
class Product:
    """
    商品类
    
    存储商品的基本信息和价格历史
    
    Attributes:
        name: 商品名称
        url: 商品页面URL
        selector: 价格元素的CSS选择器
        alert_threshold: 价格预警阈值
        price_history: 价格历史记录
    """
    name: str
    url: str
    selector: str
    alert_threshold: Optional[float] = None
    price_history: List[PricePoint] = field(default_factory=list)
    
    def add_price(self, price: float, timestamp: Optional[datetime] = None) -> None:
        """
        添加价格记录
        
        Args:
            price: 当前价格
            timestamp: 记录时间，默认为当前时间
        """
        point = PricePoint(price=price, timestamp=timestamp or datetime.now())
        self.price_history.append(point)
    
    def get_current_price(self) -> Optional[float]:
        """获取当前（最新）价格"""
        if self.price_history:
            return self.price_history[-1].price
        return None
    
    def get_price_change(self) -> Optional[float]:
        """
        计算价格变化
        
        Returns:
            价格变化百分比，如果没有历史数据则返回None
        """
        if len(self.price_history) < 2:
            return None
        
        current = self.price_history[-1].price
        previous = self.price_history[-2].price
        
        if previous == 0:
            return None
            
        return ((current - previous) / previous) * 100
    
    def should_alert(self) -> bool:
        """
        判断是否需要触发价格预警
        
        Returns:
            如果当前价格低于阈值返回True
        """
        if self.alert_threshold is None:
            return False
        
        current = self.get_current_price()
        if current is None:
            return False
            
        return current <= self.alert_threshold
    
    def get_price_stats(self) -> dict:
        """
        获取价格统计信息
        
        Returns:
            包含最高价、最低价、平均价的字典
        """
        if not self.price_history:
            return {}
        
        prices = [p.price for p in self.price_history]
        return {
            "max": max(prices),
            "min": min(prices),
            "avg": sum(prices) / len(prices),
            "count": len(prices)
        }
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "name": self.name,
            "url": self.url,
            "selector": self.selector,
            "alert_threshold": self.alert_threshold,
            "current_price": self.get_current_price(),
            "price_history": [p.to_dict() for p in self.price_history],
            "stats": self.get_price_stats()
        }