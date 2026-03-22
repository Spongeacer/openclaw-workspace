"""主流程编排 - 串联各模块，管理生命周期"""
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional
from loguru import logger

from ..config import get_settings
from .downloader import YouTubeDownloader, VideoUnavailableError
from .transcriber import WhisperXTranscriber
from .translator import StepFunTranslator
from .tts_engine import StepFunTTS


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
        
        # 初始化各模块
        self.downloader = YouTubeDownloader(self.temp_dir)
        self.transcriber = WhisperXTranscriber(
            device=self.config.whisper.device,
            compute_type=self.config.whisper.compute_type,
            model_size=self.config.whisper.model_size,
            batch_size=self.config.whisper.batch_size,
            min_speakers=self.config.whisper.min_speakers,
            max_speakers=self.config.whisper.max_speakers
        )
        
        provider_config = self.config.get_provider_config()
        self.translator = StepFunTranslator(
            api_key=provider_config["api_key"],
            base_url=provider_config["base_url"],
            model=provider_config["chat_model"]
        )
        
        self.tts = StepFunTTS(
            api_key=provider_config["api_key"],
            voice_config=self.config.get_voice_config(),
            base_url=provider_config["base_url"],
            model=provider_config.get("tts_model", "step-tts-2"),
            sample_rate=self.config.output.sample_rate
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
            
            # Stage 2: 识别
            logger.info(f"[{task_id}] Stage 2/4: Transcribing with WhisperX...")
            segments = self.transcriber.transcribe(raw_path)
            logger.info(f"[{task_id}] Transcribed {len(segments)} segments")
            
            # 保存英文识别结果
            en_segments_path = work_dir / "en_segments.json"
            with open(en_segments_path, "w", encoding="utf-8") as f:
                json.dump([s.__dict__ for s in segments], f, ensure_ascii=False, indent=2)
            
            if not segments:
                raise ValueError("No speech segments detected")
            
            # Stage 3: 翻译
            logger.info(f"[{task_id}] Stage 3/4: Translating to Chinese...")
            zh_segments = self.translator.translate_segments(segments)
            logger.info(f"[{task_id}] Translation complete")
            
            # 保存中文翻译结果
            zh_segments_path = work_dir / "zh_segments.json"
            with open(zh_segments_path, "w", encoding="utf-8") as f:
                json.dump([s.__dict__ for s in zh_segments], f, ensure_ascii=False, indent=2)
            
            # Stage 4: TTS 与混音
            logger.info(f"[{task_id}] Stage 4/4: Synthesizing Chinese audio...")
            output_path = work_dir / "final_stereo.mp3"
            self.tts.mix_stereo(zh_segments, output_path)
            logger.success(f"[{task_id}] Success! Output: {output_path}")
            
            # 清理中间文件（如果不保留）
            if not self.config.output.keep_intermediate:
                logger.info(f"[{task_id}] Cleaning up intermediate files...")
                if raw_path.exists():
                    raw_path.unlink()
                if en_segments_path.exists():
                    en_segments_path.unlink()
                if zh_segments_path.exists():
                    zh_segments_path.unlink()
            
            return output_path
            
        except VideoUnavailableError as e:
            logger.error(f"[{task_id}] Video unavailable: {e}")
            raise
        except Exception as e:
            logger.error(f"[{task_id}] Pipeline failed: {e}")
            # 保留工作目录供调试
            raise
        finally:
            # 卸载模型释放内存
            self.transcriber.unload_models()
