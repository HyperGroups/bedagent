# bedagent

<img src="images/bedagent.svg" alt="bedagent" width="240" />

> 我躺着想，Agent 起来干。

```text
Design Version: D0.1
Codename: Book of Sloth / Sage
Status: design exploration
```

bedagent 是给“没有手脚的思想者”准备的 **Agent 控制系统**。

它不是单个 Agent，也不是通用 Agent 框架。它是一套把想法变成安全行动的 **控制层 + 协议 + 角色系统**。

这个人可能正躺在床上：不想打字，不想看长屏幕，不想维护复杂流程，但脑子一直在想。bedagent 要接住这些想法，陪他推演，把想法整理成任务，再调度下游 Agent 在安全边界内执行。

bedagent 的大脑里需要一个“最智者”：它不急着执行，而是先保护主线、剪掉低价值分支、问关键问题、做取舍。

命名上，bedagent 采用床与懒的体系：**Book of Sloth** 是懒人哲学，**Sage** 是最智者，**Dream** 是推演沙盒，**Blanket** 是风险保护，**Hands** 是执行沙盒，**Pillow Note** 是短汇报。

## 第一原则

**懒到极致的人是一等公民。**

这不是玩笑，而是产品约束：

- 能语音就不要打字；
- 能短反馈就不要长报告；
- 能自动推进就不要让用户盯着；
- 能在沙盒里试错就不要碰真实世界；
- 只有高风险动作才把人拉回来确认；
- 能剪掉低价值分支就不要浪费注意力。

## bedagent 到底是什么

bedagent 有三种形态：

| 形态 | 是什么 | 说明 |
|------|--------|------|
| 文档协议 | Book of Sloth + Sage 协议 + action manifest | 最小形态，让现有 Agent 遵守 |
| 本地控制层 | 输入监听 + Sage 判断 + 沙盒调度 + 短汇报 | 中间形态，本地 controller |
| Agent 集群 | Sage / Scribe / Blanket / Hands / Audit 等角色协作 | 完整形态，但仍服务同一控制目标 |

所以 bedagent **可以演化成 Agent 集群**，但它的本质不是“又一个 Agent”，而是：

> 让思想者用最少操作安全地驱动 Agent 的控制系统。

## 和 sofagent 的关系

bedagent 与 sofagent 有明确关系：二者共享“躺着让 Agent 干活”的愿景。

sofagent 来自 **sofa + agent**：躺在沙发上，让 Agent 把活干了。

bedagent 来自 **bed + agent**：躺在床上，把想法交给 Agent 去推演和执行。

sofagent 是 bedagent 的灵感来源和上下文来源，尤其是“Agent 需要纪律”这件事。但 bedagent 的产品重心不同：

| 维度 | sofagent | bedagent |
|------|----------|----------|
| 姿态 | 沙发 | 床 |
| 第一性问题 | Agent 不守规矩怎么办 | 人在床上一直想，但懒得操作怎么办 |
| 中心 | Agent 行为 | 思想者的想法到安全行动 |
| 重点 | 纪律层 | 控制层 + 推演层 + 低屏幕交互 |
| 隐喻 | 沙发上的纪律委员 | 床上的思想者外骨骼 |

一句话：

```text
bedagent = sofagent 的纪律层 + 思想捕获 + Agent 大脑 + 执行沙盒 + 低屏幕交互
```

## 核心链路

```text
床上想法
→ Capture 捕获
→ Sage 最智者
→ Focus 剪枝
→ Think 推演沙盒
→ Plan 任务整理
→ Gate 风险闸门
→ Act 执行沙盒
→ Report 短汇报
→ Memory 反思沉淀
```

核心原则是：

> Brain before Hands. 先过脑，再动手。

先允许 Agent 在“脑子里”乱想；再允许它在沙盒里试错；最后才允许它触碰真实世界。

但“想”也不能无限发散。bedagent 的节奏是：

> 想的时候快，剪枝要狠，动手前慢，执行要稳。

## 当前仓库状态

根目录现在是 bedagent 的新产品设计区。历史实现和参考代码放在：

```text
ref/ref_repos/sofagent/              # 上游参考快照
ref/ref_repos/bedagent-bootstrap/    # 早期 bedagent 历史实现快照
```

它们提交在仓库里，方便 GitHub 浏览和 `rg` 搜索，但不再是 active root 的源代码。

并行候选想法放在：

```text
ideas/                              # 候选路线，不是 active root
```

概念展示网站放在：

```text
site/                               # 静态 GitHub Pages 站点
```

合并到 `main` 后，GitHub Actions 会把 `site/` 发布到 `gh-pages` 分支。

## 文档

| 文档 | 说明 |
|------|------|
| [docs/README.md](docs/README.md) | 文档中心：推荐阅读顺序、主线/候选/参考说明 |
| [docs/what-is-bedagent.md](docs/what-is-bedagent.md) | bedagent 是什么：控制层、协议、角色系统还是 Agent 集群 |
| [docs/sofagent-context.md](docs/sofagent-context.md) | sofagent 作为同源隐喻、灵感来源和上下文来源 |
| [docs/design-versioning.md](docs/design-versioning.md) | 设计版本体系：想法快速切换时如何记录主线 |
| [docs/design-log.md](docs/design-log.md) | 设计决策记录：关键 pivot 和取舍 |
| [docs/workspace-strategy.md](docs/workspace-strategy.md) | 目录、分支、ref 快照如何配合管理想法切换 |
| [docs/philosophy.md](docs/philosophy.md) | sofagent 与 bedagent 的哲学对比 |
| [docs/lazy-philosophy-and-sage.md](docs/lazy-philosophy-and-sage.md) | 懒人哲学与“最智者”角色 |
| [docs/naming-system.md](docs/naming-system.md) | 床、懒、最智者主题的命名系统 |
| [docs/vocabulary.md](docs/vocabulary.md) | 床/懒/智/沙盒/语音等语义词汇素材库 |
| [docs/laziness-and-pruning.md](docs/laziness-and-pruning.md) | 懒的分型、快速思考与剪枝原则 |
| [docs/research-map.md](docs/research-map.md) | 相关工作研究地图：语音、PKM、Agent、Guardrails、沙盒 |
| [docs/capability-map.md](docs/capability-map.md) | bedagent 应该有哪些功能 |
| [docs/sandbox-brain.md](docs/sandbox-brain.md) | Agent 大脑、推演沙盒、执行沙盒 |
| [docs/voice-control.md](docs/voice-control.md) | 床上低屏幕/语音控制规划 |
| [docs/agent-constraint-frameworks.md](docs/agent-constraint-frameworks.md) | Agent 约束/治理框架调研 |
| [ideas/README.md](ideas/README.md) | 候选路线索引 |
| [ref/README.md](ref/README.md) | 参考快照目录说明 |
| [site/](site/) | bedagent 理念展示网站源码 |

## 不是什么

- 不是另一个通用 Agent 框架；
- 不是聊天机器人；
- 不是单纯语音助手；
- 不是把 sofagent 改名；
- 不是让 Agent 绕过确认去乱干。

bedagent 的目标是：

> 让最懒的思想者，也能安全地指挥最勤快的 Agent。
