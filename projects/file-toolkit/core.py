#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File Toolkit - 文件批量处理工具
核心功能模块
"""

import os
import re
import shutil
import zipfile
import tarfile
from pathlib import Path
from datetime import datetime
from typing import List, Callable, Optional, Tuple
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BatchRenamer:
    """批量重命名工具"""
    
    @staticmethod
    def rename_by_pattern(
        directory: str,
        pattern: str,
        replacement: str,
        recursive: bool = False,
        dry_run: bool = True
    ) -> List[Tuple[str, str]]:
        """
        使用正则表达式批量重命名文件
        
        Args:
            directory: 目标目录
            pattern: 正则表达式模式
            replacement: 替换字符串
            recursive: 是否递归处理子目录
            dry_run: 是否仅预览不执行
            
        Returns:
            重命名前后的文件路径列表
        """
        results = []
        path = Path(directory)
        
        # 获取文件列表
        if recursive:
            files = [f for f in path.rglob('*') if f.is_file()]
        else:
            files = [f for f in path.iterdir() if f.is_file()]
        
        regex = re.compile(pattern)
        
        for file_path in files:
            old_name = file_path.name
            new_name = regex.sub(replacement, old_name)
            
            if new_name != old_name:
                new_path = file_path.parent / new_name
                results.append((str(file_path), str(new_path)))
                
                if not dry_run:
                    try:
                        file_path.rename(new_path)
                        logger.info(f"重命名: {old_name} -> {new_name}")
                    except Exception as e:
                        logger.error(f"重命名失败 {old_name}: {e}")
        
        return results
    
    @staticmethod
    def rename_by_sequence(
        directory: str,
        prefix: str = "",
        suffix: str = "",
        start: int = 1,
        padding: int = 3,
        recursive: bool = False,
        dry_run: bool = True
    ) -> List[Tuple[str, str]]:
        """
        按序号批量重命名文件
        
        Args:
            directory: 目标目录
            prefix: 文件名前缀
            suffix: 文件名后缀（不含扩展名）
            start: 起始序号
            padding: 序号位数（补零）
            recursive: 是否递归处理
            dry_run: 是否仅预览
        """
        results = []
        path = Path(directory)
        
        if recursive:
            files = sorted([f for f in path.rglob('*') if f.is_file()])
        else:
            files = sorted([f for f in path.iterdir() if f.is_file()])
        
        counter = start
        
        for file_path in files:
            ext = file_path.suffix
            new_name = f"{prefix}{str(counter).zfill(padding)}{suffix}{ext}"
            new_path = file_path.parent / new_name
            
            results.append((str(file_path), str(new_path)))
            
            if not dry_run:
                try:
                    file_path.rename(new_path)
                    logger.info(f"重命名: {file_path.name} -> {new_name}")
                except Exception as e:
                    logger.error(f"重命名失败 {file_path.name}: {e}")
            
            counter += 1
        
        return results
    
    @staticmethod
    def rename_by_date(
        directory: str,
        date_format: str = "%Y%m%d_%H%M%S",
        prefix: str = "",
        use_creation_time: bool = False,
        recursive: bool = False,
        dry_run: bool = True
    ) -> List[Tuple[str, str]]:
        """
        按文件日期批量重命名
        
        Args:
            directory: 目标目录
            date_format: 日期格式字符串
            prefix: 文件名前缀
            use_creation_time: 是否使用创建时间（否则使用修改时间）
            recursive: 是否递归处理
            dry_run: 是否仅预览
        """
        results = []
        path = Path(directory)
        
        if recursive:
            files = [f for f in path.rglob('*') if f.is_file()]
        else:
            files = [f for f in path.iterdir() if f.is_file()]
        
        for file_path in files:
            stat = file_path.stat()
            if use_creation_time:
                timestamp = stat.st_ctime
            else:
                timestamp = stat.st_mtime
            
            date_str = datetime.fromtimestamp(timestamp).strftime(date_format)
            ext = file_path.suffix
            new_name = f"{prefix}{date_str}{ext}"
            new_path = file_path.parent / new_name
            
            # 处理重名
            counter = 1
            original_new_path = new_path
            while new_path.exists():
                new_name = f"{prefix}{date_str}_{counter}{ext}"
                new_path = file_path.parent / new_name
                counter += 1
            
            results.append((str(file_path), str(new_path)))
            
            if not dry_run:
                try:
                    file_path.rename(new_path)
                    logger.info(f"重命名: {file_path.name} -> {new_name}")
                except Exception as e:
                    logger.error(f"重命名失败 {file_path.name}: {e}")
        
        return results


class ImageProcessor:
    """图片批量处理工具"""
    
    SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
    
    def __init__(self):
        self.pil_available = False
        try:
            from PIL import Image
            self.pil_available = True
            self.Image = Image
        except ImportError:
            logger.warning("PIL/Pillow 未安装，图片处理功能不可用")
    
    def _check_pil(self):
        """检查PIL是否可用"""
        if not self.pil_available:
            raise ImportError("请先安装 Pillow: pip install Pillow")
    
    def convert_format(
        self,
        directory: str,
        target_format: str,
        quality: int = 95,
        recursive: bool = False,
        delete_original: bool = False,
        dry_run: bool = True
    ) -> List[Tuple[str, str]]:
        """
        批量转换图片格式
        
        Args:
            directory: 目标目录
            target_format: 目标格式 (jpg, png, webp等)
            quality: 输出质量 (1-100)
            recursive: 是否递归处理
            delete_original: 是否删除原文件
            dry_run: 是否仅预览
            
        Returns:
            转换前后的文件路径列表
        """
        self._check_pil()
        results = []
        path = Path(directory)
        target_format = target_format.lower().lstrip('.')
        
        if recursive:
            files = [f for f in path.rglob('*') if f.is_file()]
        else:
            files = [f for f in path.iterdir() if f.is_file()]
        
        for file_path in files:
            if file_path.suffix.lower() not in self.SUPPORTED_FORMATS:
                continue
            
            new_path = file_path.with_suffix(f'.{target_format}')
            results.append((str(file_path), str(new_path)))
            
            if not dry_run:
                try:
                    with self.Image.open(file_path) as img:
                        # 处理RGBA转RGB
                        if target_format in ['jpg', 'jpeg'] and img.mode in ('RGBA', 'LA', 'P'):
                            background = self.Image.new('RGB', img.size, (255, 255, 255))
                            if img.mode == 'P':
                                img = img.convert('RGBA')
                            if img.mode in ('RGBA', 'LA'):
                                background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                                img = background
                            else:
                                img = img.convert('RGB')
                        
                        save_kwargs = {}
                        if target_format in ['jpg', 'jpeg']:
                            save_kwargs['quality'] = quality
                            save_kwargs['optimize'] = True
                        elif target_format == 'png':
                            save_kwargs['optimize'] = True
                        elif target_format == 'webp':
                            save_kwargs['quality'] = quality
                        
                        img.save(new_path, **save_kwargs)
                    
                    logger.info(f"转换: {file_path.name} -> {new_path.name}")
                    
                    if delete_original and file_path != new_path:
                        file_path.unlink()
                        logger.info(f"删除原文件: {file_path.name}")
                        
                except Exception as e:
                    logger.error(f"转换失败 {file_path.name}: {e}")
        
        return results
    
    def resize_images(
        self,
        directory: str,
        width: Optional[int] = None,
        height: Optional[int] = None,
        scale: Optional[float] = None,
        maintain_aspect: bool = True,
        recursive: bool = False,
        suffix: str = "_resized",
        dry_run: bool = True
    ) -> List[Tuple[str, str]]:
        """
        批量调整图片尺寸
        
        Args:
            directory: 目标目录
            width: 目标宽度
            height: 目标高度
            scale: 缩放比例（与width/height互斥）
            maintain_aspect: 是否保持宽高比
            recursive: 是否递归处理
            suffix: 输出文件后缀
            dry_run: 是否仅预览
        """
        self._check_pil()
        results = []
        path = Path(directory)
        
        if recursive:
            files = [f for f in path.rglob('*') if f.is_file()]
        else:
            files = [f for f in path.iterdir() if f.is_file()]
        
        for file_path in files:
            if file_path.suffix.lower() not in self.SUPPORTED_FORMATS:
                continue
            
            new_name = f"{file_path.stem}{suffix}{file_path.suffix}"
            new_path = file_path.parent / new_name
            results.append((str(file_path), str(new_path)))
            
            if not dry_run:
                try:
                    with self.Image.open(file_path) as img:
                        orig_width, orig_height = img.size
                        
                        if scale:
                            new_width = int(orig_width * scale)
                            new_height = int(orig_height * scale)
                        elif width and height and not maintain_aspect:
                            new_width, new_height = width, height
                        elif width:
                            new_width = width
                            new_height = int(orig_height * (width / orig_width))
                        elif height:
                            new_height = height
                            new_width = int(orig_width * (height / orig_height))
                        else:
                            logger.warning(f"跳过 {file_path.name}: 未指定尺寸参数")
                            continue
                        
                        resized = img.resize((new_width, new_height), self.Image.LANCZOS)
                        resized.save(new_path)
                        logger.info(f"调整尺寸: {file_path.name} ({orig_width}x{orig_height}) -> ({new_width}x{new_height})")
                        
                except Exception as e:
                    logger.error(f"调整尺寸失败 {file_path.name}: {e}")
        
        return results


class FileOrganizer:
    """文件批量整理工具"""
    
    @staticmethod
    def organize_by_date(
        directory: str,
        date_format: str = "%Y-%m",
        use_creation_time: bool = False,
        recursive: bool = False,
        dry_run: bool = True
    ) -> List[Tuple[str, str]]:
        """
        按日期整理文件到文件夹
        
        Args:
            directory: 目标目录
            date_format: 日期文件夹格式
            use_creation_time: 是否使用创建时间
            recursive: 是否递归处理
            dry_run: 是否仅预览
            
        Returns:
            移动前后的文件路径列表
        """
        results = []
        path = Path(directory)
        
        if recursive:
            files = [f for f in path.rglob('*') if f.is_file()]
        else:
            files = [f for f in path.iterdir() if f.is_file()]
        
        for file_path in files:
            stat = file_path.stat()
            if use_creation_time:
                timestamp = stat.st_ctime
            else:
                timestamp = stat.mtime
            
            date_folder = datetime.fromtimestamp(timestamp).strftime(date_format)
            target_dir = path / date_folder
            target_path = target_dir / file_path.name
            
            # 处理重名
            counter = 1
            original_target = target_path
            while target_path.exists():
                stem = original_target.stem
                suffix = original_target.suffix
                target_path = target_dir / f"{stem}_{counter}{suffix}"
                counter += 1
            
            results.append((str(file_path), str(target_path)))
            
            if not dry_run:
                try:
                    target_dir.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(file_path), str(target_path))
                    logger.info(f"移动: {file_path.name} -> {date_folder}/")
                except Exception as e:
                    logger.error(f"移动失败 {file_path.name}: {e}")
        
        return results
    
    @staticmethod
    def organize_by_type(
        directory: str,
        custom_types: Optional[dict] = None,
        recursive: bool = False,
        dry_run: bool = True
    ) -> List[Tuple[str, str]]:
        """
        按文件类型整理文件到文件夹
        
        Args:
            directory: 目标目录
            custom_types: 自定义类型映射 {扩展名: 文件夹名}
            recursive: 是否递归处理
            dry_run: 是否仅预览
        """
        results = []
        path = Path(directory)
        
        # 默认类型映射
        type_mapping = {
            # 图片
            '.jpg': 'Images', '.jpeg': 'Images', '.png': 'Images', '.gif': 'Images',
            '.bmp': 'Images', '.tiff': 'Images', '.webp': 'Images', '.svg': 'Images',
            '.raw': 'Images', '.psd': 'Images', '.ai': 'Images',
            # 视频
            '.mp4': 'Videos', '.avi': 'Videos', '.mkv': 'Videos', '.mov': 'Videos',
            '.wmv': 'Videos', '.flv': 'Videos', '.webm': 'Videos', '.m4v': 'Videos',
            # 音频
            '.mp3': 'Audio', '.wav': 'Audio', '.flac': 'Audio', '.aac': 'Audio',
            '.ogg': 'Audio', '.wma': 'Audio', '.m4a': 'Audio',
            # 文档
            '.pdf': 'Documents', '.doc': 'Documents', '.docx': 'Documents',
            '.xls': 'Documents', '.xlsx': 'Documents', '.ppt': 'Documents',
            '.pptx': 'Documents', '.txt': 'Documents', '.rtf': 'Documents',
            '.csv': 'Documents', '.md': 'Documents',
            # 压缩包
            '.zip': 'Archives', '.rar': 'Archives', '.7z': 'Archives',
            '.tar': 'Archives', '.gz': 'Archives', '.bz2': 'Archives',
            # 代码
            '.py': 'Code', '.js': 'Code', '.html': 'Code', '.css': 'Code',
            '.java': 'Code', '.cpp': 'Code', '.c': 'Code', '.h': 'Code',
            '.php': 'Code', '.rb': 'Code', '.go': 'Code', '.rs': 'Code',
            # 可执行文件
            '.exe': 'Executables', '.msi': 'Executables', '.dmg': 'Executables',
            '.app': 'Executables', '.deb': 'Executables', '.rpm': 'Executables',
        }
        
        # 合并自定义类型
        if custom_types:
            type_mapping.update(custom_types)
        
        if recursive:
            files = [f for f in path.rglob('*') if f.is_file()]
        else:
            files = [f for f in path.iterdir() if f.is_file()]
        
        for file_path in files:
            ext = file_path.suffix.lower()
            folder_name = type_mapping.get(ext, 'Others')
            
            target_dir = path / folder_name
            target_path = target_dir / file_path.name
            
            # 处理重名
            counter = 1
            original_target = target_path
            while target_path.exists():
                stem = original_target.stem
                suffix = original_target.suffix
                target_path = target_dir / f"{stem}_{counter}{suffix}"
                counter += 1
            
            results.append((str(file_path), str(target_path)))
            
            if not dry_run:
                try:
                    target_dir.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(file_path), str(target_path))
                    logger.info(f"移动: {file_path.name} -> {folder_name}/")
                except Exception as e:
                    logger.error(f"移动失败 {file_path.name}: {e}")
        
        return results


class ArchiveManager:
    """压缩/解压管理工具"""
    
    SUPPORTED_ARCHIVE = {'.zip', '.tar', '.tar.gz', '.tgz', '.tar.bz2', '.tbz2', '.bz2'}
    
    def compress(
        self,
        sources: List[str],
        output_path: str,
        archive_format: str = 'zip',
        compression_level: int = 6
    ) -> str:
        """
        批量压缩文件/文件夹
        
        Args:
            sources: 要压缩的文件/文件夹路径列表
            output_path: 输出压缩包路径
            archive_format: 压缩格式 (zip, tar, tar.gz, tar.bz2)
            compression_level: 压缩级别 (1-9)
            
        Returns:
            输出文件路径
        """
        output_path = Path(output_path)
        
        if archive_format == 'zip':
            return self._compress_zip(sources, output_path, compression_level)
        elif archive_format in ['tar', 'tar.gz', 'tgz', 'tar.bz2', 'tbz2']:
            return self._compress_tar(sources, output_path, archive_format)
        else:
            raise ValueError(f"不支持的压缩格式: {archive_format}")
    
    def _compress_zip(
        self,
        sources: List[str],
        output_path: Path,
        compression_level: int
    ) -> str:
        """ZIP压缩"""
        import zlib
        
        compression = zipfile.ZIP_DEFLATED
        
        with zipfile.ZipFile(output_path, 'w', compression, compresslevel=compression_level) as zf:
            for source in sources:
                source_path = Path(source)
                
                if source_path.is_file():
                    zf.write(source_path, source_path.name)
                    logger.info(f"添加文件: {source_path.name}")
                elif source_path.is_dir():
                    for file_path in source_path.rglob('*'):
                        if file_path.is_file():
                            arcname = file_path.relative_to(source_path.parent)
                            zf.write(file_path, arcname)
                            logger.info(f"添加: {arcname}")
        
        logger.info(f"压缩完成: {output_path}")
        return str(output_path)
    
    def _compress_tar(
        self,
        sources: List[str],
        output_path: Path,
        archive_format: str
    ) -> str:
        """TAR压缩"""
        # 确定压缩模式
        if archive_format in ['tar.gz', 'tgz']:
            mode = 'w:gz'
        elif archive_format in ['tar.bz2', 'tbz2']:
            mode = 'w:bz2'
        else:
            mode = 'w'
        
        with tarfile.open(output_path, mode) as tf:
            for source in sources:
                source_path = Path(source)
                tf.add(source_path, arcname=source_path.name)
                logger.info(f"添加: {source_path.name}")
        
        logger.info(f"压缩完成: {output_path}")
        return str(output_path)
    
    def extract(
        self,
        archive_path: str,
        output_dir: Optional[str] = None,
        password: Optional[str] = None
    ) -> str:
        """
        解压文件
        
        Args:
            archive_path: 压缩包路径
            output_dir: 输出目录（默认为压缩包所在目录）
            password: 解压密码（仅ZIP支持）
            
        Returns:
            输出目录路径
        """
        archive_path = Path(archive_path)
        
        if output_dir is None:
            output_dir = archive_path.parent / archive_path.stem
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        ext = ''.join(archive_path.suffixes).lower()
        
        if ext == '.zip':
            self._extract_zip(archive_path, output_dir, password)
        elif ext in ['.tar', '.tar.gz', '.tgz', '.tar.bz2', '.tbz2']:
            self._extract_tar(archive_path, output_dir)
        else:
            raise ValueError(f"不支持的压缩格式: {ext}")
        
        logger.info(f"解压完成: {output_dir}")
        return str(output_dir)
    
    def _extract_zip(
        self,
        archive_path: Path,
        output_dir: Path,
        password: Optional[str] = None
    ):
        """ZIP解压"""
        with zipfile.ZipFile(archive_path, 'r') as zf:
            if password:
                zf.setpassword(password.encode())
            
            # 检查并修复文件名编码
            for member in zf.namelist():
                try:
                    member.encode('ascii')
                except UnicodeEncodeError:
                    # 尝试GBK编码（中文Windows常见）
                    try:
                        member = member.encode('cp437').decode('gbk')
                    except:
                        pass
                
                zf.extract(member, output_dir)
                logger.info(f"解压: {member}")
    
    def _extract_tar(
        self,
        archive_path: Path,
        output_dir: Path
    ):
        """TAR解压"""
        with tarfile.open(archive_path, 'r') as tf:
            tf.extractall(output_dir)
            for member in tf.getmembers():
                logger.info(f"解压: {member.name}")
    
    def batch_extract(
        self,
        directory: str,
        output_dir: Optional[str] = None,
        recursive: bool = False,
        delete_after: bool = False
    ) -> List[str]:
        """
        批量解压目录中的压缩包
        
        Args:
            directory: 目标目录
            output_dir: 输出目录基路径
            recursive: 是否递归查找
            delete_after: 解压后是否删除原压缩包
            
        Returns:
            解压后的目录列表
        """
        results = []
        path = Path(directory)
        
        if recursive:
            archives = [f for f in path.rglob('*') if f.is_file()]
        else:
            archives = [f for f in path.iterdir() if f.is_file()]
        
        # 过滤支持的压缩格式
        archives = [f for f in archives if ''.join(f.suffixes).lower() in self.SUPPORTED_ARCHIVE]
        
        for archive in archives:
            try:
                if output_dir:
                    out = Path(output_dir) / archive.stem
                else:
                    out = None
                
                extracted = self.extract(str(archive), str(out) if out else None)
                results.append(extracted)
                
                if delete_after:
                    archive.unlink()
                    logger.info(f"删除压缩包: {archive.name}")
                    
            except Exception as e:
                logger.error(f"解压失败 {archive.name}: {e}")
        
        return results


# 便捷函数

def preview_changes(changes: List[Tuple[str, str]], max_show: int = 20):
    """预览变更列表"""
    print(f"\n预览变更 ({len(changes)} 项):")
    print("-" * 60)
    
    for i, (old, new) in enumerate(changes[:max_show]):
        old_name = Path(old).name
        new_name = Path(new).name
        print(f"{i+1}. {old_name}")
        print(f"   -> {new_name}")
    
    if len(changes) > max_show:
        print(f"\n... 还有 {len(changes) - max_show} 项")
    
    print("-" * 60)


def confirm_action(prompt: str = "确认执行?") -> bool:
    """确认操作"""
    response = input(f"\n{prompt} [y/N]: ").strip().lower()
    return response in ['y', 'yes']
