# bedagent 命名系统

> 词汇素材库见 [vocabulary.md](vocabulary.md)。本文负责确定命名规则和推荐套装，词汇表负责收集相近语义候选词。

bedagent 的命名应该同时表达三件事：

1. **床**：低屏幕、休息姿态、躺着想；
2. **懒**：少操作、少废话、少分叉；
3. **智**：最智者负责判断、剪枝、取舍。

命名目标不是可爱，而是让每个名字都提醒产品边界。

## 总体风格

| 原则 | 说明 |
|------|------|
| 短 | 模块名尽量 1-2 个词 |
| 有隐喻 | 但不能难懂 |
| 能落到功能 | 不为了诗意牺牲可理解性 |
| 懒与智并存 | 不只 lazy，也要 sage |

推荐组合：

```text
Book of Sloth   懒人哲学
Sage            最智者
Nest            思想捕获与暂存
Dream           推演沙盒
Blanket         风险保护
Hands           执行沙盒
Whisper         语音交互
Pillow Note     短反馈/床头便签
```

## 最高概念

| 中文 | 英文 | 说明 |
|------|------|------|
| 懒人之书 | **Book of Sloth** | bedagent 的懒人哲学总纲 |
| 最智者 | **Sage** | Agent Brain 的最高判断层 |
| 床上模式 | **Bed Mode** | 低屏幕/低操作模式 |
| 思想者 | **Sleeper-Thinker** | 目标用户画像 |
| 思想者外骨骼 | **Thought Exoskeleton** | bedagent 的产品隐喻 |

`Book of Sloth` 是哲学书，不是功能模块；`Sage` 是角色，不是执行器。

## 核心链路命名

| 阶段 | 推荐名 | 作用 |
|------|--------|------|
| Capture | **Nest** | 接住想法，先放进巢里 |
| Sage | **Sage** | 最智者判断主线和价值 |
| Focus | **Prune** | 剪枝：展开、暂存、合并、剪掉 |
| Think | **Dream** | 推演沙盒，在梦里试想 |
| Plan | **Fold** | 把散乱想法折叠成计划 |
| Gate | **Blanket** | 给人盖被子：保护、隔离风险 |
| Act | **Hands** | Agent 手脚，在沙盒里执行 |
| Report | **Pillow Note** | 枕边短报，只讲重点 |
| Memory | **Bedside Journal** | 床头日记，沉淀偏好和反思 |

完整链路：

```text
Nest → Sage → Prune → Dream → Fold → Blanket → Hands → Pillow Note → Bedside Journal
```

对应现有通用名：

```text
Capture → Sage → Focus → Think → Plan → Gate → Act → Report → Memory
```

## 角色命名

| 角色 | 英文名 | 职责 |
|------|--------|------|
| 思想者 | Sleeper-Thinker | 人类用户 |
| 最智者 | Sage | 判断、剪枝、取舍 |
| 记录员 | Scribe | 捕获想法、整理片段 |
| 守门员 | Blanket Guard | 风险闸门 |
| 手脚 | Hands | 执行沙盒里的 Agent |
| 审计员 | Night Watch | 看日志、看证据、看有没有乱来 |

建议规则：

- 用户-facing 可以用中文：“最智者”“枕边短报”；
- 协议/文件名用英文：`sage`, `pillow_note`, `bedside_journal`；
- 执行 Agent 不叫 Sage，避免把判断者和执行者混淆。

## 协议字段命名

### Sage 输出

```yaml
sage:
  restatement: "用户真正想解决的问题"
  main_thread: "当前主线"
  keep:
    - "值得展开的分支"
  park:
    - "以后再说"
  prune:
    - "剪掉的分支"
  questions:
    - "最多三个关键问题"
  recommendation: "下一步建议"
  risk: "green | yellow | red"
```

### Pillow Note 短报

```yaml
pillow_note:
  status: "done | waiting | blocked | failed"
  one_liner: "一句话结论"
  needs_user: true
  next_word: "确认 / 暂停 / 明天再说"
```

### Blanket 风险闸门

```yaml
blanket:
  risk: "green | yellow | red"
  reason: "为什么是这个风险"
  confirmation_required: true
  forbidden_without_screen: true
```

## 命令命名

语音口令保持中文自然语言，内部命令保持短英文。

| 口令 | 内部命令 | 说明 |
|------|----------|------|
| 记一下 | `nest` | 捕获，不执行 |
| 帮我想想 | `dream` | 进入推演 |
| 剪一下 | `prune` | 只做聚焦剪枝 |
| 找最智者 | `sage` | 让 Sage 给判断 |
| 整理成任务 | `fold` | 形成计划 |
| 盖上被子 | `blanket` | 风险检查 |
| 可以动手 | `hands` | 进入执行沙盒 |
| 枕边汇报 | `pillow` | 短报告 |
| 明天再说 | `sleep` | 暂存，不展开 |

## 文件/目录建议

未来 active implementation 可以采用：

```text
bedagent/
├── book-of-sloth.md
├── sage.md
├── protocols/
│   ├── sage.yaml
│   ├── blanket.yaml
│   └── pillow-note.yaml
├── modes/
│   ├── bed-mode.md
│   ├── dream-mode.md
│   └── hands-mode.md
└── journal/
    └── bedside-journal.md
```

当前仓库仍处于设计阶段，先不急着创建实现目录。

## 版本代号

| 代号 | 用途 |
|------|------|
| Nap | 小修、小实验 |
| Blanket | 风险闸门版本 |
| Dream | 推演沙盒版本 |
| Sage | 最智者版本 |
| Nest | 想法捕获版本 |
| Pillow | 短反馈版本 |
| Hibernation | 长期后台/多设备版本 |

## 避免的名字

| 名字 | 原因 |
|------|------|
| LazyAgent | 太直白，缺少哲学感 |
| SleepAgent | 容易误解成睡眠健康 |
| DreamAgent | 只覆盖推演，不覆盖执行 |
| Butler | 太像传统助理，不够“思想者外骨骼” |
| Copilot | 已被占用且隐喻偏驾驶 |

## 推荐主叙事

```text
Book of Sloth 是宪法，
Sage 是大脑，
Blanket 是闸门，
Hands 是手脚，
Pillow Note 是汇报。
```

一句话：

> 懒有书，事有智者，动手有沙盒。
