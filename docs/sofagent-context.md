# sofagent 上下文

bedagent 与 sofagent 有明确关系，但不是简单 fork 或改名。

## 同源隐喻

sofagent 的名字来自：

> sofa + agent

它表达的是：

> 躺在沙发上，让 Agent 把活干了。

bedagent 的名字来自：

> bed + agent

它表达的是：

> 躺在床上，把想法交给 Agent 去推演和执行。

沙发和床都指向同一个大方向：

> 人不再长时间坐在电脑前亲自操作，而是以更低操作姿态驱动 Agent。

所以二者不是毫无关系。bedagent 是在 sofagent 的语义上下文里继续向前走。

## 灵感来源

sofagent 给 bedagent 的主要启发：

| sofagent 启发 | bedagent 转化 |
|---------------|---------------|
| Agent 需要纪律 | Agent 需要先过脑，再动手 |
| 先读后写、验证再干 | Sage / Blanket / Hands 的控制链 |
| 任务闭环和反思 | Bedside Journal / Pillow Note |
| 提交时审计 | Hands 执行后必须有证据 |
| 躺在沙发上等 Agent 干活 | 躺在床上边想边指挥 Agent |

sofagent 让我们看到：

> 只让 Agent 变强不够，还要给 Agent 加纪律。

bedagent 在此基础上继续追问：

> 如果人已经懒到不想坐起来操作，但脑子还在高速思考，系统应该长什么样？

## 关键差异

| 维度 | sofagent | bedagent |
|------|----------|----------|
| 姿态 | 沙发 | 床 |
| 核心问题 | Agent 不守规矩怎么办 | 思想者懒得操作但一直在想怎么办 |
| 中心 | Agent 行为 | 人的想法到安全行动 |
| 重点 | 纪律层 | 控制层 + 推演层 + 低屏幕交互 |
| 产物 | 约束 Agent 的 Skill/脚本/审计 | 思想者的 Agent 控制系统 |

## 不是关系

bedagent 不是：

- sofagent 改名；
- sofagent 的替代品；
- sofagent 的完整复制；
- 对 sofagent 的否定。

bedagent 是：

> 以 sofagent 为上下文和灵感来源，围绕“床上思想者”重新定义的 Agent 控制系统。

## 为什么保留 ref 快照

仓库里保留了：

```text
ref/ref_repos/sofagent/
ref/ref_repos/bedagent-bootstrap/
```

原因：

1. 让 GitHub 上能看到灵感来源和历史上下文；
2. 方便用 `rg` 搜索纪律层、审计、脚本等设计；
3. 避免 active root 被历史实现绑架；
4. 后续需要实现时，可以从 ref 中挑选值得重写的部分。

## 一句话

> sofagent 是“沙发上的纪律委员”，bedagent 是“床上的思想者外骨骼”。

二者共享“躺着让 Agent 干活”的愿景，但 bedagent 的重心从 Agent 守纪律，转向思想者如何低操作、安全地驱动 Agent。
