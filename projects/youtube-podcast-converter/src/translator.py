"""翻译引擎模块 - 调用 StepFun API 进行意译翻译"""
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple
import openai
from tenacity import retry, stop_after_attempt, wait_exponential

# 导入语音识别模块的数据类
from .transcriber import Segment


@dataclass
class ChineseSegment:
    """中文语音片段数据类"""
    speaker: str
    text: str
    emotion: str  # 高兴、严肃、温柔等
    style: Optional[str] = None  # 预留


class StepFunTranslator:
    """StepFun 翻译引擎"""
    
    # 情绪标签正则表达式
    EMOTION_PATTERN = re.compile(r'\[情绪:(.+?)\]')
    
    # 有效的情绪列表
    VALID_EMOTIONS = [
        "高兴", "悲伤", "生气", "兴奋", 
        "困惑", "惊讶", "温柔", "严肃",
        "快速", "慢速", "中性"
    ]
    
    def __init__(
        self, 
        api_key: str, 
        base_url: str = "https://api.stepfun.com/v1", 
        model: str = "step-2-mini"
    ):
        """
        初始化翻译器
        
        Args:
            api_key: StepFun API 密钥
            base_url: API 基础 URL
            model: 模型名称
        """
        self.client = openai.OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
    
    @retry(
        stop=stop_after_attempt(3), 
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def _translate_batch(self, texts: List[str]) -> List[str]:
        """
        批量翻译文本
        
        Args:
            texts: 英文文本列表
            
        Returns:
            中文翻译结果列表
        """
        # 组合文本，用分隔符标记
        combined = "\n---\n".join([f"[{i}] {t}" for i, t in enumerate(texts)])
        
        system_prompt = """你是资深播客本地化专家。将英文译为地道中文口语：
1. 去翻译腔：删除"那么"、"就是"，改用"其实"、"说白了"
2. 每段前加 [情绪:xxx]，从[高兴/悲伤/生气/兴奋/困惑/惊讶/温柔/严肃/快速/慢速/中性]选
3. 保留说话人上下文，确保翻译连贯
4. 意译优先，传达情绪而非逐字翻译
5. 如果原文是疑问句，译文也要是疑问句

格式示例：
[情绪:严肃] 今天咱们要聊个严肃话题。
[情绪:高兴] 哈哈，这太有意思了！

待译内容："""
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": combined}
            ],
            temperature=0.6,
            max_tokens=2000
        )
        
        result = response.choices[0].message.content
        return self._parse_batch_result(result, len(texts))
    
    def _parse_batch_result(self, result: str, expected_count: int) -> List[str]:
        """
        解析批量翻译结果
        
        Args:
            result: API 返回的文本
            expected_count: 期望的段落数
            
        Returns:
            分段后的翻译结果
        """
        # 按 --- 分隔
        parts = result.split("---")
        parts = [p.strip() for p in parts if p.strip()]
        
        # 如果数量不匹配，尝试按行分割
        if len(parts) != expected_count:
            lines = []
            for line in result.split("\n"):
                line = line.strip()
                # 查找包含情绪标签的行
                if line and ("[情绪:" in line or any(e in line for e in self.VALID_EMOTIONS)):
                    lines.append(line)
            parts = lines
        
        # 补齐或截断到期望数量
        if len(parts) < expected_count:
            parts.extend(["[情绪:中性] 翻译失败"] * (expected_count - len(parts)))
        
        return parts[:expected_count]
    
    def _extract_emotion(self, text: str) -> Tuple[str, str]:
        """
        从文本中提取情绪标签
        
        Args:
            text: 带情绪标签的文本
            
        Returns:
            (情绪, 清理后的文本)
        """
        match = self.EMOTION_PATTERN.search(text)
        if match:
            emotion = match.group(1).strip()
            # 验证情绪是否有效
            if emotion not in self.VALID_EMOTIONS:
                emotion = "中性"
            clean_text = self.EMOTION_PATTERN.sub("", text).strip()
            return emotion, clean_text
        return "中性", text
    
    def _group_by_speaker(
        self, 
        segments: List[Segment], 
        max_batch_size: int = 5
    ) -> List[List[Segment]]:
        """
        按说话人分组（连续同说话人）
        
        Args:
            segments: 语音片段列表
            max_batch_size: 每组最大数量
            
        Returns:
            分组后的片段列表
        """
        if not segments:
            return []
        
        batches = []
        current_batch = [segments[0]]
        
        for seg in segments[1:]:
            # 如果说话人相同且未达上限，加入当前组
            if seg.speaker == current_batch[-1].speaker and len(current_batch) < max_batch_size:
                current_batch.append(seg)
            else:
                # 开始新组
                batches.append(current_batch)
                current_batch = [seg]
        
        # 添加最后一组
        if current_batch:
            batches.append(current_batch)
        
        return batches
    
    def translate_segments(self, segments: List[Segment]) -> List[ChineseSegment]:
        """
        翻译语音片段
        
        Args:
            segments: 英文语音片段列表
            
        Returns:
            中文语音片段列表
        """
        if not segments:
            return []
        
        chinese_segments = []
        
        # 按说话人分组，保持上下文连贯性
        batches = self._group_by_speaker(segments, max_batch_size=5)
        
        for batch in batches:
            texts = [seg.text for seg in batch]
            
            try:
                translated_texts = self._translate_batch(texts)
            except Exception as e:
                # 翻译失败时使用原文并标记
                translated_texts = [f"[情绪:中性] {seg.text}" for seg in batch]
            
            for seg, trans in zip(batch, translated_texts):
                emotion, clean_text = self._extract_emotion(trans)
                
                # 如果清理后文本为空，使用原文
                if not clean_text.strip():
                    clean_text = seg.text
                    emotion = "中性"
                
                chinese_segments.append(ChineseSegment(
                    speaker=seg.speaker,
                    text=clean_text,
                    emotion=emotion
                ))
        
        return chinese_segments
