# ideas

`ideas/` 用来停放候选路线。这里的内容不是 active root 主线，也不是产品承诺。

使用规则见 [../docs/workspace-strategy.md](../docs/workspace-strategy.md)。

## 当前候选路线

| 路线 | 状态 | 主问题 |
|------|------|--------|
| [sage-first](sage-first/) | candidate | 最智者是否应该成为 D0.x 的第一主线？ |
| [voice-first](voice-first/) | candidate | 是否先从低屏幕语音入口做 MVP？ |
| [sandbox-first](sandbox-first/) | candidate | 是否先从执行沙盒和 worktree 闭环做 MVP？ |
| [mobile-bedside](mobile-bedside/) | candidate | 是否需要床边手机/旧设备作为控制器？ |

## 状态说明

| 状态 | 含义 |
|------|------|
| `candidate` | 候选，可能进入主线 |
| `parked` | 暂存，以后再说 |
| `deprecated` | 已废弃，不再作为方向 |

## 进入主线的条件

一个 idea 要进入 active root，至少需要：

1. 能说明它为什么比其他路线更适合作为最小闭环；
2. 能与 `Sage / Blanket / Hands` 控制结构兼容；
3. 能写入 `docs/design-log.md` 形成 ADR；
4. 如有必要，升级 Design Version，例如 `D0.1 → D0.2`。

## 不要在这里做什么

- 不要把完整历史实现复制进来；
- 不要把外部项目源码放进来；
- 不要把 candidate 当成 active 设计；
- 不要无记录地把想法从 ideas 搬进根目录。

一句话：

> 梦可以分房间，醒来只走一条路。
