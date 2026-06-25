# Agent 约束/治理框架调研

> 更完整的相关工作全景见 [research-map.md](research-map.md)。本文只聚焦 Gate / 约束 / 审计这一块。

## 结论

目前没有一个开源框架同时覆盖：

- 跨平台 Agent 纪律；
- 思想捕获；
- 推演沙盒；
- 工具调用前审批；
- 执行沙盒；
- 提交时审计；
- 低屏幕语音控制。

主流生态更像拼图。bedagent 不应该变成另一个 Agent runtime，而应该做：

> 跨平台纪律层 + 推演/执行沙盒协议 + 审计层 + 低屏幕交互层。

## 分类

| 类型 | 代表项目 | 可借鉴点 |
|------|----------|----------|
| 被动指令层 | AGENTS.md / CLAUDE.md / Cursor Rules / SKILL.md | 跨工具 Markdown 指令 |
| 对话 Rails | NeMo Guardrails | input/dialog/retrieval/execution/output rails 分层 |
| 输出校验 | Guardrails AI | validators、结构化输出校验、re-ask |
| 输入输出扫描 | LLM Guard / Llama Guard / Rebuff | PII、prompt injection、泄密扫描 |
| 工作流/HITL | LangGraph | interrupt、checkpoint、人类审批、持久状态 |
| 多 Agent 编排 | CrewAI / AutoGen / Semantic Kernel / LangChain | 角色、任务图、handoff、工具调用 |
| 语音 Agent | Pipecat / TEN / Kiwi Voice | STT/TTS、VAD、barge-in、实时语音 |
| 观测审计 | LangSmith / Langfuse / OpenTelemetry | trace、调用链、成本、审计 |

## bedagent 应该吸收什么

### 1. Policy-before-dispatch

```text
Agent 提议动作
→ action manifest
→ policy 判断 allow / warn / require_approval / block
→ 执行或等待人类
→ 写审计记录
```

### 2. Rails 分层

| Rails | bedagent 对应 |
|-------|---------------|
| Input | 想法捕获、风险识别、需求澄清 |
| Dialog | 推演沙盒、反问、checkpoint |
| Retrieval | 先读后写、引用来源 |
| Execution | 执行沙盒、高风险审批、幂等 |
| Output | 短汇报、审计、反思 |

### 3. Validator 小而可信

适合做：

- 输出是否可解析；
- 是否列出风险；
- 是否有验收标准；
- 是否跑过测试；
- 是否有 approval；
- 是否修改了任务无关文件。

不适合早期做：

- “架构是否优雅”；
- “代码质量是否优秀”；
- “Agent 是否真的理解用户”。

### 4. HITL 必须配幂等

暂停/恢复可能重放节点。bedagent 必须：

- 先生成 operation id；
- 副作用只在 approval 后执行；
- 恢复前检查 operation id 是否已完成；
- 不能重复发邮件、付款、push。

## 采用策略

应该做：

1. 保留 Markdown 核心；
2. 定义 action manifest；
3. 定义 approval 状态机；
4. 输出 AGENTS.md / CLAUDE.md / Cursor Rules；
5. 对接框架，不替代框架。

暂时不做：

1. 不做 Python Agent 框架；
2. 不直接依赖 NeMo/Guardrails/LangGraph；
3. 不做大型 Web 控制台；
4. 不做万能 LLM 评分裁判。
