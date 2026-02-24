"""
图表生成器 - Chart Generator

用于生成价格趋势图表
支持多种图表类型：折线图、柱状图等
"""

import os
import logging
from datetime import datetime
from typing import Optional

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.figure import Figure

from .product import Product

logger = logging.getLogger(__name__)


class ChartGenerator:
    """
    图表生成器类
    
    用于生成价格趋势的可视化图表
    
    Attributes:
        output_dir: 图表输出目录
        style: matplotlib样式
    """
    
    def __init__(self, output_dir: str = "./output/charts"):
        """
        初始化图表生成器
        
        Args:
            output_dir: 图表输出目录
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # 设置matplotlib中文字体支持
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'SimHei', 'Arial Unicode MS']
        plt.rcParams['axes.unicode_minus'] = False
    
    def generate_trend_chart(self, product: Product, 
                            width: int = 12, 
                            height: int = 6) -> str:
        """
        生成价格趋势折线图
        
        Args:
            product: 商品对象
            width: 图表宽度（英寸）
            height: 图表高度（英寸）
            
        Returns:
            生成的图表文件路径
        """
        if not product.price_history:
            logger.warning(f"No price history for {product.name}")
            return ""
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(width, height))
        
        # 提取数据
        dates = [p.timestamp for p in product.price_history]
        prices = [p.price for p in product.price_history]
        
        # 绘制折线图
        ax.plot(dates, prices, marker='o', linewidth=2, markersize=6, 
                color='#2196F3', label='Price')
        
        # 填充区域
        ax.fill_between(dates, prices, alpha=0.3, color='#2196F3')
        
        # 设置标题和标签
        ax.set_title(f'{product.name} - Price Trend', fontsize=14, fontweight='bold')
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel(f'Price ({product.price_history[0].currency})', fontsize=12)
        
        # 格式化日期
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
        plt.xticks(rotation=45)
        
        # 添加网格
        ax.grid(True, linestyle='--', alpha=0.7)
        
        # 添加预警线
        if product.alert_threshold:
            ax.axhline(y=product.alert_threshold, color='red', 
                      linestyle='--', linewidth=2, label=f'Alert Threshold')
        
        # 添加图例
        ax.legend(loc='best')
        
        # 添加统计信息
        stats = product.get_price_stats()
        if stats:
            stats_text = f"Min: {stats['min']:.2f} | Max: {stats['max']:.2f} | Avg: {stats['avg']:.2f}"
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
                   verticalalignment='top', bbox=dict(boxstyle='round', 
                   facecolor='wheat', alpha=0.5))
        
        # 调整布局
        plt.tight_layout()
        
        # 保存图表
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_name = "".join(c if c.isalnum() else "_" for c in product.name)
        filename = f"{safe_name}_{timestamp}.png"
        filepath = os.path.join(self.output_dir, filename)
        
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close(fig)
        
        logger.info(f"Chart generated: {filepath}")
        return filepath
    
    def generate_comparison_chart(self, products: list, 
                                 width: int = 14, 
                                 height: int = 8) -> str:
        """
        生成多个商品的价格对比图
        
        Args:
            products: 商品列表
            width: 图表宽度
            height: 图表高度
            
        Returns:
            生成的图表文件路径
        """
        if not products:
            logger.warning("No products to compare")
            return ""
        
        fig, ax = plt.subplots(figsize=(width, height))
        
        colors = ['#2196F3', '#4CAF50', '#FF9800', '#9C27B0', '#F44336']
        
        for i, product in enumerate(products):
            if product.price_history:
                dates = [p.timestamp for p in product.price_history]
                prices = [p.price for p in product.price_history]
                
                color = colors[i % len(colors)]
                ax.plot(dates, prices, marker='o', linewidth=2, 
                       label=product.name, color=color)
        
        ax.set_title('Price Comparison', fontsize=14, fontweight='bold')
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Price', fontsize=12)
        
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.xticks(rotation=45)
        
        ax.grid(True, linestyle='--', alpha=0.7)
        ax.legend(loc='best')
        
        plt.tight_layout()
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"comparison_{timestamp}.png"
        filepath = os.path.join(self.output_dir, filename)
        
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close(fig)
        
        logger.info(f"Comparison chart generated: {filepath}")
        return filepath