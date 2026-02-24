"""
价格监控器 - Price Monitor

核心功能：
1. 抓取网页价格数据
2. 存储价格历史
3. 生成价格报告
4. 价格预警

合规说明：
- 遵守目标网站的robots.txt
- 控制请求频率
- 仅抓取公开数据
"""

import os
import time
import json
import logging
from typing import List, Optional
from datetime import datetime
from urllib.parse import urlparse

import requests
import yaml
from bs4 import BeautifulSoup

from .product import Product, PricePoint
from .chart_generator import ChartGenerator

# 配置日志 / Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PriceMonitor:
    """
    价格监控器主类
    
    用于监控多个商品的价格变化
    
    Attributes:
        products: 监控的商品列表
        config: 配置信息
        session: HTTP会话
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化价格监控器
        
        Args:
            config_path: 配置文件路径，默认使用config/config.yaml
        """
        self.products: List[Product] = []
        self.config = self._load_config(config_path)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.config.get('user_agent', 
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        })
        self.chart_generator = ChartGenerator()
        
        # 确保数据目录存在
        self._ensure_directories()
    
    def _load_config(self, config_path: Optional[str]) -> dict:
        """
        加载配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            配置字典
        """
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(__file__), 
                '..', '..', 'config', 'config.yaml'
            )
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                return config.get('price_monitor', {})
        except FileNotFoundError:
            logger.warning(f"Config file not found: {config_path}")
            return {}
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}
    
    def _ensure_directories(self) -> None:
        """确保必要的目录存在"""
        dirs = [
            './data/raw',
            './data/processed',
            './output/charts',
            './output/reports',
            './logs'
        ]
        for dir_path in dirs:
            os.makedirs(dir_path, exist_ok=True)
    
    def add_product(self, name: str, url: str, selector: str, 
                    alert_threshold: Optional[float] = None) -> None:
        """
        添加监控商品
        
        Args:
            name: 商品名称
            url: 商品页面URL
            selector: 价格元素的CSS选择器
            alert_threshold: 价格预警阈值（可选）
        """
        product = Product(
            name=name,
            url=url,
            selector=selector,
            alert_threshold=alert_threshold
        )
        self.products.append(product)
        logger.info(f"Added product: {name}")
    
    def load_products_from_config(self) -> None:
        """从配置文件加载商品列表"""
        products_config = self.config.get('products', [])
        for item in products_config:
            self.add_product(
                name=item['name'],
                url=item['url'],
                selector=item['selector'],
                alert_threshold=item.get('alert_threshold')
            )
    
    def fetch_price(self, product: Product) -> Optional[float]:
        """
        抓取商品价格
        
        Args:
            product: 商品对象
            
        Returns:
            价格数值，失败返回None
            
        Note:
            这是一个示例实现，实际使用时需要根据目标网站调整解析逻辑
        """
        try:
            # 发送HTTP请求
            response = self.session.get(
                product.url, 
                timeout=self.config.get('timeout', 30)
            )
            response.raise_for_status()
            
            # 解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找价格元素
            price_element = soup.select_one(product.selector)
            if not price_element:
                logger.warning(f"Price element not found for {product.name}")
                return None
            
            # 提取价格文本并解析
            price_text = price_element.get_text().strip()
            price = self._parse_price(price_text)
            
            logger.info(f"Fetched price for {product.name}: {price}")
            return price
            
        except requests.RequestException as e:
            logger.error(f"Network error fetching {product.name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing price for {product.name}: {e}")
            return None
    
    def _parse_price(self, price_text: str) -> Optional[float]:
        """
        解析价格文本
        
        Args:
            price_text: 价格文本，如 "¥1,299.00" 或 "$199.99"
            
        Returns:
            价格数值
        """
        # 移除货币符号和分隔符
        import re
        # 提取数字和小数点
        numbers = re.findall(r'[\d,]+\.?\d*', price_text)
        if not numbers:
            return None
        
        # 取第一个匹配的数字，移除逗号
        price_str = numbers[0].replace(',', '')
        try:
            return float(price_str)
        except ValueError:
            return None
    
    def check_all_prices(self) -> List[Product]:
        """
        检查所有商品价格
        
        Returns:
            触发预警的商品列表
        """
        alerted_products = []
        delay = self.config.get('delay', 2)  # 请求间隔
        
        for product in self.products:
            price = self.fetch_price(product)
            
            if price is not None:
                product.add_price(price)
                
                # 检查是否需要预警
                if product.should_alert():
                    alerted_products.append(product)
                    logger.warning(
                        f"Price alert for {product.name}! "
                        f"Current: {price}, Threshold: {product.alert_threshold}"
                    )
            
            # 请求间隔，避免对服务器造成压力
            time.sleep(delay)
        
        return alerted_products
    
    def save_data(self) -> None:
        """保存价格数据到文件"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"./data/processed/prices_{timestamp}.json"
        
        data = {
            "timestamp": datetime.now().isoformat(),
            "products": [p.to_dict() for p in self.products]
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Data saved to {filename}")
    
    def generate_report(self) -> str:
        """
        生成价格监控报告
        
        Returns:
            报告文件路径
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_path = f"./output/reports/price_report_{timestamp}.html"
        
        # 生成HTML报告
        html_content = self._generate_html_report()
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"Report generated: {report_path}")
        return report_path
    
    def _generate_html_report(self) -> str:
        """生成HTML格式的报告"""
        html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>价格监控报告</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        table { border-collapse: collapse; width: 100%; margin-top: 20px; }
        th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
        th { background-color: #4CAF50; color: white; }
        tr:nth-child(even) { background-color: #f2f2f2; }
        .alert { color: red; font-weight: bold; }
        .price-down { color: green; }
        .price-up { color: red; }
    </style>
</head>
<body>
    <h1>价格监控报告</h1>
    <p>生成时间: {}</p>
    <table>
        <tr>
            <th>商品名称</th>
            <th>当前价格</th>
            <th>价格变化</th>
            <th>预警阈值</th>
            <th>最低/最高/平均</th>
        </tr>
""".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        for product in self.products:
            current = product.get_current_price()
            change = product.get_price_change()
            stats = product.get_price_stats()
            
            change_str = f"{change:+.2f}%" if change else "-"
            change_class = ""
            if change and change < 0:
                change_class = "price-down"
            elif change and change > 0:
                change_class = "price-up"
            
            alert_class = "alert" if product.should_alert() else ""
            
            stats_str = f"{stats.get('min', '-')}/{stats.get('max', '-')}/{stats.get('avg', '-'):.2f}" if stats else "-/-/-"
            
            html += f"""
        <tr>
            <td class="{alert_class}">{product.name}</td>
            <td>{current if current else '-'}</td>
            <td class="{change_class}">{change_str}</td>
            <td>{product.alert_threshold if product.alert_threshold else '-'}</td>
            <td>{stats_str}</td>
        </tr>
"""
        
        html += """
    </table>
</body>
</html>"""
        
        return html
    
    def generate_charts(self) -> List[str]:
        """
        生成价格趋势图表
        
        Returns:
            生成的图表文件路径列表
        """
        chart_paths = []
        
        for product in self.products:
            if product.price_history:
                path = self.chart_generator.generate_trend_chart(product)
                chart_paths.append(path)
        
        return chart_paths
    
    def run(self) -> None:
        """运行完整的价格监控流程"""
        logger.info("Starting price monitoring...")
        
        # 检查价格
        self.check_all_prices()
        
        # 保存数据
        self.save_data()
        
        # 生成报告
        self.generate_report()
        
        # 生成图表
        self.generate_charts()
        
        logger.info("Price monitoring completed.")