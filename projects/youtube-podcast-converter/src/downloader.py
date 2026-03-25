"""
YouTube 播客音频下载器模块

使用 yt-dlp 从 YouTube 提取音频流，输出 192kbps MP3
支持 M1/ARM64 架构，包含完善的错误处理和磁盘空间检查
支持自动代理路由选择和断点续传
"""

import os
import shutil
import logging
import socket
import time
import requests
from pathlib import Path
from typing import Optional, List, Dict, Tuple
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


@dataclass
class ProxyResult:
    """代理测试结果"""
    name: str
    url: str
    available: bool
    connect_time: Optional[float]
    download_speed: Optional[float]
    error: Optional[str] = None


class AutoProxyRouter:
    """
    自动代理路由选择器
    
    自动检测并选择最快的代理节点
    """
    
    # 代理节点列表 (名称, 地址)
    PROXY_NODES: List[Tuple[str, str]] = [
        ("Privoxy HTTP", "http://127.0.0.1:8118"),
        ("Trojan SOCKS5", "socks5://127.0.0.1:1080"),
    ]
    
    # 测试配置
    TEST_URL = "https://www.youtube.com"
    TEST_TIMEOUT = 10
    TEST_DOWNLOAD_SIZE = 512 * 1024  # 测试下载 512KB
    
    def __init__(self):
        self._cached_best_proxy: Optional[str] = None
        self._cache_time: Optional[float] = None
        self._cache_ttl = 300  # 缓存 5 分钟
    
    def _check_port_available(self, proxy_url: str) -> bool:
        """检查代理端口是否开放"""
        try:
            host, port = proxy_url.replace("http://", "").replace("socks5://", "").split(":")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host, int(port)))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    def _test_proxy(self, name: str, proxy_url: str) -> ProxyResult:
        """测试单个代理"""
        # 1. 检查端口
        if not self._check_port_available(proxy_url):
            return ProxyResult(
                name=name,
                url=proxy_url,
                available=False,
                connect_time=None,
                download_speed=None,
                error="端口未开放"
            )
        
        # 2. 测试连接和下载速度
        try:
            proxies = {
                "http": proxy_url,
                "https": proxy_url
            }
            
            # 测试连接时间
            start = time.time()
            response = requests.get(
                self.TEST_URL,
                proxies=proxies,
                timeout=self.TEST_TIMEOUT,
                stream=True
            )
            connect_time = time.time() - start
            
            # 测试下载速度（下载前 512KB）
            start = time.time()
            downloaded = 0
            
            for chunk in response.iter_content(chunk_size=8192):
                downloaded += len(chunk)
                if downloaded >= self.TEST_DOWNLOAD_SIZE:
                    break
            
            download_time = time.time() - start
            download_speed = (downloaded / 1024 / 1024) / download_time  # MB/s
            
            return ProxyResult(
                name=name,
                url=proxy_url,
                available=True,
                connect_time=connect_time,
                download_speed=download_speed,
                error=None
            )
            
        except requests.exceptions.Timeout:
            return ProxyResult(
                name=name,
                url=proxy_url,
                available=True,
                connect_time=None,
                download_speed=None,
                error="连接超时"
            )
        except Exception as e:
            return ProxyResult(
                name=name,
                url=proxy_url,
                available=True,
                connect_time=None,
                download_speed=None,
                error=str(e)
            )
    
    def select_best_proxy(self, force_test: bool = False, exclude: Optional[set] = None) -> Optional[str]:
        """
        选择最快的代理
        
        Args:
            force_test: 强制重新测试，不使用缓存
            exclude: 要排除的代理集合
            
        Returns:
            最佳代理 URL 或 None
        """
        exclude = exclude or set()
        
        # 检查缓存
        if not force_test and self._cached_best_proxy:
            if self._cached_best_proxy not in exclude:
                if time.time() - self._cache_time < self._cache_ttl:
                    logger.debug(f"使用缓存的代理: {self._cached_best_proxy}")
                    return self._cached_best_proxy
        
        logger.info("开始测试代理节点...")
        
        # 测试所有代理
        results: List[ProxyResult] = []
        for name, url in self.PROXY_NODES:
            if url in exclude:
                logger.info(f"  ⏭️  {name}: 已排除")
                continue
            result = self._test_proxy(name, url)
            results.append(result)
        
        # 打印结果
        logger.info("代理测试结果:")
        for r in results:
            if r.available and r.download_speed:
                logger.info(f"  ✅ {r.name}: {r.download_speed:.2f} MB/s ({r.connect_time:.2f}s)")
            elif r.available:
                logger.info(f"  ⚠️  {r.name}: {r.error or '速度测试失败'}")
            else:
                logger.info(f"  ❌ {r.name}: {r.error}")
        
        # 选择最快的（按下载速度排序）
        available = [r for r in results if r.available and r.download_speed]
        if not available:
            logger.warning("没有可用的代理")
            return None
        
        best = max(available, key=lambda r: r.download_speed)
        logger.info(f"选择最佳代理: {best.name} ({best.download_speed:.2f} MB/s)")
        
        # 缓存结果
        self._cached_best_proxy = best.url
        self._cache_time = time.time()
        
        return best.url
    
    def get_proxy(self, exclude: Optional[set] = None) -> Optional[str]:
        """获取代理（自动选择或缓存）"""
        return self.select_best_proxy(exclude=exclude)
    
    def clear_cache(self):
        """清除代理缓存"""
        logger.info("清除代理缓存")
        self._cached_best_proxy = None
        self._cache_time = None


class YouTubeDownloader:
    """
    YouTube 音频下载器
    
    功能:
    - 使用 yt-dlp 提取最佳音频流
    - 自动选择最快代理节点
    - 代理失效时自动切换并重试
    - 断点续传支持
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
    
    def __init__(self, output_dir: Path, auto_proxy: bool = True):
        """
        初始化下载器
        
        Args:
            output_dir: 音频输出目录
            auto_proxy: 是否启用自动代理选择
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.auto_proxy = auto_proxy
        self._proxy_router: Optional[AutoProxyRouter] = None
        
        # 验证 yt-dlp 可用
        if yt_dlp is None:
            raise ImportError("yt-dlp 未安装，无法初始化下载器")
        
        logger.info(f"YouTubeDownloader 初始化完成，输出目录: {self.output_dir}")
        if auto_proxy:
            logger.info("自动代理路由已启用（支持断点续传和代理切换）")
    
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
        
        # 添加代理
        proxy = self._get_proxy()
        if proxy:
            ydl_opts['proxy'] = proxy
        
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
                'members-only', 'sign in', 'age-restricted'
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
    
    def download(self, url: str, max_retries: int = 3) -> Path:
        """
        下载 YouTube 视频音频（支持断点续传和代理切换）
        
        Args:
            url: YouTube 视频 URL
            max_retries: 最大重试次数
            
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
        
        # 2. 提取视频信息（只执行一次）
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
        
        # 4. 尝试下载（支持重试和代理切换）
        last_error = None
        used_proxies = set()
        
        for attempt in range(1, max_retries + 1):
            logger.info(f"下载尝试 {attempt}/{max_retries}")
            
            try:
                # 获取代理（避开已失败的）
                proxy = self._get_proxy(exclude=used_proxies)
                if proxy:
                    logger.info(f"使用代理: {proxy}")
                    used_proxies.add(proxy)
                
                # 执行下载
                return self._do_download(url, video_info, proxy)
                
            except VideoUnavailableError:
                # 视频不可用不需要重试
                raise
            except (DownloadError, yt_dlp.utils.DownloadError) as e:
                error_msg = str(e).lower()
                
                # 检查是否是代理相关错误
                if any(keyword in error_msg for keyword in [
                    'timeout', 'timed out', 'connection', 'refused',
                    'reset', 'broken pipe', 'ssl', 'certificate'
                ]):
                    logger.warning(f"代理可能失效: {e}")
                    last_error = e
                    
                    # 清除代理缓存，强制重新测试
                    if self._proxy_router:
                        self._proxy_router.clear_cache()
                    
                    # 继续下一次尝试
                    if attempt < max_retries:
                        wait_time = min(2 ** attempt, 10)  # 指数退避，最多10秒
                        logger.info(f"{wait_time}秒后重试...")
                        time.sleep(wait_time)
                        continue
                else:
                    # 其他错误直接抛出
                    raise
        
        # 所有尝试都失败
        raise DownloadError(f"下载失败，已尝试 {max_retries} 次。最后错误: {last_error}")
    
    def _do_download(self, url: str, video_info: VideoInfo, proxy: Optional[str]) -> Path:
        """
        执行实际下载
        
        Args:
            url: YouTube URL
            video_info: 视频信息
            proxy: 代理地址
            
        Returns:
            下载的文件路径
        """
        ydl_opts = self._get_ydl_options(video_info.video_id, proxy)
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info(f"开始下载音频: {video_info.video_id}")
            
            # 下载视频（会自动提取音频为 MP3）
            ydl.download([url])
            
            # 构建预期输出文件路径
            expected_filename = f"{video_info.video_id}_{video_info.title[:100]}.mp3"
            safe_filename = self._sanitize_filename(expected_filename)
            output_path = self.output_dir / safe_filename
            
            # 如果上面的路径不存在，尝试查找生成的文件
            if not output_path.exists():
                matching_files = list(self.output_dir.glob(f"{video_info.video_id}_*.mp3"))
                if matching_files:
                    output_path = matching_files[0]
            
            if not output_path.exists():
                raise DownloadError(f"下载完成但未找到输出文件")
            
            logger.info(f"下载完成: {output_path}")
            return output_path.resolve()
    
    def _get_ydl_options(self, video_id: str, proxy: Optional[str] = None) -> dict:
        """
        生成 yt-dlp 下载选项
        
        Args:
            video_id: YouTube 视频 ID
            proxy: 代理地址
            
        Returns:
            yt-dlp 配置字典
        """
        output_template = str(self.output_dir / f"%(id)s_%(title).100s.%(ext)s")
        
        opts = {
            # 音频格式选择：选择最小的音频格式以加快速度
            'format': 'worstaudio/worst',
            
            # 使用 aria2c 多线程下载
            'external_downloader': 'aria2c',
            'external_downloader_args': ['-x', '16', '-s', '16', '-k', '1M'],
            
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
            
            # 断点续传支持
            'continuedl': True,
            'retries': 3,
            'fragment_retries': 3,
            'skip_unavailable_fragments': True,
            
            # 写入 info json 方便调试
            'writeinfojson': False,
            
            # 限制文件名长度（避免系统限制）
            'trim_file_name': 100,
        }
        
        # 添加代理配置
        if proxy:
            opts['proxy'] = proxy
        
        return opts
    
    def _get_proxy(self, exclude: Optional[set] = None) -> Optional[str]:
        """
        获取代理地址
        
        Args:
            exclude: 要排除的代理集合
            
        Returns:
            代理 URL 或 None
        """
        if not self.auto_proxy:
            return None
        
        if self._proxy_router is None:
            self._proxy_router = AutoProxyRouter()
        
        return self._proxy_router.get_proxy(exclude=exclude)
    
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
def download_audio(url: str, output_dir: str = "./downloads", auto_proxy: bool = True) -> Path:
    """
    快速下载 YouTube 音频的便捷函数
    
    Args:
        url: YouTube 视频 URL
        output_dir: 输出目录
        auto_proxy: 是否启用自动代理选择
        
    Returns:
        下载的 MP3 文件路径
    """
    downloader = YouTubeDownloader(Path(output_dir), auto_proxy=auto_proxy)
    return downloader.download(url)


if __name__ == "__main__":
    # 简单测试
    logging.basicConfig(level=logging.INFO)
    
    # 测试代理路由
    print("=" * 60)
    print("代理路由测试")
    print("=" * 60)
    
    router = AutoProxyRouter()
    best_proxy = router.select_best_proxy(force_test=True)
    
    if best_proxy:
        print(f"\n✅ 最佳代理: {best_proxy}")
    else:
        print("\n❌ 没有可用的代理")
    
    # 示例 URL（使用时替换为实际 URL）
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    try:
        downloader = YouTubeDownloader(Path("./test_downloads"))
        info = downloader.get_video_info(test_url)
        print(f"\n视频标题: {info.title}")
        print(f"时长: {info.duration} 秒")
        print(f"上传者: {info.uploader}")
    except Exception as e:
        print(f"测试失败: {e}")
