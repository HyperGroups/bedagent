# Agent 大脑与沙盒系统

bedagent 要解决两个问题：

1. Agent 乱想；
2. Agent 乱改。

这两个问题不能用同一个沙盒解决。

## 乱想：推演沙盒

推演沙盒是 Agent 的大脑。

它不改代码，不跑命令，不触碰真实世界，只做思考：

```text
用户想法
→ 多种理解
→ 主线定位
→ 分支剪枝
→ 澄清问题
→ 多种方案
→ 风险评估
→ 推荐路径
→ action manifest
```

产物示例：

```yaml
goal: "把 bedagent 从历史实现仓库清成新产品设计仓库"
assumptions:
  - "历史实现已在 ref 目录保留"
  - "active root 应该只保留当前设计主线"
options:
  - name: "只清 README"
    risk: "low"
  - name: "删除旧实现代码"
    risk: "medium"
risks:
  - "删除 active 脚本后旧 CI 会失效"
decision:
  recommended: "删除旧实现与旧 CI，保留 ref 快照"
next_action:
  type: "plan"
```

推演沙盒的目标：

> 允许 Agent 在脑子里发散，但不允许它把发散直接变成修改。

它还要避免无限发散：

| 分支判断 | 处理 |
|----------|------|
| 服务当前主线 | 展开 |
| 有价值但时机不对 | 暂存 |
| 与已有问题重复 | 合并 |
| 低价值、不可验证、只是绕圈 | 剪掉 |

Agent Brain 的输出应该包含 `focus` 字段：

```yaml
focus:
  main_thread: "设计 bedagent 的哲学与 MVP"
  expanded:
    - "Agent 大脑"
    - "执行沙盒"
  parked:
    - "声纹识别"
  pruned:
    - "命名细节争论"
```

## 乱改：执行沙盒

执行沙盒是 Agent 的手。

它负责让 Agent 试错，但试错发生在隔离环境：

- git worktree；
- 临时分支；
- sandbox repo；
- container；
- dry-run；
- preview environment。

执行沙盒必须输出：

- 改了什么；
- 为什么改；
- 验证结果；
- 风险点；
- 是否建议合并到真实分支。

## Brain before Hands

完整链路：

```text
Human Thought
→ Agent Brain
→ Risk Gate
→ Agent Hands
→ Real World
```

原则：

1. 没有 brain proposal，不进入执行；
2. 没有 risk gate，不执行高风险动作；
3. 没有 sandbox evidence，不合并真实世界；
4. 没有 short report，不算完成。

## 风险闸门

| 风险 | 行为 |
|------|------|
| 绿 | 可在沙盒自动执行，短汇报 |
| 黄 | 先复述计划，确认后沙盒执行 |
| 红 | 必须二次确认，必要时屏幕端确认 |

红色动作包括：

- 删除数据；
- push 到远端；
- 外发消息；
- 付款；
- 生产配置变更；
- 泄露敏感信息。

## action manifest

bedagent 可以用一个轻量 manifest 连接大脑和手：

```yaml
action:
  id: "act_20260625_001"
  source: "voice"
  goal: "清理根目录"
  risk: "yellow"
  sandbox_required: true
  confirmation_required: true
proposal:
  summary: "删除历史实现，保留 ref 快照和核心设计文档"
  expected_changes:
    - "remove old implementation directories"
    - "rewrite README"
    - "add design docs"
decision:
  status: "pending"
```

这个 manifest 是未来语音控制、沙盒执行和审计系统的共同接口。
