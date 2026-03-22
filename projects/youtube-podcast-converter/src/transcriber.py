"""语音识别与说话人分离模块 - 使用 WhisperX 本地 ASR"""
import gc
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import torch
import whisperx


@dataclass
class Segment:
    """语音片段数据类"""
    speaker: str  # SPEAKER_00, SPEAKER_01...
    text: str
    start: float  # 秒
    end: float    # 秒


class WhisperXTranscriber:
    """WhisperX 语音识别器（支持说话人分离）"""
    
    def __init__(
        self, 
        device: str = "cpu", 
        compute_type: str = "int8",
        model_size: str = "medium",
        batch_size: int = 4,
        min_speakers: int = 2,
        max_speakers: int = 3
    ):
        """
        初始化语音识别器
        
        Args:
            device: 运行设备（M1 强制 cpu）
            compute_type: 计算类型（int8 降低内存）
            model_size: Whisper 模型大小
            batch_size: 批处理大小
            min_speakers: 最少说话人数
            max_speakers: 最多说话人数
        """
        self.device = device
        self.compute_type = compute_type
        self.model_size = model_size
        self.batch_size = batch_size
        self.min_speakers = min_speakers
        self.max_speakers = max_speakers
        
        self.model = None
        self.diarize_model = None
        self.align_model = None
        self.align_metadata = None
    
    def load_models(self):
        """延迟加载模型（避免初始化即占用内存）"""
        if self.model is None:
            self.model = whisperx.load_model(
                self.model_size,
                self.device,
                compute_type=self.compute_type,
                language="en"  # 强制英文
            )
        
        if self.diarize_model is None:
            self.diarize_model = whisperx.DiarizationPipeline(
                device=self.device
            )
    
    def unload_models(self):
        """卸载模型释放内存"""
        self.model = None
        self.diarize_model = None
        self.align_model = None
        self.align_metadata = None
        gc.collect()
        if self.device == "mps" and torch.backends.mps.is_available():
            torch.mps.empty_cache()
    
    def transcribe(self, audio_path: Path) -> List[Segment]:
        """
        转录音频文件
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            带说话人标签的片段列表
        """
        # 确保模型已加载
        self.load_models()
        
        # 加载音频
        audio = whisperx.load_audio(str(audio_path))
        
        # 1. 转录
        result = self.model.transcribe(
            audio, 
            batch_size=self.batch_size,
            language="en"
        )
        
        # 2. 对齐（提升时间戳精度）
        if self.align_model is None:
            self.align_model, self.align_metadata = whisperx.load_align_model(
                language_code="en",
                device=self.device
            )
        
        result = whisperx.align(
            result["segments"],
            self.align_model,
            self.align_metadata,
            audio,
            self.device,
            return_char_alignments=False
        )
        
        # 3. 说话人分离
        diarize_segments = self.diarize_model(
            audio,
            min_speakers=self.min_speakers,
            max_speakers=self.max_speakers
        )
        
        # 4. 分配说话人到词级别
        result = whisperx.assign_word_speakers(diarize_segments, result)
        
        # 5. 转换为标准格式
        segments = []
        for seg in result.get("segments", []):
            speaker = seg.get("speaker", "UNKNOWN")
            # 标准化说话人标签
            if speaker and isinstance(speaker, str):
                speaker = speaker.upper().replace(" ", "_")
            else:
                speaker = "UNKNOWN"
            
            segments.append(Segment(
                speaker=speaker,
                text=seg.get("text", "").strip(),
                start=float(seg.get("start", 0)),
                end=float(seg.get("end", 0))
            ))
        
        # 清理内存
        gc.collect()
        if self.device == "mps" and torch.backends.mps.is_available():
            torch.mps.empty_cache()
        
        return segments
