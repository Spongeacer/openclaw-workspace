"""测试模块 - 验证各组件功能"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from loguru import logger


def test_config():
    """测试配置模块"""
    logger.info("Testing config module...")
    
    from config import get_settings
    
    try:
        settings = get_settings(Path(__file__).parent.parent / "config")
        
        assert settings.provider == "stepfun" or settings.provider == "minimax"
        assert settings.whisper.device == "cpu"
        assert settings.whisper.compute_type == "int8"
        assert settings.output.sample_rate == 44100
        
        voice_config = settings.get_voice_config()
        assert "voice_pool_male" in voice_config
        assert "voice_pool_female" in voice_config
        assert len(voice_config["voice_pool_male"]) > 0
        
        emotion_mapping = settings.get_emotion_mapping()
        assert "高兴" in emotion_mapping
        assert "严肃" in emotion_mapping
        
        logger.success("✓ Config module test passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Config module test failed: {e}")
        return False


def test_downloader():
    """测试下载器模块"""
    logger.info("Testing downloader module...")
    
    from src.downloader import YouTubeDownloader, VideoUnavailableError
    from src.utils import validate_youtube_url, extract_video_id
    
    try:
        # 测试 URL 验证
        assert validate_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == True
        assert validate_youtube_url("https://youtu.be/dQw4w9WgXcQ") == True
        assert validate_youtube_url("invalid_url") == False
        
        # 测试视频 ID 提取
        video_id = extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert video_id == "dQw4w9WgXcQ"
        
        # 测试下载器初始化
        downloader = YouTubeDownloader(Path("./temp"))
        assert downloader.output_dir.exists()
        
        logger.success("✓ Downloader module test passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Downloader module test failed: {e}")
        return False


def test_transcriber():
    """测试语音识别模块"""
    logger.info("Testing transcriber module...")
    
    from src.transcriber import WhisperXTranscriber, Segment
    
    try:
        # 测试数据类
        segment = Segment(
            speaker="SPEAKER_00",
            text="Hello world",
            start=0.0,
            end=1.5
        )
        assert segment.speaker == "SPEAKER_00"
        assert segment.text == "Hello world"
        
        # 测试初始化
        transcriber = WhisperXTranscriber(
            device="cpu",
            compute_type="int8"
        )
        assert transcriber.device == "cpu"
        assert transcriber.compute_type == "int8"
        
        logger.success("✓ Transcriber module test passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Transcriber module test failed: {e}")
        return False


def test_translator():
    """测试翻译模块"""
    logger.info("Testing translator module...")
    
    from src.translator import StepFunTranslator, ChineseSegment
    from src.transcriber import Segment
    
    try:
        # 测试数据类
        zh_segment = ChineseSegment(
            speaker="SPEAKER_00",
            text="你好世界",
            emotion="高兴"
        )
        assert zh_segment.speaker == "SPEAKER_00"
        assert zh_segment.emotion == "高兴"
        
        # 测试情绪提取
        translator = StepFunTranslator.__new__(StepFunTranslator)
        translator.VALID_EMOTIONS = ["高兴", "严肃", "中性"]
        translator.EMOTION_PATTERN = __import__('re').compile(r'\[情绪:(.+?)\]')
        
        emotion, text = translator._extract_emotion("[情绪:高兴] 你好")
        assert emotion == "高兴"
        assert text == "你好"
        
        # 测试无效情绪
        emotion, text = translator._extract_emotion("[情绪:未知] 你好")
        assert emotion == "中性"  # 默认回退
        
        logger.success("✓ Translator module test passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Translator module test failed: {e}")
        return False


def test_tts():
    """测试 TTS 模块"""
    logger.info("Testing TTS module...")
    
    from src.tts_engine import StepFunTTS
    
    try:
        # 测试初始化
        voice_config = {
            "voice_pool_male": ["voice1", "voice2"],
            "voice_pool_female": ["voice3", "voice4"]
        }
        
        tts = StepFunTTS.__new__(StepFunTTS)
        tts.voice_config = voice_config
        tts.voice_map = tts._random_assign_voices()
        
        assert "SPEAKER_00" in tts.voice_map
        assert "SPEAKER_01" in tts.voice_map
        assert tts.voice_map["SPEAKER_00"] in voice_config["voice_pool_male"]
        assert tts.voice_map["SPEAKER_01"] in voice_config["voice_pool_female"]
        
        # 测试情绪映射
        tts._emotion_to_voice_label = StepFunTTS._emotion_to_voice_label
        
        label = tts._emotion_to_voice_label(tts, "高兴")
        assert label.get("emotion") == "高兴"
        
        label = tts._emotion_to_voice_label(tts, "温柔")
        assert label.get("style") == "温柔"
        
        # 测试语速
        tts._get_speed = StepFunTTS._get_speed
        assert tts._get_speed(tts, "快速") == 1.1
        assert tts._get_speed(tts, "慢速") == 0.9
        assert tts._get_speed(tts, "正常") == 1.0
        
        logger.success("✓ TTS module test passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ TTS module test failed: {e}")
        return False


def run_all_tests():
    """运行所有测试"""
    logger.info("=" * 60)
    logger.info("Running All Tests")
    logger.info("=" * 60)
    
    results = []
    
    results.append(("Config", test_config()))
    results.append(("Downloader", test_downloader()))
    results.append(("Transcriber", test_transcriber()))
    results.append(("Translator", test_translator()))
    results.append(("TTS", test_tts()))
    
    logger.info("=" * 60)
    logger.info("Test Results Summary")
    logger.info("=" * 60)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"{name:20s} {status}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    logger.info("=" * 60)
    logger.info(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        logger.success("All tests passed!")
        return 0
    else:
        logger.warning("Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
