# 项目更新记录

## 2025-03-23 - 流水线重构

### 1. 流水线架构更新 (`src/pipeline.py`)

**变更**: 从 5 阶段改为 6 阶段流水线

```
旧: Download → ASR → Translate → TTS → Quality Check
新: Download → ASR → Translate → QA Reorganize → TTS → Quality Check
```

**改进**:
- ✅ 新增 QA 重组阶段（不再跳过）
- ✅ TTS 阶段使用 `synthesize_qa_pairs` 替代 `mix_mono`
- ✅ 支持断点续传（自动保存/恢复进度）

---

### 2. TTS 引擎统一 (`src/tts_engine.py`)

**变更**: 删除基础版，统一使用增强版

```bash
# 删除的文件
src/tts_engine.py (基础版) → 删除
src/tts_engine_v2.py → 重命名为 tts_engine.py
src/rate_limiter.py → 删除（增强版内置）
```

**增强版功能**（现在是默认）:
- 自动重试（400/429/超时）
- 断点续传
- 文本自动切分
- 详细进度日志

---

### 3. 项目结构精简

**删除的文件**:
- `src/stage1_translate_qa.py` 等旧版本脚本
- `src/utils/` 空目录
- `tests/` 测试目录
- `rate_limiter.py`（功能已合并）
- 各种临时报告文件

---

## 2025-03-23 重大更新

### 1. 翻译模块优化 (`src/translator.py`)

**问题**: 
- 专业名词被错误翻译 (Agent → 代理)
- 人名被音译 (Andrej Karpathy → Andre Kpofi)
- 翻译腔太重

**修复**:
```python
# 新增规则
1. 专业名词保留英文：Agent, OpenClaw, AI, LLM, GPT, API...
2. 人名保留原文：Andrej Karpathy, No Priors
3. 禁止的错误翻译：Kpofi, Noprier, Dobe, Aquint
4. 口语化表达："这非常有压力" → "这压力挺大的"
```

**模型升级**:
- `step-1-8k` → `step-2-16k` (更强的翻译能力)

---

### 2. QA 重组器重构 (`src/qa_reorganizer.py`)

**问题**:
- 对话没有结构，听众迷失
- 段落过长 (>200 字符)
- 没有开场和结尾

**新增功能**:
- ✅ 自动段落切分 (最大 150 字符)
- ✅ 开场包装：节目介绍 + 嘉宾介绍
- ✅ 过渡段落：每 5 个 QA 插入过渡语
- ✅ 结尾包装：感谢语 + 结束语

**示例**:
```
[开场] 欢迎收听 No Priors，我是主持人...
[QA 1] 问题1 → 回答1
[QA 2] 问题2 → 回答2
...
[过渡] 刚才聊了不少技术细节，换个角度聊聊？
[QA 6] 问题6 → 回答6
...
[结尾] 感谢 Andrej 的分享...
```

---

### 3. TTS 引擎增强版 (`src/tts_engine.py`)

**注意**: 现已统一为增强版，作为默认 TTS 引擎

**新增功能**:

| 功能 | 说明 |
|------|------|
| 自动重试 | 400/429/超时 自动重试 3 次 |
| 指数退避 | 429 时等待 Retry-After |
| 文本切分 | 超长文本自动切分 (<400 字符) |
| 断点续传 | 中断后从上次位置继续 |
| 进度保存 | 每 5 个 QA 保存中间文件 |
| 详细日志 | 显示进度和统计 |

---

### 4. 质量检查模块 (`src/quality_checker.py`)

**新增功能**:
- ✅ 翻译质量检查 (错误翻译、翻译腔、长度)
- ✅ QA 完整性检查 (长度、过渡比例、开场/结尾)
- ✅ 音频完整性检查 (时长、声道、文件大小)

**使用**:
```bash
python check_quality.py output/pipeline_xxx/
```

**输出示例**:
```
❌ 未通过 [TRANSLATION]
  - 发现错误翻译: "kpofi" 应为 "Karpathy"
  - 段落过长 (203字符)

❌ 未通过 [AUDIO]
  - 音频时长过短 (2.0分钟)，预期约32.5分钟
```

---

### 5. 音频输出改为单声道

**修改文件**: `src/tts_engine.py`

```python
# 移除立体声分离
# set_channels(2) → set_channels(1)
# pan() → 移除
```

---

### 6. 新增脚本

| 脚本 | 用途 |
|------|------|
| `check_quality.py` | 检查已有文件质量 |
| `regenerate_tts.py` | 重新生成 TTS (断点续传) |
| `run_full_pipeline.py` | 一键执行完整流水线 |
| `run_pipeline_stages.py` | 分阶段执行 |

---

## 已知问题

### 1. TTS 生成时间过长
- 65 对 QA = 130 段音频
- 每段 6 秒间隔 = 13 分钟
- 实际可能 20-30 分钟 (含重试)

**解决**: 使用断点续传，可中断后恢复

### 2. StepFun API 不稳定
- 偶尔 400/429 错误
- 需要重试机制

**解决**: TTS 引擎已内置自动重试机制

### 3. 翻译质量依赖模型
- `step-2-mini` 质量一般
- `step-2-16k` 质量更好但更慢

**建议**: 使用 `step-2-16k`，耐心等待

---

## 当前状态 (v2.1)

- ✅ 流水线：6 阶段完整流程
- ✅ TTS：增强版（自动重试 + 断点续传）
- ✅ 结构：精简后 19 个核心文件
- ✅ 文档：README + UPDATES 已更新

---

## 下一步优化

- [ ] 并行 TTS 生成 (多个 API Key)
- [ ] 本地 TTS 模型 (减少 API 依赖)
- [ ] 音频压缩优化
- [ ] 视频字幕生成
