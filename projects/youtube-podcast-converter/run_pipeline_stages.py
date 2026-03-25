#!/usr/bin/env python3
"""
分阶段流水线 - 避免内存问题
所有参数从配置文件读取，支持命令行指定工作目录和源文件
"""
import sys
import json
import shutil
import argparse
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from config import get_settings


def stage1_asr(work_dir: Path, raw_mp3_path: Path, scripts_config, output_config):
    """Stage 1: ASR 识别"""
    print("="*70)
    print("Stage 1/3: ASR 语音识别")
    print("="*70)
    
    from src.transcriber import SiliconFlowASR
    from config import get_settings
    
    config = get_settings()
    work_dir.mkdir(parents=True, exist_ok=True)
    
    # 复制 raw.mp3
    raw_path = work_dir / "raw.mp3"
    if not raw_path.exists():
        if not raw_mp3_path.exists():
            print(f"✗ 错误: 源文件不存在: {raw_mp3_path}")
            return None
        shutil.copy(raw_mp3_path, raw_path)
    
    # 使用配置中的 API Key
    siliconflow_key = config.siliconflow_api_key
    
    asr = SiliconFlowASR(
        api_key=siliconflow_key,
        model=scripts_config.asr_model,
        language=scripts_config.asr_language,
        timeout=scripts_config.asr_timeout
    )
    
    try:
        segments = asr.transcribe(raw_path)
        print(f"\n✓ ASR 完成: {len(segments)} 段")
        
        # 保存结果
        en_path = work_dir / "en_segments.json"
        with open(en_path, 'w', encoding='utf-8') as f:
            json.dump([s.__dict__ for s in segments], f, ensure_ascii=False, indent=2)
        
        # 显示统计
        total_chars = sum(len(s.text) for s in segments)
        print(f"  总字符数: {total_chars:,}")
        print(f"  平均每段: {total_chars//len(segments) if segments else 0} 字符")
        
        if len(segments) < 5:
            print(f"⚠ 警告: 分段数量较少 ({len(segments)} 段)")
            return None
            
        return segments
        
    except Exception as e:
        print(f"\n✗ ASR 失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def stage2_translate(segments, work_dir: Path, scripts_config):
    """Stage 2: 翻译"""
    print("\n" + "="*70)
    print("Stage 2/3: 翻译为中文")
    print("="*70)
    
    from config import get_settings
    from src.translator import StepFunTranslator
    
    config = get_settings()
    tts_config = config.get_tts_config()
    stepfun_key = tts_config.api_key
    
    if not stepfun_key:
        print("✗ 错误: 未配置 StepFun API Key")
        return None
    
    translator = StepFunTranslator(
        api_key=stepfun_key,
        base_url=tts_config.base_url,
        model=scripts_config.translator_model
    )
    
    try:
        # 分批翻译
        batch_size = scripts_config.translation_batch_size
        all_zh_segments = []
        total_batches = (len(segments) - 1) // batch_size + 1
        
        for i in range(0, len(segments), batch_size):
            batch = segments[i:i+batch_size]
            print(f"  翻译批次 {i//batch_size + 1}/{total_batches} ({len(batch)} 段)...")
            
            zh_batch = translator.translate_segments(batch)
            all_zh_segments.extend(zh_batch)
        
        print(f"\n✓ 翻译完成: {len(all_zh_segments)} 段")
        
        # 保存
        zh_path = work_dir / "zh_segments.json"
        with open(zh_path, 'w', encoding='utf-8') as f:
            json.dump([s.__dict__ for s in all_zh_segments], f, ensure_ascii=False, indent=2)
        
        # 显示示例
        print("\n翻译示例:")
        for i, seg in enumerate(all_zh_segments[:3]):
            print(f"  [{i}] [{seg.emotion}] {seg.text[:50]}...")
        
        return all_zh_segments
        
    except Exception as e:
        print(f"\n✗ 翻译失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def stage3_tts(zh_segments, work_dir: Path, tts_engine_config):
    """Stage 3: TTS 合成"""
    print("\n" + "="*70)
    print("Stage 3/3: TTS 语音合成")
    print("="*70)
    
    from config import get_settings
    from src.tts_engine import StepFunTTS
    
    config = get_settings()
    tts_config = config.get_tts_config()
    stepfun_key = tts_config.api_key
    
    if not stepfun_key:
        print("✗ 错误: 未配置 StepFun API Key")
        return False
    
    voice_config = config.get_voice_config()
    
    print(f"   模型: {tts_config.tts_model}")
    print(f"   音色: {voice_config['voice_pool_male'][0]} / {voice_config['voice_pool_female'][0]}")
    
    tts = StepFunTTS(
        api_key=stepfun_key,
        voice_config=voice_config,
        base_url=tts_config.base_url,
        model=tts_config.tts_model,
        sample_rate=tts_engine_config.sample_rate,
        min_interval=tts_engine_config.min_interval,
        max_retries=tts_engine_config.max_retries,
        text_max_length=tts_engine_config.text_max_length
    )
    
    output_path = work_dir / "final_stereo.mp3"
    
    try:
        print(f"  合成 {len(zh_segments)} 段音频...")
        result_path = tts.mix_mono(zh_segments, output_path)
        
        if result_path.exists():
            size_mb = result_path.stat().st_size / 1024 / 1024
            print(f"\n✓ TTS 完成!")
            print(f"  输出: {result_path}")
            print(f"  大小: {size_mb:.2f} MB")
            
            if size_mb >= 10:
                print(f"\n{'='*70}")
                print(f"✓✓✓ 流水线成功完成! 文件大小正常 (>{10}MB)")
                print(f"{'='*70}")
                return True
            else:
                print(f"⚠ 警告: 文件较小 ({size_mb:.2f} MB)，但已生成")
                return True
        else:
            print(f"\n✗ 输出文件未生成")
            return False
            
    except Exception as e:
        print(f"\n✗ TTS 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def find_raw_mp3_source(scripts_config, output_config):
    """查找 raw.mp3 源文件"""
    # 1. 检查配置的源路径
    if scripts_config.raw_mp3_source:
        path = Path(scripts_config.raw_mp3_source)
        if path.exists():
            return path
    
    # 2. 尝试在现有 pipeline 目录中查找
    output_base = Path(output_config.output_dir)
    if output_base.exists():
        pipeline_dirs = [d for d in output_base.iterdir() if d.is_dir() and d.name.startswith("pipeline_")]
        if pipeline_dirs:
            latest = sorted(pipeline_dirs, key=lambda d: d.stat().st_mtime, reverse=True)[0]
            raw_path = latest / "raw.mp3"
            if raw_path.exists():
                return raw_path
    
    return None


def main():
    # 加载配置
    config = get_settings()
    scripts_config = config.get_scripts_config().pipeline
    tts_engine_config = config.get_tts_engine_config()
    output_config = config.get_output_config()
    
    parser = argparse.ArgumentParser(description="分阶段流水线执行")
    parser.add_argument(
        "--raw-mp3", "-r",
        type=str,
        default="",
        help="raw.mp3 源文件路径"
    )
    parser.add_argument(
        "--work-dir", "-w",
        type=str,
        default="",
        help="工作目录（默认自动生成）"
    )
    parser.add_argument(
        "--stage", "-s",
        type=str,
        choices=["all", "asr", "translate", "tts"],
        default="all",
        help="执行阶段 (默认: all)"
    )
    args = parser.parse_args()
    
    # 确定工作目录
    if args.work_dir:
        work_dir = Path(args.work_dir)
    else:
        work_dir = Path(output_config.output_dir) / f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # 确定 raw.mp3 路径
    if args.raw_mp3:
        raw_mp3_path = Path(args.raw_mp3)
    else:
        raw_mp3_path = find_raw_mp3_source(scripts_config, output_config)
    
    if not raw_mp3_path or not raw_mp3_path.exists():
        print("✗ 错误: 无法找到 raw.mp3 源文件")
        print("   请使用 --raw-mp3 参数指定，或配置 raw_mp3_source")
        return 1
    
    print("\n" + "="*70)
    print("YouTube 播客转换流水线 - 分阶段执行 (配置驱动)")
    print("="*70)
    print(f"工作目录: {work_dir}")
    print(f"源音频: {raw_mp3_path}")
    print(f"执行阶段: {args.stage}")
    
    segments = None
    zh_segments = None
    
    # Stage 1: ASR
    if args.stage in ["all", "asr"]:
        segments = stage1_asr(work_dir, raw_mp3_path, scripts_config, output_config)
        if not segments:
            print("\n✗ Stage 1 失败，停止")
            return 1
    
    # Stage 2: 翻译
    if args.stage in ["all", "translate"]:
        if segments is None:
            # 尝试从文件加载
            en_path = work_dir / "en_segments.json"
            if en_path.exists():
                from src.translator import Segment
                with open(en_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                segments = [Segment(**item) for item in data]
                print(f"✓ 从文件加载 {len(segments)} 段")
            else:
                print("✗ 错误: 没有 ASR 结果，请先运行 --stage asr")
                return 1
        
        zh_segments = stage2_translate(segments, work_dir, scripts_config)
        if not zh_segments:
            print("\n✗ Stage 2 失败，停止")
            return 1
    
    # Stage 3: TTS
    if args.stage in ["all", "tts"]:
        if zh_segments is None:
            # 尝试从文件加载
            zh_path = work_dir / "zh_segments.json"
            if zh_path.exists():
                from src.translator import ChineseSegment
                with open(zh_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                zh_segments = [ChineseSegment(**item) for item in data]
                print(f"✓ 从文件加载 {len(zh_segments)} 段")
            else:
                print("✗ 错误: 没有翻译结果，请先运行 --stage translate")
                return 1
        
        success = stage3_tts(zh_segments, work_dir, tts_engine_config)
        if not success:
            return 1
    
    return 0


if __name__ == "__main__":
    import os
    os.chdir(str(Path(__file__).parent))
    
    exit_code = main()
    sys.exit(exit_code)
