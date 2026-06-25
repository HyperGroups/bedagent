# bedagent 词汇表

这是一份给 bedagent 命名用的语义词库。它不是最终命名清单，而是后续给模块、协议、命令、版本代号、文档标题取名时的素材池。

使用原则：

1. 先选语义场，再选词；
2. 用户可见名称要直觉清楚；
3. 协议/文件名要短、稳定、可拼写；
4. 不要为了诗意牺牲功能边界；
5. 懒与智要同时存在。

## 核心推荐词

| 词 | 语义 | 推荐用途 | 备注 |
|----|------|----------|------|
| Sloth | 懒、树懒、慢 | 懒人哲学总纲 | `Book of Sloth` 最推荐 |
| Sage | 智者、贤者 | 最智者角色 | Agent Brain 的最高判断层 |
| Nest | 巢、安放 | 想法捕获 | 接住碎片想法 |
| Dream | 梦、推演 | 推演沙盒 | 在梦里试想，不碰现实 |
| Prune | 修剪、剪枝 | Focus 模式 | 处理无限分支 |
| Fold | 折叠、整理 | 计划生成 | 把散乱想法折成任务 |
| Blanket | 被子、保护 | 风险闸门 | 包住风险，隔离危险 |
| Hands | 手脚、执行 | 执行沙盒 | Agent 作为人的手脚 |
| Pillow Note | 枕边便签 | 短汇报 | 一句话结果 |
| Bedside Journal | 床头日记 | 记忆/反思 | 用户偏好与任务反思 |

## 床与休息语义

| 英文 | 中文感 | 适合用途 | 注意 |
|------|--------|----------|------|
| Bed | 床 | 产品主隐喻、Bed Mode | 直白、稳定 |
| Pillow | 枕头 | 短反馈、轻提示 | 适合温柔、小信息 |
| Blanket | 被子 | 风险保护、权限包裹 | 很适合 Gate |
| Quilt | 被褥 | 保护层、组合策略 | 比 Blanket 更柔和 |
| Sheet | 床单、表单 | 清单、manifest | 容易和 spreadsheet 混淆 |
| Bedside | 床边 | 日志、日记、设备 | `Bedside Journal` 很自然 |
| Nightstand | 床头柜 | 暂存区、工具箱 | 偏物理容器 |
| Cradle | 摇篮 | 捕获、温柔承载 | 可用于早期想法孵化 |
| Nest | 巢 | 捕获、收纳、孵化 | 比 Bed 更主动 |
| Nap | 小睡 | 小版本、小实验 | 适合版本代号 |
| Doze | 打盹 | 暂停、轻量后台 | 口感较轻 |
| Hibernation | 冬眠 | 长期后台、延后执行 | 适合长期任务 |
| Dream | 梦 | 推演、想象、沙盒 | 注意不要误解成幻想产品 |
| Slumber | 睡眠 | 深度后台模式 | 偏文学 |
| Lullaby | 摇篮曲 | TTS、安静提示 | 适合声音，不适合核心逻辑 |

## 懒与省力语义

| 英文 | 中文感 | 适合用途 | 注意 |
|------|--------|----------|------|
| Sloth | 懒、树懒 | 哲学、品牌调性 | 有七宗罪意味，但有辨识度 |
| Lazy | 懒 | 普通描述 | 太直白，不适合主名 |
| Ease | 轻松、省力 | 用户体验原则 | 正面、优雅 |
| Idleness | 闲散、无事 | 哲学文档 | 偏文学 |
| Leisure | 闲暇 | 用户状态 | 太生活方式 |
| Effortless | 不费力 | 体验目标 | 适合 slogan |
| Frictionless | 无摩擦 | 交互原则 | 偏产品术语 |
| Minimal | 最少 | 设计原则 | 稳定但泛化 |
| Inertia | 惯性 | 不想动 | 负面/物理感强 |
| Wu Wei | 无为 | 哲学 | 英文用户理解门槛高 |

推荐：

- 哲学书：`Book of Sloth`
- 体验原则：`Effortless`, `Frictionless`, `Ease`
- 避免主品牌：`LazyAgent`, `LazyOS`

## 智慧与判断语义

| 英文 | 中文感 | 适合用途 | 注意 |
|------|--------|----------|------|
| Sage | 智者、贤者 | 最智者 | 最推荐 |
| Oracle | 神谕 | 预测/问答 | 容易显得神秘和绝对 |
| Mentor | 导师 | 教练式建议 | 太像教育产品 |
| Counsel | 谘询、劝告 | 建议/取舍 | 可作为动词 |
| Judge | 法官 | 审查/裁决 | 太硬，适合审计 |
| Arbiter | 仲裁者 | 多 Agent 冲突裁定 | 适合冲突解决 |
| Curator | 策展人 | 筛选、整理 | 适合知识/想法筛选 |
| Editor | 编辑 | 压缩、改写 | 适合短汇报 |
| Critic | 批评者 | 反驳、审查 | 适合反方角色 |
| Watcher | 观察者 | 监控 | 可用于 audit |

推荐：

- 最高判断：`Sage`
- 冲突裁定：`Arbiter`
- 反驳检查：`Critic`
- 证据审计：`Night Watch` / `Watcher`

## 思考与推演语义

| 英文 | 中文感 | 适合用途 | 注意 |
|------|--------|----------|------|
| Thought | 想法 | 通用字段 | 太泛 |
| Mind | 心智 | 模块总称 | 可用于 Mind layer |
| Brain | 大脑 | Agent Brain | 直观 |
| Dream | 梦 | 推演沙盒 | 与床主题强相关 |
| Reverie | 白日梦 | 发散想象 | 偏文学 |
| Muse | 灵感 | 创意捕获 | 可能太拟人 |
| Reflect | 反思 | 复盘 | 已有产品名，但语义清晰 |
| Deliberate | 深思熟虑 | 高风险判断 | 适合作动词 |
| Simulate | 模拟 | 推演 | 技术感强 |
| Scenario | 场景 | 多方案推演 | 稳定 |
| Branch | 分支 | 想法分叉 | 可用于内部字段 |

推荐：

- 推演沙盒：`Dream`
- 深度判断：`Deliberation`
- 分支结构：`branch`, `scenario`

## 捕获与暂存语义

| 英文 | 中文感 | 适合用途 | 注意 |
|------|--------|----------|------|
| Capture | 捕获 | 通用动作 | 稳定 |
| Nest | 巢 | 想法捕获 | 最推荐 |
| Inbox | 收件箱 | 待整理想法 | 常见 |
| Pocket | 口袋 | 暂存 | 与 Pocket 产品重名但通用 |
| Stash | 藏起来 | 暂存 | 稍随意 |
| Park | 停放 | 以后再说 | 适合 `park` 字段 |
| Hold | 保留 | 暂停/保留 | 通用 |
| Pin | 固定 | 重要想法 | 常见 |
| Seed | 种子 | 初始想法 | 适合孵化 |
| Spark | 火花 | 灵感 | 偏创意 |

推荐：

- 捕获模块：`Nest`
- 暂存字段：`park`
- 初始想法：`seed` / `spark`

## 剪枝与专注语义

| 英文 | 中文感 | 适合用途 | 注意 |
|------|--------|----------|------|
| Prune | 剪枝 | Focus 核心动作 | 最推荐 |
| Focus | 专注 | 通用模式 | 稳定 |
| Trim | 修剪 | 轻量删除 | 偏文本 |
| Cull | 淘汰 | 强剪枝 | 语气较硬 |
| Filter | 过滤 | 规则筛选 | 技术感 |
| Merge | 合并 | 重复主题合并 | 稳定 |
| Park | 暂存 | 有价值但以后再说 | 与捕获语义共用 |
| Drop | 丢弃 | 剪掉 | 直白 |
| Narrow | 收窄 | 减少范围 | 适合澄清 |
| Thread | 主线 | 当前主题线索 | 推荐 |

推荐四动作：

```yaml
keep: 展开
park: 暂存
merge: 合并
prune: 剪掉
```

## 保护与闸门语义

| 英文 | 中文感 | 适合用途 | 注意 |
|------|--------|----------|------|
| Gate | 闸门 | 通用风险控制 | 稳定但普通 |
| Guard | 守卫 | 安全角色 | 常见 |
| Blanket | 被子 | 风险保护 | 最有 bedagent 特色 |
| Shield | 盾 | 安全防护 | 偏安全产品 |
| Rail | 护栏 | Guardrails 对齐 | 适合框架对照 |
| Brake | 刹车 | 停止危险动作 | 很直观 |
| Lock | 锁 | 权限控制 | 偏硬 |
| Safe | 保险箱 | 沙盒/隔离 | 泛化 |
| Boundary | 边界 | 规则边界 | 适合文档 |
| Consent | 同意 | 人类确认 | 适合 approval |

推荐：

- 产品命名：`Blanket`
- 协议概念：`gate`, `approval`, `consent`
- 危险停止：`brake`

## 执行与手脚语义

| 英文 | 中文感 | 适合用途 | 注意 |
|------|--------|----------|------|
| Hands | 手脚 | 执行沙盒 Agent | 最推荐 |
| Act | 行动 | 通用阶段 | 稳定 |
| Doer | 执行者 | 执行角色 | 稍口语 |
| Runner | 运行者 | 任务执行 | 技术常见 |
| Worker | 工人 | 多 Agent 执行 | 常见 |
| Butler | 管家 | 助理 | 不推荐，偏传统助理 |
| Fetch | 去取 | 简单执行 | 适合小动作 |
| Carry | 搬运 | 执行/转移 | 偏物理 |
| Apply | 应用 | 应用变更 | 技术稳定 |
| Commit | 提交 | git 语义 | 仅用于 git |

推荐：

- 执行沙盒：`Hands`
- 执行动作：`act`, `apply`
- 多执行者：`workers`

## 沙盒与隔离语义

| 英文 | 中文感 | 适合用途 | 注意 |
|------|--------|----------|------|
| Sandbox | 沙盒 | 通用隔离 | 稳定 |
| Worktree | Git 工作树 | 代码执行沙盒 | 技术准确 |
| Dream | 梦 | 推演沙盒 | 用于脑内沙盒 |
| Trial | 试验 | 尝试 | 稳定 |
| Rehearsal | 彩排 | 执行前演练 | 很适合 dry-run |
| Playground | 游乐场 | 实验 | 稍轻浮 |
| Lab | 实验室 | 研究/试验 | 泛用 |
| Chamber | 房间 | 隔离空间 | 偏硬 |
| Preview | 预览 | 部署/产品 | 技术常见 |
| Dry Run | 空跑 | 不产生副作用 | 稳定 |

推荐：

- 思考沙盒：`Dream`
- 执行沙盒：`Hands Sandbox`
- 预演：`Rehearsal`

## 语音与低屏幕语义

| 英文 | 中文感 | 适合用途 | 注意 |
|------|--------|----------|------|
| Whisper | 低声说 | 语音交互 | 最推荐 |
| Voice | 语音 | 通用 | 稳定 |
| Murmur | 低语 | 轻声输入 | 偏文学 |
| Dictate | 听写 | 输入 | 太工具化 |
| Listen | 倾听 | STT | 稳定 |
| Speak | 朗读 | TTS | 稳定 |
| Barge-in | 打断 | 语音打断 | 技术术语 |
| Wake Word | 唤醒词 | 语音入口 | 技术术语 |
| Push-to-talk | 按住说 | MVP 入口 | 技术术语 |
| Quiet Mode | 安静模式 | 夜间不打扰 | 推荐 |

推荐：

- 语音模块：`Whisper`
- 夜间：`Quiet Mode`
- 打断：`barge_in`

## 汇报与反馈语义

| 英文 | 中文感 | 适合用途 | 注意 |
|------|--------|----------|------|
| Pillow Note | 枕边便签 | 短汇报 | 最推荐 |
| Note | 便签 | 通用 | 稳定 |
| Brief | 简报 | 摘要 | 很适合短汇报 |
| Summary | 总结 | 通用 | 稳定 |
| Digest | 摘要合集 | 日报/周报 | 适合批量 |
| One-liner | 一句话 | 字段名 | 稳定 |
| Whisper Back | 低声回复 | 语音短反馈 | 可用于 TTS |
| Receipt | 回执 | 执行证据 | 适合审计 |
| Evidence | 证据 | 验证材料 | 稳定 |
| Signal | 信号 | 状态提示 | 泛化 |

推荐：

- 短汇报：`Pillow Note`
- 证据回执：`receipt`
- 日报：`digest`

## 记忆与反思语义

| 英文 | 中文感 | 适合用途 | 注意 |
|------|--------|----------|------|
| Journal | 日记 | 反思记忆 | 稳定 |
| Bedside Journal | 床头日记 | bedagent 记忆 | 最推荐 |
| Memory | 记忆 | 通用 | 稳定 |
| Reflection | 反思 | 失败复盘 | 稳定 |
| Trace | 轨迹 | 调用链 | 技术感 |
| Log | 日志 | 执行记录 | 稳定 |
| Chronicle | 编年史 | 长期历史 | 偏文学 |
| Ledger | 账本 | 审计记录 | 稳重 |
| Diary | 日记 | 个人化 | 比 Journal 更私密 |
| Recall | 回忆 | 检索记忆 | 有产品名冲突 |

推荐：

- 用户记忆：`Bedside Journal`
- 审计记录：`Ledger`
- 调用链：`trace`

## 风险词汇

| 英文 | 用途 |
|------|------|
| green | 自动推进 |
| yellow | 复述后确认 |
| red | 二次确认/屏幕确认 |
| blocked | 阻塞 |
| waiting | 等用户 |
| parked | 暂存 |
| pruned | 剪掉 |
| approved | 已批准 |
| rejected | 已拒绝 |
| expired | 确认过期 |

## 命名避坑

| 避免 | 原因 |
|------|------|
| LazyAgent | 太直白，像玩笑，不像哲学 |
| SleepAgent | 容易误解成睡眠健康 |
| DreamAgent | 只覆盖推演，不覆盖执行 |
| Butler | 像传统助理，不像外骨骼 |
| Copilot | 已被占用，且隐喻偏驾驶 |
| Autopilot | 容易暗示无需确认，违背高风险闸门 |
| Oracle | 过于神谕，容易暗示绝对正确 |
| God Mode | 风险太高，违背 bedagent 气质 |

## 推荐词组

| 中文 | 英文 |
|------|------|
| 懒人之书 | Book of Sloth |
| 最智者协议 | Sage Protocol |
| 床上模式 | Bed Mode |
| 枕边短报 | Pillow Note |
| 床头日记 | Bedside Journal |
| 盖被子检查 | Blanket Check |
| 梦中推演 | Dream Rehearsal |
| 手脚沙盒 | Hands Sandbox |
| 低语输入 | Whisper Input |
| 主线剪枝 | Thread Pruning |

## 当前推荐套装

如果只选一套，使用：

```text
Book of Sloth
Sage
Nest
Prune
Dream
Fold
Blanket
Hands
Pillow Note
Bedside Journal
```

这套命名同时覆盖：

- 懒；
- 床；
- 思考；
- 剪枝；
- 沙盒；
- 保护；
- 汇报；
- 记忆。
