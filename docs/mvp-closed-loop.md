# MVP closed-loop implementation

```text
Design Version: D0.1
Product Milestone: v0.6.0-mvp (prototype)
Status: implemented (retention report + full policy explain + weighted retrieval)
```

This document tracks the first executable bedagent loop in this repository.

## Scope

Implemented flow:

```text
Capture -> Sage -> Focus -> Think -> Plan -> Blanket -> Confirm -> Act Sandbox -> Short Report -> Memory
```

Implemented artifact:

- `mvp/bedagent_mvp.py` (zero-dependency Python CLI).

## Command examples

```bash
python3 mvp/bedagent_mvp.py run \
  --idea "Implement minimal loop and produce structured manifest" \
  --auto-confirm
```

```bash
python3 mvp/bedagent_mvp.py run --idea-file mvp/sample_idea.txt --non-interactive
```

## What is implemented now

1. **Capture**  
   Stores raw idea text with timestamp.
2. **Sage**  
   Produces main thread, intent tag, and key clarification questions.
3. **Focus**  
   Splits idea into branches and marks each as `expand`, `park`, `merge`, or `prune`.
4. **Think**  
   Generates option-level reasoning and a risk preview.
5. **Plan**  
   Produces executable task list and handoff summary.
6. **Blanket**  
   Applies policy-driven risk gates from `mvp/blanket_policy.json`.
7. **Confirm**  
   Enforces explicit approval before execution (default deny in non-interactive mode).
8. **Act Sandbox**  
   Uses pluggable adapters:
   - `simulated`
   - `worktree-dry-run` (generate plan only, no git side effect)
   - `worktree-live` (real `git worktree add`, blocked unless explicit side-effect flag)
9. **Short Report**  
   Produces one sentence `pillow_note`.
10. **Memory**  
   Appends run summary to `.bedagent/memory/journal.ndjson` (append-only).
11. **Worktree Lifecycle**  
   Supports managed worktree listing and cleanup through `worktree` subcommand.
12. **Policy Explain**  
   `worktree-live` now records a check tree (risk gate, keyword gate, side-effect gate).
13. **Memory Retrieval**  
   `memory-search` provides TF-IDF + cosine retrieval across recent journal entries.
14. **Retention Report**  
   `worktree retention-report` previews cleanup candidates without deleting anything.

## Output contract

Each run writes:

```text
.bedagent/runs/<run_id>/manifest.json
```

The manifest includes all stage outputs and is intended to be the seed contract
for future protocol stabilization (`sage`, `action manifest`, `blanket`,
`pillow_note`).

## New v0.5 runtime options

```bash
python3 mvp/bedagent_mvp.py run \
  --idea "Prepare safe branch execution plan" \
  --blanket-policy mvp/blanket_policy.json \
  --sandbox-adapter worktree-live \
  --memory-journal .bedagent/memory/journal.ndjson \
  --git-repo-root . \
  --allow-side-effects \
  --auto-confirm
```

`--auto-confirm` is still constrained by blanket policy (`allow_auto_confirm_red`).

Memory recap command:

```bash
python3 mvp/bedagent_mvp.py recap --memory-journal .bedagent/memory/journal.ndjson --limit 5
```

Memory semantic search:

```bash
python3 mvp/bedagent_mvp.py memory-search \
  --query "billing rollout plan" \
  --memory-journal .bedagent/memory/journal.ndjson \
  --limit 100 \
  --top-k 3
```

Worktree lifecycle commands:

```bash
python3 mvp/bedagent_mvp.py worktree list --worktree-root .bedagent/worktrees
python3 mvp/bedagent_mvp.py worktree cleanup --run-id <run_id> --allow-side-effects --force
python3 mvp/bedagent_mvp.py worktree cleanup --apply-retention --blanket-policy mvp/blanket_policy.json --allow-side-effects --force
python3 mvp/bedagent_mvp.py worktree retention-report --blanket-policy mvp/blanket_policy.json --worktree-root .bedagent/worktrees
```

## Current limitations

- No speech input/output yet.
- No external model API; stage reasoning is heuristic.
- No container executor yet; live execution currently focuses on git worktree path.
- Memory retrieval is weighted lexical-semantic (TF-IDF); no embedding/rerank pipeline yet.

## Next implementation steps

1. Add embedding-backed retrieval and rerank for memory search.
2. Add scheduled/automatic retention enforcement using existing report path.
3. Add container/VM adapters behind the same side-effect gate.
4. Add voice adapter as optional input/output layer.
