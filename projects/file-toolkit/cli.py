#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File Toolkit - 命令行界面
"""

import argparse
import sys
import os
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from core import (
    BatchRenamer, ImageProcessor, FileOrganizer, ArchiveManager,
    preview_changes, confirm_action
)


def create_parser():
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        prog='file-toolkit',
        description='文件批量处理工具 - 支持重命名、图片处理、文件整理、压缩解压',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 批量重命名（正则替换）
  python cli.py rename regex -d ./photos -p "IMG_" -r "Photo_" --execute

  # 按序号重命名
  python cli.py rename sequence -d ./photos -p "vacation_" --start 1 --padding 3 --execute

  # 按日期重命名
  python cli.py rename date -d ./photos --prefix "img_" --execute

  # 批量转换图片格式
  python cli.py image convert -d ./photos -f webp -q 90 --execute

  # 批量调整图片尺寸
  python cli.py image resize -d ./photos --width 1920 --height 1080 --execute

  # 按日期整理文件
  python cli.py organize date -d ./downloads --format "%Y-%m" --execute

  # 按类型整理文件
  python cli.py organize type -d ./downloads --execute

  # 压缩文件
  python cli.py archive compress -i ./folder1 ./file1.txt -o output.zip

  # 解压文件
  python cli.py archive extract -i archive.zip -o ./output

  # 批量解压
  python cli.py archive batch-extract -d ./downloads --execute
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # ========== 重命名命令 ==========
    rename_parser = subparsers.add_parser('rename', help='批量重命名文件')
    rename_subparsers = rename_parser.add_subparsers(dest='rename_type', help='重命名类型')
    
    # 正则重命名
    regex_parser = rename_subparsers.add_parser('regex', help='正则表达式替换')
    regex_parser.add_argument('-d', '--directory', required=True, help='目标目录')
    regex_parser.add_argument('-p', '--pattern', required=True, help='正则表达式模式')
    regex_parser.add_argument('-r', '--replacement', required=True, help='替换字符串')
    regex_parser.add_argument('--recursive', action='store_true', help='递归处理子目录')
    regex_parser.add_argument('--execute', action='store_true', help='实际执行（默认仅预览）')
    
    # 序号重命名
    seq_parser = rename_subparsers.add_parser('sequence', help='按序号重命名')
    seq_parser.add_argument('-d', '--directory', required=True, help='目标目录')
    seq_parser.add_argument('-p', '--prefix', default='', help='文件名前缀')
    seq_parser.add_argument('-s', '--suffix', default='', help='文件名后缀')
    seq_parser.add_argument('--start', type=int, default=1, help='起始序号')
    seq_parser.add_argument('--padding', type=int, default=3, help='序号位数')
    seq_parser.add_argument('--recursive', action='store_true', help='递归处理子目录')
    seq_parser.add_argument('--execute', action='store_true', help='实际执行')
    
    # 日期重命名
    date_parser = rename_subparsers.add_parser('date', help='按日期重命名')
    date_parser.add_argument('-d', '--directory', required=True, help='目标目录')
    date_parser.add_argument('--format', default='%Y%m%d_%H%M%S', help='日期格式')
    date_parser.add_argument('--prefix', default='', help='文件名前缀')
    date_parser.add_argument('--use-ctime', action='store_true', help='使用创建时间')
    date_parser.add_argument('--recursive', action='store_true', help='递归处理子目录')
    date_parser.add_argument('--execute', action='store_true', help='实际执行')
    
    # ========== 图片处理命令 ==========
    image_parser = subparsers.add_parser('image', help='批量图片处理')
    image_subparsers = image_parser.add_subparsers(dest='image_type', help='图片处理类型')
    
    # 格式转换
    convert_parser = image_subparsers.add_parser('convert', help='转换图片格式')
    convert_parser.add_argument('-d', '--directory', required=True, help='目标目录')
    convert_parser.add_argument('-f', '--format', required=True, help='目标格式 (jpg/png/webp等)')
    convert_parser.add_argument('-q', '--quality', type=int, default=95, help='输出质量 (1-100)')
    convert_parser.add_argument('--recursive', action='store_true', help='递归处理')
    convert_parser.add_argument('--delete-original', action='store_true', help='删除原文件')
    convert_parser.add_argument('--execute', action='store_true', help='实际执行')
    
    # 调整尺寸
    resize_parser = image_subparsers.add_parser('resize', help='调整图片尺寸')
    resize_parser.add_argument('-d', '--directory', required=True, help='目标目录')
    resize_parser.add_argument('-W', '--width', type=int, help='目标宽度')
    resize_parser.add_argument('-H', '--height', type=int, help='目标高度')
    resize_parser.add_argument('-s', '--scale', type=float, help='缩放比例')
    resize_parser.add_argument('--no-aspect', action='store_true', help='不保持宽高比')
    resize_parser.add_argument('--recursive', action='store_true', help='递归处理')
    resize_parser.add_argument('--suffix', default='_resized', help='输出文件后缀')
    resize_parser.add_argument('--execute', action='store_true', help='实际执行')
    
    # ========== 文件整理命令 ==========
    organize_parser = subparsers.add_parser('organize', help='批量整理文件')
    organize_subparsers = organize_parser.add_subparsers(dest='organize_type', help='整理类型')
    
    # 按日期整理
    org_date_parser = organize_subparsers.add_parser('date', help='按日期整理')
    org_date_parser.add_argument('-d', '--directory', required=True, help='目标目录')
    org_date_parser.add_argument('-f', '--format', default='%Y-%m', help='日期文件夹格式')
    org_date_parser.add_argument('--use-ctime', action='store_true', help='使用创建时间')
    org_date_parser.add_argument('--recursive', action='store_true', help='递归处理')
    org_date_parser.add_argument('--execute', action='store_true', help='实际执行')
    
    # 按类型整理
    org_type_parser = organize_subparsers.add_parser('type', help='按类型整理')
    org_type_parser.add_argument('-d', '--directory', required=True, help='目标目录')
    org_type_parser.add_argument('--recursive', action='store_true', help='递归处理')
    org_type_parser.add_argument('--execute', action='store_true', help='实际执行')
    
    # ========== 压缩解压命令 ==========
    archive_parser = subparsers.add_parser('archive', help='压缩/解压文件')
    archive_subparsers = archive_parser.add_subparsers(dest='archive_type', help='操作类型')
    
    # 压缩
    compress_parser = archive_subparsers.add_parser('compress', help='压缩文件/文件夹')
    compress_parser.add_argument('-i', '--input', nargs='+', required=True, help='要压缩的文件/文件夹')
    compress_parser.add_argument('-o', '--output', required=True, help='输出路径')
    compress_parser.add_argument('-f', '--format', default='zip', 
                                  choices=['zip', 'tar', 'tar.gz', 'tar.bz2'],
                                  help='压缩格式')
    compress_parser.add_argument('-l', '--level', type=int, default=6, help='压缩级别 (1-9)')
    
    # 解压
    extract_parser = archive_subparsers.add_parser('extract', help='解压文件')
    extract_parser.add_argument('-i', '--input', required=True, help='压缩包路径')
    extract_parser.add_argument('-o', '--output', help='输出目录')
    extract_parser.add_argument('-p', '--password', help='解压密码')
    
    # 批量解压
    batch_extract_parser = archive_subparsers.add_parser('batch-extract', help='批量解压')
    batch_extract_parser.add_argument('-d', '--directory', required=True, help='目标目录')
    batch_extract_parser.add_argument('-o', '--output', help='输出目录基路径')
    batch_extract_parser.add_argument('--recursive', action='store_true', help='递归查找')
    batch_extract_parser.add_argument('--delete-after', action='store_true', help='解压后删除原文件')
    batch_extract_parser.add_argument('--execute', action='store_true', help='实际执行（预览模式下仅列出）')
    
    return parser


def handle_rename(args):
    """处理重命名命令"""
    renamer = BatchRenamer()
    
    if args.rename_type == 'regex':
        changes = renamer.rename_by_pattern(
            args.directory, args.pattern, args.replacement,
            args.recursive, dry_run=not args.execute
        )
    elif args.rename_type == 'sequence':
        changes = renamer.rename_by_sequence(
            args.directory, args.prefix, args.suffix,
            args.start, args.padding, args.recursive,
            dry_run=not args.execute
        )
    elif args.rename_type == 'date':
        changes = renamer.rename_by_date(
            args.directory, args.format, args.prefix,
            args.use_ctime, args.recursive,
            dry_run=not args.execute
        )
    else:
        print("错误: 请指定重命名类型 (regex/sequence/date)")
        return 1
    
    if not changes:
        print("没有需要重命名的文件")
        return 0
    
    preview_changes(changes)
    
    if not args.execute:
        print("\n这是预览模式，使用 --execute 参数执行实际重命名")
    else:
        print(f"\n成功重命名 {len(changes)} 个文件")
    
    return 0


def handle_image(args):
    """处理图片命令"""
    processor = ImageProcessor()
    
    if args.image_type == 'convert':
        changes = processor.convert_format(
            args.directory, args.format, args.quality,
            args.recursive, args.delete_original,
            dry_run=not args.execute
        )
    elif args.image_type == 'resize':
        changes = processor.resize_images(
            args.directory, args.width, args.height, args.scale,
            not args.no_aspect, args.recursive, args.suffix,
            dry_run=not args.execute
        )
    else:
        print("错误: 请指定图片处理类型 (convert/resize)")
        return 1
    
    if not changes:
        print("没有需要处理的图片文件")
        return 0
    
    preview_changes(changes)
    
    if not args.execute:
        print("\n这是预览模式，使用 --execute 参数执行实际处理")
    else:
        print(f"\n成功处理 {len(changes)} 个文件")
    
    return 0


def handle_organize(args):
    """处理整理命令"""
    organizer = FileOrganizer()
    
    if args.organize_type == 'date':
        changes = organizer.organize_by_date(
            args.directory, args.format,
            args.use_ctime, args.recursive,
            dry_run=not args.execute
        )
    elif args.organize_type == 'type':
        changes = organizer.organize_by_type(
            args.directory, None, args.recursive,
            dry_run=not args.execute
        )
    else:
        print("错误: 请指定整理类型 (date/type)")
        return 1
    
    if not changes:
        print("没有需要整理的文件")
        return 0
    
    preview_changes(changes)
    
    if not args.execute:
        print("\n这是预览模式，使用 --execute 参数执行实际整理")
    else:
        print(f"\n成功整理 {len(changes)} 个文件")
    
    return 0


def handle_archive(args):
    """处理压缩解压命令"""
    manager = ArchiveManager()
    
    if args.archive_type == 'compress':
        try:
            result = manager.compress(
                args.input, args.output, args.format, args.level
            )
            print(f"压缩完成: {result}")
        except Exception as e:
            print(f"压缩失败: {e}")
            return 1
    
    elif args.archive_type == 'extract':
        try:
            result = manager.extract(args.input, args.output, args.password)
            print(f"解压完成: {result}")
        except Exception as e:
            print(f"解压失败: {e}")
            return 1
    
    elif args.archive_type == 'batch-extract':
        if not args.execute:
            # 预览模式：列出找到的压缩包
            path = Path(args.directory)
            if args.recursive:
                archives = list(path.rglob('*'))
            else:
                archives = list(path.iterdir())
            
            archives = [f for f in archives if f.is_file() and 
                       ''.join(f.suffixes).lower() in manager.SUPPORTED_ARCHIVE]
            
            if not archives:
                print("没有找到压缩包文件")
                return 0
            
            print(f"\n找到 {len(archives)} 个压缩包:")
            for i, arc in enumerate(archives, 1):
                print(f"{i}. {arc.name}")
            print("\n使用 --execute 参数执行解压")
        else:
            results = manager.batch_extract(
                args.directory, args.output,
                args.recursive, args.delete_after
            )
            print(f"\n成功解压 {len(results)} 个压缩包")
    
    else:
        print("错误: 请指定操作类型 (compress/extract/batch-extract)")
        return 1
    
    return 0


def main():
    """主函数"""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # 检查目录参数是否存在
    if hasattr(args, 'directory') and not os.path.isdir(args.directory):
        print(f"错误: 目录不存在: {args.directory}")
        return 1
    
    # 路由到对应的处理函数
    if args.command == 'rename':
        return handle_rename(args)
    elif args.command == 'image':
        return handle_image(args)
    elif args.command == 'organize':
        return handle_organize(args)
    elif args.command == 'archive':
        return handle_archive(args)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
