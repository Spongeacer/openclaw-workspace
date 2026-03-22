"""工具函数模块"""
from pathlib import Path
from typing import Optional
import re


def validate_youtube_url(url: str) -> bool:
    """
    验证 YouTube URL 格式
    
    Args:
        url: 待验证的 URL
        
    Returns:
        是否有效
    """
    youtube_regex = re.compile(
        r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'
        r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
    )
    return bool(youtube_regex.match(url))


def extract_video_id(url: str) -> Optional[str]:
    """
    从 YouTube URL 提取视频 ID
    
    Args:
        url: YouTube URL
        
    Returns:
        视频 ID 或 None
    """
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([^&=%\?]{11})',
        r'youtube\.com/shorts/([^&=%\?]{11})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None


def format_duration(seconds: float) -> str:
    """
    格式化时长
    
    Args:
        seconds: 秒数
        
    Returns:
        格式化字符串 (HH:MM:SS)
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"
