# 设计版本体系

bedagent 现在处于设计探索期。这个阶段会频繁出现新想法、新命名、新架构和方向切换。

所以版本号不能只用传统软件发布版本。我们需要两套版本：

1. **Product Version**：未来真正发布的软件版本；
2. **Design Version**：当前思想、命名、协议和产品形态的设计快照。

## 为什么需要设计版本

bedagent 的早期工作不是“实现功能”，而是找到正确问题：

- bedagent 是什么；
- 懒到底是什么意思；
- 最智者是什么；
- 是否是 Agent 集群；
- 语音、沙盒、记忆、审计如何组合；
- 哪些方向只是暂存，哪些方向成为主线。

这些想法会切换得很快。如果没有设计版本，文档会互相打架。

## 版本层级

| 层级 | 格式 | 用途 |
|------|------|------|
| Product Version | `v0.1.0`, `v1.0.0` | 真实软件发布、CLI/API 兼容性 |
| Design Version | `D0.1`, `D0.2`, `D1.0` | 设计快照、哲学/命名/架构切换 |
| Decision ID | `ADR-0001` | 单个关键决策 |
| Idea Branch | `idea/sage`, `idea/voice`, `idea/sandbox` | 暂存或探索中的想法 |
| Codename | `Sage`, `Dream`, `Blanket` | 对外叙事和阶段代号 |

## 当前状态

当前 active root 是：

```text
Design Version: D0.1
Codename: Book of Sloth / Sage
Status: design exploration + MVP prototyping
```

D0.1 的核心定义：

```text
bedagent = 面向床上思想者的 Agent 控制系统
形态 = 控制层 + 协议 + 角色系统
链路 = Nest → Sage → Prune → Dream → Fold → Blanket → Hands → Pillow Note → Bedside Journal
Milestone = v0.4.0-mvp (policy + adapter + recap summary + worktree lifecycle)
```

## Design Version 规则

### D0.x：探索期

用于当前阶段：

- 哲学变化；
- 命名变化；
- 文档重组；
- 角色边界变化；
- MVP 形态变化。

D0.x 不承诺实现稳定。

### D1.x：协议稳定期

进入 D1.x 的条件：

- `sage` 协议稳定；
- `action manifest` 稳定；
- `blanket` 风险闸门稳定；
- `pillow_note` 短报格式稳定；
- 至少一个本地闭环跑通。

D1.x 开始要求向后兼容。

### v0.x：产品实现期

只有当出现可运行实现时，才启用 Product Version。

例如：

- CLI；
- 本地 controller；
- voice adapter；
- sandbox adapter；
- audit 工具。

## 状态标签

每个设计主题应该有一个状态：

| 状态 | 含义 |
|------|------|
| `active` | 当前主线 |
| `candidate` | 候选，可能进入主线 |
| `parked` | 暂存，以后再说 |
| `deprecated` | 已废弃，不再作为方向 |
| `reference` | 仅作参考，不是 active 设计 |

示例：

```yaml
topic: "voice control"
status: "candidate"
reason: "重要，但不是 D0.1 的主线实现"
```

## Pivot 规则

当我们改变核心方向时，不直接覆盖旧说法，而是写一条决策记录。

Pivot 条件：

- “bedagent 是什么”发生变化；
- 核心链路变化；
- 命名系统变化；
- MVP 范围变化；
- 某个模块从 active 变 parked/deprecated。

每次 pivot 至少记录：

```yaml
decision:
  id: "ADR-0001"
  design_version: "D0.1"
  date: "2026-06-25"
  change: "bedagent 从历史实现仓库转为设计仓库"
  keep:
    - "sofagent discipline as reference"
  park:
    - "old install scripts"
  prune:
    - "active root historical implementation"
  reason: "先确定产品哲学和控制层形态"
```

## 文档头建议

核心文档可以在后续加一个轻量状态块：

```yaml
design_version: D0.1
status: active
codename: Sage
last_decision: ADR-0003
```

当前阶段不强制所有文档都有 frontmatter，避免形式负担过重。

## 与 Git 分支的关系

Git 分支记录代码演化，Design Version 记录思想演化。

目录、分支、ref 快照的具体使用规则见 [workspace-strategy.md](workspace-strategy.md)。

推荐：

```text
Git branch: cursor/bedagent-foundation-6e9e
Design version: D0.1
Codename: Sage
```

如果后续出现互相冲突的大方向，可以开 Git 分支：

```text
idea/sage-first
idea/voice-first
idea/sandbox-first
```

但每个分支仍然要写自己的 Design Version 和决策记录。

## 设计切换原则

bedagent 允许快速切换想法，但不允许无记录地切换主线。

一句话：

> 想法可以乱飞，版本要钉住。

更 bedagent 一点：

> 快速做梦，醒来记账。
