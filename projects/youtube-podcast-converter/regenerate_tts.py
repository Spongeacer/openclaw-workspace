#!/usr/bin/env python3
"""
重新生成 TTS 音频 - 使用增强版引擎
从配置文件读取所有参数，支持命令行指定工作目录
"""
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from config import get_settings
from src.tts_engine import StepFunTTS


def find_latest_work_dir(output_dir: Path) -> Path:
    """自动查找最新的 pipeline 工作目录"""
    pipeline_dirs = sorted(
        [d for d in output_dir.iterdir() if d.is_dir() and d.name.startswith("pipeline_")],
        key=lambda d: d.stat().st_mtime,
        reverse=True
    )
    if pipeline_dirs:
        return pipeline_dirs[0]
    return output_dir


def load_qa_pairs(qa_pairs_path: Path):
    """加载 QA 对文件"""
    from dataclasses import dataclass
    
    @dataclass
    class QAPair:
        q_speaker: str
        a_speaker: str
        question: str
        answer: str
        q_emotion: str
        a_emotion: str
    
    with open(qa_pairs_path, 'r', encoding='utf-8') as f:
        qa_pairs_data = json.load(f)
    
    qa_pairs = []
    for p in qa_pairs_data:
        qa_pairs.append(QAPair(
            q_speaker=p.get('q_speaker', 'SPEAKER_00'),
            a_speaker=p.get('a_speaker', 'SPEAKER_01'),
            question=p.get('question', ''),
            answer=p.get('answer', ''),
            q_emotion=p.get('q_emotion', '中性'),
            a_emotion=p.get('a_emotion', '中性')
        ))
    
    return qa_pairs


def main():
    # 加载配置
    config = get_settings()
    scripts_config = config.get_scripts_config().regenerate_tts
    tts_engine_config = config.get_tts_engine_config()
    output_config = config.get_output_config()
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="重新生成 TTS 音频")
    parser.add_argument(
        "--work-dir", "-w",
        type=str,
        default=scripts_config.default_work_dir,
        help="工作目录路径（默认从配置读取或自动查找）"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="",
        help="输出音频路径（默认从配置生成）"
    )
    args = parser.parse_args()
    
    # 确定工作目录
    if args.work_dir:
        work_dir = Path(args.work_dir)
    else:
        output_base = Path(output_config.output_dir)
        work_dir = find_latest_work_dir(output_base)
    
    # 确定文件路径
    qa_pairs_file = work_dir / scripts_config.qa_pairs_file
    progress_file = work_dir / scripts_config.progress_file
    output_audio = Path(args.output) if args.output else work_dir / scripts_config.output_audio
    
    # 检查文件存在性
    if not qa_pairs_file.exists():
        print(f"✗ 错误: QA 对文件不存在: {qa_pairs_file}")
        print(f"   请确保已运行完整流水线生成 qa_pairs.json")
        return 1
    
    print("=" * 60)
    print("重新生成 TTS 音频 (配置驱动)")
    print("=" * 60)
    print(f"\n📁 工作目录: {work_dir}")
    print(f"📄 QA 文件: {qa_pairs_file}")
    print(f"🎵 输出音频: {output_audio}")
    print(f"💾 进度文件: {progress_file}")
    
    # 加载 QA 对
    print(f"\n📂 加载 QA 对...")
    qa_pairs = load_qa_pairs(qa_pairs_file)
    print(f"✓ 加载 {len(qa_pairs)} 对 QA")
    
    # 估算时间
    total_segments = len(qa_pairs) * 2  # Q + A
    estimated_minutes = (total_segments * tts_engine_config.min_interval) / 60
    print(f"⏱️  预计耗时: {estimated_minutes:.1f} 分钟")
    print(f"   Q+A 共 {total_segments} 段")
    print(f"   请求间隔: {tts_engine_config.min_interval}s")
    print(f"   最大重试: {tts_engine_config.max_retries} 次")
    
    # 获取 TTS 配置
    tts_config = config.get_tts_config()
    voice_config = {
        "voice_pool_male": tts_config.voice_pool.male,
        "voice_pool_female": tts_config.voice_pool.female
    }
    
    # 初始化 TTS
    print(f"\n🎙️ 初始化 TTS 引擎...")
    print(f"   模型: {tts_config.tts_model}")
    print(f"   音色: {voice_config['voice_pool_male'][0]} / {voice_config['voice_pool_female'][0]}")
    
    tts = StepFunTTS(
        api_key=tts_config.api_key,
        voice_config=voice_config,
        base_url=tts_config.base_url,
        model=tts_config.tts_model,
        sample_rate=tts_engine_config.sample_rate,
        min_interval=tts_engine_config.min_interval,
        max_retries=tts_engine_config.max_retries,
        text_max_length=tts_engine_config.text_max_length
    )
    
    # 生成音频
    print(f"\n🚀 开始生成音频...")
    print("-" * 60)
    
    try:
        tts.synthesize_qa_pairs(
            qa_pairs=qa_pairs,
            output_path=output_audio,
            progress_file=progress_file,
            add_qa_silence=tts_engine_config.add_qa_silence
        )
        
        # 检查文件
        if output_audio.exists():
            size_mb = output_audio.stat().st_size / 1024 / 1024
            duration_min = (total_segments * 6) / 60  # 粗略估算
            print(f"\n✅ 音频生成成功!")
            print(f"   文件: {output_audio}")
            print(f"   大小: {size_mb:.2f} MB")
            print(f"   预计时长: ~{duration_min:.1f} 分钟")
            return 0
        else:
            print(f"\n❌ 音频文件未生成")
            return 1
            
    except KeyboardInterrupt:
        print(f"\n\n⏸️ 用户中断，进度已保存到 {progress_file}")
        print(f"   下次运行会自动恢复")
        return 130
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
