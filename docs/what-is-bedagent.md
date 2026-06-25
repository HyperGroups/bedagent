# bedagent 是什么

一句话：

> bedagent 是一个面向“床上思想者”的 Agent 控制系统。

它不是单个 Agent，也不是通用 Agent 框架。它是一套把想法变成安全行动的 **控制层 + 协议 + 角色系统**。

## 更准确的定义

bedagent 接收人的碎片想法，经过最智者判断、剪枝、推演、风险闸门和沙盒执行，再把结果用短反馈交还给人。

```text
Human Thought
→ bedagent Control Layer
→ Agent Runtime / Sandbox / Tools
→ Short Report / Memory
```

## 它是 Agent 吗？

不是一个单独 Agent。

bedagent 更像一个“上层控制系统”，内部可以调度多个角色：

| 角色 | 名字 | 是否执行 |
|------|------|----------|
| 懒人哲学 | Book of Sloth | 否，定义原则 |
| 最智者 | Sage | 否，负责判断 |
| 捕获器 | Nest / Scribe | 否，记录和整理想法 |
| 剪枝器 | Prune | 否，保护主线 |
| 推演器 | Dream | 否，脑内沙盒 |
| 风险闸门 | Blanket | 否，决定能否动手 |
| 执行者 | Hands | 是，在沙盒里执行 |
| 汇报者 | Pillow Note | 否，短反馈 |
| 记忆层 | Bedside Journal | 否，沉淀偏好和反思 |

其中只有 **Hands** 是执行 Agent。Sage 不是执行者，不能直接改真实世界。

## 它是 Agent 集群吗？

可以是，但不是起点。

bedagent 有三种形态：

### 1. 文档协议形态

最小形态：

- `Book of Sloth`：懒人原则；
- `sage` 输出协议；
- `action manifest`；
- `blanket` 风险闸门；
- `pillow_note` 短汇报。

这一阶段甚至不需要新 runtime，只要让现有 Agent 遵守协议。

### 2. 本地控制层形态

中间形态：

- 监听文本/语音输入；
- 生成 `sage` 判断；
- 生成 action manifest；
- 调用 git worktree / sandbox；
- 输出短汇报和日志。

这时 bedagent 是一个本地 controller。

### 3. Agent 集群形态

完整形态：

- Sage Agent；
- Scribe Agent；
- Critic / Arbiter Agent；
- Hands Agent；
- Audit Agent；
- Voice Adapter；
- Sandbox Adapter。

这时 bedagent 可以表现为一个 Agent 集群，但它仍然不是“又一个通用 Agent 框架”。它只服务一个目标：

> 让思想者用最少操作安全地驱动 Agent。

## 系统边界

bedagent 自己负责：

- 捕获想法；
- 剪枝；
- 推演；
- 风险判断；
- 执行前确认；
- 沙盒调度；
- 短汇报；
- 记忆和审计协议。

bedagent 不直接负责：

- 训练模型；
- 替代 Claude/Codex/OpenClaw/LangGraph；
- 提供通用 workflow engine；
- 自己实现所有 STT/TTS；
- 绕过人类确认。

## 与其他东西的关系

| 外部系统 | bedagent 怎么用 |
|----------|----------------|
| Claude Code / Codex / OpenClaw | 作为下游执行 Agent/runtime |
| LangGraph / CrewAI / AutoGen | 作为可选编排 runtime |
| Pipecat / Kiwi Voice / TEN | 作为语音 adapter |
| E2B / Daytona / Vercel Sandbox / worktree | 作为执行沙盒 |
| NeMo / Guardrails AI / LLM Guard | 作为 Gate 参考或可选 validator |
| sofagent | 作为纪律层和历史参考 |

## 不是做什么，而是谁说了算

bedagent 的关键不是“能调用多少工具”，而是控制权结构：

```text
人类思想者：负责价值和最终确认
Sage：负责判断和剪枝
Blanket：负责风险闸门
Hands：负责沙盒执行
Audit/Journal：负责证据和记忆
```

如果一个系统只有执行 Agent，没有 Sage 和 Gate，它不是 bedagent。

如果一个系统只有语音聊天，没有沙盒和审计，它也不是 bedagent。

## 最小 MVP

最小可用的 bedagent 应该是：

```text
输入一个想法
→ Sage 复述和剪枝
→ 生成一个可执行计划
→ Blanket 判断风险
→ Hands 在 worktree 执行
→ Pillow Note 一句话汇报
```

所以 bedagent 的 MVP 不是“语音助手”，也不是“Agent 集群”，而是：

> 想法到安全行动的最小闭环。
