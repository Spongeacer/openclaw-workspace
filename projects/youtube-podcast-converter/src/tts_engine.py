"""增强版 TTS 引擎 - 带重试和错误处理"""
import io
import json
import random
import requests
import time
from pathlib import Path
from typing import Dict, List, Optional
from pydub import AudioSegment
from pydub.effects import normalize

try:
    from .translator import ChineseSegment
except ImportError:
    from src.translator import ChineseSegment


class StepFunTTS:
    """StepFun TTS 引擎 - 增强版"""
    
    def __init__(
        self, 
        api_key: str, 
        voice_config: Dict,
        base_url: str = "https://api.stepfun.com/v1",
        model: str = "step-tts-mini",
        sample_rate: int = 24000,
        default_speed: float = 1.5,
        min_interval: float = 6.0,  # 最小间隔 6 秒
        max_retries: int = 3,
        text_max_length: int = 500  # 最大文本长度
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.sample_rate = sample_rate
        self.voice_config = voice_config
        self.default_speed = default_speed
        self.min_interval = min_interval
        self.max_retries = max_retries
        self.text_max_length = text_max_length
        self.last_request_time = 0
        
        # 音色映射
        self.voice_map = self._assign_voices()
        
        # 统计
        self.stats = {
            "success": 0,
            "failed": 0,
            "retried": 0
        }
    
    def _assign_voices(self) -> Dict[str, str]:
        """分配音色"""
        male_voices = self.voice_config.get("voice_pool_male", ["cixingnansheng"])
        female_voices = self.voice_config.get("voice_pool_female", ["elegantgentle-female"])
        
        return {
            "SPEAKER_00": male_voices[0],
            "SPEAKER_01": female_voices[0],
            "DEFAULT": male_voices[0]
        }
    
    def _wait_rate_limit(self):
        """等待速率限制"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            sleep_time = self.min_interval - elapsed
            print(f"  ⏳ 等待 {sleep_time:.1f}s (速率限制)...")
            time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    def _split_text(self, text: str) -> List[str]:
        """切分超长文本"""
        if len(text) <= self.text_max_length:
            return [text]
        
        # 按句子切分
        import re
        sentences = re.split(r'(?<=[。！？；.!?;])\s*', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        parts = []
        current = ""
        
        for sent in sentences:
            if len(current) + len(sent) < self.text_max_length:
                current += sent
            else:
                if current:
                    parts.append(current)
                current = sent
        
        if current:
            parts.append(current)
        
        return parts if parts else [text[:self.text_max_length]]
    
    def _call_tts_api(self, text: str, voice_id: str, emotion: str) -> Optional[bytes]:
        """调用 TTS API，带重试"""
        speed = self._get_speed(emotion)
        
        # 构建 payload
        payload = {
            "model": self.model,
            "input": text,
            "voice": voice_id,
            "audio_format": "mp3",
            "sample_rate": self.sample_rate,
            "speed": speed
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        for attempt in range(self.max_retries):
            try:
                self._wait_rate_limit()
                
                response = requests.post(
                    f"{self.base_url}/audio/speech",
                    json=payload,
                    headers=headers,
                    timeout=60
                )
                
                # 处理 429 速率限制
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 30))
                    print(f"  ⚠️ 速率限制，等待 {retry_after}s...")
                    time.sleep(retry_after)
                    self.stats["retried"] += 1
                    continue
                
                # 处理 400 错误
                if response.status_code == 400:
                    error_detail = response.text
                    print(f"  ⚠️ 400 错误: {error_detail[:200]}")
                    # 可能是文本太长，尝试切分
                    if len(text) > 200 and attempt < self.max_retries - 1:
                        print(f"  🔄 文本可能过长，重试...")
                        self.stats["retried"] += 1
                        continue
                    return None
                
                response.raise_for_status()
                return response.content
                
            except requests.exceptions.Timeout:
                print(f"  ⚠️ 超时，重试 ({attempt+1}/{self.max_retries})...")
                self.stats["retried"] += 1
                time.sleep(5)
            except Exception as e:
                print(f"  ⚠️ 错误: {e}，重试 ({attempt+1}/{self.max_retries})...")
                self.stats["retried"] += 1
                time.sleep(5)
        
        return None
    
    def _get_speed(self, emotion: str) -> float:
        """根据情绪获取语速"""
        speed_map = {
            "快速": 1.8,
            "兴奋": 1.6,
            "高兴": 1.4,
            "生气": 1.4,
            "中性": 1.2,
            "困惑": 1.0,
            "悲伤": 0.9,
            "温柔": 0.9,
            "慢速": 0.8
        }
        return speed_map.get(emotion, 1.2)
    
    def synthesize_segment(self, segment: ChineseSegment) -> AudioSegment:
        """合成单个段落"""
        voice_id = self.voice_map.get(segment.speaker, self.voice_map["DEFAULT"])
        
        # 切分长文本
        text_parts = self._split_text(segment.text)
        audio_parts = []
        
        for part in text_parts:
            audio_data = self._call_tts_api(part, voice_id, segment.emotion)
            if audio_data:
                audio = AudioSegment.from_mp3(io.BytesIO(audio_data))
                audio_parts.append(audio)
        
        if not audio_parts:
            self.stats["failed"] += 1
            # 返回静音
            return AudioSegment.silent(duration=100, frame_rate=self.sample_rate)
        
        # 合并多个部分
        combined = audio_parts[0]
        for audio in audio_parts[1:]:
            combined += audio
        
        # 后处理
        combined = self._post_process(combined)
        self.stats["success"] += 1
        
        return combined
    
    def _post_process(self, audio: AudioSegment) -> AudioSegment:
        """音频后处理"""
        # 标准化采样率
        if audio.frame_rate != self.sample_rate:
            audio = audio.set_frame_rate(self.sample_rate)
        
        # 转为单声道
        if audio.channels > 1:
            audio = audio.set_channels(1)
        
        # 音量归一化
        audio = normalize(audio)
        
        return audio
    
    def synthesize_qa_pairs(
        self,
        qa_pairs: List,
        output_path: Path,
        progress_file: Optional[Path] = None,
        add_qa_silence: int = 300
    ) -> Path:
        """
        合成 QA 对，支持断点续传
        
        Args:
            qa_pairs: QA 对列表
            output_path: 输出路径
            progress_file: 进度文件路径（用于断点续传）
            add_qa_silence: Q-A 间隔（毫秒）
        """
        # 加载进度
        completed = set()
        if progress_file and progress_file.exists():
            with open(progress_file, 'r') as f:
                data = json.load(f)
                completed = set(data.get('completed', []))
            print(f"🔄 恢复进度: {len(completed)}/{len(qa_pairs)} 已完成")
        
        # 创建或加载音频
        if progress_file and output_path.exists() and completed:
            mixed = AudioSegment.from_mp3(output_path)
            # 计算当前时间点
            current_time = len(mixed)
        else:
            mixed = None
            current_time = 0
        
        total = len(qa_pairs)
        
        for i, pair in enumerate(qa_pairs):
            if i in completed:
                continue
            
            print(f"\n[{i+1}/{total}] 合成 QA 对...")
            
            # 合成 Q
            print(f"  Q: {pair.question[:50]}...")
            q_seg = ChineseSegment(
                speaker=pair.q_speaker,
                text=pair.question,
                emotion=pair.q_emotion
            )
            q_audio = self.synthesize_segment(q_seg)
            
            # 合成 A
            print(f"  A: {pair.answer[:50]}...")
            a_seg = ChineseSegment(
                speaker=pair.a_speaker,
                text=pair.answer,
                emotion=pair.a_emotion
            )
            a_audio = self.synthesize_segment(a_seg)
            
            # 使用拼接而非 overlay
            if mixed is None:
                mixed = q_audio
            else:
                mixed = mixed + q_audio
            
            # 添加 Q-A 间隔
            if add_qa_silence > 0:
                mixed = mixed + AudioSegment.silent(duration=add_qa_silence, frame_rate=self.sample_rate)
            
            mixed = mixed + a_audio
            
            # 添加段落间隔
            mixed = mixed + AudioSegment.silent(duration=200, frame_rate=self.sample_rate)
            
            # 保存进度
            completed.add(i)
            if progress_file:
                with open(progress_file, 'w') as f:
                    json.dump({
                        'completed': list(completed),
                        'last_index': i,
                        'stats': self.stats
                    }, f)
            
            # 每 5 个保存一次音频
            if (i + 1) % 5 == 0:
                mixed.export(output_path, format="mp3", bitrate="192k")
                print(f"  💾 已保存中间文件")
        
        # 最终导出
        output_path.parent.mkdir(parents=True, exist_ok=True)
        mixed.export(output_path, format="mp3", bitrate="192k")
        
        print(f"\n{'='*50}")
        print(f"✅ TTS 完成!")
        print(f"   成功: {self.stats['success']}")
        print(f"   失败: {self.stats['failed']}")
        print(f"   重试: {self.stats['retried']}")
        print(f"{'='*50}")
        
        return output_path
