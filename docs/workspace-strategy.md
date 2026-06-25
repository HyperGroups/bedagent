# 目录与分支策略

bedagent 早期会有大量方向切换。为了既能快速发散，又不污染 active root，需要同时使用：

1. **目录**：并排保存多个想法；
2. **分支**：隔离互相冲突的大改；
3. **ref 快照**：保留历史和外部参考；
4. **Design Version / ADR**：记录主线切换。

## 三种空间

| 空间 | 路径/命名 | 用途 | 是否 active |
|------|-----------|------|-------------|
| Active Root | `/` | 当前主线设计 | 是 |
| Ideas | `ideas/<topic>/` | 并行候选想法、草稿、分支路线 | 否 |
| References | `ref/ref_repos/<repo>/` | 历史代码、外部项目快照 | 否 |

## 目录 vs 分支

### 用目录

适合：

- 文档想法；
- 命名候选；
- 互不冲突的设计路线；
- 暂时不确定是否进入主线的思考；
- 可以被 `rg` 搜索的资料。

例子：

```text
ideas/voice-first/
ideas/sage-first/
ideas/sandbox-first/
ideas/mobile-bedside/
```

目录的好处是可见、可搜索、可并排比较。

### 用分支

适合：

- 会大规模改 active root；
- 互相冲突的架构；
- 要跑不同实现路线；
- 需要独立 PR 讨论；
- 会引入/删除大量文件。

例子：

```text
idea/sage-first
idea/voice-first
idea/sandbox-first
```

分支的好处是隔离，但不如目录方便同时搜索。

### 用 ref 快照

适合：

- 上游参考；
- 历史实现；
- 不再作为当前设计主线的代码；
- 需要保留但不想继续编辑的资料。

例子：

```text
ref/ref_repos/sofagent/
ref/ref_repos/bedagent-bootstrap/
```

ref 的状态应是 `reference`，不是 active。

## ideas 目录结构

每个 idea 至少包含一个 README：

```text
ideas/<topic>/
└── README.md
```

README 模板：

```markdown
# <topic>

status: candidate | parked | deprecated
design_version: D0.x
main_question: ...

## 想法

## 为什么值得想

## 为什么暂时不进主线

## 进入主线的条件
```

## 当前建议目录

```text
ideas/
├── sage-first/
├── voice-first/
├── sandbox-first/
└── mobile-bedside/
```

这些目录不是承诺，只是方便后续把分叉想法停放起来。

## 主线切换流程

当一个 idea 要进入 active root：

1. 更新对应 `ideas/<topic>/README.md` 状态；
2. 更新 `docs/design-log.md`，新增 ADR；
3. 更新 `README.md` 的 Design Version 或主线说明；
4. 如有必要，把 Design Version 从 `D0.1` 升到 `D0.2`；
5. 再修改 active root 文档。

## 删除/废弃流程

不要直接删掉想法。先改状态：

```yaml
status: deprecated
reason: "被 Sage-first 主线吸收"
```

只有当它已经进入 ref 快照或完全无价值时，才删除。

## 决策规则

一句话：

> 目录负责并排想，分支负责隔离改，ADR 负责记住为什么。

更 bedagent 一点：

> 梦可以分房间，醒来只走一条路。
