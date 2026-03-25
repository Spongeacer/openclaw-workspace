"""QA 重组模块 - 将连续段落重组为问答对，支持智能切分和添加过渡"""
from dataclasses import dataclass
from typing import List, Optional, Dict
from src.translator import ChineseSegment


@dataclass
class QAPair:
    """问答对数据结构"""
    index: int           # 序号
    question: str        # 问题文本
    answer: str          # 回答文本
    q_speaker: str       # 提问者
    a_speaker: str       # 回答者
    q_emotion: str       # 问题情绪
    a_emotion: str       # 回答情绪
    start_time: float    # 开始时间
    end_time: float      # 结束时间
    is_transition: bool = False  # 是否为过渡段落
    
    def is_valid(self, min_q_length: int = 20, min_a_length: int = 30) -> bool:
        """检查 QA 对是否有效"""
        return (
            len(self.question) >= min_q_length and
            len(self.answer) >= min_a_length
        )


class QAReorganizer:
    """QA 重组器 - 支持智能切分和节目包装"""
    
    def __init__(
        self,
        max_segment_length: int = 150,  # 最大段落长度
        min_q_length: int = 20,
        min_a_length: int = 30,
        add_intros: bool = True,         # 添加开场/结尾
        add_transitions: bool = True,    # 添加过渡
        topic_break_interval: int = 5    # 每几个 QA 插入过渡
    ):
        self.max_segment_length = max_segment_length
        self.min_q_length = min_q_length
        self.min_a_length = min_a_length
        self.add_intros = add_intros
        self.add_transitions = add_transitions
        self.topic_break_interval = topic_break_interval
        
        # 音色分配
        self.voice_pool_q = ["elegantgentle-female"]
        self.voice_pool_a = ["cixingnansheng"]
    
    def reorganize(
        self, 
        segments: List[ChineseSegment],
        speaker_roles: Optional[Dict[str, str]] = None
    ) -> List[QAPair]:
        """
        将段落重组为 QA 对
        
        Args:
            segments: 中文语音片段列表
            speaker_roles: 说话人角色映射
        
        Returns:
            QA 对列表
        """
        if not segments:
            return []
        
        # 自动推断角色
        if speaker_roles is None:
            speaker_roles = self._infer_roles(segments)
        
        # 1. 先按角色分组形成原始 QA 对
        raw_pairs = self._create_raw_pairs(segments, speaker_roles)
        
        # 2. 切分过长段落
        split_pairs = self._split_long_pairs(raw_pairs)
        
        # 3. 添加开场
        final_pairs = []
        if self.add_intros:
            intro_pairs = self._create_intro(segments[0].speaker, segments[1].speaker if len(segments) > 1 else segments[0].speaker)
            final_pairs.extend(intro_pairs)
        
        # 4. 添加过渡
        for i, pair in enumerate(split_pairs):
            if self.add_transitions and i > 0 and i % self.topic_break_interval == 0:
                transition = self._create_transition(i, pair.q_speaker, pair.a_speaker)
                final_pairs.append(transition)
            final_pairs.append(pair)
        
        # 5. 添加结尾
        if self.add_intros:
            outro_pairs = self._create_outro(
                split_pairs[-1].q_speaker if split_pairs else segments[0].speaker,
                split_pairs[-1].a_speaker if split_pairs else segments[0].speaker
            )
            final_pairs.extend(outro_pairs)
        
        # 重新编号
        for i, pair in enumerate(final_pairs):
            pair.index = i + 1
        
        return final_pairs
    
    def _create_raw_pairs(
        self, 
        segments: List[ChineseSegment],
        speaker_roles: Dict[str, str]
    ) -> List[QAPair]:
        """创建原始 QA 对"""
        qa_pairs = []
        current_q = None
        current_q_seg = None
        current_q_index = 0
        
        for i, seg in enumerate(segments):
            role = speaker_roles.get(seg.speaker, 'Q')
            
            if role == 'Q':
                current_q = seg.text
                current_q_seg = seg
                current_q_index = i
                
            elif role == 'A' and current_q is not None:
                pair = QAPair(
                    index=len(qa_pairs) + 1,
                    question=current_q,
                    answer=seg.text,
                    q_speaker=current_q_seg.speaker,
                    a_speaker=seg.speaker,
                    q_emotion=current_q_seg.emotion or "中性",
                    a_emotion=seg.emotion or "中性",
                    start_time=float(current_q_index),
                    end_time=float(i)
                )
                if pair.is_valid(self.min_q_length, self.min_a_length):
                    qa_pairs.append(pair)
                
                current_q = None
                current_q_seg = None
        
        return qa_pairs
    
    def _split_long_pairs(self, pairs: List[QAPair]) -> List[QAPair]:
        """切分过长的 QA 对"""
        result = []
        
        for pair in pairs:
            # 切分长 Q
            q_parts = self._split_text(pair.question, self.max_segment_length)
            a_parts = self._split_text(pair.answer, self.max_segment_length)
            
            # 如果只有一段，直接添加
            if len(q_parts) == 1 and len(a_parts) == 1:
                result.append(pair)
                continue
            
            # 如果 Q 和 A 都很长，交替添加
            max_parts = max(len(q_parts), len(a_parts))
            for i in range(max_parts):
                if i < len(q_parts):
                    # Q 的后续段落作为新的 Q
                    new_pair = QAPair(
                        index=0,  # 稍后重新编号
                        question=q_parts[i],
                        answer=a_parts[i] if i < len(a_parts) else "（继续）",
                        q_speaker=pair.q_speaker,
                        a_speaker=pair.a_speaker,
                        q_emotion=pair.q_emotion,
                        a_emotion=pair.a_emotion,
                        start_time=pair.start_time,
                        end_time=pair.end_time
                    )
                    result.append(new_pair)
                elif i < len(a_parts):
                    # 只有 A 还有内容
                    new_pair = QAPair(
                        index=0,
                        question="接着刚才的说...",
                        answer=a_parts[i],
                        q_speaker=pair.q_speaker,
                        a_speaker=pair.a_speaker,
                        q_emotion="中性",
                        a_emotion=pair.a_emotion,
                        start_time=pair.start_time,
                        end_time=pair.end_time
                    )
                    result.append(new_pair)
        
        return result
    
    def _split_text(self, text: str, max_length: int) -> List[str]:
        """按语义切分文本"""
        if len(text) <= max_length:
            return [text]
        
        # 按句子切分
        import re
        sentences = re.split(r'(?<=[。！？；.!?;])\s*', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        parts = []
        current = ""
        
        for sent in sentences:
            if len(current) + len(sent) < max_length:
                current += sent
            else:
                if current:
                    parts.append(current)
                current = sent
        
        if current:
            parts.append(current)
        
        # 如果还是太长，强制切分
        if not parts:
            parts = [text[i:i+max_length] for i in range(0, len(text), max_length)]
        
        return parts
    
    def _create_intro(self, q_speaker: str, a_speaker: str) -> List[QAPair]:
        """创建开场包装"""
        return [
            QAPair(
                index=0,
                question="欢迎收听 No Priors，我是主持人。今天我们有幸邀请到了 Andrej Karpathy，聊聊 AI 代码代理。",
                answer="嗨，大家好，我是 Andrej。这个话题挺有意思的，咱们好好聊聊。",
                q_speaker=q_speaker,
                a_speaker=a_speaker,
                q_emotion="高兴",
                a_emotion="高兴",
                start_time=0.0,
                end_time=1.0,
                is_transition=True
            ),
            QAPair(
                index=0,
                question="本期话题是代码代理。简单说，AI 现在能帮我们写代码了，这事儿到底意味着什么？",
                answer="对，这个话题挺有意思的。咱们得好好聊聊。",
                q_speaker=q_speaker,
                a_speaker=a_speaker,
                q_emotion="兴奋",
                a_emotion="兴奋",
                start_time=1.0,
                end_time=2.0,
                is_transition=True
            )
        ]
    
    def _create_outro(self, q_speaker: str, a_speaker: str) -> List[QAPair]:
        """创建结尾包装"""
        return [
            QAPair(
                index=0,
                question="好，今天的对话就到这里。感谢 Andrej 的分享，希望对大家有所启发。",
                answer="谢谢邀请，希望这些内容对大家有帮助。咱们下次再聊。",
                q_speaker=q_speaker,
                a_speaker=a_speaker,
                q_emotion="高兴",
                a_emotion="高兴",
                start_time=999.0,
                end_time=1000.0,
                is_transition=True
            )
        ]
    
    def _create_transition(self, index: int, q_speaker: str, a_speaker: str) -> QAPair:
        """创建过渡段落"""
        transitions = [
            ("刚才聊了不少技术细节，可能有点干，咱们换个角度聊聊？", "行啊，换个思路说说，看看还有什么角度可以探讨。"),
            ("说到这儿，我突然想到一个有意思的点。", "哦？什么有意思的点，说来听听。"),
            ("那咱们接着往下聊。", "好的，继续聊，看看还有什么值得探讨的。"),
            ("这个问题挺关键的，咱们展开说说。", "没问题，这个问题确实值得深入聊聊。"),
        ]
        
        # 根据 index 选择不同的过渡语
        if index <= 5:
            q_text, a_text = transitions[0]
        elif index <= 10:
            q_text, a_text = transitions[1]
        elif index <= 15:
            q_text, a_text = transitions[2]
        else:
            q_text, a_text = transitions[3]
        
        return QAPair(
            index=0,
            question=q_text,
            answer=a_text,
            q_speaker=q_speaker,
            a_speaker=a_speaker,
            q_emotion="中性",
            a_emotion="中性",
            start_time=float(index),
            end_time=float(index) + 0.5,
            is_transition=True
        )
    
    def _infer_roles(self, segments: List[ChineseSegment]) -> Dict[str, str]:
        """推断说话人角色"""
        speakers = []
        for seg in segments:
            if seg.speaker not in speakers:
                speakers.append(seg.speaker)
        
        roles = {}
        for i, speaker in enumerate(speakers):
            if i == 0:
                roles[speaker] = 'Q'
            elif i == 1:
                roles[speaker] = 'A'
            else:
                roles[speaker] = 'Q'  # 其他人也当 Q
        
        return roles
    
    def assign_voices(self, qa_pairs: List[QAPair]) -> Dict[str, str]:
        """分配音色"""
        voice_map = {}
        
        for pair in qa_pairs:
            if pair.q_speaker not in voice_map:
                voice_map[pair.q_speaker] = self.voice_pool_q[0]
            if pair.a_speaker not in voice_map:
                voice_map[pair.a_speaker] = self.voice_pool_a[0]
        
        return voice_map
    
    def to_dict_list(self, qa_pairs: List[QAPair]) -> List[dict]:
        """转换为字典列表"""
        return [
            {
                "index": pair.index,
                "question": pair.question,
                "answer": pair.answer,
                "q_speaker": pair.q_speaker,
                "a_speaker": pair.a_speaker,
                "q_emotion": pair.q_emotion,
                "a_emotion": pair.a_emotion,
                "start_time": pair.start_time,
                "end_time": pair.end_time,
                "is_transition": pair.is_transition
            }
            for pair in qa_pairs
        ]
