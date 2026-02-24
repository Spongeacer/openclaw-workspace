"""
价格监控演示脚本 - Price Monitor Demo

演示如何使用价格监控模块
包含模拟数据生成，无需真实抓取网页
"""

import os
import sys
import random
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.price_monitor.monitor import PriceMonitor
from src.price_monitor.product import Product
from src.price_monitor.chart_generator import ChartGenerator


def generate_mock_price_data(product: Product, days: int = 30) -> None:
    """
    生成模拟价格数据
    
    Args:
        product: 商品对象
        days: 生成多少天的数据
    """
    # 初始价格
    base_price = random.uniform(100, 1000)
    
    for i in range(days):
        # 随机价格波动 (-10% 到 +10%)
        change = random.uniform(-0.1, 0.1)
        price = base_price * (1 + change)
        
        # 日期递减
        timestamp = datetime.now() - timedelta(days=days-i)
        
        product.add_price(price, timestamp)
        
        # 更新基准价格（模拟趋势）
        base_price = price


def run_demo():
    """运行价格监控演示"""
    print("=" * 60)
    print("价格监控演示 - Price Monitor Demo")
    print("=" * 60)
    
    # 创建监控器
    monitor = PriceMonitor()
    
    # 添加示例商品（使用模拟数据）
    print("\n[1] 添加监控商品...")
    
    products_data = [
        {
            "name": "iPhone 15 Pro",
            "url": "https://example.com/iphone15",
            "selector": ".price",
            "alert_threshold": 6999.0
        },
        {
            "name": "MacBook Air M2",
            "url": "https://example.com/macbook",
            "selector": ".current-price",
            "alert_threshold": 8999.0
        },
        {
            "name": "AirPods Pro 2",
            "url": "https://example.com/airpods",
            "selector": ".sale-price",
            "alert_threshold": 1599.0
        }
    ]
    
    for data in products_data:
        monitor.add_product(**data)
        print(f"  ✓ 已添加: {data['name']}")
    
    # 生成模拟历史数据
    print("\n[2] 生成模拟历史数据（30天）...")
    for product in monitor.products:
        generate_mock_price_data(product, days=30)
        current = product.get_current_price()
        stats = product.get_price_stats()
        print(f"  ✓ {product.name}: 当前 ¥{current:.2f}, "
              f"最低 ¥{stats['min']:.2f}, 最高 ¥{stats['max']:.2f}")
    
    # 检查价格预警
    print("\n[3] 检查价格预警...")
    alerted = []
    for product in monitor.products:
        if product.should_alert():
            alerted.append(product)
            print(f"  ⚠️  {product.name}: 当前价格低于预警阈值!")
    
    if not alerted:
        print("  ℹ️  暂无商品触发价格预警")
    
    # 生成图表
    print("\n[4] 生成价格趋势图表...")
    chart_paths = monitor.generate_charts()
    for path in chart_paths:
        print(f"  ✓ 图表已保存: {path}")
    
    # 生成对比图
    print("\n[5] 生成价格对比图...")
    comparison_path = monitor.chart_generator.generate_comparison_chart(monitor.products)
    print(f"  ✓ 对比图已保存: {comparison_path}")
    
    # 保存数据
    print("\n[6] 保存价格数据...")
    monitor.save_data()
    print("  ✓ 数据已保存到 ./data/processed/")
    
    # 生成报告
    print("\n[7] 生成HTML报告...")
    report_path = monitor.generate_report()
    print(f"  ✓ 报告已保存: {report_path}")
    
    print("\n" + "=" * 60)
    print("演示完成！请查看 output/ 目录生成的图表和报告")
    print("=" * 60)


if __name__ == "__main__":
    run_demo()