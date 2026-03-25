"""语音识别模块 - 使用 SiliconFlow Whisper API (OpenAI兼容格式)"""
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import requests


@dataclass
class Segment:
    """语音片段数据类"""
    speaker: str  # SPEAKER_00, SPEAKER_01...
    text: str
    start: float  # 秒
    end: float    # 秒


class SiliconFlowASR:
    """
    硅基流动 (SiliconFlow) ASR 语音识别器
    
    使用 OpenAI 兼容格式的 Whisper API
    模型: FunAudioLLM/SenseVoiceSmall (阿里开源，中文识别优秀)
    """
    
    # 支持的模型
    DEFAULT_MODEL = "FunAudioLLM/SenseVoiceSmall"
    WHISPER_MODELS = [
        "FunAudioLLM/SenseVoiceSmall",  # 推荐，中文识别好，免费额度
        "whisper-large-v3",              # OpenAI Whisper Large V3
        "whisper-large-v3-turbo",        # Groq 托管版本，速度快
    ]
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.siliconflow.cn/v1",
        model: str = "FunAudioLLM/SenseVoiceSmall",
        language: str = "en",
        timeout: int = 300,
        max_retries: int = 3
    ):
        """
        初始化 SiliconFlow ASR
        
        Args:
            api_key: SiliconFlow API 密钥
            base_url: API 基础 URL
            model: ASR 模型名称
            language: 识别语言 (en/zh/auto)
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.language = language
        self.timeout = timeout
        self.max_retries = max_retries
    
    def transcribe(self, audio_path: Path) -> List[Segment]:
        """
        识别音频文件
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            Segment 列表
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")
        
        # 获取音频时长（用于时间戳估算）
        audio_duration = self._get_audio_duration(audio_path)
        
        url = f"{self.base_url}/audio/transcriptions"
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # 检测文件格式
        ext = audio_path.suffix.lower().lstrip('.')
        if ext == 'mp3':
            mime_type = 'audio/mpeg'
        elif ext == 'wav':
            mime_type = 'audio/wav'
        elif ext == 'm4a':
            mime_type = 'audio/mp4'
        elif ext == 'ogg':
            mime_type = 'audio/ogg'
        else:
            mime_type = 'audio/mpeg'
        
        file_size_mb = audio_path.stat().st_size / 1024 / 1024
        print(f"[ASR] 上传文件: {audio_path.name} ({file_size_mb:.1f} MB, ~{audio_duration/60:.1f} 分钟)")
        
        # 重试机制
        for attempt in range(self.max_retries):
            try:
                with open(audio_path, "rb") as f:
                    files = {
                        "file": (audio_path.name, f, mime_type),
                        "model": (None, self.model),
                        "language": (None, self.language),
                        "response_format": (None, "verbose_json")  # 获取时间戳信息
                    }
                    
                    print(f"[ASR] 调用 SiliconFlow Whisper API (尝试 {attempt + 1}/{self.max_retries})...")
                    response = requests.post(url, headers=headers, files=files, timeout=self.timeout)
                    response.raise_for_status()
                    result = response.json()
                    
                    print(f"[ASR] 识别完成！")
                    return self._parse_result(result, audio_duration)
                    
            except requests.exceptions.Timeout:
                print(f"[ASR] 请求超时，重试 {attempt + 1}/{self.max_retries}...")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise TimeoutError(f"ASR 请求超时（{self.timeout}秒）")
                    
            except requests.exceptions.RequestException as e:
                print(f"[ASR] 请求失败: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise
        
        return []
    
    def _get_audio_duration(self, audio_path: Path) -> float:
        """获取音频文件时长（秒）"""
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(audio_path)
            return len(audio) / 1000.0  # 毫秒转秒
        except Exception as e:
            print(f"[ASR] 警告: 无法获取音频时长，使用默认值: {e}")
            # 根据文件大小估算（假设 128kbps MP3）
            file_size_bytes = audio_path.stat().st_size
            # 128 kbps = 16 KB/s
            estimated_seconds = file_size_bytes / (16 * 1024)
            return min(estimated_seconds, 7200)  # 最大2小时
    
    def _parse_result(self, result: dict, audio_duration: float = 3600.0) -> List[Segment]:
        """
        解析 ASR API 响应
        
        OpenAI Whisper 格式:
        {
            "text": "完整文本",
            "segments": [
                {
                    "text": "...",
                    "start": 0.0,
                    "end": 1.0,
                    "speaker": "SPEAKER_00"  # 如果有说话人分离
                }
            ]
        }
        
        Args:
            result: API 返回的 JSON
            audio_duration: 音频总时长（秒），用于估算时间戳
        """
        segments = []
        
        # 检查是否有 segments（带时间戳）
        if "segments" in result and result["segments"]:
            for seg in result["segments"]:
                segments.append(Segment(
                    speaker=seg.get("speaker", "SPEAKER_00"),
                    text=seg.get("text", "").strip(),
                    start=float(seg.get("start", 0)),
                    end=float(seg.get("end", 0))
                ))
        elif "text" in result:
            # 只有完整文本，使用智能分割策略
            text = result["text"].strip()
            segments = self._smart_segment_text(text, audio_duration)
        
        print(f"[ASR] 解析完成: {len(segments)} 段")
        # 打印前几段用于调试
        for i, seg in enumerate(segments[:5]):
            print(f"  [{i}] {seg.speaker}: {seg.text[:60]}...")
        if len(segments) > 5:
            print(f"  ... 共 {len(segments)} 段")
        return segments
    
    def _smart_segment_text(self, text: str, total_duration: float = 3600.0) -> List[Segment]:
        """
        智能文本分割 - 将长文本切分为合理的对话片段
        
        策略：
        1. 按句子切分（考虑多种标点）
        2. 检测说话人切换信号（问答模式、称呼等）
        3. 合并短句形成自然段落（100-300字符）
        4. 估算时间戳
        
        Args:
            text: 完整文本
            total_duration: 音频总时长（秒）
            
        Returns:
            Segment 列表
        """
        import re
        
        # 步骤1: 预处理 - 清理文本
        text = self._preprocess_text(text)
        
        # 步骤2: 按句子切分
        raw_sentences = self._split_into_sentences(text)
        
        # 步骤3: 检测说话人切换点
        speaker_changes = self._detect_speaker_changes(raw_sentences)
        
        # 步骤4: 合并成段落（考虑说话人边界）
        paragraphs = self._merge_into_paragraphs(raw_sentences, speaker_changes)
        
        # 步骤5: 分配说话人和时间戳
        segments = self._assign_speakers_and_timestamps(paragraphs, total_duration)
        
        return segments
    
    def _preprocess_text(self, text: str) -> str:
        """预处理文本 - 清理异常字符"""
        # 移除多余的空白
        text = ' '.join(text.split())
        # 修复常见的连写问题
        text = text.replace('?.', '?').replace('!.', '!')
        return text
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """将文本切分为句子列表"""
        import re
        
        # 英文句子结束标点: . ! ? 
        # 同时处理省略号 ...
        pattern = r'(?<=[.!?])\s+|(?<=[.]{3})\s+'
        sentences = re.split(pattern, text)
        
        # 清理并过滤
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # 处理过长的句子（超过500字符的进一步切分）
        result = []
        for sent in sentences:
            if len(sent) > 500:
                # 按逗号或分号进一步切分
                sub_sents = re.split(r'(?<=[,;])\s+', sent)
                sub_sents = [s.strip() for s in sub_sents if s.strip()]
                if len(sub_sents) > 1:
                    result.extend(sub_sents)
                else:
                    result.append(sent)
            else:
                result.append(sent)
        
        return result
    
    def _detect_speaker_changes(self, sentences: List[str]) -> List[int]:
        """
        检测可能的说话人切换点
        
        返回句子索引列表，表示在这些位置之后可能切换说话人
        """
        import re
        
        change_points = []
        
        # 信号1: 问句后面可能是回答
        question_words = ['?', 'what', 'how', 'why', 'when', 'where', 'who', 
                         'can you', 'could you', 'do you', 'are you', 'is it',
                         '告诉我', '什么', '怎么', '为什么', '哪里', '谁']
        
        # 信号2: 对话标记
        dialogue_markers = [
            r'\b(yes|yeah|no|nope|sure|okay|right|exactly|absolutely|definitely)\b',
            r'\b(well|so|but|and|because|however|therefore)\b',
            r'\b(I think|I believe|I feel|I mean|you know)\b',
        ]
        
        # 信号3: 称呼（可能表示回应）
        name_patterns = [
            r'\b(Andre|Andre[\w]*)\b',
            r'\b(Peter|Elon|Sam|Bill)\b',
            r'\b(yeah?,?\s+(Andre|Peter))\b',
        ]
        
        for i, sent in enumerate(sentences):
            sent_lower = sent.lower()
            
            # 如果是问句，标记下一句可能是回答
            if any(q in sent_lower for q in question_words) or sent.endswith('?'):
                if i + 1 < len(sentences):
                    change_points.append(i)
                continue
            
            # 如果以对话标记开头，可能是新说话人
            for pattern in dialogue_markers:
                if re.match(pattern, sent_lower, re.IGNORECASE):
                    if i > 0 and i not in change_points:
                        change_points.append(i - 1)  # 标记前一句结束
                    break
            
            # 如果包含称呼，可能是回应
            for pattern in name_patterns:
                if re.search(pattern, sent, re.IGNORECASE):
                    if i > 0 and (i - 1) not in change_points:
                        change_points.append(i - 1)
                    break
        
        return sorted(set(change_points))
    
    def _merge_into_paragraphs(
        self, 
        sentences: List[str], 
        speaker_changes: List[int]
    ) -> List[str]:
        """
        将句子合并成段落
        
        规则:
        - 目标段落长度: 150-400 字符
        - 在说话人切换点强制分段
        - 避免过长段落（超过600字符）
        """
        if not sentences:
            return []
        
        paragraphs = []
        current = sentences[0]
        
        for i in range(1, len(sentences)):
            sent = sentences[i]
            
            # 检查是否需要分段
            should_split = False
            
            # 条件1: 当前段落已足够长（>300字符）且遇到说话人切换
            if len(current) > 300 and (i - 1) in speaker_changes:
                should_split = True
            
            # 条件2: 当前段落已经很长了（>500字符）
            elif len(current) > 500:
                should_split = True
            
            # 条件3: 下一句很短（<30字符），可能是简短回应
            elif len(sent) < 30 and len(current) > 100:
                should_split = True
            
            # 条件4: 当前段落太短（<100字符），继续合并
            elif len(current) < 100:
                should_split = False
            
            # 条件5: 合并后会太长（>600字符）
            elif len(current) + len(sent) > 600:
                should_split = True
            
            if should_split:
                paragraphs.append(current.strip())
                current = sent
            else:
                current += " " + sent
        
        # 添加最后一段
        if current.strip():
            paragraphs.append(current.strip())
        
        return paragraphs
    
    def _assign_speakers_and_timestamps(
        self, 
        paragraphs: List[str], 
        total_duration: float
    ) -> List[Segment]:
        """
        为段落分配说话人和时间戳
        
        策略:
        - 交替分配 SPEAKER_00 和 SPEAKER_01（模拟对话）
        - 根据文本长度比例分配时间
        """
        if not paragraphs:
            return []
        
        segments = []
        
        # 计算总字符数
        total_chars = sum(len(p) for p in paragraphs)
        
        # 语速估算（字符/秒）
        chars_per_sec = 15 if self.language == "en" else 8
        
        current_time = 0.0
        current_speaker = 0  # 0 或 1
        
        for i, para in enumerate(paragraphs):
            # 估算时长
            est_duration = len(para) / chars_per_sec
            
            # 添加最小和最大时长限制
            est_duration = max(3.0, min(est_duration, 60.0))  # 3-60秒
            
            # 检测是否应该切换说话人
            # 使用简单的交替策略，但考虑段落内容
            if i > 0:
                # 检查是否可能是同一人继续说话
                para_lower = para.lower()
                continuation_markers = ['and ', 'but ', 'so ', 'because ', 'also ', 'plus ']
                is_continuation = any(para_lower.startswith(m) for m in continuation_markers)
                
                # 检查是否明确是回应
                response_markers = ['yes', 'yeah', 'no', 'nope', 'sure', 'right', 'exactly', 
                                   'i think', 'i believe', 'well,', 'so,']
                is_response = any(para_lower.startswith(m) for m in response_markers)
                
                if is_response:
                    current_speaker = 1 - current_speaker  # 切换
                elif not is_continuation:
                    # 默认交替，但允许连续3段同一人
                    if i % 2 == 0:
                        current_speaker = 1 - current_speaker
            
            speaker = f"SPEAKER_{current_speaker:02d}"
            
            segments.append(Segment(
                speaker=speaker,
                text=para,
                start=current_time,
                end=current_time + est_duration
            ))
            
            current_time += est_duration + 0.5  # 添加0.5秒间隔
        
        # 校准时间戳到总时长
        if segments and current_time > 0:
            actual_duration = segments[-1].end
            if actual_duration > 0 and total_duration > 0:
                scale = total_duration / actual_duration
                for seg in segments:
                    seg.start *= scale
                    seg.end *= scale
        
        return segments
    
    def unload_models(self):
        """释放模型资源（云端 API 无需释放）"""
        pass


# 保持兼容性，StepFunASR 别名
class StepFunASR(SiliconFlowASR):
    """StepFunASR 现在使用 SiliconFlow 实现（更好的兼容性和稳定性）"""
    pass
