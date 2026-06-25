# 设计决策记录

> Design Version: D0.1
> Status: active design log

本文件记录 bedagent 设计主线的关键切换。小想法可以进入普通文档；改变主线的决定要进入这里。

## ADR-0001：从历史实现仓库切换为设计仓库

```yaml
date: 2026-06-25
design_version: D0.1
status: accepted
```

### 决策

active root 不再保留早期迁移来的完整 sofagent-style 实现，而是清理成轻量产品设计仓库。

### 保留

- 上游 `sofagent` 快照；
- 早期 `bedagent-bootstrap` 快照；
- MIT 许可和 NOTICE；
- 当前设计文档。

### 暂存

- install scripts；
- bedagent-audit；
- CI workflows；
- 旧 changelog / benchmark / cases。

### 原因

当前最大问题不是实现，而是定义：

> bedagent 到底是什么。

先确定哲学、角色、控制层和命名，再决定哪些旧实现值得拿回来。

## ADR-0002：定义 bedagent 为 Agent 控制系统

```yaml
date: 2026-06-25
design_version: D0.1
status: accepted
```

### 决策

bedagent 不是单个 Agent，也不是通用 Agent 框架，而是：

```text
控制层 + 协议 + 角色系统
```

### 三种形态

1. 文档协议形态；
2. 本地控制层形态；
3. Agent 集群形态。

### 原因

如果只说“不是聊天机器人 / 不是语音助手 / 不是 sofagent 改名”，仍然不能解释 bedagent 是什么。

新的定义让边界清楚：

- Sage 不执行；
- Hands 才执行；
- Blanket 负责风险；
- 外部 Agent/runtime 是下游。

## ADR-0003：确立懒人哲学与最智者

```yaml
date: 2026-06-25
design_version: D0.1
status: accepted
```

### 决策

bedagent 有两根柱子：

```text
Book of Sloth：懒人哲学
Sage：最智者
```

### 原因

“懒”本身不够。懒可以节省操作，也可能逃避判断。

因此需要最智者把懒变成智慧：

- 保护主线；
- 剪掉低价值分支；
- 问关键问题；
- 做取舍；
- 阻止低价值执行。

## ADR-0004：引入认知剪枝

```yaml
date: 2026-06-25
design_version: D0.1
status: accepted
```

### 决策

快速思考不能无限发散。bedagent 的节奏是：

```text
想的时候快，
剪枝要狠，
动手前慢，
执行要稳。
```

核心链路从：

```text
Capture → Think → Plan → Gate → Act
```

升级为：

```text
Capture → Sage → Focus → Think → Plan → Gate → Act
```

### 原因

懒不仅是少行动，也是不愿意在低价值分支上浪费注意力。

## ADR-0005：采用床/懒/智命名系统

```yaml
date: 2026-06-25
design_version: D0.1
status: accepted
```

### 决策

采用当前推荐套装：

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

### 原因

命名要提醒产品边界：

- 懒不是逃避责任；
- 智者不是执行者；
- 沙盒不是现实；
- 短报不是长报告。

## ADR-0006：Design Version 与 Product Version 分离

```yaml
date: 2026-06-25
design_version: D0.1
status: accepted
```

### 决策

当前阶段使用 Design Version：

```text
D0.1 — Book of Sloth / Sage
```

Product Version 只在出现真实可运行实现后启用。

### 原因

bedagent 还处于想法快速切换期。用传统产品版本号会制造误导。

设计版本记录思想演化，产品版本记录软件发布。
