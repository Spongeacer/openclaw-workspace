#!/usr/bin/env python3
"""
完整性检查工具 - 检查现有文件的质量
支持从配置文件读取默认路径

用法:
    python3 check_quality.py [work_dir]
    
示例:
    python3 check_quality.py output/pipeline_20260322_232931
    python3 check_quality.py  # 使用配置中的默认目录或自动查找最新
"""

import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import get_settings
from src.quality_checker import QualityChecker
from src.translator import ChineseSegment


def find_latest_pipeline_dir(output_dir: Path) -> Path:
    """自动查找最新的 pipeline 目录"""
    pipeline_dirs = [
        d for d in output_dir.iterdir() 
        if d.is_dir() and d.name.startswith("pipeline_")
    ]
    if pipeline_dirs:
        return sorted(pipeline_dirs, key=lambda d: d.stat().st_mtime, reverse=True)[0]
    return None


def load_segments(json_path: Path) -> list:
    """加载翻译后的段落"""
    if not json_path.exists():
        return []
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    segments = []
    for item in data:
        if isinstance(item, dict):
            segments.append(ChineseSegment(
                speaker=item.get('speaker', ''),
                text=item.get('text', ''),
                emotion=item.get('emotion', '中性'),
                style=item.get('style')
            ))
    
    return segments


def main():
    # 加载配置
    config = get_settings()
    scripts_config = config.get_scripts_config().regenerate_tts
    output_config = config.get_output_config()
    
    parser = argparse.ArgumentParser(description="检查流水线输出质量")
    parser.add_argument(
        "work_dir",
        type=str,
        nargs="?",
        default="",
        help="工作目录路径（默认从配置或自动查找）"
    )
    parser.add_argument(
        "--zh-segments",
        type=str,
        default="",
        help="中文段落文件名（默认: zh_segments.json 或 zh_segments_v2.json）"
    )
    parser.add_argument(
        "--qa-pairs",
        type=str,
        default="",
        help="QA 对文件名（默认: qa_pairs.json 或 qa_pairs_v2.json）"
    )
    parser.add_argument(
        "--audio",
        type=str,
        default="",
        help="音频文件名（默认: podcast_final_v2.mp3）"
    )
    args = parser.parse_args()
    
    # 确定工作目录
    if args.work_dir:
        work_dir = Path(args.work_dir)
    elif scripts_config.default_work_dir:
        work_dir = Path(scripts_config.default_work_dir)
    else:
        # 自动查找
        output_base = Path(output_config.output_dir)
        work_dir = find_latest_pipeline_dir(output_base)
        if work_dir is None:
            print("✗ 错误: 无法找到 pipeline 目录")
            print(f"   请指定工作目录或配置 default_work_dir")
            return 1
    
    print(f"检查目录: {work_dir}")
    print("=" * 70)
    
    # 确定文件路径
    zh_segments_file = args.zh_segments or "zh_segments_v2.json"
    qa_pairs_file = args.qa_pairs or "qa_pairs_v2.json"
    audio_file = args.audio or "podcast_final_v2.mp3"
    
    zh_segments_path = work_dir / zh_segments_file
    qa_pairs_path = work_dir / qa_pairs_file
    audio_path = work_dir / audio_file
    
    # 如果没有 v2 版本，尝试普通版本
    if not zh_segments_path.exists():
        zh_segments_path = work_dir / "zh_segments.json"
    if not qa_pairs_path.exists():
        qa_pairs_path = work_dir / "qa_pairs.json"
    
    # 加载文件
    zh_segments = load_segments(zh_segments_path) if zh_segments_path.exists() else []
    qa_pairs = []
    if qa_pairs_path.exists():
        with open(qa_pairs_path, 'r', encoding='utf-8') as f:
            qa_pairs = json.load(f)
    
    print(f"\n📁 文件检查:")
    print(f"   中文段落: {zh_segments_path} ({len(zh_segments)} 段)")
    print(f"   QA 对: {qa_pairs_path} ({len(qa_pairs)} 对)")
    print(f"   音频: {audio_path} ({'存在' if audio_path.exists() else '不存在'})")
    
    # 运行检查
    print(f"\n🔍 运行质量检查...")
    checker = QualityChecker()
    
    check_results = checker.run_all_checks(
        segments=zh_segments,
        qa_pairs=qa_pairs,
        audio_path=audio_path if audio_path.exists() else None
    )
    
    # 生成报告
    report = checker.generate_report(check_results)
    
    # 保存报告
    report_path = work_dir / "quality_report.txt"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    # 打印结果
    print(report)
    print(f"\n📝 报告已保存: {report_path}")
    
    # 返回退出码
    critical_issues = [r for r in check_results if not r.passed and r.stage in ['translation', 'audio']]
    return 1 if critical_issues else 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
