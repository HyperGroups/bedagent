# MVP closed-loop implementation

```text
Design Version: D0.1
Product Milestone: v0.2.0-mvp (prototype)
Status: implemented (local prototype + policy/adapter/memory)
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
9. **Short Report**  
   Produces one sentence `pillow_note`.
10. **Memory**  
   Appends run summary to `.bedagent/memory/journal.ndjson` (append-only).

## Output contract

Each run writes:

```text
.bedagent/runs/<run_id>/manifest.json
```

The manifest includes all stage outputs and is intended to be the seed contract
for future protocol stabilization (`sage`, `action manifest`, `blanket`,
`pillow_note`).

## New v0.2 runtime options

```bash
python3 mvp/bedagent_mvp.py run \
  --idea "Prepare safe branch execution plan" \
  --blanket-policy mvp/blanket_policy.json \
  --sandbox-adapter worktree-dry-run \
  --memory-journal .bedagent/memory/journal.ndjson \
  --git-repo-root . \
  --auto-confirm
```

`--auto-confirm` is still constrained by blanket policy (`allow_auto_confirm_red`).

## Current limitations

- No speech input/output yet.
- No external model API; stage reasoning is heuristic.
- No real command execution yet; Hands is simulated or dry-run planned.
- Memory is append-only journaling; no retrieval/ranking yet.

## Next implementation steps

1. Add deterministic `blanket` enforcement tests for custom policy overrides.
2. Add real worktree executor behind explicit `--allow-side-effects` gate.
3. Add memory reader for recap/prior-run suggestions.
4. Add voice adapter as optional input/output layer.
