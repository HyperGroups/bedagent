# bedagent 研究地图

bedagent 不是从零发明一个孤岛，而是把几个成熟方向重新组合到一个新用户画像上：

> 一个没有手脚、懒到极致、躺在床上的思想者。

这张地图回答三个问题：

1. 相关领域已经有什么；
2. 它们解决了 bedagent 链路里的哪一段；
3. bedagent 应该如何吸收，而不是盲目照搬。

## 总览

```text
Thought Capture  →  Agent Brain  →  Gate  →  Hands Sandbox  →  Memory/Audit
       ↑                ↑             ↑             ↑                ↑
   PKM / Notes      ReAct/ToT      Guardrails     E2B/Daytona       Langfuse
   Voice Memo       Reflexion      Policy Rails   Vercel Sandbox    task logs
   Ambient Memory   Plan-Execute   HITL           worktree          bedagent-audit
       ↑
   Voice / Hands-free
   Talon / Serenade / Pipecat / Kiwi Voice
```

## 研究地图表

| 方向 | 代表工作 | 已解决什么 | bedagent 吸收方式 | 缺口 |
|------|----------|------------|-------------------|------|
| 语音助手 / 实时语音 Agent | [Pipecat](https://github.com/pipecat-ai/pipecat), [TEN Framework](https://github.com/TEN-framework/TEN-framework), [Kiwi Voice](https://github.com/ekleziast/kiwi-voice), OpenAI Realtime | STT/TTS、VAD、barge-in、实时语音链路 | 作为 Voice adapter 候选；bedagent 只定义语音命令契约和风险确认 | 不负责任务审计、执行沙盒、思想整理 |
| 无手操作 / 语音编程 | [Talon Voice](https://talonvoice.com/), [Serenade](https://serenade.ai/), Apple Voice Control, Windows Voice Access | 用语音替代键盘鼠标，帮助没有手的人操作电脑 | 借鉴可定制口令、hands-free accessibility、低屏幕交互 | 仍然是“操作电脑”，不是“减少操作本身” |
| 想法捕获 / 第二大脑 | Notion AI, Obsidian, Mem, Reflect, Logseq, Rewind/Limitless | 捕获、整理、搜索、链接人的想法 | 作为 Mind/Memory 参考：低摩擦捕获、自动归类、长期记忆 | 多数停在笔记，不继续执行和审计 |
| Agent 推理/规划 | ReAct, Plan-and-Execute, Reflexion, Tree of Thoughts, Self-Refine | 让 Agent 在行动前推理、规划、反思、搜索多方案 | 作为 Agent Brain 的推演策略库 | 多数是内部算法，不是面向床上思想者的交互产品 |
| Agent 编排框架 | LangGraph, CrewAI, AutoGen, Semantic Kernel / Microsoft Agent Framework, LangChain, LlamaIndex | 多 Agent、工具调用、handoff、状态图、持久工作流 | 作为下游 runtime 或 adapter；bedagent 不替代它们 | 通常默认用户是开发者，需要管理流程 |
| Guardrails / 约束 | [NeMo Guardrails](https://github.com/NVIDIA/NeMo-Guardrails), [Guardrails AI](https://github.com/guardrails-ai/guardrails), [LLM Guard](https://github.com/protectai/llm-guard), Llama Guard, Rebuff | 输入/输出扫描、对话 rails、结构校验、prompt injection/PII 防护 | 作为 Gate 层参考：rails 分层、validator、policy-before-dispatch | 关注安全合规，不关注懒人低交互体验 |
| 执行沙盒 | [Sandbox Agent](https://github.com/rivet-dev/sandbox-agent), E2B, Daytona, Vercel Sandbox, Docker, devcontainer, git worktree | 隔离运行 Agent，试错、跑命令、生成 diff | 作为 Hands Sandbox：先在隔离环境动手，成功后再合并 | 能防乱改，不能防乱想 |
| 观测/审计 | LangSmith, Langfuse, OpenTelemetry GenAI, git diff audit | trace、调用链、成本、审计证据 | 作为 Memory/Audit：Agent 不能自证清白，必须留证据 | 通常不定义前置产品交互 |
| 被动指令文件 | AGENTS.md, CLAUDE.md, Cursor Rules, SKILL.md | 跨工具项目规则、启动上下文、轻量约束 | 输出 bedagent discipline layer 到多平台规则文件 | 靠 Agent 自觉加载，强约束不足 |

## 与 bedagent 五层能力的对应

| bedagent 模块 | 外部参照 | 吸收方式 |
|---------------|----------|----------|
| Mind 捕获与思考 | Notion/Mem/Reflect/Obsidian、语音备忘录、ambient memory | 低摩擦捕获、自动归类、想法转任务 |
| Voice 低屏幕交互 | Talon、Serenade、Pipecat、TEN、Kiwi Voice | 口令系统、STT/TTS、打断、短反馈 |
| Gate 风险与纪律 | sofagent、NeMo Guardrails、Guardrails AI、LLM Guard、AGENTS.md | 纪律层、rails 分层、validator、approval |
| Hands 执行沙盒 | git worktree、Sandbox Agent、E2B、Daytona、Vercel Sandbox | 隔离执行、dry-run、diff、测试、回滚 |
| Memory/Audit 记忆审计 | Reflexion、LangSmith/Langfuse、git diff audit | 反思沉淀、trace、证据、短汇报 |

## bedagent 的独特切口

其他工作大多在做：

> 更强的 Agent。

bedagent 要做的是：

> 更少操作的人，如何安全地驱动 Agent。

关键差异：

1. 用户画像是“懒到极致的思想者”，不是开发者控制台用户；
2. 入口是想法，不是任务表单；
3. 先有推演沙盒，再有执行沙盒；
4. 短反馈是一等公民；
5. 高风险确认必须存在，但不能把所有步骤都变成人工审批；
6. 参考框架只作为 adapter，不成为产品中心。

## 集成策略

### P0：文档协议层

- 定义 thought capture 格式；
- 定义 action manifest；
- 定义 risk gate；
- 定义 short report；
- 定义 sandbox evidence。

### P1：本地工作流层

- 用 git worktree 做最小执行沙盒；
- 用 Markdown 文件保存 manifest 和 evidence；
- 用系统听写或纯文本模拟 voice input；
- 用 `rg`/diff/audit 做最小验证。

### P2：Adapter 层

- Voice adapter：Pipecat / Kiwi Voice / TEN；
- Runtime adapter：OpenClaw / LangGraph / Claude Code / Codex；
- Sandbox adapter：Sandbox Agent / E2B / Daytona / Vercel Sandbox；
- Rules adapter：AGENTS.md / CLAUDE.md / Cursor Rules。

### P3：产品层

- 床上模式；
- 手机/床边设备遥控器；
- 低屏幕短反馈；
- 长任务等待、暂停、恢复、第二天继续。

## 不照搬什么

- 不照搬 PKM 的复杂知识库结构；
- 不照搬 Agent 框架的开发者控制台；
- 不照搬 Guardrails 的全量安全产品；
- 不照搬 voice coding 的“用嘴替代键盘”；
- 不照搬沙盒平台的基础设施叙事。

bedagent 只吸收能服务这个人的东西：

> 我躺着想，Agent 起来干。
