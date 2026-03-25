#!/usr/bin/env python3
"""
完整流水线测试 - 使用现有 raw.mp3
跳过下载阶段，直接运行 ASR+翻译+TTS
所有参数从配置文件读取
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


def run_pipeline(work_dir: Path, raw_mp3_path: Path = None):
    """运行完整流水线"""
    # 加载配置
    config = get_settings()
    scripts_config = config.get_scripts_config().pipeline
    tts_engine_config = config.get_tts_engine_config()
    output_config = config.get_output_config()
    
    print("="*70)
    print("YouTube 播客转换流水线 - 完整测试 (配置驱动)")
    print("="*70)
    
    # 确定 raw.mp3 源路径
    if raw_mp3_path is None:
        if scripts_config.raw_mp3_source:
            raw_mp3_path = Path(scripts_config.raw_mp3_source)
        else:
            # 尝试从现有输出目录查找
            output_base = Path(output_config.output_dir)
            pipeline_dirs = [d for d in output_base.iterdir() if d.is_dir() and d.name.startswith("pipeline_")]
            if pipeline_dirs:
                # 使用最新的
                latest_dir = sorted(pipeline_dirs, key=lambda d: d.stat().st_mtime, reverse=True)[0]
                raw_mp3_path = latest_dir / "raw.mp3"
    
    if not raw_mp3_path or not raw_mp3_path.exists():
        print(f"✗ 错误: raw.mp3 不存在: {raw_mp3_path}")
        print(f"   请指定 --raw-mp3 参数或配置 raw_mp3_source")
        return False
    
    # 创建工作目录
    work_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n工作目录: {work_dir}")
    print(f"源音频: {raw_mp3_path}")
    
    # 复制 raw.mp3
    raw_path = work_dir / "raw.mp3"
    if not raw_path.exists():
        shutil.copy(raw_mp3_path, raw_path)
    print(f"✓ 复制 raw.mp3 ({raw_path.stat().st_size / 1024 / 1024:.1f} MB)")
    
    # ========== Stage 1: ASR ==========
    print("\n" + "-"*70)
    print("Stage 1/3: ASR 语音识别")
    print("-"*70)
    
    from src.transcriber import SiliconFlowASR
    
    # 从配置获取 SiliconFlow Key
    siliconflow_key = config.siliconflow_api_key
    
    asr = SiliconFlowASR(
        api_key=siliconflow_key,
        base_url="https://api.siliconflow.cn/v1",
        model=scripts_config.asr_model,
        language=scripts_config.asr_language,
        timeout=scripts_config.asr_timeout
    )
    
    try:
        segments = asr.transcribe(raw_path)
        print(f"✓ ASR 完成: {len(segments)} 段")
        
        # 保存英文结果
        en_path = work_dir / "en_segments.json"
        with open(en_path, 'w', encoding='utf-8') as f:
            json.dump([s.__dict__ for s in segments], f, ensure_ascii=False, indent=2)
        
        if len(segments) < 5:
            print(f"⚠ 警告: 分段数量较少 ({len(segments)} 段)，可能影响翻译/TTS 效果")
        
    except Exception as e:
        print(f"✗ ASR 失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # ========== Stage 2: 翻译 ==========
    print("\n" + "-"*70)
    print("Stage 2/3: 翻译为中文")
    print("-"*70)
    
    tts_config = config.get_tts_config()
    stepfun_key = tts_config.api_key
    
    if not stepfun_key:
        print("✗ 错误: 未配置 StepFun API Key")
        print("   请设置环境变量 STEPFUN_API_KEY 或更新配置文件")
        return False
    
    from src.translator import StepFunTranslator
    
    translator = StepFunTranslator(
        api_key=stepfun_key,
        base_url=tts_config.base_url,
        model=scripts_config.translator_model
    )
    
    try:
        zh_segments = translator.translate_segments(segments)
        print(f"✓ 翻译完成: {len(zh_segments)} 段")
        
        # 保存中文结果
        zh_path = work_dir / "zh_segments.json"
        with open(zh_path, 'w', encoding='utf-8') as f:
            json.dump([s.__dict__ for s in zh_segments], f, ensure_ascii=False, indent=2)
        
        # 显示前3段
        print("\n翻译示例:")
        for i, seg in enumerate(zh_segments[:3]):
            print(f"  [{i}] [{seg.emotion}] {seg.text[:60]}...")
        
    except Exception as e:
        print(f"✗ 翻译失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # ========== Stage 3: TTS ==========
    print("\n" + "-"*70)
    print("Stage 3/3: TTS 语音合成")
    print("-"*70)
    
    from src.tts_engine import StepFunTTS
    
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
        result_path = tts.mix_mono(zh_segments, output_path)
        
        if result_path.exists():
            size_mb = result_path.stat().st_size / 1024 / 1024
            print(f"✓ TTS 完成: {result_path}")
            print(f"✓ 文件大小: {size_mb:.2f} MB")
            
            if size_mb < 1:
                print(f"⚠ 警告: 文件过小 ({size_mb:.2f} MB)，可能生成有问题")
                return False
            
            print(f"\n{'='*70}")
            print(f"✓✓✓ 流水线完成! 输出: {result_path}")
            print(f"{'='*70}")
            return True
        else:
            print(f"✗ 输出文件未生成")
            return False
            
    except Exception as e:
        print(f"✗ TTS 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    config = get_settings()
    output_config = config.get_output_config()
    
    parser = argparse.ArgumentParser(description="运行完整流水线")
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
    args = parser.parse_args()
    
    # 确定工作目录
    if args.work_dir:
        work_dir = Path(args.work_dir)
    else:
        work_dir = Path(output_config.output_dir) / f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # 确定 raw.mp3 路径
    raw_mp3_path = Path(args.raw_mp3) if args.raw_mp3 else None
    
    success = run_pipeline(work_dir, raw_mp3_path)
    return 0 if success else 1


if __name__ == "__main__":
    import os
    os.chdir(str(Path(__file__).parent))
    
    exit_code = main()
    sys.exit(exit_code)
