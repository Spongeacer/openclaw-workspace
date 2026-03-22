#!/usr/bin/env python3
"""
YouTube 英文播客转中文语音合成系统

使用方法:
    python main.py <youtube_url>
    
示例:
    python main.py "https://www.youtube.com/watch?v=xxxxx"
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

import argparse
from loguru import logger

from src import PodcastPipeline
from src.utils import validate_youtube_url


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="将 YouTube 英文播客转换为中文语音"
    )
    parser.add_argument(
        "url",
        help="YouTube 视频 URL"
    )
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        default="config",
        help="配置目录路径 (默认: config)"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="output",
        help="输出目录路径 (默认: output)"
    )
    
    args = parser.parse_args()
    
    # 验证 URL
    if not validate_youtube_url(args.url):
        logger.error("无效的 YouTube URL")
        sys.exit(1)
    
    # 创建流水线
    config_dir = Path(args.config)
    if not config_dir.exists():
        logger.error(f"配置目录不存在: {config_dir}")
        sys.exit(1)
    
    logger.info("=" * 60)
    logger.info("YouTube 播客转中文语音合成系统")
    logger.info("=" * 60)
    logger.info(f"输入 URL: {args.url}")
    logger.info(f"配置目录: {config_dir.absolute()}")
    logger.info("=" * 60)
    
    try:
        # 运行流水线
        pipeline = PodcastPipeline(config_dir)
        output_path = pipeline.run(args.url)
        
        logger.success("=" * 60)
        logger.success("转换完成！")
        logger.success(f"输出文件: {output_path.absolute()}")
        logger.success("=" * 60)
        
    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"转换失败: {e}")
        logger.error("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
