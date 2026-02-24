import requests
from bs4 import BeautifulSoup
import json
import time
import os
from datetime import datetime
from typing import List, Dict, Optional
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from dataclasses import dataclass, asdict
import yaml


@dataclass
class PriceRecord:
    """价格记录数据类"""
    timestamp: str
    price: float
    currency: str
    product_name: str
    url: str


class PriceMonitor:
    """电商价格监控器 - 支持多个商品URL监控"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self.data_dir = self.config.get('data_dir', 'data/price')
        self.history_file = os.path.join(self.data_dir, 'price_history.json')
        self._ensure_data_dir()
        self.price_history = self._load_history()
        
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
            'data_dir': 'data/price',
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0'
            },
            'products': [],
            'price_threshold': 0.05  # 价格变化阈值 5%
        }
    
    def _ensure_data_dir(self):
        """确保数据目录存在"""
        os.makedirs(self.data_dir, exist_ok=True)
    
    def _load_history(self) -> Dict[str, List[Dict]]:
        """加载历史价格数据"""
        if os.path.exists(self.history_file):
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _save_history(self):
        """保存价格历史"""
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(self.price_history, f, ensure_ascii=False, indent=2)
    
    def fetch_price(self, url: str, selectors: Dict[str, str]) -> Optional[PriceRecord]:
        """
        抓取商品价格
        
        Args:
            url: 商品页面URL
            selectors: CSS选择器配置 {'name': '选择器', 'price': '选择器', 'currency': '选择器'}
        
        Returns:
            PriceRecord 或 None
        """
        headers = self.config.get('headers', {})
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取商品名称
            name_elem = soup.select_one(selectors.get('name', 'h1'))
            product_name = name_elem.get_text(strip=True) if name_elem else "Unknown"
            
            # 提取价格
            price_elem = soup.select_one(selectors.get('price', '.price'))
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                # 提取数字
                price = self._extract_price(price_text)
            else:
                price = 0.0
            
            # 提取货币
            currency_elem = soup.select_one(selectors.get('currency', '.currency'))
            currency = currency_elem.get_text(strip=True) if currency_elem else "¥"
            
            return PriceRecord(
                timestamp=datetime.now().isoformat(),
                price=price,
                currency=currency,
                product_name=product_name,
                url=url
            )
            
        except requests.RequestException as e:
            print(f"请求失败 {url}: {e}")
            return None
        except Exception as e:
            print(f"解析失败 {url}: {e}")
            return None
    
    def _extract_price(self, text: str) -> float:
        """从文本中提取价格数字"""
        import re
        # 匹配数字（支持千分位逗号和小数点）
        numbers = re.findall(r'[\d,]+\.?\d*', text.replace(',', ''))
        if numbers:
            try:
                return float(numbers[0])
            except ValueError:
                pass
        return 0.0
    
    def check_all_products(self) -> List[PriceRecord]:
        """检查所有配置的商品价格"""
        products = self.config.get('products', [])
        results = []
        
        for product in products:
            url = product.get('url')
            selectors = product.get('selectors', {})
            
            if not url:
                continue
                
            print(f"正在检查: {product.get('name', url)}")
            record = self.fetch_price(url, selectors)
            
            if record:
                results.append(record)
                self._update_history(record)
                
                # 检查价格变化
                self._check_price_change(record)
                
            time.sleep(2)  # 礼貌延迟
            
        self._save_history()
        return results
    
    def _update_history(self, record: PriceRecord):
        """更新价格历史"""
        url = record.url
        if url not in self.price_history:
            self.price_history[url] = []
        
        self.price_history[url].append(asdict(record))
        # 保留最近100条记录
        self.price_history[url] = self.price_history[url][-100:]
    
    def _check_price_change(self, record: PriceRecord):
        """检查价格变化并提醒"""
        url = record.url
        history = self.price_history.get(url, [])
        
        if len(history) >= 2:
            prev_price = history[-2]['price']
            curr_price = record.price
            
            if prev_price > 0:
                change_pct = (curr_price - prev_price) / prev_price
                threshold = self.config.get('price_threshold', 0.05)
                
                if abs(change_pct) >= threshold:
                    direction = "上涨" if change_pct > 0 else "下跌"
                    print(f"⚠️ 价格变动提醒: {record.product_name}")
                    print(f"   价格{direction}: {prev_price:.2f} → {curr_price:.2f} ({change_pct*100:+.1f}%)")
    
    def generate_trend_chart(self, url: str = None, days: int = 30):
        """
        生成价格趋势图
        
        Args:
            url: 特定商品URL，None则生成所有商品
            days: 显示最近N天的数据
        """
        if url:
            urls = [url]
        else:
            urls = list(self.price_history.keys())
        
        for product_url in urls:
            history = self.price_history.get(product_url, [])
            if len(history) < 2:
                continue
            
            # 过滤最近N天
            cutoff = datetime.now().timestamp() - days * 86400
            filtered = [h for h in history 
                       if datetime.fromisoformat(h['timestamp']).timestamp() > cutoff]
            
            if len(filtered) < 2:
                continue
            
            dates = [datetime.fromisoformat(h['timestamp']) for h in filtered]
            prices = [h['price'] for h in filtered]
            product_name = filtered[-1]['product_name'][:30]  # 截断名称
            
            plt.figure(figsize=(12, 6))
            plt.plot(dates, prices, marker='o', linewidth=2, markersize=4)
            plt.title(f'价格趋势: {product_name}', fontsize=14)
            plt.xlabel('日期', fontsize=12)
            plt.ylabel(f'价格 ({filtered[-1]["currency"]})', fontsize=12)
            plt.grid(True, alpha=0.3)
            
            # 格式化日期
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
            plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=max(1, days//10)))
            plt.xticks(rotation=45)
            
            # 添加当前价格标注
            current_price = prices[-1]
            plt.axhline(y=current_price, color='r', linestyle='--', alpha=0.5)
            plt.text(dates[-1], current_price, f'  {current_price:.2f}', 
                    verticalalignment='bottom')
            
            plt.tight_layout()
            
            # 保存图表
            safe_name = "".join(c if c.isalnum() else "_" for c in product_name)[:30]
            chart_path = os.path.join(self.data_dir, f'trend_{safe_name}.png')
            plt.savefig(chart_path, dpi=150, bbox_inches='tight')
            plt.close()
            
            print(f"📊 趋势图已保存: {chart_path}")
    
    def get_price_summary(self) -> str:
        """获取价格摘要报告"""
        lines = ["=" * 50, "价格监控摘要", "=" * 50]
        
        for url, history in self.price_history.items():
            if not history:
                continue
            
            latest = history[-1]
            lines.append(f"\n📦 {latest['product_name']}")
            lines.append(f"   当前价格: {latest['currency']}{latest['price']:.2f}")
            lines.append(f"   监控URL: {url[:60]}...")
            
            if len(history) >= 2:
                first = history[0]
                change = latest['price'] - first['price']
                change_pct = (change / first['price'] * 100) if first['price'] > 0 else 0
                lines.append(f"   历史变动: {change:+.2f} ({change_pct:+.1f}%)")
        
        return "\n".join(lines)


def main():
    """主函数"""
    monitor = PriceMonitor()
    
    print("🔍 开始价格监控...")
    results = monitor.check_all_products()
    
    print(f"\n✅ 成功检查 {len(results)} 个商品")
    
    # 生成趋势图
    print("\n📈 生成价格趋势图...")
    monitor.generate_trend_chart()
    
    # 打印摘要
    print("\n" + monitor.get_price_summary())


if __name__ == "__main__":
    main()
