# YouTube Podcast Converter

将 YouTube 英文播客转换为中文语音播客的自动化流水线。支持对话式 QA 格式、开场/结尾包装、质量检查等功能。

## 🎯 核心功能

| 功能 | 说明 |
|------|------|
| **YouTube 下载** | yt-dlp + aria2c 多线程下载，支持断点续传 |
| **语音识别 (ASR)** | SiliconFlow Whisper 识别英文内容 |
| **智能翻译** | StepFun Chat API (step-2-16k) 意译，保留专业名词 |
| **QA 重组** | 将连续对话重组为问答对，添加开场/过渡/结尾 |
| **语音合成 (TTS)** | StepFun TTS 生成中文语音，单声道输出 |
| **质量检查** | 自动检查翻译质量、QA 完整性、音频时长 |

## 🏗️ 架构流程

```
YouTube URL → Download → ASR → Translate → QA Reorganize → TTS → Quality Check → Output
```

## 📁 项目结构

```
.
├── src/
│   ├── pipeline.py           # 主流水线（6阶段）
│   ├── downloader.py         # YouTube 下载器
│   ├── transcriber.py        # ASR 语音识别
│   ├── translator.py         # 翻译模块
│   ├── qa_reorganizer.py     # QA 重组器
│   ├── tts_engine.py         # TTS 引擎（增强版）
│   └── quality_checker.py    # 质量检查器
├── config/
│   ├── settings.yaml         # 配置文件
│   └── .env                  # API Key
├── check_quality.py          # 质量检查脚本
├── regenerate_tts.py         # 重新生成 TTS（断点续传）
├── run_full_pipeline.py      # 完整流水线
├── run_pipeline_stages.py    # 分阶段执行
└── README.md
```

## 🔧 安装

```bash
# 安装依赖
pip install -r requirements.txt

# 安装系统依赖
apt-get install ffmpeg  # 音频处理
```

## ⚙️ 配置

所有参数统一通过 `config/settings.yaml` 管理，支持环境变量覆盖。

### 环境变量（敏感信息）

```bash
export STEPFUN_API_KEY="your-stepfun-key"
export SILICONFLOW_API_KEY="your-siliconflow-key"
```

### 配置文件

编辑 `config/settings.yaml`:

```yaml
providers:
  stepfun:
    base_url: "https://api.stepfun.com/v1"
    chat_model: "step-2-16k"      # 翻译模型
    tts_model: "step-tts-mini"     # TTS 模型

# TTS 引擎参数
tts_engine:
  min_interval: 6.0              # 请求间隔（秒）
  max_retries: 3                 # 最大重试次数
  text_max_length: 400           # 最大文本长度
  sample_rate: 24000             # 采样率

# 脚本运行时配置
scripts:
  regenerate_tts:
    qa_pairs_file: "qa_pairs_v2.json"
    output_audio: "podcast_final_v2.mp3"
  pipeline:
    asr_model: "FunAudioLLM/SenseVoiceSmall"
    translator_model: "step-2-mini"
```

## 🚀 使用方式

### 方式 1: 完整流水线 (配置驱动)

```bash
# 使用配置中的默认设置
python run_full_pipeline.py

# 指定源文件和工作目录
python run_full_pipeline.py --raw-mp3 /path/to/raw.mp3 --work-dir ./output/my_run
```

### 方式 2: 分阶段执行

```bash
# 执行所有阶段
python run_pipeline_stages.py

# 仅执行 ASR
python run_pipeline_stages.py --stage asr --raw-mp3 /path/to/raw.mp3

# 仅执行翻译（需要已有 ASR 结果）
python run_pipeline_stages.py --stage translate --work-dir ./output/pipeline_xxx

# 仅执行 TTS（需要已有翻译结果）
python run_pipeline_stages.py --stage tts --work-dir ./output/pipeline_xxx
```

### 方式 3: 重新生成 TTS (断点续传)

```bash
# 自动查找最新的 pipeline 目录
python regenerate_tts.py

# 指定工作目录
python regenerate_tts.py --work-dir ./output/pipeline_xxx

# 指定输出路径
python regenerate_tts.py -w ./output/pipeline_xxx -o ./output/final.mp3
```

### 方式 4: 质量检查

```bash
# 自动查找最新的 pipeline 目录
python check_quality.py

# 指定目录
python check_quality.py ./output/pipeline_xxx
```

检查已生成文件的质量：

```bash
python check_quality.py output/pipeline_xxx/
```

## 📊 输出文件

```
output/
└── pipeline_{timestamp}/
    ├── raw.mp3              # 原始音频
    ├── en_segments.json     # 英文识别结果
    ├── zh_segments.json     # 中文翻译结果
    ├── qa_pairs.json        # QA 对（含开场/过渡/结尾）
    ├── final_podcast.mp3    # 最终音频
    ├── quality_report.txt   # 质量检查报告
    └── tts_progress.json    # TTS 进度（断点续传用）
```

## 💰 成本估算

65 分钟播客示例 (No Priors):

| 阶段 | 服务 | 费用 |
|------|------|------|
| ASR | SiliconFlow Whisper | ~¥0.13 |
| 翻译 | StepFun step-2-16k | ~¥2-3 |
| TTS | StepFun TTS | ~¥3-5 |
| **总计** | | **¥5-8** |

## ⚙️ 配置选项

### settings.yaml

```yaml
providers:
  stepfun:
    api_key: "xxx"
    base_url: "https://api.stepfun.com/v1"
    chat_model: "step-2-16k"      # 翻译模型
    tts_model: "step-tts-mini"        # TTS 模型
  
  siliconflow:
    api_key: "xxx"
    base_url: "https://api.siliconflow.cn/v1"

output:
  sample_rate: 24000
  bitrate: "192k"
  channels: 1                      # 单声道

voice_config:
  voice_pool_male: ["cixingnansheng"]
  voice_pool_female: ["elegantgentle-female"]
```

## 🛡️ 常见问题

### 1. TTS 400 错误

**原因**: 文本过长或参数无效  
**解决**: TTS 引擎会自动切分长文本（最大 400 字符）

### 2. TTS 429 速率限制

**原因**: API 请求太快  
**解决**: 引擎自动等待 Retry-After，支持断点续传

### 3. 翻译质量差

**原因**: 模型不够强或 prompt 不当  
**解决**: 
- 使用 `step-2-16k` 模型
- 检查专业名词保留（Agent, OpenClaw 等）
- 检查人名保留（Andrej Karpathy, No Priors）

### 4. 音频时长不对

**原因**: TTS 生成不完整  
**解决**: 
```bash
python check_quality.py output/pipeline_xxx/
# 然后重新生成 TTS
python regenerate_tts.py
```

## 📝 更新日志

### v2.1 (2025-03-23) - 流水线重构
- ✅ 流水线改为 6 阶段（新增 QA 重组阶段）
- ✅ TTS 统一使用增强版（支持断点续传）
- ✅ 删除 TTS 基础版和 rate_limiter 模块
- ✅ 项目结构精简

### v2.0 (2025-03-23)
- ✅ 新增 QA 重组器，支持开场/过渡/结尾
- ✅ 新增质量检查模块
- ✅ 新增 TTS 增强版，支持断点续传
- ✅ 翻译 prompt 优化，保留专业名词
- ✅ 改为单声道输出
- ✅ 新增分阶段执行脚本

### v1.0 (2025-03-22)
- ✅ 基础流水线
- ✅ YouTube 下载
- ✅ ASR 识别
- ✅ 翻译 + TTS

## 🎯 路线图

- [ ] 支持更多 TTS 提供商
- [ ] 视频字幕生成
- [ ] Web UI 界面
- [ ] 批量处理多个视频
- [ ] 自动上传到播客平台

## 📄 License

MIT
