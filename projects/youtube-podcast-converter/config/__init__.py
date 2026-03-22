"""
配置中心模块
基于 Pydantic BaseSettings 的多层配置系统
支持多厂商 TTS 配置切换（StepFun / MiniMax）
"""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Literal, Any, Union
from functools import lru_cache

from pydantic import BaseModel, Field, field_validator, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


# ==================== 基础路径配置 ====================
BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = Path(__file__).parent
DEFAULT_YAML_PATH = CONFIG_DIR / "settings.yaml"


# ==================== 情绪标签映射 ====================
class EmotionMapping(BaseModel):
    """情绪标签映射表：翻译层 -> StepFun API"""
    # 基础情绪
    neutral: str = "neutral"           # 中性
    happy: str = "happy"               # 开心
    sad: str = "sad"                   # 悲伤
    angry: str = "angry"               # 愤怒
    fearful: str = "fearful"           # 恐惧
    surprised: str = "surprised"       # 惊讶
    disgusted: str = "disgusted"       # 厌恶
    
    # 播客专用情绪
    excited: str = "excited"           # 兴奋
    calm: str = "calm"                 # 平静
    curious: str = "curious"           # 好奇
    empathetic: str = "empathetic"     # 共情
    professional: str = "professional" # 专业
    humorous: str = "humorous"         # 幽默
    questioning: str = "questioning"   # 疑问
    storytelling: str = "storytelling" # 讲故事
    
    def get_api_emotion(self, emotion: str) -> str:
        """将翻译层情绪标签转换为 StepFun API 情绪标签"""
        return getattr(self, emotion, self.neutral)


# ==================== 音色配置 ====================
class VoicePool(BaseModel):
    """音色池配置"""
    male: List[str] = Field(default_factory=list, description="男性音色列表")
    female: List[str] = Field(default_factory=list, description="女性音色列表")
    default_male: str = Field(default="", description="默认男性音色")
    default_female: str = Field(default="", description="默认女性音色")
    
    def get_voice(self, gender: Literal["male", "female"], index: Optional[int] = None) -> str:
        """获取指定性别的音色"""
        pool = self.male if gender == "male" else self.female
        if not pool:
            return self.default_male if gender == "male" else self.default_female
        
        if index is not None and 0 <= index < len(pool):
            return pool[index]
        
        return pool[0] if pool else (self.default_male if gender == "male" else self.default_female)


# ==================== 厂商配置基类 ====================
class TTSProviderConfig(BaseModel):
    """TTS 厂商配置基类"""
    api_key: str = Field(default="", description="API 密钥")
    base_url: str = Field(default="", description="API 基础 URL")
    timeout: int = Field(default=30, description="请求超时时间（秒）")
    max_retries: int = Field(default=3, description="最大重试次数")


class StepFunConfig(TTSProviderConfig):
    """StepFun API 配置"""
    provider: Literal["stepfun"] = "stepfun"
    
    # 模型配置
    chat_model: str = Field(default="step-1-8k", description="对话模型")
    tts_model: str = Field(default="step-tts-mini", description="TTS 模型")
    
    # 音色池
    voice_pool: VoicePool = Field(default_factory=lambda: VoicePool(
        male=["cixingnansheng", "xiaoshun", "xiaochen", "xiaoming"],
        female=["cixingnvsheng", "xiaoxiao", "xiaoyan", "xiaomei"],
        default_male="cixingnansheng",
        default_female="cixingnvsheng"
    ))
    
    # TTS 参数
    speed: float = Field(default=1.0, ge=0.5, le=2.0, description="语速倍率")
    volume: float = Field(default=1.0, ge=0.0, le=2.0, description="音量倍率")
    
    # 情绪映射
    emotion_mapping: EmotionMapping = Field(default_factory=EmotionMapping)


class MiniMaxConfig(TTSProviderConfig):
    """MiniMax API 配置"""
    provider: Literal["minimax"] = "minimax"
    
    # 模型配置
    chat_model: str = Field(default="abab6-chat", description="对话模型")
    tts_model: str = Field(default="speech-01-turbo", description="TTS 模型")
    
    # 音色池
    voice_pool: VoicePool = Field(default_factory=lambda: VoicePool(
        male=["male-qn-qingse", "male-qn-jingying", "male-qn-badao", "male-qn-daxuesheng"],
        female=["female-shaonv", "female-yujie", "female-chengshu", "female-tianmei"],
        default_male="male-qn-qingse",
        default_female="female-shaonv"
    ))
    
    # TTS 参数
    speed: float = Field(default=1.0, ge=0.5, le=2.0, description="语速倍率")
    volume: int = Field(default=10, ge=0, le=10, description="音量等级 0-10")
    pitch: int = Field(default=0, ge=-10, le=10, description="音调调整 -10~10")


# ==================== Whisper 配置 ====================
class WhisperConfig(BaseModel):
    """Whisper 语音识别配置"""
    # 模型配置
    model_size: Literal["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"] = Field(
        default="large-v3",
        description="Whisper 模型大小"
    )
    
    # 设备配置
    device: Literal["cpu", "cuda", "auto"] = Field(default="auto", description="计算设备")
    compute_type: Literal["int8", "float16", "float32", "default"] = Field(
        default="float16",
        description="计算精度"
    )
    
    # 批处理配置
    batch_size: int = Field(default=16, ge=1, le=64, description="批处理大小")
    
    # 说话人分离配置
    min_speakers: Optional[int] = Field(default=None, ge=1, le=10, description="最小说话人数")
    max_speakers: Optional[int] = Field(default=None, ge=1, le=10, description="最大说话人数")
    
    # 语言配置
    language: str = Field(default="zh", description="主要语言代码")
    
    # VAD 配置
    vad_filter: bool = Field(default=True, description="启用 VAD 过滤")
    vad_parameters: Dict[str, Any] = Field(
        default_factory=lambda: {"threshold": 0.5, "min_speech_duration_ms": 250},
        description="VAD 参数"
    )


# ==================== 输出配置 ====================
class OutputConfig(BaseModel):
    """输出文件配置"""
    # 音频格式
    format: Literal["mp3", "wav", "m4a", "ogg", "flac"] = Field(default="mp3", description="输出格式")
    sample_rate: int = Field(default=24000, description="采样率 Hz")
    channels: Literal[1, 2] = Field(default=1, description="声道数 1=单声道 2=立体声")
    bitrate: str = Field(default="128k", description="比特率（MP3 有效）")
    
    # 质量配置
    quality: Literal["low", "medium", "high", "ultra"] = Field(default="high", description="输出质量")
    
    # 中间文件配置
    keep_intermediate: bool = Field(default=False, description="保留中间文件")
    intermediate_format: Literal["wav", "flac"] = Field(default="wav", description="中间文件格式")
    
    # 输出目录
    output_dir: str = Field(default="./output", description="输出目录")
    temp_dir: str = Field(default="./temp", description="临时目录")
    
    @field_validator('output_dir', 'temp_dir')
    @classmethod
    def validate_path(cls, v: str) -> str:
        """验证并转换路径"""
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return str(path.absolute())


# ==================== 播客处理配置 ====================
class PodcastConfig(BaseModel):
    """播客处理配置"""
    # 分句配置
    max_sentence_length: int = Field(default=100, ge=20, le=500, description="最大句子长度")
    min_sentence_length: int = Field(default=5, ge=1, le=50, description="最小句子长度")
    
    # 并发配置
    max_concurrent_requests: int = Field(default=5, ge=1, le=20, description="最大并发请求数")
    request_interval: float = Field(default=0.5, ge=0.0, le=5.0, description="请求间隔秒数")
    
    # 重试配置
    retry_attempts: int = Field(default=3, ge=1, le=10, description="重试次数")
    retry_delay: float = Field(default=1.0, ge=0.0, le=10.0, description="重试延迟秒数")
    
    # 说话人映射
    speaker_mapping: Dict[str, Dict[str, str]] = Field(
        default_factory=lambda: {
            "SPEAKER_00": {"gender": "female", "emotion": "neutral"},
            "SPEAKER_01": {"gender": "male", "emotion": "neutral"}
        },
        description="说话人到音色/情绪的映射"
    )


# ==================== 主配置类 ====================
class Settings(BaseSettings):
    """
    应用程序主配置类
    优先级: 环境变量 > .env 文件 > YAML 配置 > 默认值
    """
    
    # Pydantic v2 配置
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False
    )
    
    # ==================== 环境变量配置 ====================
    # 激活的 TTS 厂商
    active_provider: Literal["stepfun", "minimax"] = Field(
        default="stepfun",
        alias="ACTIVE_PROVIDER",
        description="当前激活的 TTS 厂商"
    )
    
    # API 密钥（优先从环境变量读取）
    stepfun_api_key: str = Field(default="", alias="STEPFUN_API_KEY")
    minimax_api_key: str = Field(default="", alias="MINIMAX_API_KEY")
    
    # Whisper 模型路径
    whisper_model_dir: str = Field(default="./models", alias="WHISPER_MODEL_DIR")
    
    # 日志级别
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        alias="LOG_LEVEL"
    )
    
    # ==================== YAML 加载的配置 ====================
    # 这些将在初始化时从 YAML 文件加载
    _yaml_data: Dict[str, Any] = {}
    
    # 各模块配置（延迟初始化）
    _stepfun_config: Optional[StepFunConfig] = None
    _minimax_config: Optional[MiniMaxConfig] = None
    _whisper_config: Optional[WhisperConfig] = None
    _output_config: Optional[OutputConfig] = None
    _podcast_config: Optional[PodcastConfig] = None
    
    def __init__(self, yaml_path: Optional[Path] = None, **kwargs):
        super().__init__(**kwargs)
        
        # 加载 YAML 配置
        yaml_file = yaml_path or DEFAULT_YAML_PATH
        if yaml_file.exists():
            with open(yaml_file, 'r', encoding='utf-8') as f:
                self._yaml_data = yaml.safe_load(f) or {}
        else:
            self._yaml_data = {}
            print(f"Warning: YAML config file not found at {yaml_file}")
    
    # ==================== 配置获取方法 ====================
    
    def get_tts_config(self) -> Union[StepFunConfig, MiniMaxConfig]:
        """获取当前激活的 TTS 配置"""
        if self.active_provider == "stepfun":
            return self._get_stepfun_config()
        elif self.active_provider == "minimax":
            return self._get_minimax_config()
        else:
            raise ValueError(f"Unknown provider: {self.active_provider}")
    
    def _get_stepfun_config(self) -> StepFunConfig:
        """获取 StepFun 配置（带缓存）"""
        if self._stepfun_config is None:
            provider_config = self._yaml_data.get("providers", {}).get("stepfun", {})
            
            # 环境变量覆盖 YAML 配置
            self._stepfun_config = StepFunConfig(
                api_key=self.stepfun_api_key or provider_config.get("api_key", ""),
                base_url=provider_config.get("base_url", "https://api.stepfun.com/v1"),
                chat_model=provider_config.get("chat_model", "step-1-8k"),
                tts_model=provider_config.get("tts_model", "step-tts-mini"),
                timeout=provider_config.get("timeout", 30),
                max_retries=provider_config.get("max_retries", 3),
                speed=provider_config.get("speed", 1.0),
                volume=provider_config.get("volume", 1.0),
                voice_pool=VoicePool(**provider_config.get("voice_pool", {})),
                emotion_mapping=EmotionMapping(**provider_config.get("emotion_mapping", {}))
            )
        return self._stepfun_config
    
    def _get_minimax_config(self) -> MiniMaxConfig:
        """获取 MiniMax 配置（带缓存）"""
        if self._minimax_config is None:
            provider_config = self._yaml_data.get("providers", {}).get("minimax", {})
            
            self._minimax_config = MiniMaxConfig(
                api_key=self.minimax_api_key or provider_config.get("api_key", ""),
                base_url=provider_config.get("base_url", "https://api.minimax.chat/v1"),
                chat_model=provider_config.get("chat_model", "abab6-chat"),
                tts_model=provider_config.get("tts_model", "speech-01-turbo"),
                timeout=provider_config.get("timeout", 30),
                max_retries=provider_config.get("max_retries", 3),
                speed=provider_config.get("speed", 1.0),
                volume=provider_config.get("volume", 10),
                pitch=provider_config.get("pitch", 0),
                voice_pool=VoicePool(**provider_config.get("voice_pool", {}))
            )
        return self._minimax_config
    
    def get_whisper_config(self) -> WhisperConfig:
        """获取 Whisper 配置"""
        if self._whisper_config is None:
            whisper_data = self._yaml_data.get("whisper", {})
            self._whisper_config = WhisperConfig(**whisper_data)
        return self._whisper_config
    
    def get_output_config(self) -> OutputConfig:
        """获取输出配置"""
        if self._output_config is None:
            output_data = self._yaml_data.get("output", {})
            self._output_config = OutputConfig(**output_data)
        return self._output_config
    
    def get_podcast_config(self) -> PodcastConfig:
        """获取播客处理配置"""
        if self._podcast_config is None:
            podcast_data = self._yaml_data.get("podcast", {})
            self._podcast_config = PodcastConfig(**podcast_data)
        return self._podcast_config
    
    # ==================== 快捷方法 ====================
    
    def get_voice_for_speaker(self, speaker_id: str) -> Dict[str, str]:
        """根据说话人 ID 获取音色配置"""
        podcast_config = self.get_podcast_config()
        mapping = podcast_config.speaker_mapping.get(speaker_id, {
            "gender": "female",
            "emotion": "neutral"
        })
        
        tts_config = self.get_tts_config()
        voice = tts_config.voice_pool.get_voice(mapping["gender"])
        emotion = getattr(tts_config.emotion_mapping, mapping["emotion"], "neutral") \
            if hasattr(tts_config, 'emotion_mapping') else "neutral"
        
        return {
            "voice": voice,
            "emotion": emotion,
            "gender": mapping["gender"],
            "emotion_label": mapping["emotion"]
        }
    
    def get_all_available_voices(self) -> Dict[str, List[str]]:
        """获取所有可用音色列表"""
        tts_config = self.get_tts_config()
        return {
            "male": tts_config.voice_pool.male,
            "female": tts_config.voice_pool.female
        }
    
    def reload_yaml(self, yaml_path: Optional[Path] = None):
        """重新加载 YAML 配置"""
        yaml_file = yaml_path or DEFAULT_YAML_PATH
        if yaml_file.exists():
            with open(yaml_file, 'r', encoding='utf-8') as f:
                self._yaml_data = yaml.safe_load(f) or {}
        
        # 清空缓存
        self._stepfun_config = None
        self._minimax_config = None
        self._whisper_config = None
        self._output_config = None
        self._podcast_config = None


# ==================== 全局实例 ====================

@lru_cache()
def get_settings(yaml_path: Optional[Path] = None) -> Settings:
    """获取配置单例（带缓存）"""
    return Settings(yaml_path=yaml_path)


# 便捷导入
def get_config() -> Settings:
    """获取配置实例的快捷方式"""
    return get_settings()


# ==================== 配置验证 ====================

def validate_config(settings: Optional[Settings] = None) -> Dict[str, Any]:
    """
    验证配置完整性
    返回验证结果字典
    """
    if settings is None:
        settings = get_settings()
    
    result = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "info": {}
    }
    
    # 检查 TTS 配置
    try:
        tts_config = settings.get_tts_config()
        if not tts_config.api_key:
            result["warnings"].append(f"{settings.active_provider} API key is not set")
        result["info"]["active_provider"] = settings.active_provider
        result["info"]["available_voices"] = len(tts_config.voice_pool.male) + len(tts_config.voice_pool.female)
    except Exception as e:
        result["errors"].append(f"TTS config error: {str(e)}")
        result["valid"] = False
    
    # 检查 Whisper 配置
    try:
        whisper_config = settings.get_whisper_config()
        result["info"]["whisper_model"] = whisper_config.model_size
    except Exception as e:
        result["errors"].append(f"Whisper config error: {str(e)}")
        result["valid"] = False
    
    # 检查输出配置
    try:
        output_config = settings.get_output_config()
        result["info"]["output_format"] = output_config.format
        result["info"]["output_dir"] = output_config.output_dir
    except Exception as e:
        result["errors"].append(f"Output config error: {str(e)}")
        result["valid"] = False
    
    return result


# ==================== 调试输出 ====================

if __name__ == "__main__":
    # 测试配置加载
    print("=" * 60)
    print("YouTube Podcast Converter - Configuration Test")
    print("=" * 60)
    
    config = get_settings()
    
    print(f"\nActive Provider: {config.active_provider}")
    print(f"Log Level: {config.log_level}")
    
    # TTS 配置
    tts = config.get_tts_config()
    print(f"\n--- TTS Config ({config.active_provider}) ---")
    print(f"Chat Model: {tts.chat_model}")
    print(f"TTS Model: {tts.tts_model}")
    print(f"Male Voices: {tts.voice_pool.male}")
    print(f"Female Voices: {tts.voice_pool.female}")
    
    if hasattr(tts, 'emotion_mapping'):
        print(f"Emotions: {list(tts.emotion_mapping.model_fields.keys())}")
    
    # Whisper 配置
    whisper = config.get_whisper_config()
    print(f"\n--- Whisper Config ---")
    print(f"Model: {whisper.model_size}")
    print(f"Device: {whisper.device}")
    print(f"Compute Type: {whisper.compute_type}")
    print(f"Batch Size: {whisper.batch_size}")
    
    # 输出配置
    output = config.get_output_config()
    print(f"\n--- Output Config ---")
    print(f"Format: {output.format}")
    print(f"Sample Rate: {output.sample_rate}")
    print(f"Channels: {output.channels}")
    print(f"Keep Intermediate: {output.keep_intermediate}")
    
    # 播客配置
    podcast = config.get_podcast_config()
    print(f"\n--- Podcast Config ---")
    print(f"Max Sentence Length: {podcast.max_sentence_length}")
    print(f"Max Concurrent: {podcast.max_concurrent_requests}")
    print(f"Speaker Mapping: {list(podcast.speaker_mapping.keys())}")
    
    # 验证配置
    print(f"\n--- Validation ---")
    validation = validate_config(config)
    print(f"Valid: {validation['valid']}")
    if validation['errors']:
        print(f"Errors: {validation['errors']}")
    if validation['warnings']:
        print(f"Warnings: {validation['warnings']}")
    print(f"Info: {validation['info']}")
    
    print("\n" + "=" * 60)
    print("Configuration loaded successfully!")
    print("=" * 60)
