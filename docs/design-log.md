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

## ADR-0007：引入 ideas 目录与分支策略

```yaml
date: 2026-06-25
design_version: D0.1
status: accepted
```

### 决策

引入三种空间：

```text
active root: 当前主线
ideas/: 候选路线和并行设计
ref/ref_repos/: 历史和外部参考快照
```

同时保留 Git 分支用于真正互相冲突的大改。

### 原因

当前阶段会频繁切换想法。如果所有想法都直接改 active root，文档会互相打架；如果所有想法都开分支，又不方便 `rg` 并排搜索。

因此：

- 目录负责并排想；
- 分支负责隔离改；
- ADR 负责记住为什么。

### 初始候选路线

```text
ideas/sage-first/
ideas/voice-first/
ideas/sandbox-first/
ideas/mobile-bedside/
```

## ADR-0008：定义 sofagent 为上下文与灵感来源

```yaml
date: 2026-06-25
design_version: D0.1
status: accepted
```

### 决策

bedagent 与 sofagent 的关系定义为：

```text
同源隐喻 + 灵感来源 + 上下文来源
```

而不是：

```text
简单 fork / 改名 / 替代品
```

### 原因

sofagent 的 “sofa + agent” 已经表达了“躺着让 Agent 干活”的方向。bedagent 沿着这个语义继续推进，但把重心从“Agent 纪律层”扩展到“床上思想者的 Agent 控制系统”。

### 保留

- sofagent 的纪律层启发；
- 先读后写、验证再干、谨慎修改；
- 反思和审计意识；
- `ref/ref_repos/sofagent/` 作为可浏览上下文。

### 改写

- 从沙发姿态到床上姿态；
- 从 Agent 行为中心到思想者想法中心；
- 从纪律层到控制层 + 推演层 + 低屏幕交互。

## ADR-0009：启动最小闭环可执行原型

```yaml
date: 2026-06-26
design_version: D0.1
status: accepted
product_milestone: v0.1.0-mvp
```

### 决策

从纯文档设计进入“可执行但保守”的本地 MVP，实现：

```text
Capture -> Sage -> Focus -> Think -> Plan -> Confirm -> Act Sandbox -> Short Report
```

并把每次运行输出成结构化 `manifest.json`，作为后续协议稳定化种子。

### 范围

- 在 `mvp/bedagent_mvp.py` 落地零依赖 CLI；
- 默认要求确认，非交互模式默认拒绝执行；
- Hands 先以沙盒模拟执行，避免真实副作用；
- 产出 `pillow_note` 一句话短报和运行证据。

### 原因

“全面推进”阶段需要从概念进入执行证据，但不能过早引入复杂 runtime 或高风险自动执行。

先跑通闭环，才能迭代语音、策略文件、真实沙盒适配器和记忆层。

## ADR-0010：引入 Blanket 策略文件、可插拔 Sandbox Adapter、Append-only Memory

```yaml
date: 2026-06-26
design_version: D0.1
status: accepted
product_milestone: v0.2.0-mvp
```

### 决策

在 v0.1.0-mvp 的最小闭环上增加三项运行时骨架：

1. `blanket_policy.json` 作为可配置风险策略；
2. `sandbox_adapter` 抽象（`simulated` + `worktree-dry-run`）；
3. append-only memory journal（NDJSON）。

### 原因

“全面推进”需要从“能跑一次”升级到“可配置、可扩展、可追溯”：

- 可配置：风险规则不能硬编码在实现里；
- 可扩展：Hands 需要有适配器边界，后续接 container/worktree 才不重写；
- 可追溯：每次运行要沉淀最小记忆证据。

### 边界

- `worktree-dry-run` 只生成执行计划，不直接执行 git 命令；
- memory 目前只追加，不做检索、合并、总结；
- 仍然保持“默认保守”，避免真实副作用。

## ADR-0011：增加 Memory Recap 与显式 Side-effect Gate 的 worktree-live 执行器

```yaml
date: 2026-06-26
design_version: D0.1
status: accepted
product_milestone: v0.3.0-mvp
```

### 决策

在 v0.2.0-mvp 基础上新增：

1. `recap` 子命令，用于读取 memory journal 的最近记录；
2. `worktree-live` adapter，可执行真实 `git worktree add`；
3. `--allow-side-effects` 显式开关，默认不允许副作用；
4. 自定义 blanket policy 覆盖测试，确保策略对确认逻辑生效。

### 原因

“全面推进”阶段不仅要有“记录”，还要有“回看”；不仅要有“适配器边界”，还要有“受控真实执行路径”。

### 边界

- `worktree-live` 只覆盖 worktree 创建，不做自动提交/推送；
- 未显式传入 `--allow-side-effects` 时，live 执行必须阻断；
- recap 只做结构化回放，不做语义摘要或检索增强。

## ADR-0012：增加 worktree 生命周期管理与 live adapter 细粒度策略闸门

```yaml
date: 2026-06-26
design_version: D0.1
status: accepted
product_milestone: v0.4.0-mvp
```

### 决策

在 v0.3.0-mvp 基础上继续推进：

1. 增加 `worktree` 子命令，支持 `list` / `cleanup`；
2. live adapter 增加按风险级别和关键词的策略闸门；
3. recap 增加 topic/status 的轻量摘要。

### 原因

仅有“创建 worktree”不足以形成完整 Hands 运维闭环；仅有“追加日志”不足以形成快速回看闭环。

v0.4 目标是让控制层具备：

- 可执行（create）；
- 可管理（list/cleanup）；
- 可回看（summary recap）；
- 可约束（risk + keyword gates）。

### 边界

- cleanup 仍需显式 `--allow-side-effects`；
- 不做自动 TTL 清理或批量策略调度；
- 摘要仍是启发式，不引入模型依赖。

## ADR-0013：引入 retention 策略清理、memory semantic search、live policy explain

```yaml
date: 2026-06-26
design_version: D0.1
status: accepted
product_milestone: v0.5.0-mvp
```

### 决策

在 v0.4.0-mvp 上继续推进三项：

1. `worktree cleanup --apply-retention`，按 `ttl_hours + max_keep` 选取清理候选；
2. `memory-search` 子命令，基于 TF-IDF + cosine 做近似语义检索；
3. `worktree-live` 增加 policy explain（risk/keyword/side-effect 三段检查树）。

### 原因

“全面推进”到这个阶段，需要把“可执行”升级为“可治理 + 可回忆 + 可解释”：

- 可治理：worktree 不应无限积累；
- 可回忆：journal 不应只追加不检索；
- 可解释：执行被拦截时必须告诉人为什么。

### 边界

- retention 仍通过显式命令触发，不做后台自动任务；
- semantic search 仍是轻量 lexical 方案，不依赖外部模型；
- policy explain 先覆盖 live adapter，不代表全链路解释器已完成。

## ADR-0014：补齐 retention dry-run 报告与运行期全链路 explain 输出

```yaml
date: 2026-06-26
design_version: D0.1
status: accepted
product_milestone: v0.6.0-mvp
```

### 决策

在 v0.5.0-mvp 上补齐三点：

1. 增加 `worktree retention-report`（只报告候选，不执行删除）；
2. 每次 run 在 manifest 输出 `policy_explain` 链路（Blanket -> Confirm -> Act）；
3. `memory-search` 由单字段拼接改为多字段加权检索（idea/pillow/status/risk）。

### 原因

推进到 v0.6 后，需要同时满足“可审阅、可解释、可回忆”：

- retention 的治理动作要先可预览；
- 执行前后的策略判断要可追踪；
- 记忆检索要避免被单一字段主导。

### 边界

- retention-report 仅输出，不做副作用；
- explain 先聚焦 run 闭环，不覆盖所有子命令；
- retrieval 仍是本地无依赖实现，不引入外部向量库。
