"""
YouTube 播客音频下载器模块

使用 yt-dlp 从 YouTube 提取音频流，输出 192kbps MP3
支持 M1/ARM64 架构，包含完善的错误处理和磁盘空间检查
"""

import os
import shutil
import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from urllib.parse import urlparse

# 尝试导入 yt_dlp，如果失败则提供安装提示
try:
    import yt_dlp
except ImportError:
    yt_dlp = None
    raise ImportError(
        "yt-dlp 未安装。请运行: pip install yt-dlp\n"
        "M1 Mac 用户请确保安装 ARM64 版本: arch -arm64 pip install yt-dlp"
    )

# 配置日志
logger = logging.getLogger(__name__)


class YouTubeError(Exception):
    """YouTube 下载基础异常"""
    pass


class VideoUnavailableError(YouTubeError):
    """视频不可用异常（私有、删除、地域限制等）"""
    pass


class DiskSpaceError(YouTubeError):
    """磁盘空间不足异常"""
    pass


class DownloadError(YouTubeError):
    """下载过程中发生的其他错误"""
    pass


@dataclass
class VideoInfo:
    """视频信息数据结构"""
    title: str
    duration: int  # 秒
    filesize_approx: Optional[int]  # 字节（预估）
    uploader: str
    video_id: str


class YouTubeDownloader:
    """
    YouTube 音频下载器
    
    功能:
    - 使用 yt-dlp 提取最佳音频流
    - 转换为 192kbps MP3
    - 磁盘空间预留检查（2倍音频大小）
    - M1/ARM64 原生支持
    
    使用示例:
        downloader = YouTubeDownloader(Path("./downloads"))
        audio_path = downloader.download("https://youtube.com/watch?v=...")
    """
    
    # 磁盘空间预留倍数
    DISK_SPACE_MULTIPLIER = 2.0
    
    # 预估音频文件大小（kbps * 秒 / 8 = bytes）
    # 192 kbps = 24 KB/s
    BYTES_PER_SECOND = 24000
    
    def __init__(self, output_dir: Path):
        """
        初始化下载器
        
        Args:
            output_dir: 音频输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 验证 yt-dlp 可用
        if yt_dlp is None:
            raise ImportError("yt-dlp 未安装，无法初始化下载器")
        
        logger.info(f"YouTubeDownloader 初始化完成，输出目录: {self.output_dir}")
    
    def _validate_url(self, url: str) -> bool:
        """
        验证 YouTube URL 格式
        
        Args:
            url: 待验证的 URL
            
        Returns:
            是否为有效的 YouTube URL
        """
        parsed = urlparse(url)
        
        # 支持的 YouTube 域名
        youtube_hosts = [
            'youtube.com',
            'www.youtube.com',
            'youtu.be',
            'm.youtube.com',
            'music.youtube.com'
        ]
        
        return parsed.netloc in youtube_hosts or parsed.netloc.endswith('youtube.com')
    
    def _extract_info(self, url: str) -> VideoInfo:
        """
        提取视频信息（不下载）
        
        Args:
            url: YouTube 视频 URL
            
        Returns:
            VideoInfo 对象
            
        Raises:
            VideoUnavailableError: 视频不可用时抛出
        """
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if info is None:
                    raise VideoUnavailableError(f"无法获取视频信息: {url}")
                
                # 获取文件大小（优先使用 bestaudio 的大小）
                filesize = None
                formats = info.get('formats', [])
                
                # 查找音频格式的大小
                for fmt in formats:
                    if fmt.get('acodec') != 'none' and fmt.get('vcodec') == 'none':
                        filesize = fmt.get('filesize') or fmt.get('filesize_approx')
                        if filesize:
                            break
                
                # 如果没有找到音频格式大小，进行估算
                if filesize is None:
                    duration = info.get('duration', 0) or 0
                    filesize = duration * self.BYTES_PER_SECOND
                
                return VideoInfo(
                    title=info.get('title', 'Unknown'),
                    duration=info.get('duration', 0) or 0,
                    filesize_approx=filesize,
                    uploader=info.get('uploader', 'Unknown'),
                    video_id=info.get('id', '')
                )
                
        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e).lower()
            
            # 判断具体的不可用原因
            if any(keyword in error_msg for keyword in [
                'private', 'removed', 'unavailable', 
                'members-only', 'sign in', 'age-restricted',
                'not available', 'disabled', 'blocked'
            ]):
                raise VideoUnavailableError(f"视频不可用: {url} - {e}")
            
            raise DownloadError(f"提取视频信息失败: {e}")
    
    def _check_disk_space(self, required_bytes: int) -> bool:
        """
        检查磁盘空间是否充足
        
        Args:
            required_bytes: 需要的字节数
            
        Returns:
            空间是否充足
            
        Raises:
            DiskSpaceError: 空间不足时抛出
        """
        # 获取输出目录所在磁盘的使用情况
        disk_usage = shutil.disk_usage(self.output_dir)
        available = disk_usage.free
        
        # 预留 2 倍空间
        required_with_buffer = int(required_bytes * self.DISK_SPACE_MULTIPLIER)
        
        logger.debug(f"磁盘检查: 需要 {required_with_buffer / 1024 / 1024:.2f} MB, "
                    f"可用 {available / 1024 / 1024:.2f} MB")
        
        if available < required_with_buffer:
            raise DiskSpaceError(
                f"磁盘空间不足。需要: {required_with_buffer / 1024 / 1024:.2f} MB "
                f"(含 {self.DISK_SPACE_MULTIPLIER}x 预留), "
                f"可用: {available / 1024 / 1024:.2f} MB"
            )
        
        return True
    
    def _get_ydl_options(self, video_id: str) -> dict:
        """
        生成 yt-dlp 下载选项
        
        Args:
            video_id: YouTube 视频 ID
            
        Returns:
            yt-dlp 配置字典
        """
        output_template = str(self.output_dir / f"%(id)s_%(title).100s.%(ext)s")
        
        return {
            # 音频格式选择：最佳音频，或最佳（回退）
            'format': 'bestaudio/best',
            
            # 后处理：提取音频为 MP3，192kbps
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            
            # 输出模板
            'outtmpl': output_template,
            
            # 安静模式，减少日志输出
            'quiet': True,
            'no_warnings': True,
            
            # 覆盖已存在文件
            'overwrites': True,
            
            # 网络设置（增加稳定性）
            'retries': 3,
            'fragment_retries': 3,
            'skip_unavailable_fragments': True,
            
            # 写入 info json 方便调试
            'writeinfojson': False,
            
            # 限制文件名长度（避免系统限制）
            'trim_file_name': 100,
        }
    
    def download(self, url: str) -> Path:
        """
        下载 YouTube 视频音频
        
        Args:
            url: YouTube 视频 URL
            
        Returns:
            下载的 MP3 文件路径
            
        Raises:
            VideoUnavailableError: 视频不可用（私有/删除/地域限制等）
            DiskSpaceError: 磁盘空间不足
            DownloadError: 下载过程中发生其他错误
            ValueError: URL 格式无效
        """
        # 1. 验证 URL
        if not self._validate_url(url):
            raise ValueError(f"无效的 YouTube URL: {url}")
        
        logger.info(f"开始处理视频: {url}")
        
        # 2. 提取视频信息
        try:
            video_info = self._extract_info(url)
            logger.info(f"视频信息: {video_info.title} ({video_info.duration}s)")
        except VideoUnavailableError:
            raise
        except Exception as e:
            raise DownloadError(f"获取视频信息失败: {e}")
        
        # 3. 检查磁盘空间
        if video_info.filesize_approx:
            self._check_disk_space(video_info.filesize_approx)
        
        # 4. 执行下载
        try:
            ydl_opts = self._get_ydl_options(video_info.video_id)
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info(f"开始下载音频: {video_info.video_id}")
                
                # 下载视频（会自动提取音频为 MP3）
                ydl.download([url])
                
                # 构建预期输出文件路径
                # yt-dlp 会处理文件名清理，我们需要找到实际生成的文件
                expected_filename = f"{video_info.video_id}_{video_info.title[:100]}.mp3"
                # 清理文件名中的非法字符
                safe_filename = self._sanitize_filename(expected_filename)
                output_path = self.output_dir / safe_filename
                
                # 如果上面的路径不存在，尝试查找生成的文件
                if not output_path.exists():
                    # 搜索以 video_id 开头的 mp3 文件
                    matching_files = list(self.output_dir.glob(f"{video_info.video_id}_*.mp3"))
                    if matching_files:
                        output_path = matching_files[0]
                
                if not output_path.exists():
                    raise DownloadError(f"下载完成但未找到输出文件")
                
                logger.info(f"下载完成: {output_path}")
                return output_path.resolve()
                
        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e).lower()
            
            # 重新检查不可用错误
            if any(keyword in error_msg for keyword in [
                'private', 'removed', 'unavailable', 
                'members-only', 'sign in', 'age-restricted'
            ]):
                raise VideoUnavailableError(f"下载时视频不可用: {e}")
            
            raise DownloadError(f"下载失败: {e}")
            
        except Exception as e:
            raise DownloadError(f"下载过程中发生未知错误: {e}")
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        清理文件名中的非法字符
        
        Args:
            filename: 原始文件名
            
        Returns:
            清理后的文件名
        """
        # 替换或移除非法字符
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # 限制长度
        name, ext = os.path.splitext(filename)
        max_name_len = 100 - len(ext)
        if len(name) > max_name_len:
            name = name[:max_name_len]
        
        return name + ext
    
    def get_video_info(self, url: str) -> VideoInfo:
        """
        获取视频信息（不下载）
        
        Args:
            url: YouTube 视频 URL
            
        Returns:
            VideoInfo 对象
        """
        if not self._validate_url(url):
            raise ValueError(f"无效的 YouTube URL: {url}")
        
        return self._extract_info(url)


# 便捷函数
def download_audio(url: str, output_dir: str = "./downloads") -> Path:
    """
    快速下载 YouTube 音频的便捷函数
    
    Args:
        url: YouTube 视频 URL
        output_dir: 输出目录
        
    Returns:
        下载的 MP3 文件路径
    """
    downloader = YouTubeDownloader(Path(output_dir))
    return downloader.download(url)


if __name__ == "__main__":
    # 简单测试
    logging.basicConfig(level=logging.INFO)
    
    # 示例 URL（使用时替换为实际 URL）
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    try:
        downloader = YouTubeDownloader(Path("./test_downloads"))
        info = downloader.get_video_info(test_url)
        print(f"视频标题: {info.title}")
        print(f"时长: {info.duration} 秒")
        print(f"上传者: {info.uploader}")
    except Exception as e:
        print(f"测试失败: {e}")
