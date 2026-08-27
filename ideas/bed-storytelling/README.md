# bed-storytelling

status: candidate
design_version: D0.1
main_question: 能否把 bedagent 的口述闭环用于「躺着写小说」？

## 想法

bedagent 的一个妙用：**躺在床上写小说**。

不是一次性生成完整章节，而是 **vibe coding 式口述**：

1. 你躺着，把故事片段讲出来（将来接 Voice，现在先用文本模拟口述）；
2. Sage 听懂主线，追问关键空白；
3. Focus 帮你展开 / 暂存 / 合并 / 剪掉发散分支；
4. Agent 用短反馈跟你对齐，故事 bible 持续变完整；
5. Memory 保留每次口述回合，随时 `recap` 回顾。

这和写代码的 vibe coding 同构：

| vibe coding | bed storytelling |
|-------------|------------------|
| 口述需求 / 改法 | 口述情节 / 人物 / 设定 |
| Agent 追问边界 | Sage 追问动机、时间线、冲突 |
| 小步迭代 | 一段一段把故事讲全 |
| 沙盒试跑 | 章节草稿 / 大纲分支（未来） |
| 短报告 | pillow recap：主线 + 待对齐问题 |

## MVP 入口

```bash
# 交互口述（多行，空行发送）
python3 mvp/bedagent_mvp.py story tell --title "会做梦的维修AI"

# 恢复已有 session
python3 mvp/bedagent_mvp.py story tell --story-id <session-id>

# 先用 seed 文件开讲，再进入交互
python3 mvp/bedagent_mvp.py story tell \
  --title "会做梦的维修AI" \
  --seed-file mvp/sample_story_seed.txt

# 单段口述（脚本 / 测试友好）
python3 mvp/bedagent_mvp.py story once \
  --title "会做梦的维修AI" \
  --fragment-file mvp/sample_story_seed.txt \
  --auto-confirm

# 回答 Sage 追问（对齐）
python3 mvp/bedagent_mvp.py story answer \
  --story-id <session-id> \
  --answer-file mvp/sample_story_answer.txt

# 恢复最近一次会话
python3 mvp/bedagent_mvp.py story resume
python3 mvp/bedagent_mvp.py story tell --resume

# 章节扩写（Draft Sandbox）
python3 mvp/bedagent_mvp.py story draft --story-id <session-id> --expand

# 导出 markdown 大纲 + 对话 transcript
python3 mvp/bedagent_mvp.py story export --story-id <session-id>

# 列出所有 story session
python3 mvp/bedagent_mvp.py story list
```

交互模式命令（`story tell` 内）：

| 命令 | 作用 |
|------|------|
| `/answer` | 回复 Sage 待对齐问题 |
| `/draft` | 生成章节草图 + 大纲 |
| `/export` | 导出 markdown |
| `/questions` | 查看待对齐问题 |
| `/recap` | 床边回顾 |

产物目录：`.bedagent/stories/<session-id>/`

- `bible.json` — 主线、人物、线索、时间线、开放/已对齐问题
- `fragments.ndjson` — 原始口述
- `turns.ndjson` — 每轮 Sage/Focus/Blanket/Agent 对话
- `drafts/` — 章节草图、大纲、pillow 短摘要
- `exports/` — 导出的 story-bible.md、transcript.md

大改确认策略：`mvp/story_blanket_policy.json`（主线 pivot、删角色、重写等）

## 为什么值得想

- 比「改代码」更贴近 bedagent 原始用户画像：没有手脚、一直在想的**思想者**；
- 输入天然是碎片，正好复用 Capture → Sage → Focus 控制层；
- vibe coding 已验证「口述 + 来回对齐」有效，故事创作是同构场景；
- 未来 Voice 适配器可直接替换文本输入，无需改控制层。

## 为什么暂时不进主线

当前 product milestone 仍是工程闭环 MVP（v0.12）。
story 模式作为 **平行情景适配器** 验证控制层可迁移性，不替代 sandbox-first 主线。

## 进入主线的条件

- 有真实口述 / 语音会话案例（至少 3 次完整回合）；
- bible schema 稳定，能导出章节或大纲；
- 与 Voice-first 路线对齐或有明确 ADR；
- 能说明比「直接用 ChatGPT 写小说」多出的控制价值（Focus 剪枝、Blanket 大改确认、Memory 审计）。

## 下一步

1. ~~Voice 适配器：把 `--fragment` 换成语音转写流~~ ✅ DashScope ASR/TTS + `story voice`
2. ~~章节 Act 沙盒：把 `expand` 线索落成 `drafts/chapter-N.md`~~ ✅ `story draft`
3. ~~Blanket 策略：删人设 / 改主线等「红色」改动必须确认~~ ✅ `story_blanket_policy.json`
4. embedding 检索：跨故事会话找相似伏笔。 ✅ `story search`（TF-IDF，v0.9）
5. LLM 适配器：可选接入模型增强 Sage 追问与章节扩写（保持控制层不变）。 ✅ `--use-llm` / DashScope Qwen（v0.9 追问，v0.10 `story draft --expand`）
6. 会话恢复与记忆合流：`story resume`、口述写入 journal、`search` 统一检索。 ✅ v0.10
7. 夜间短反馈：quiet TTS + night pillow。 ✅ v0.10
8. 语音分轮与本地回退：VAD、句子 TTS、Whisper/Piper auto fallback。 ✅ v0.12
