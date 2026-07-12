# voice-first

status: candidate
design_version: D0.1
main_question: 是否先从低屏幕语音入口做 MVP？

## 想法

bedagent 的 Voice 层现已接入 **阿里云 DashScope 百炼**：

- **ASR**：`fun-asr-realtime`（本地音频文件转写）
- **TTS**：`cosyvoice-v3-flash`（短反馈播报，默认音色 `longxiaochun`）

与 story 口述模式组合：**躺着说话 → 转写 → Sage/Focus → TTS 短回复**。

## MVP 入口

安装可选依赖：

```bash
pip install -r mvp/requirements-voice.txt
export DASHSCOPE_API_KEY="sk-..."
# 可选：业务空间专属域名
export DASHSCOPE_WORKSPACE_ID="ws-..."
```

独立语音命令：

```bash
python3 mvp/bedagent_mvp.py voice transcribe --audio-file input.wav
python3 mvp/bedagent_mvp.py voice speak --text "收到，继续讲。" --output reply.wav
```

Story 语音口述：

```bash
# 单轮：音频 → 转写 → 故事 bible → TTS
python3 mvp/bedagent_mvp.py story voice-once \
  --title "会做梦的维修AI" \
  --audio-file input.wav \
  --auto-confirm

# 交互语音循环（音频路径 / mic / /text fallback）
python3 mvp/bedagent_mvp.py story voice \
  --title "会做梦的维修AI" \
  --mic \
  --play-reply
```

配置：`mvp/voice_config.json`（模型、音色、录音时长、敏感词 TTS 屏蔽）

## 设计对齐

| voice-control 原则 | 实现 |
|--------------------|------|
| 短反馈 | `build_tts_summary()` 截断到 ~220 字 |
| 不读秘密 | `secret_block_keywords` 触发替换播报 |
| 可打断 | 语音口令映射：暂停/继续/取消/汇报一下 |
| 不猜测 | ASR 空结果直接报错，不写入 bible |

## 为什么暂时不进主线

工程闭环 MVP 仍以 sandbox/worktree 为主；Voice 作为 **可选 adapter**，依赖 DashScope API Key。

## 下一步

1. 双向流式 ASR（麦克风边说边转写）；
2. Qwen 文本模型接入 Sage 追问（仍走 Blanket）；
3. 床边手机/Web 推送音频入口；
4. 离线 fallback（本地 Whisper + Piper）。
