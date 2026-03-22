"""TTS 引擎与混音模块 - 调用 StepFun TTS API 生成立体声音频"""
import io
import random
import requests
from pathlib import Path
from typing import Dict, List, Optional
from pydub import AudioSegment
from pydub.effects import normalize

# 导入翻译模块的数据类
from .translator import ChineseSegment


class StepFunTTS:
    """StepFun TTS 引擎"""
    
    def __init__(
        self, 
        api_key: str, 
        voice_config: Dict,
        base_url: str = "https://api.stepfun.com/v1",
        model: str = "step-tts-2",
        sample_rate: int = 44100
    ):
        """
        初始化 TTS 引擎
        
        Args:
            api_key: StepFun API 密钥
            voice_config: 音色配置（voice_pool_male/female）
            base_url: API 基础 URL
            model: TTS 模型名称
            sample_rate: 输出采样率
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.sample_rate = sample_rate
        self.voice_config = voice_config
        
        # 随机分配音色（实例化时确定，确保整段音频音色一致）
        self.voice_map = self._random_assign_voices()
    
    def _random_assign_voices(self) -> Dict[str, str]:
        """
        为说话人随机分配音色
        
        Returns:
            说话人到音色的映射
        """
        male_voices = self.voice_config.get("voice_pool_male", ["zixinnansheng"])
        female_voices = self.voice_config.get("voice_pool_female", ["elegantgentle-female"])
        
        male_voice = random.choice(male_voices)
        female_voice = random.choice(female_voices)
        
        # SPEAKER_00 使用男声，SPEAKER_01 使用女声
        # 其他说话人随机分配
        return {
            "SPEAKER_00": male_voice,
            "SPEAKER_01": female_voice,
            "DEFAULT": male_voice
        }
    
    def _emotion_to_voice_label(self, emotion: str) -> Dict[str, str]:
        """
        将情绪映射为 StepFun voice_label
        
        Args:
            emotion: 情绪标签
            
        Returns:
            voice_label 字典
        """
        emotion_tags = ["高兴", "悲伤", "生气", "兴奋", "困惑", "惊讶", "中性"]
        style_tags = ["温柔", "严肃", "快速", "慢速"]
        
        label = {}
        if emotion in emotion_tags:
            label["emotion"] = emotion
        elif emotion in style_tags:
            label["style"] = emotion
        
        return label
    
    def _get_speed(self, emotion: str) -> float:
        """
        根据情绪获取语速
        
        Args:
            emotion: 情绪标签
            
        Returns:
            语速倍数
        """
        if emotion == "快速":
            return 1.1
        elif emotion == "慢速":
            return 0.9
        return 1.0
    
    def synthesize_segment(self, segment: ChineseSegment) -> AudioSegment:
        """
        合成单段音频
        
        Args:
            segment: 中文语音片段
            
        Returns:
            pydub AudioSegment
        """
        # 获取音色
        voice_id = self.voice_map.get(segment.speaker, self.voice_map["DEFAULT"])
        
        # 获取 voice_label
        voice_label = self._emotion_to_voice_label(segment.emotion)
        
        # 获取语速
        speed = self._get_speed(segment.emotion)
        
        # 构建请求
        payload = {
            "model": self.model,
            "input": segment.text,
            "voice_id": voice_id,
            "audio_format": "mp3",
            "sample_rate": self.sample_rate,
            "speed": speed
        }
        
        # 添加 voice_label（如果有）
        if voice_label:
            payload["voice_label"] = voice_label
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 发送请求
        response = requests.post(
            f"{self.base_url}/audio/speech",
            json=payload,
            headers=headers,
            timeout=60
        )
        response.raise_for_status()
        
        # 流式读取音频数据
        audio_data = io.BytesIO(response.content)
        segment_audio = AudioSegment.from_mp3(audio_data)
        
        # 标准化采样率
        if segment_audio.frame_rate != self.sample_rate:
            segment_audio = segment_audio.set_frame_rate(self.sample_rate)
        
        # 标准化声道数（转为单声道后再处理）
        if segment_audio.channels > 1:
            segment_audio = segment_audio.set_channels(1)
        
        # 音量归一化
        segment_audio = normalize(segment_audio)
        
        # 声道映射
        if segment.speaker == "SPEAKER_00":
            return segment_audio.pan(-1.0)  # 全左声道
        elif segment.speaker == "SPEAKER_01":
            return segment_audio.pan(1.0)   # 全右声道
        else:
            # 其他说话人居中
            return segment_audio.pan(0.0)
    
    def mix_stereo(
        self, 
        segments: List[ChineseSegment], 
        output_path: Path
    ) -> Path:
        """
        合成所有段落并混音为立体声
        
        Args:
            segments: 中文语音片段列表
            output_path: 输出文件路径
            
        Returns:
            输出文件路径
        """
        if not segments:
            raise ValueError("No segments to synthesize")
        
        # 计算总时长（取最后一个 segment 的 end 时间）
        # 由于没有原始时间戳，我们按顺序拼接
        mixed = AudioSegment.silent(duration=0, frame_rate=self.sample_rate)
        mixed = mixed.set_channels(2)  # 强制立体声
        
        # 当前时间点（毫秒）
        current_time = 0
        
        for i, seg in enumerate(segments):
            try:
                # 合成音频
                audio = self.synthesize_segment(seg)
                
                # 混合到当前时间点
                mixed = mixed.overlay(audio, position=current_time)
                
                # 更新时间点（添加小段间隔，模拟自然对话停顿）
                current_time += len(audio) + 200  # 200ms 间隔
                
            except Exception as e:
                # 单段失败记录日志，继续处理
                print(f"TTS 失败 for {seg.speaker}: {seg.text[:30]}... Error: {e}")
                continue
        
        # 导出
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        mixed.export(
            output_path,
            format="mp3",
            bitrate="192k",
            tags={
                'artist': 'AI Podcast Converter',
                'title': 'Converted Chinese Podcast'
            }
        )
        
        return output_path
