"""主流程编排 - 串联各模块，管理生命周期"""
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional
from loguru import logger

try:
    from ..config import get_settings
    from .downloader import YouTubeDownloader, VideoUnavailableError
    from .transcriber import SiliconFlowASR, StepFunASR
    from .translator import StepFunTranslator
    from .qa_reorganizer import QAReorganizer
    from .tts_engine import StepFunTTS
    from .quality_checker import QualityChecker, CheckResult
except ImportError:
    # 直接运行时的导入
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from config import get_settings
    from src.downloader import YouTubeDownloader, VideoUnavailableError
    from src.transcriber import SiliconFlowASR, StepFunASR
    from src.translator import StepFunTranslator
    from src.qa_reorganizer import QAReorganizer
    from src.tts_engine import StepFunTTS
    from src.quality_checker import QualityChecker, CheckResult


class PodcastPipeline:
    """播客转换流水线"""
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        初始化流水线
        
        Args:
            config_dir: 配置目录路径
        """
        self.config = get_settings(config_dir)
        
        # 初始化工作目录
        self.output_dir = Path("./output")
        self.temp_dir = Path("./temp")
        self.output_dir.mkdir(exist_ok=True)
        self.temp_dir.mkdir(exist_ok=True)
        
        # 获取提供商配置
        provider_config = self.config.get_provider_config()
        
        # 初始化各模块
        self.downloader = YouTubeDownloader(self.temp_dir)
        
        # 使用 SiliconFlow ASR (Whisper API)
        # 从环境变量或配置读取 SiliconFlow API Key
        siliconflow_key = provider_config.get("siliconflow_api_key") or "sk-loulnfpbpzkhwtkfzjeysrgkoflcagblvinuncxyajtiypbn"
        self.transcriber = SiliconFlowASR(
            api_key=siliconflow_key,
            base_url="https://api.siliconflow.cn/v1",
            model="FunAudioLLM/SenseVoiceSmall",  # 阿里开源，中文识别优秀
            language="en"  # 英文识别
        )
        
        self.translator = StepFunTranslator(
            api_key=provider_config["api_key"],
            base_url=provider_config["base_url"],
            model=provider_config["chat_model"]
        )
        
        # 初始化 QA 重组器
        self.qa_reorganizer = QAReorganizer(
            max_segment_length=150,
            min_q_length=20,
            min_a_length=30,
            add_intros=True,
            add_transitions=True,
            topic_break_interval=5
        )
        
        self.tts = StepFunTTS(
            api_key=provider_config["api_key"],
            voice_config=self.config.get_voice_config(),
            base_url=provider_config["base_url"],
            model=provider_config.get("tts_model", "step-tts-mini"),
            sample_rate=self.config.get_output_config().sample_rate,
            min_interval=6.0,
            max_retries=3,
            text_max_length=400
        )
    
    def run(self, youtube_url: str) -> Path:
        """
        运行完整流水线
        
        Args:
            youtube_url: YouTube 视频 URL
            
        Returns:
            最终输出文件路径
        """
        # 生成任务 ID
        task_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(youtube_url) % 10000:04d}"
        work_dir = self.output_dir / task_id
        work_dir.mkdir(parents=True, exist_ok=True)
        
        # 设置日志
        log_file = work_dir / "pipeline.log"
        logger.add(log_file, rotation="10 MB")
        
        try:
            # Stage 1: 下载
            logger.info(f"[{task_id}] Stage 1/4: Downloading audio from YouTube...")
            audio_path = self.downloader.download(youtube_url)
            raw_path = work_dir / "raw.mp3"
            shutil.move(str(audio_path), str(raw_path))
            logger.info(f"[{task_id}] Download complete: {raw_path}")
            
            # Stage 2: 识别 (SiliconFlow Whisper)
            logger.info(f"[{task_id}] Stage 2/4: Transcribing with SiliconFlow Whisper (SenseVoiceSmall)...")
            segments = self.transcriber.transcribe(raw_path)
            logger.info(f"[{task_id}] Transcribed {len(segments)} segments")
            
            # 保存英文识别结果
            en_segments_path = work_dir / "en_segments.json"
            with open(en_segments_path, "w", encoding="utf-8") as f:
                json.dump([s.__dict__ for s in segments], f, ensure_ascii=False, indent=2)
            
            if not segments:
                raise ValueError("No speech segments detected")
            
            # Stage 3: 翻译
            logger.info(f"[{task_id}] Stage 3/5: Translating to Chinese...")
            zh_segments = self.translator.translate_segments(segments)
            logger.info(f"[{task_id}] Translation complete: {len(zh_segments)} segments")
            
            # 保存中文翻译结果
            zh_segments_path = work_dir / "zh_segments.json"
            with open(zh_segments_path, "w", encoding="utf-8") as f:
                json.dump([s.__dict__ for s in zh_segments], f, ensure_ascii=False, indent=2)
            
            # Stage 4: QA 重组
            logger.info(f"[{task_id}] Stage 4/5: Reorganizing into QA pairs...")
            qa_pairs = self.qa_reorganizer.reorganize(zh_segments)
            logger.info(f"[{task_id}] QA reorganization complete: {len(qa_pairs)} pairs")
            
            # 保存 QA 对
            qa_pairs_path = work_dir / "qa_pairs.json"
            with open(qa_pairs_path, "w", encoding="utf-8") as f:
                json.dump(self.qa_reorganizer.to_dict_list(qa_pairs), f, ensure_ascii=False, indent=2)
            
            # Stage 5: TTS 与混音
            logger.info(f"[{task_id}] Stage 5/5: Synthesizing Chinese audio...")
            output_path = work_dir / "final_podcast.mp3"
            progress_file = work_dir / "tts_progress.json"
            
            self.tts.synthesize_qa_pairs(
                qa_pairs=qa_pairs,
                output_path=output_path,
                progress_file=progress_file,
                add_qa_silence=300
            )
            logger.success(f"[{task_id}] Audio synthesis complete: {output_path}")
            
            # Stage 6: 质量检查
            logger.info(f"[{task_id}] Running quality checks...")
            checker = QualityChecker()
            
            check_results = checker.run_all_checks(
                segments=zh_segments,
                qa_pairs=self.qa_reorganizer.to_dict_list(qa_pairs),
                audio_path=output_path
            )
            
            # 生成并保存检查报告
            report = checker.generate_report(check_results)
            report_path = work_dir / "quality_report.txt"
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report)
            
            logger.info(f"[{task_id}] Quality report saved: {report_path}")
            
            # 检查是否有严重错误
            critical_issues = [r for r in check_results if not r.passed and r.stage in ['translation', 'audio']]
            if critical_issues:
                logger.warning(f"[{task_id}] ⚠️ Quality issues detected:")
                for issue in critical_issues:
                    logger.warning(f"  - {issue.stage}: {issue.message}")
            else:
                logger.success(f"[{task_id}] ✅ All quality checks passed")
            
            logger.success(f"[{task_id}] Success! Output: {output_path}")
            
            # 清理中间文件（如果不保留）
            output_config = self.config.get_output_config()
            if not output_config.keep_intermediate:
                logger.info(f"[{task_id}] Cleaning up intermediate files...")
                if raw_path.exists():
                    raw_path.unlink()
                if en_segments_path.exists():
                    en_segments_path.unlink()
                if zh_segments_path.exists():
                    zh_segments_path.unlink()
                if qa_pairs_path.exists():
                    qa_pairs_path.unlink()
            
            return output_path
            
        except VideoUnavailableError as e:
            logger.error(f"[{task_id}] Video unavailable: {e}")
            raise
        except Exception as e:
            logger.error(f"[{task_id}] Pipeline failed: {e}")
            # 保留工作目录供调试
            raise
        finally:
            # StepFun ASR 无需卸载模型
            self.transcriber.unload_models()
