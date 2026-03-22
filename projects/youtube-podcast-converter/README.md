# YouTube 英文播客转中文语音合成系统

将 YouTube 英文多人对话视频转换为**自然中文播客音频**（带角色区分与情绪表达）。

## 系统架构

```
YouTube URL
    ↓
[Downloader] - yt-dlp 提取音频 (192kbps MP3)
    ↓
[Transcriber] - WhisperX medium (本地 ASR + 说话人分离)
    ↓
[Translator] - StepFun step-2-mini (意译 + 情绪标签)
    ↓
[TTSEngine] - StepFun step-tts-2 (随机音色 + 立体声)
    ↓
中文播客音频 (立体声 MP3)
```

## 运行环境

- **平台**: Apple M1 Mac (16GB RAM)
- **ASR 模式**: CPU (int8 量化，内存 < 2GB)
- **云端 API**: StepFun (翻译 + TTS)

## 安装

### 1. 克隆仓库

```bash
git clone <repo-url>
cd youtube-podcast-converter
```

### 2. 创建虚拟环境

```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
cp config/.env.example config/.env
# 编辑 config/.env，填入你的 StepFun API Key
```

### 5. 安装 FFmpeg

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg
```

## 使用方法

```bash
python main.py "https://www.youtube.com/watch?v=xxxxx"
```

### 可选参数

```bash
python main.py <youtube_url> \
    --config config \
    --output output
```

## 配置说明

### 环境变量 (.env)

```bash
ACTIVE_PROVIDER=stepfun
STEPFUN_API_KEY=your_api_key_here
STEPFUN_BASE_URL=https://api.stepfun.com/v1
```

### 业务配置 (settings.yaml)

- **音色池**: 男声/女声各 4 种，随机分配
- **情绪标签**: 10 种（高兴/悲伤/生气/兴奋/困惑/惊讶/温柔/严肃/快速/慢速）
- **WhisperX**: medium 模型，CPU 模式，int8 量化

## 输出结构

```
output/
└── {timestamp}_{video_id}/
    ├── raw.mp3              # 原始音频
    ├── en_segments.json     # 英文识别结果
    ├── zh_segments.json     # 中文翻译结果（含情绪）
    ├── final_stereo.mp3     # 最终输出（立体声）
    └── pipeline.log         # 处理日志
```

## 立体声说明

- **左声道 (-1.0)**: SPEAKER_00（主持人）
- **右声道 (+1.0)**: SPEAKER_01（嘉宾）
- **200ms 间隔**: 模拟自然对话停顿

## 故障排除

### 磁盘空间不足

确保有至少 1GB 可用空间（临时文件 + 输出）。

### WhisperX 内存错误

M1 基础版强制使用 CPU 模式 + int8 量化，内存占用 < 2GB。

### API 限流

翻译模块使用指数退避重试（2s/4s/8s，最多 3 次）。

## License

MIT
