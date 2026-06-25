# Agent 约束/治理框架调研

> 调研时间：2026-06-25。
> 目的：为 bedagent 后续能力规划提供参照。本文不表示要引入这些依赖。

## 结论先行

目前没有一个开源框架能同时覆盖：

- 跨 Agent 平台的常驻纪律；
- 工具调用前的策略拦截；
- 人类审批；
- 任务反思；
- 提交时审计；
- 低屏幕语音控制。

主流生态更像拼图：Agent 框架负责“怎么跑”，Guardrails 负责“输入/输出/对话怎么拦”，Workflow 负责“怎么暂停/恢复”，Observability 负责“怎么看见”。bedagent 的机会是做 **跨平台纪律层 + 审计层 + 轻量协议**，而不是再造一个 Agent runtime。

## 分类对照

| 类型 | 代表项目 | 核心能力 | 与 bedagent 的关系 |
|------|----------|----------|--------------------|
| 被动指令层 | AGENTS.md / CLAUDE.md / Cursor Rules / SKILL.md | 仓库或平台级 Markdown 规则，启动时加载 | bedagent 当前最接近这一层，但增加了反思、闭环和安装验证 |
| 对话 Rails | [NVIDIA NeMo Guardrails](https://github.com/NVIDIA/NeMo-Guardrails) | Colang 定义输入/输出/对话/检索/执行 rails | 可借鉴“rails 分类”和可编程策略，但不适合直接绑定 |
| 输出校验 | [Guardrails AI](https://github.com/guardrails-ai/guardrails) | RAIL / validators 校验结构、内容、PII、毒性等 | 可借鉴 validator marketplace 和 re-ask 机制，用于 audit/报告输出 |
| 输入输出扫描 | [LLM Guard](https://github.com/protectai/llm-guard), Llama Guard, Rebuff | PII、prompt injection、毒性、泄密扫描 | 可作为未来 skill-safety-check / task-record 脱敏增强参考 |
| 工作流/HITL | LangGraph | interrupt、checkpoint、human-in-the-loop、durable execution | 可借鉴暂停/恢复/审批状态；必须注意 replay 与幂等风险 |
| 多 Agent 编排 | CrewAI, AutoGen, Semantic Kernel / Microsoft Agent Framework, LangChain, LlamaIndex | 角色、任务图、工具调用、handoff | 这些负责“跑 Agent”，bedagent 应作为外层纪律/审计，不替代它们 |
| 语音 Agent | Pipecat, TEN Framework, Kiwi Voice | STT/TTS、VAD、barge-in、WebRTC/WebSocket、多模态 | 语音控制层可复用它们，bedagent 只定义命令契约和安全策略 |
| 观测/审计 | LangSmith, Langfuse, OpenTelemetry GenAI 语义 | trace、token、调用链、成本 | bedagent-audit 可与这些互补；当前保持 git/file 零依赖路线 |

## 可借鉴的设计模式

### 1. Policy-before-dispatch

很多治理方案的核心形状一致：

```text
Agent 提议动作
→ 生成 action manifest（工具名、参数、影响范围、风险）
→ policy engine 判断 allow / warn / require_approval / block
→ 执行或等待人类
→ 写审计记录
```

bedagent 可以把这个模式落成轻量文件协议：

```yaml
action:
  tool: git_push
  target: origin/main
  risk: red
  reason: publish completed task
  requires_confirmation: true
decision:
  status: require_approval
  approved_by: null
```

早期不用引入策略引擎，先用 Markdown/YAML manifest + bash/TS 审计即可。

### 2. Rails 分层

NeMo Guardrails 的启发是：不要把所有约束写成一坨 prompt。按生命周期分：

| Rails | bedagent 对应 |
|-------|---------------|
| Input rails | task-aware 风险识别、需求澄清 |
| Dialog rails | loop-check 防跑偏、checkpoint |
| Retrieval rails | 先读后写、引用来源检查 |
| Execution rails | 高风险工具调用审批、幂等检查 |
| Output rails | task-closure、最终汇报、bedagent-audit |

bedagent 后续文档应继续按生命周期组织，避免概念堆叠。

### 3. Validator 而不是万能裁判

Guardrails AI 的启发是：确定性校验越小越可信。

适合 bedagent 的 validator：

- JSON/YAML 输出是否可解析；
- 是否包含验收标准；
- 是否列出被修改文件；
- 是否跑过测试；
- 是否把敏感字段写入日志；
- 是否修改了任务无关文件。

不适合早期做的 validator：

- “代码质量好不好”；
- “架构是否优雅”；
- “Agent 是否真的理解用户”。

这些判断太主观，容易让误报率爆炸。

### 4. Human-in-the-loop 必须配幂等

LangGraph interrupt/checkpoint 的启发很重要：暂停/恢复不是免费的。很多工作流在 resume 时会重放节点逻辑，若副作用放在 interrupt 之前，可能重复发邮件、扣款、push。

bedagent 已有幂等检查雏形，语音确认和未来协同层都应遵守：

- 执行前生成 operation id；
- 写入 proposal；
- 用户确认只改变 decision；
- 真正副作用只在 decision=approved 后执行一次；
- 恢复任务前先查 operation id 是否已完成。

### 5. AGENTS.md 作为跨工具出口

AGENTS.md/CLAUDE.md/Cursor Rules 的趋势说明：跨工具 Markdown 指令正在收敛。

bedagent 可以提供：

- `bedagent export agents-md`：生成仓库级 AGENTS.md；
- `bedagent export claude-md`：生成 CLAUDE.md 或 `@AGENTS.md` 引用；
- `bedagent export cursor-rules`：生成 `.cursor/rules/*.mdc`；
- 只导出纪律层核心，不导出平台专属 Hook。

这样 bedagent 不需要控制每个 Agent 平台，也能把纪律层分发出去。

## bedagent 采用策略

### 应该做

1. **保留跨平台 Markdown 核心**：这是 bedagent 的差异化，不被任何框架锁定。
2. **把约束显式分层**：输入、对话、执行、输出、审计。
3. **引入 action manifest**：让高风险动作先变成可审查对象。
4. **把审批做成状态机**：pending / approved / rejected / expired。
5. **把 audit 做成独立层**：不信 Agent 自述，只看 diff、日志、manifest。
6. **对接而非替代框架**：LangGraph/CrewAI/AutoGen 等可以是下游 runtime。

### 暂时不做

1. 不把 bedagent 改成 Python Agent 框架；
2. 不直接依赖 NeMo/Guardrails/LangGraph；
3. 不做大型 Web 控制台；
4. 不做“LLM 评分一切”的万能审查；
5. 不为每个平台维护一套完全不同的规则。

## 候选路线图

| 阶段 | 目标 | 交付物 |
|------|------|--------|
| P0 | 明确协议 | action manifest 草案、risk 分级、approval 状态机文档 |
| P1 | 审计增强 | bedagent-audit 读取 manifest，检查红色动作是否有 approval |
| P2 | 指令导出 | AGENTS.md / CLAUDE.md / Cursor Rules 导出器 |
| P3 | Runtime adapter | 针对 LangGraph / CrewAI / OpenClaw 的 pre-tool-call 适配示例 |
| P4 | 语音控制 | 复用 Pipecat/Kiwi/TEN，把语音输入转成同一套 manifest/approval 流程 |

## 关键风险

- **误报率**：超过 10% 用户就会关闭审计；
- **重复执行副作用**：暂停/恢复必须先解决幂等；
- **平台碎片化**：不要为了每个平台写一套不同宪法；
- **文档过载**：约束越多，Agent 越不遵守；
- **语音误触发**：床上模式必须默认保守。
