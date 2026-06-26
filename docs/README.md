# bedagent 文档中心

```text
Design Version: D0.1
Codename: Book of Sloth / Sage
Status: design exploration
```

这里是 bedagent 当前设计主线的文档入口。根目录 README 负责一句话说明项目；本文件负责告诉读者应该按什么顺序阅读。

## 先读这 4 份

| 顺序 | 文档 | 解决的问题 |
|------|------|------------|
| 1 | [what-is-bedagent.md](what-is-bedagent.md) | bedagent 到底是什么：Agent、Agent 集群，还是控制系统 |
| 2 | [philosophy.md](philosophy.md) | bedagent 的目标用户、与 sofagent 的关系、核心哲学 |
| 3 | [lazy-philosophy-and-sage.md](lazy-philosophy-and-sage.md) | Book of Sloth 与 Sage 两根柱子 |
| 4 | [laziness-and-pruning.md](laziness-and-pruning.md) | 懒的分型、快速思考与认知剪枝 |

如果只读一个结论：

> bedagent 是给床上思想者的 Agent 控制系统。它用 Sage 保护主线，用 Blanket 控制风险，用 Hands 在沙盒执行。

## 设计主线

| 文档 | 内容 |
|------|------|
| [capability-map.md](capability-map.md) | Mind / Voice / Gate / Hands / Memory 五层能力地图 |
| [sandbox-brain.md](sandbox-brain.md) | Agent Brain、推演沙盒、执行沙盒、action manifest |
| [voice-control.md](voice-control.md) | 床上低屏幕/语音控制规划 |
| [agent-constraint-frameworks.md](agent-constraint-frameworks.md) | Guardrails、HITL、约束框架调研 |
| [research-map.md](research-map.md) | 相关工作全景：语音、PKM、Agent、沙盒、审计 |

## 命名与语言

| 文档 | 内容 |
|------|------|
| [naming-system.md](naming-system.md) | bedagent 的正式命名系统 |
| [vocabulary.md](vocabulary.md) | 床、懒、智、沙盒、语音、记忆等候选词库 |

当前推荐套装：

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

## 版本与工作区

| 文档 | 内容 |
|------|------|
| [design-versioning.md](design-versioning.md) | Design Version / Product Version / ADR / Codename 的关系 |
| [design-log.md](design-log.md) | 关键设计决策记录 |
| [workspace-strategy.md](workspace-strategy.md) | active root、ideas、ref、branch 如何配合 |

当前主线：

```text
Design Version: D0.1
Active thread: Book of Sloth / Sage
```

## 相关上下文

| 文档 | 内容 |
|------|------|
| [sofagent-context.md](sofagent-context.md) | sofagent 作为同源隐喻、灵感来源和上下文来源 |

参考代码和历史快照在：

```text
ref/ref_repos/sofagent/
ref/ref_repos/bedagent-bootstrap/
```

## 候选路线

候选路线不属于 active root 主线，放在 `ideas/`：

```text
ideas/sage-first/
ideas/voice-first/
ideas/sandbox-first/
ideas/mobile-bedside/
```

索引见 [../ideas/README.md](../ideas/README.md)。

## 文档维护规则

1. 如果改变“bedagent 是什么”，必须更新 [what-is-bedagent.md](what-is-bedagent.md) 和 [design-log.md](design-log.md)。
2. 如果改变核心链路，必须更新 README、[capability-map.md](capability-map.md)、[design-log.md](design-log.md)。
3. 如果只是新想法，先放进 `ideas/<topic>/`，不要直接改 active root。
4. 如果只是外部参考，放进 `ref/ref_repos/` 或 [research-map.md](research-map.md)。
5. 如果文档互相打架，以最新 ADR 为准。

一句话：

> 想法可以乱飞，文档要有主线。
