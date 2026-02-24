#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File Toolkit - 图形用户界面
使用 tkinter 构建，简单易用
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
import threading
import json

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from core import (
    BatchRenamer, ImageProcessor, FileOrganizer, ArchiveManager,
    preview_changes
)


class ToolTip:
    """工具提示类"""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.widget.bind("<Enter>", self.show)
        self.widget.bind("<Leave>", self.hide)
    
    def show(self, event=None):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        
        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(self.tooltip, text=self.text, 
                        background="#ffffe0", relief="solid", borderwidth=1,
                        font=("Microsoft YaHei", 9))
        label.pack()
    
    def hide(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None


class FileToolkitGUI:
    """文件工具包图形界面"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("📁 文件处理工具箱 File Toolkit")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        
        # 设置样式
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.configure_styles()
        
        # 初始化处理器
        self.renamer = BatchRenamer()
        self.image_processor = ImageProcessor()
        self.organizer = FileOrganizer()
        self.archive_manager = ArchiveManager()
        
        # 创建界面
        self.create_menu()
        self.create_main_frame()
        self.create_status_bar()
        
        # 加载配置
        self.config_file = Path.home() / '.file_toolkit_config.json'
        self.load_config()
    
    def configure_styles(self):
        """配置界面样式"""
        self.style.configure('TFrame', background='#f5f5f5')
        self.style.configure('TLabel', background='#f5f5f5', font=('Microsoft YaHei', 10))
        self.style.configure('TButton', font=('Microsoft YaHei', 10), padding=5)
        self.style.configure('TEntry', font=('Microsoft YaHei', 10))
        self.style.configure('TCheckbutton', background='#f5f5f5', font=('Microsoft YaHei', 10))
        self.style.configure('TNotebook', background='#f5f5f5')
        self.style.configure('TNotebook.Tab', font=('Microsoft YaHei', 11), padding=10)
        
        # 标题样式
        self.style.configure('Header.TLabel', font=('Microsoft YaHei', 14, 'bold'), 
                           foreground='#2196F3', background='#f5f5f5')
        
        # 操作按钮样式
        self.style.configure('Action.TButton', font=('Microsoft YaHei', 11, 'bold'),
                           background='#4CAF50', foreground='white')
        
        # 预览按钮样式
        self.style.configure('Preview.TButton', font=('Microsoft YaHei', 11),
                           background='#2196F3', foreground='white')
    
    def create_menu(self):
        """创建菜单栏"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="打开目录", command=self.browse_directory)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        
        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="使用说明", command=self.show_help)
        help_menu.add_command(label="关于", command=self.show_about)
    
    def create_main_frame(self):
        """创建主框架"""
        # 主容器
        main_container = ttk.Frame(self.root, padding="10")
        main_container.grid(row=0, column=0, sticky="nsew")
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_container.columnconfigure(0, weight=1)
        main_container.rowconfigure(1, weight=1)
        
        # 标题
        header = ttk.Label(main_container, text="📁 文件处理工具箱", 
                          style='Header.TLabel')
        header.grid(row=0, column=0, pady=(0, 10), sticky="w")
        
        # 创建标签页
        self.notebook = ttk.Notebook(main_container)
        self.notebook.grid(row=1, column=0, sticky="nsew", pady=5)
        
        # 添加各个功能标签页
        self.create_rename_tab()
        self.create_image_tab()
        self.create_organize_tab()
        self.create_archive_tab()
        
        # 日志区域
        self.create_log_area(main_container)
    
    def create_rename_tab(self):
        """创建重命名标签页"""
        tab = ttk.Frame(self.notebook, padding="15")
        self.notebook.add(tab, text="📝 批量重命名")
        
        # 目录选择
        row = 0
        ttk.Label(tab, text="目标目录:").grid(row=row, column=0, sticky="w", pady=5)
        self.rename_dir_var = tk.StringVar()
        ttk.Entry(tab, textvariable=self.rename_dir_var, width=50).grid(row=row, column=1, sticky="ew", padx=5)
        ttk.Button(tab, text="浏览...", command=lambda: self.browse_directory(self.rename_dir_var)).grid(row=row, column=2)
        
        # 重命名类型
        row += 1
        ttk.Label(tab, text="重命名方式:").grid(row=row, column=0, sticky="w", pady=10)
        self.rename_type_var = tk.StringVar(value="sequence")
        ttk.Radiobutton(tab, text="按序号", variable=self.rename_type_var, 
                       value="sequence", command=self.update_rename_options).grid(row=row, column=1, sticky="w")
        ttk.Radiobutton(tab, text="按日期", variable=self.rename_type_var, 
                       value="date", command=self.update_rename_options).grid(row=row, column=1, sticky="w", padx=(80, 0))
        ttk.Radiobutton(tab, text="正则替换", variable=self.rename_type_var, 
                       value="regex", command=self.update_rename_options).grid(row=row, column=1, sticky="w", padx=(160, 0))
        
        # 选项框架
        row += 1
        self.rename_options_frame = ttk.LabelFrame(tab, text="选项", padding="10")
        self.rename_options_frame.grid(row=row, column=0, columnspan=3, sticky="ew", pady=10)
        self.rename_options_frame.columnconfigure(1, weight=1)
        
        # 序号选项
        self.seq_frame = ttk.Frame(self.rename_options_frame)
        ttk.Label(self.seq_frame, text="前缀:").grid(row=0, column=0, sticky="w")
        self.seq_prefix_var = tk.StringVar(value="file_")
        ttk.Entry(self.seq_frame, textvariable=self.seq_prefix_var, width=20).grid(row=0, column=1, sticky="w", padx=5)
        
        ttk.Label(self.seq_frame, text="后缀:").grid(row=0, column=2, sticky="w", padx=(15, 0))
        self.seq_suffix_var = tk.StringVar()
        ttk.Entry(self.seq_frame, textvariable=self.seq_suffix_var, width=15).grid(row=0, column=3, sticky="w", padx=5)
        
        ttk.Label(self.seq_frame, text="起始序号:").grid(row=1, column=0, sticky="w", pady=10)
        self.seq_start_var = tk.IntVar(value=1)
        ttk.Spinbox(self.seq_frame, from_=0, to=9999, textvariable=self.seq_start_var, width=8).grid(row=1, column=1, sticky="w", padx=5)
        
        ttk.Label(self.seq_frame, text="位数:").grid(row=1, column=2, sticky="w", padx=(15, 0))
        self.seq_padding_var = tk.IntVar(value=3)
        ttk.Spinbox(self.seq_frame, from_=1, to=10, textvariable=self.seq_padding_var, width=8).grid(row=1, column=3, sticky="w", padx=5)
        
        # 日期选项
        self.date_frame = ttk.Frame(self.rename_options_frame)
        ttk.Label(self.date_frame, text="前缀:").grid(row=0, column=0, sticky="w")
        self.date_prefix_var = tk.StringVar()
        ttk.Entry(self.date_frame, textvariable=self.date_prefix_var, width=20).grid(row=0, column=1, sticky="w", padx=5)
        
        ttk.Label(self.date_frame, text="日期格式:").grid(row=1, column=0, sticky="w", pady=10)
        self.date_format_var = tk.StringVar(value="%Y%m%d_%H%M%S")
        format_combo = ttk.Combobox(self.date_frame, textvariable=self.date_format_var, 
                                   values=["%Y%m%d_%H%M%S", "%Y-%m-%d", "%Y%m%d", "%Y年%m月%d日"], width=20)
        format_combo.grid(row=1, column=1, sticky="w", padx=5)
        
        self.date_use_ctime_var = tk.BooleanVar()
        ttk.Checkbutton(self.date_frame, text="使用创建时间(否则用修改时间)", 
                       variable=self.date_use_ctime_var).grid(row=2, column=0, columnspan=2, sticky="w")
        
        # 正则选项
        self.regex_frame = ttk.Frame(self.rename_options_frame)
        ttk.Label(self.regex_frame, text="查找模式:").grid(row=0, column=0, sticky="w")
        self.regex_pattern_var = tk.StringVar()
        ttk.Entry(self.regex_frame, textvariable=self.regex_pattern_var, width=40).grid(row=0, column=1, sticky="ew", padx=5)
        
        ttk.Label(self.regex_frame, text="替换为:").grid(row=1, column=0, sticky="w", pady=10)
        self.regex_replacement_var = tk.StringVar()
        ttk.Entry(self.regex_frame, textvariable=self.regex_replacement_var, width=40).grid(row=1, column=1, sticky="ew", padx=5)
        
        # 通用选项
        row += 1
        self.rename_recursive_var = tk.BooleanVar()
        ttk.Checkbutton(tab, text="递归处理子目录", variable=self.rename_recursive_var).grid(row=row, column=0, columnspan=2, sticky="w", pady=5)
        
        # 按钮
        row += 1
        btn_frame = ttk.Frame(tab)
        btn_frame.grid(row=row, column=0, columnspan=3, pady=20)
        
        ttk.Button(btn_frame, text="👁️ 预览", command=self.preview_rename, 
                  style='Preview.TButton', width=12).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="✅ 执行", command=self.execute_rename, 
                  style='Action.TButton', width=12).pack(side="left", padx=5)
        
        # 初始化显示
        self.update_rename_options()
        
        tab.columnconfigure(1, weight=1)
    
    def create_image_tab(self):
        """创建图片处理标签页"""
        tab = ttk.Frame(self.notebook, padding="15")
        self.notebook.add(tab, text="🖼️ 图片处理")
        
        # 目录选择
        row = 0
        ttk.Label(tab, text="目标目录:").grid(row=row, column=0, sticky="w", pady=5)
        self.image_dir_var = tk.StringVar()
        ttk.Entry(tab, textvariable=self.image_dir_var, width=50).grid(row=row, column=1, sticky="ew", padx=5)
        ttk.Button(tab, text="浏览...", command=lambda: self.browse_directory(self.image_dir_var)).grid(row=row, column=2)
        
        # 处理类型
        row += 1
        ttk.Label(tab, text="处理方式:").grid(row=row, column=0, sticky="w", pady=10)
        self.image_type_var = tk.StringVar(value="convert")
        ttk.Radiobutton(tab, text="格式转换", variable=self.image_type_var, 
                       value="convert", command=self.update_image_options).grid(row=row, column=1, sticky="w")
        ttk.Radiobutton(tab, text="调整尺寸", variable=self.image_type_var, 
                       value="resize", command=self.update_image_options).grid(row=row, column=1, sticky="w", padx=(90, 0))
        
        # 选项框架
        row += 1
        self.image_options_frame = ttk.LabelFrame(tab, text="选项", padding="10")
        self.image_options_frame.grid(row=row, column=0, columnspan=3, sticky="ew", pady=10)
        self.image_options_frame.columnconfigure(1, weight=1)
        
        # 格式转换选项
        self.convert_frame = ttk.Frame(self.image_options_frame)
        ttk.Label(self.convert_frame, text="目标格式:").grid(row=0, column=0, sticky="w")
        self.convert_format_var = tk.StringVar(value="jpg")
        format_combo = ttk.Combobox(self.convert_frame, textvariable=self.convert_format_var,
                                   values=["jpg", "png", "webp", "gif", "bmp"], width=10)
        format_combo.grid(row=0, column=1, sticky="w", padx=5)
        
        ttk.Label(self.convert_frame, text="质量(1-100):").grid(row=0, column=2, sticky="w", padx=(20, 0))
        self.convert_quality_var = tk.IntVar(value=90)
        ttk.Spinbox(self.convert_frame, from_=1, to=100, textvariable=self.convert_quality_var, width=8).grid(row=0, column=3, sticky="w", padx=5)
        
        self.convert_delete_var = tk.BooleanVar()
        ttk.Checkbutton(self.convert_frame, text="转换后删除原文件", 
                       variable=self.convert_delete_var).grid(row=1, column=0, columnspan=4, sticky="w", pady=10)
        
        # 调整尺寸选项
        self.resize_frame = ttk.Frame(self.image_options_frame)
        
        ttk.Label(self.resize_frame, text="缩放比例:").grid(row=0, column=0, sticky="w")
        self.resize_scale_var = tk.DoubleVar(value=0.5)
        ttk.Spinbox(self.resize_frame, from_=0.1, to=10.0, increment=0.1,
                   textvariable=self.resize_scale_var, width=8).grid(row=0, column=1, sticky="w", padx=5)
        ttk.Label(self.resize_frame, text="(优先使用缩放比例)").grid(row=0, column=2, sticky="w")
        
        ttk.Label(self.resize_frame, text="指定宽度:").grid(row=1, column=0, sticky="w", pady=10)
        self.resize_width_var = tk.IntVar()
        ttk.Entry(self.resize_frame, textvariable=self.resize_width_var, width=10).grid(row=1, column=1, sticky="w", padx=5)
        
        ttk.Label(self.resize_frame, text="指定高度:").grid(row=1, column=2, sticky="w", padx=(20, 0))
        self.resize_height_var = tk.IntVar()
        ttk.Entry(self.resize_frame, textvariable=self.resize_height_var, width=10).grid(row=1, column=3, sticky="w", padx=5)
        
        self.resize_aspect_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(self.resize_frame, text="保持宽高比", 
                       variable=self.resize_aspect_var).grid(row=2, column=0, columnspan=2, sticky="w")
        
        ttk.Label(self.resize_frame, text="输出后缀:").grid(row=2, column=2, sticky="w", padx=(20, 0))
        self.resize_suffix_var = tk.StringVar(value="_resized")
        ttk.Entry(self.resize_frame, textvariable=self.resize_suffix_var, width=15).grid(row=2, column=3, sticky="w", padx=5)
        
        # 通用选项
        row += 1
        self.image_recursive_var = tk.BooleanVar()
        ttk.Checkbutton(tab, text="递归处理子目录", variable=self.image_recursive_var).grid(row=row, column=0, columnspan=2, sticky="w", pady=5)
        
        # 按钮
        row += 1
        btn_frame = ttk.Frame(tab)
        btn_frame.grid(row=row, column=0, columnspan=3, pady=20)
        
        ttk.Button(btn_frame, text="👁️ 预览", command=self.preview_image, 
                  style='Preview.TButton', width=12).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="✅ 执行", command=self.execute_image, 
                  style='Action.TButton', width=12).pack(side="left", padx=5)
        
        # 初始化显示
        self.update_image_options()
        
        tab.columnconfigure(1, weight=1)
    
    def create_organize_tab(self):
        """创建文件整理标签页"""
        tab = ttk.Frame(self.notebook, padding="15")
        self.notebook.add(tab, text="📂 文件整理")
        
        # 目录选择
        row = 0
        ttk.Label(tab, text="目标目录:").grid(row=row, column=0, sticky="w", pady=5)
        self.organize_dir_var = tk.StringVar()
        ttk.Entry(tab, textvariable=self.organize_dir_var, width=50).grid(row=row, column=1, sticky="ew", padx=5)
        ttk.Button(tab, text="浏览...", command=lambda: self.browse_directory(self.organize_dir_var)).grid(row=row, column=2)
        
        # 整理类型
        row += 1
        ttk.Label(tab, text="整理方式:").grid(row=row, column=0, sticky="w", pady=10)
        self.organize_type_var = tk.StringVar(value="date")
        ttk.Radiobutton(tab, text="按日期", variable=self.organize_type_var, 
                       value="date", command=self.update_organize_options).grid(row=row, column=1, sticky="w")
        ttk.Radiobutton(tab, text="按类型", variable=self.organize_type_var, 
                       value="type", command=self.update_organize_options).grid(row=row, column=1, sticky="w", padx=(80, 0))
        
        # 选项框架
        row += 1
        self.organize_options_frame = ttk.LabelFrame(tab, text="选项", padding="10")
        self.organize_options_frame.grid(row=row, column=0, columnspan=3, sticky="ew", pady=10)
        self.organize_options_frame.columnconfigure(1, weight=1)
        
        # 按日期选项
        self.org_date_frame = ttk.Frame(self.organize_options_frame)
        ttk.Label(self.org_date_frame, text="日期格式:").grid(row=0, column=0, sticky="w")
        self.org_date_format_var = tk.StringVar(value="%Y-%m")
        format_combo = ttk.Combobox(self.org_date_frame, textvariable=self.org_date_format_var,
                                   values=["%Y-%m", "%Y-%m-%d", "%Y年%m月", "%Y"], width=15)
        format_combo.grid(row=0, column=1, sticky="w", padx=5)
        
        self.org_date_ctime_var = tk.BooleanVar()
        ttk.Checkbutton(self.org_date_frame, text="使用创建时间", 
                       variable=self.org_date_ctime_var).grid(row=1, column=0, columnspan=2, sticky="w", pady=10)
        
        # 按类型选项
        self.org_type_frame = ttk.Frame(self.organize_options_frame)
        ttk.Label(self.org_type_frame, text="文件将按类型分类到以下文件夹:").grid(row=0, column=0, sticky="w")
        
        type_text = """📷 Images: jpg, png, gif, bmp, webp, svg...
🎬 Videos: mp4, avi, mkv, mov, wmv...
🎵 Audio: mp3, wav, flac, aac, ogg...
📄 Documents: pdf, doc, xls, ppt, txt, md...
📦 Archives: zip, rar, 7z, tar, gz...
💻 Code: py, js, html, css, java, cpp...
⚙️ Others: 其他类型"""
        
        type_label = tk.Label(self.org_type_frame, text=type_text, justify="left",
                             font=('Consolas', 9), bg='#f5f5f5', fg='#333')
        type_label.grid(row=1, column=0, sticky="w", pady=5)
        
        # 通用选项
        row += 1
        self.organize_recursive_var = tk.BooleanVar()
        ttk.Checkbutton(tab, text="递归处理子目录", variable=self.organize_recursive_var).grid(row=row, column=0, columnspan=2, sticky="w", pady=5)
        
        # 按钮
        row += 1
        btn_frame = ttk.Frame(tab)
        btn_frame.grid(row=row, column=0, columnspan=3, pady=20)
        
        ttk.Button(btn_frame, text="👁️ 预览", command=self.preview_organize, 
                  style='Preview.TButton', width=12).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="✅ 执行", command=self.execute_organize, 
                  style='Action.TButton', width=12).pack(side="left", padx=5)
        
        # 初始化显示
        self.update_organize_options()
        
        tab.columnconfigure(1, weight=1)
    
    def create_archive_tab(self):
        """创建压缩解压标签页"""
        tab = ttk.Frame(self.notebook, padding="15")
        self.notebook.add(tab, text="📦 压缩解压")
        
        # 操作类型
        row = 0
        ttk.Label(tab, text="操作类型:").grid(row=row, column=0, sticky="w", pady=5)
        self.archive_op_var = tk.StringVar(value="compress")
        ttk.Radiobutton(tab, text="压缩", variable=self.archive_op_var, 
                       value="compress", command=self.update_archive_options).grid(row=row, column=1, sticky="w")
        ttk.Radiobutton(tab, text="解压", variable=self.archive_op_var, 
                       value="extract", command=self.update_archive_options).grid(row=row, column=1, sticky="w", padx=(70, 0))
        ttk.Radiobutton(tab, text="批量解压", variable=self.archive_op_var, 
                       value="batch", command=self.update_archive_options).grid(row=row, column=1, sticky="w", padx=(140, 0))
        
        # 选项框架
        row += 1
        self.archive_options_frame = ttk.LabelFrame(tab, text="选项", padding="10")
        self.archive_options_frame.grid(row=row, column=0, columnspan=3, sticky="ew", pady=10)
        self.archive_options_frame.columnconfigure(1, weight=1)
        
        # 压缩选项
        self.compress_frame = ttk.Frame(self.archive_options_frame)
        
        ttk.Label(self.compress_frame, text="选择文件/文件夹:").grid(row=0, column=0, sticky="w")
        self.compress_sources_var = tk.StringVar()
        ttk.Entry(self.compress_frame, textvariable=self.compress_sources_var, width=45).grid(row=0, column=1, sticky="ew", padx=5)
        ttk.Button(self.compress_frame, text="添加...", command=self.add_compress_sources).grid(row=0, column=2)
        
        ttk.Label(self.compress_frame, text="输出路径:").grid(row=1, column=0, sticky="w", pady=10)
        self.compress_output_var = tk.StringVar()
        ttk.Entry(self.compress_frame, textvariable=self.compress_output_var, width=45).grid(row=1, column=1, sticky="ew", padx=5)
        ttk.Button(self.compress_frame, text="浏览...", command=self.browse_save_file).grid(row=1, column=2)
        
        ttk.Label(self.compress_frame, text="格式:").grid(row=2, column=0, sticky="w")
        self.compress_format_var = tk.StringVar(value="zip")
        ttk.Combobox(self.compress_frame, textvariable=self.compress_format_var,
                    values=["zip", "tar", "tar.gz", "tar.bz2"], width=12).grid(row=2, column=1, sticky="w", padx=5)
        
        # 解压选项
        self.extract_frame = ttk.Frame(self.archive_options_frame)
        
        ttk.Label(self.extract_frame, text="压缩包路径:").grid(row=0, column=0, sticky="w")
        self.extract_source_var = tk.StringVar()
        ttk.Entry(self.extract_frame, textvariable=self.extract_source_var, width=45).grid(row=0, column=1, sticky="ew", padx=5)
        ttk.Button(self.extract_frame, text="浏览...", command=self.browse_archive_file).grid(row=0, column=2)
        
        ttk.Label(self.extract_frame, text="输出目录:").grid(row=1, column=0, sticky="w", pady=10)
        self.extract_output_var = tk.StringVar()
        ttk.Entry(self.extract_frame, textvariable=self.extract_output_var, width=45).grid(row=1, column=1, sticky="ew", padx=5)
        ttk.Button(self.extract_frame, text="浏览...", command=lambda: self.browse_directory(self.extract_output_var)).grid(row=1, column=2)
        
        ttk.Label(self.extract_frame, text="密码(可选):").grid(row=2, column=0, sticky="w")
        self.extract_password_var = tk.StringVar()
        ttk.Entry(self.extract_frame, textvariable=self.extract_password_var, width=20, show="*").grid(row=2, column=1, sticky="w", padx=5)
        
        # 批量解压选项
        self.batch_frame = ttk.Frame(self.archive_options_frame)
        
        ttk.Label(self.batch_frame, text="目标目录:").grid(row=0, column=0, sticky="w")
        self.batch_dir_var = tk.StringVar()
        ttk.Entry(self.batch_frame, textvariable=self.batch_dir_var, width=45).grid(row=0, column=1, sticky="ew", padx=5)
        ttk.Button(self.batch_frame, text="浏览...", command=lambda: self.browse_directory(self.batch_dir_var)).grid(row=0, column=2)
        
        ttk.Label(self.batch_frame, text="输出目录基路径(可选):").grid(row=1, column=0, sticky="w", pady=10)
        self.batch_output_var = tk.StringVar()
        ttk.Entry(self.batch_frame, textvariable=self.batch_output_var, width=45).grid(row=1, column=1, sticky="ew", padx=5)
        ttk.Button(self.batch_frame, text="浏览...", command=lambda: self.browse_directory(self.batch_output_var)).grid(row=1, column=2)
        
        self.batch_recursive_var = tk.BooleanVar()
        ttk.Checkbutton(self.batch_frame, text="递归查找子目录", 
                       variable=self.batch_recursive_var).grid(row=2, column=0, columnspan=2, sticky="w")
        
        self.batch_delete_var = tk.BooleanVar()
        ttk.Checkbutton(self.batch_frame, text="解压后删除原压缩包", 
                       variable=self.batch_delete_var).grid(row=3, column=0, columnspan=2, sticky="w")
        
        # 按钮
        row += 1
        self.archive_btn_frame = ttk.Frame(tab)
        self.archive_btn_frame.grid(row=row, column=0, columnspan=3, pady=20)
        
        ttk.Button(self.archive_btn_frame, text="✅ 执行", command=self.execute_archive, 
                  style='Action.TButton', width=12).pack(side="left", padx=5)
        
        # 初始化显示
        self.update_archive_options()
        
        tab.columnconfigure(1, weight=1)
    
    def create_log_area(self, parent):
        """创建日志区域"""
        log_frame = ttk.LabelFrame(parent, text="操作日志", padding="5")
        log_frame.grid(row=2, column=0, sticky="nsew", pady=5)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, 
                                                   font=('Consolas', 9))
        self.log_text.grid(row=0, column=0, sticky="nsew")
        
        # 清除按钮
        ttk.Button(log_frame, text="清除日志", command=self.clear_log).grid(row=1, column=0, sticky="e", pady=5)
    
    def create_status_bar(self):
        """创建状态栏"""
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, 
                              relief="sunken", anchor="w", padding=(5, 2))
        status_bar.grid(row=1, column=0, sticky="ew")
    
    # ========== 界面更新方法 ==========
    
    def update_rename_options(self):
        """更新重命名选项显示"""
        # 隐藏所有选项框架
        for frame in [self.seq_frame, self.date_frame, self.regex_frame]:
            frame.grid_forget()
        
        # 显示对应选项
        rename_type = self.rename_type_var.get()
        if rename_type == "sequence":
            self.seq_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
        elif rename_type == "date":
            self.date_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
        elif rename_type == "regex":
            self.regex_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
    
    def update_image_options(self):
        """更新图片处理选项显示"""
        for frame in [self.convert_frame, self.resize_frame]:
            frame.grid_forget()
        
        image_type = self.image_type_var.get()
        if image_type == "convert":
            self.convert_frame.grid(row=0, column=0, columnspan=4, sticky="ew")
        elif image_type == "resize":
            self.resize_frame.grid(row=0, column=0, columnspan=4, sticky="ew")
    
    def update_organize_options(self):
        """更新整理选项显示"""
        for frame in [self.org_date_frame, self.org_type_frame]:
            frame.grid_forget()
        
        organize_type = self.organize_type_var.get()
        if organize_type == "date":
            self.org_date_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
        elif organize_type == "type":
            self.org_type_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
    
    def update_archive_options(self):
        """更新压缩解压选项显示"""
        for frame in [self.compress_frame, self.extract_frame, self.batch_frame]:
            frame.grid_forget()
        
        op_type = self.archive_op_var.get()
        if op_type == "compress":
            self.compress_frame.grid(row=0, column=0, columnspan=3, sticky="ew")
        elif op_type == "extract":
            self.extract_frame.grid(row=0, column=0, columnspan=3, sticky="ew")
        elif op_type == "batch":
            self.batch_frame.grid(row=0, column=0, columnspan=3, sticky="ew")
    
    # ========== 文件浏览方法 ==========
    
    def browse_directory(self, var=None):
        """浏览目录"""
        directory = filedialog.askdirectory()
        if directory:
            if var:
                var.set(directory)
            else:
                # 更新所有目录变量
                self.rename_dir_var.set(directory)
                self.image_dir_var.set(directory)
                self.organize_dir_var.set(directory)
                self.batch_dir_var.set(directory)
            self.log(f"选择目录: {directory}")
    
    def browse_save_file(self):
        """浏览保存文件"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".zip",
            filetypes=[("ZIP files", "*.zip"), ("TAR files", "*.tar"), 
                      ("TAR.GZ files", "*.tar.gz"), ("All files", "*.*")]
        )
        if filename:
            self.compress_output_var.set(filename)
    
    def browse_archive_file(self):
        """浏览压缩包文件"""
        filename = filedialog.askopenfilename(
            filetypes=[("Archive files", "*.zip *.tar *.tar.gz *.tar.bz2"),
                      ("All files", "*.*")]
        )
        if filename:
            self.extract_source_var.set(filename)
    
    def add_compress_sources(self):
        """添加压缩源文件"""
        files = filedialog.askopenfilenames(title="选择要压缩的文件")
        if files:
            current = self.compress_sources_var.get()
            if current:
                current += ";"
            current += ";".join(files)
            self.compress_sources_var.set(current)
    
    # ========== 操作执行方法 ==========
    
    def preview_rename(self):
        """预览重命名"""
        directory = self.rename_dir_var.get()
        if not self.validate_directory(directory):
            return
        
        try:
            rename_type = self.rename_type_var.get()
            recursive = self.rename_recursive_var.get()
            
            if rename_type == "sequence":
                changes = self.renamer.rename_by_sequence(
                    directory,
                    prefix=self.seq_prefix_var.get(),
                    suffix=self.seq_suffix_var.get(),
                    start=self.seq_start_var.get(),
                    padding=self.seq_padding_var.get(),
                    recursive=recursive,
                    dry_run=True
                )
            elif rename_type == "date":
                changes = self.renamer.rename_by_date(
                    directory,
                    date_format=self.date_format_var.get(),
                    prefix=self.date_prefix_var.get(),
                    use_creation_time=self.date_use_ctime_var.get(),
                    recursive=recursive,
                    dry_run=True
                )
            elif rename_type == "regex":
                pattern = self.regex_pattern_var.get()
                if not pattern:
                    messagebox.showwarning("警告", "请输入正则表达式模式")
                    return
                changes = self.renamer.rename_by_pattern(
                    directory,
                    pattern=pattern,
                    replacement=self.regex_replacement_var.get(),
                    recursive=recursive,
                    dry_run=True
                )
            
            self.show_preview(changes, "重命名预览")
            
        except Exception as e:
            messagebox.showerror("错误", f"预览失败: {str(e)}")
    
    def execute_rename(self):
        """执行重命名"""
        if not messagebox.askyesno("确认", "确定要执行重命名操作吗？"):
            return
        
        directory = self.rename_dir_var.get()
        if not self.validate_directory(directory):
            return
        
        def task():
            try:
                self.set_status("正在重命名...")
                rename_type = self.rename_type_var.get()
                recursive = self.rename_recursive_var.get()
                
                if rename_type == "sequence":
                    changes = self.renamer.rename_by_sequence(
                        directory,
                        prefix=self.seq_prefix_var.get(),
                        suffix=self.seq_suffix_var.get(),
                        start=self.seq_start_var.get(),
                        padding=self.seq_padding_var.get(),
                        recursive=recursive,
                        dry_run=False
                    )
                elif rename_type == "date":
                    changes = self.renamer.rename_by_date(
                        directory,
                        date_format=self.date_format_var.get(),
                        prefix=self.date_prefix_var.get(),
                        use_creation_time=self.date_use_ctime_var.get(),
                        recursive=recursive,
                        dry_run=False
                    )
                elif rename_type == "regex":
                    changes = self.renamer.rename_by_pattern(
                        directory,
                        pattern=self.regex_pattern_var.get(),
                        replacement=self.regex_replacement_var.get(),
                        recursive=recursive,
                        dry_run=False
                    )
                
                self.root.after(0, lambda: self.operation_complete(f"成功重命名 {len(changes)} 个文件"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"操作失败: {str(e)}"))
                self.set_status("就绪")
        
        threading.Thread(target=task, daemon=True).start()
    
    def preview_image(self):
        """预览图片处理"""
        directory = self.image_dir_var.get()
        if not self.validate_directory(directory):
            return
        
        try:
            image_type = self.image_type_var.get()
            recursive = self.image_recursive_var.get()
            
            if image_type == "convert":
                changes = self.image_processor.convert_format(
                    directory,
                    target_format=self.convert_format_var.get(),
                    quality=self.convert_quality_var.get(),
                    recursive=recursive,
                    dry_run=True
                )
            elif image_type == "resize":
                width = self.resize_width_var.get() or None
                height = self.resize_height_var.get() or None
                scale = self.resize_scale_var.get() if self.resize_scale_var.get() != 1.0 else None
                
                changes = self.image_processor.resize_images(
                    directory,
                    width=width,
                    height=height,
                    scale=scale,
                    maintain_aspect=self.resize_aspect_var.get(),
                    recursive=recursive,
                    suffix=self.resize_suffix_var.get(),
                    dry_run=True
                )
            
            self.show_preview(changes, "图片处理预览")
            
        except Exception as e:
            messagebox.showerror("错误", f"预览失败: {str(e)}")
    
    def execute_image(self):
        """执行图片处理"""
        if not messagebox.askyesno("确认", "确定要执行图片处理吗？"):
            return
        
        directory = self.image_dir_var.get()
        if not self.validate_directory(directory):
            return
        
        def task():
            try:
                self.set_status("正在处理图片...")
                image_type = self.image_type_var.get()
                recursive = self.image_recursive_var.get()
                
                if image_type == "convert":
                    changes = self.image_processor.convert_format(
                        directory,
                        target_format=self.convert_format_var.get(),
                        quality=self.convert_quality_var.get(),
                        recursive=recursive,
                        delete_original=self.convert_delete_var.get(),
                        dry_run=False
                    )
                elif image_type == "resize":
                    width = self.resize_width_var.get() or None
                    height = self.resize_height_var.get() or None
                    scale = self.resize_scale_var.get() if self.resize_scale_var.get() != 1.0 else None
                    
                    changes = self.image_processor.resize_images(
                        directory,
                        width=width,
                        height=height,
                        scale=scale,
                        maintain_aspect=self.resize_aspect_var.get(),
                        recursive=recursive,
                        suffix=self.resize_suffix_var.get(),
                        dry_run=False
                    )
                
                self.root.after(0, lambda: self.operation_complete(f"成功处理 {len(changes)} 个图片文件"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"操作失败: {str(e)}"))
                self.set_status("就绪")
        
        threading.Thread(target=task, daemon=True).start()
    
    def preview_organize(self):
        """预览文件整理"""
        directory = self.organize_dir_var.get()
        if not self.validate_directory(directory):
            return
        
        try:
            organize_type = self.organize_type_var.get()
            recursive = self.organize_recursive_var.get()
            
            if organize_type == "date":
                changes = self.organizer.organize_by_date(
                    directory,
                    date_format=self.org_date_format_var.get(),
                    use_creation_time=self.org_date_ctime_var.get(),
                    recursive=recursive,
                    dry_run=True
                )
            elif organize_type == "type":
                changes = self.organizer.organize_by_type(
                    directory,
                    recursive=recursive,
                    dry_run=True
                )
            
            self.show_preview(changes, "文件整理预览")
            
        except Exception as e:
            messagebox.showerror("错误", f"预览失败: {str(e)}")
    
    def execute_organize(self):
        """执行文件整理"""
        if not messagebox.askyesno("确认", "确定要执行文件整理吗？"):
            return
        
        directory = self.organize_dir_var.get()
        if not self.validate_directory(directory):
            return
        
        def task():
            try:
                self.set_status("正在整理文件...")
                organize_type = self.organize_type_var.get()
                recursive = self.organize_recursive_var.get()
                
                if organize_type == "date":
                    changes = self.organizer.organize_by_date(
                        directory,
                        date_format=self.org_date_format_var.get(),
                        use_creation_time=self.org_date_ctime_var.get(),
                        recursive=recursive,
                        dry_run=False
                    )
                elif organize_type == "type":
                    changes = self.organizer.organize_by_type(
                        directory,
                        recursive=recursive,
                        dry_run=False
                    )
                
                self.root.after(0, lambda: self.operation_complete(f"成功整理 {len(changes)} 个文件"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"操作失败: {str(e)}"))
                self.set_status("就绪")
        
        threading.Thread(target=task, daemon=True).start()
    
    def execute_archive(self):
        """执行压缩解压操作"""
        op_type = self.archive_op_var.get()
        
        def task():
            try:
                if op_type == "compress":
                    self.set_status("正在压缩...")
                    sources = self.compress_sources_var.get().split(";")
                    sources = [s for s in sources if s]
                    if not sources:
                        self.root.after(0, lambda: messagebox.showwarning("警告", "请选择要压缩的文件"))
                        return
                    
                    output = self.compress_output_var.get()
                    if not output:
                        self.root.after(0, lambda: messagebox.showwarning("警告", "请选择输出路径"))
                        return
                    
                    result = self.archive_manager.compress(
                        sources, output,
                        archive_format=self.compress_format_var.get()
                    )
                    self.root.after(0, lambda: self.operation_complete(f"压缩完成: {result}"))
                    
                elif op_type == "extract":
                    self.set_status("正在解压...")
                    source = self.extract_source_var.get()
                    if not source:
                        self.root.after(0, lambda: messagebox.showwarning("警告", "请选择压缩包"))
                        return
                    
                    output = self.extract_output_var.get() or None
                    password = self.extract_password_var.get() or None
                    
                    result = self.archive_manager.extract(source, output, password)
                    self.root.after(0, lambda: self.operation_complete(f"解压完成: {result}"))
                    
                elif op_type == "batch":
                    self.set_status("正在批量解压...")
                    directory = self.batch_dir_var.get()
                    if not directory:
                        self.root.after(0, lambda: messagebox.showwarning("警告", "请选择目标目录"))
                        return
                    
                    results = self.archive_manager.batch_extract(
                        directory,
                        output_dir=self.batch_output_var.get() or None,
                        recursive=self.batch_recursive_var.get(),
                        delete_after=self.batch_delete_var.get()
                    )
                    self.root.after(0, lambda: self.operation_complete(f"成功解压 {len(results)} 个压缩包"))
                    
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"操作失败: {str(e)}"))
                self.set_status("就绪")
        
        if messagebox.askyesno("确认", "确定要执行此操作吗？"):
            threading.Thread(target=task, daemon=True).start()
    
    # ========== 辅助方法 ==========
    
    def validate_directory(self, directory):
        """验证目录"""
        if not directory:
            messagebox.showwarning("警告", "请选择目标目录")
            return False
        if not os.path.isdir(directory):
            messagebox.showerror("错误", f"目录不存在: {directory}")
            return False
        return True
    
    def show_preview(self, changes, title):
        """显示预览对话框"""
        if not changes:
            messagebox.showinfo("提示", "没有需要处理的文件")
            return
        
        preview_window = tk.Toplevel(self.root)
        preview_window.title(title)
        preview_window.geometry("600x400")
        preview_window.transient(self.root)
        
        # 预览文本
        text = scrolledtext.ScrolledText(preview_window, font=('Consolas', 9))
        text.pack(fill="both", expand=True, padx=10, pady=10)
        
        text.insert("end", f"共 {len(changes)} 个文件:\n")
        text.insert("end", "=" * 60 + "\n\n")
        
        for i, (old, new) in enumerate(changes[:50], 1):
            old_name = Path(old).name
            new_name = Path(new).name
            text.insert("end", f"{i}. {old_name}\n   -> {new_name}\n\n")
        
        if len(changes) > 50:
            text.insert("end", f"... 还有 {len(changes) - 50} 项\n")
        
        text.config(state="disabled")
        
        # 关闭按钮
        ttk.Button(preview_window, text="关闭", command=preview_window.destroy).pack(pady=10)
    
    def operation_complete(self, message):
        """操作完成"""
        self.log(message)
        self.set_status(message)
        messagebox.showinfo("完成", message)
    
    def log(self, message):
        """添加日志"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{timestamp}] {message}\n")
        self.log_text.see("end")
    
    def clear_log(self):
        """清除日志"""
        self.log_text.delete(1.0, "end")
    
    def set_status(self, message):
        """设置状态栏"""
        self.status_var.set(message)
        self.root.update_idletasks()
    
    def show_help(self):
        """显示帮助"""
        help_text = """使用说明:

1. 批量重命名
   - 按序号: 为文件添加序号前缀，如 file_001.jpg
   - 按日期: 使用文件日期作为文件名
   - 正则替换: 使用正则表达式替换文件名

2. 图片处理
   - 格式转换: 支持 jpg, png, webp, gif 等格式互转
   - 调整尺寸: 按比例缩放或指定宽高

3. 文件整理
   - 按日期: 将文件按修改日期分类到不同文件夹
   - 按类型: 将文件按类型(图片/视频/文档等)分类

4. 压缩解压
   - 支持 zip, tar, tar.gz, tar.bz2 格式
   - 支持批量解压目录中的所有压缩包

提示:
   - 所有操作都有预览功能，建议先预览再执行
   - 操作前请备份重要数据
"""
        messagebox.showinfo("使用说明", help_text)
    
    def show_about(self):
        """显示关于"""
        messagebox.showinfo("关于", 
            "📁 文件处理工具箱 File Toolkit\n\n"
            "版本: 1.0.0\n"
            "一个简单易用的文件批量处理工具\n\n"
            "功能:\n"
            "  • 批量重命名\n"
            "  • 图片处理\n"
            "  • 文件整理\n"
            "  • 压缩解压"
        )
    
    def load_config(self):
        """加载配置"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 可以在这里恢复用户设置
            except:
                pass
    
    def save_config(self):
        """保存配置"""
        config = {}
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except:
            pass


def main():
    """主函数"""
    root = tk.Tk()
    
    # 设置DPI感知（Windows）
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
    
    app = FileToolkitGUI(root)
    
    # 保存配置 on exit
    def on_closing():
        app.save_config()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == '__main__':
    main()
