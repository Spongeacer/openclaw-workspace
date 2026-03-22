"""src 包初始化"""

# 尝试导入各模块，失败时不抛出异常
_import_errors = {}

try:
    from .downloader import YouTubeDownloader, VideoUnavailableError
except ImportError as e:
    YouTubeDownloader = None
    VideoUnavailableError = None
    _import_errors['downloader'] = str(e)

try:
    from .transcriber import WhisperXTranscriber, Segment
except ImportError as e:
    WhisperXTranscriber = None
    Segment = None
    _import_errors['transcriber'] = str(e)

try:
    from .translator import StepFunTranslator, ChineseSegment
except ImportError as e:
    StepFunTranslator = None
    ChineseSegment = None
    _import_errors['translator'] = str(e)

try:
    from .tts_engine import StepFunTTS
except ImportError as e:
    StepFunTTS = None
    _import_errors['tts_engine'] = str(e)

try:
    from .pipeline import PodcastPipeline
except ImportError as e:
    PodcastPipeline = None
    _import_errors['pipeline'] = str(e)

__all__ = [
    'YouTubeDownloader',
    'VideoUnavailableError',
    'WhisperXTranscriber',
    'Segment',
    'StepFunTranslator',
    'ChineseSegment',
    'StepFunTTS',
    'PodcastPipeline',
]

# 导出导入错误信息以便诊断
if _import_errors:
    __import_errors__ = _import_errors
