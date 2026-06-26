# MVP closed-loop implementation

```text
Design Version: D0.1
Product Milestone: v0.1.0-mvp (prototype)
Status: implemented (local prototype)
```

This document tracks the first executable bedagent loop in this repository.

## Scope

Implemented flow:

```text
Capture -> Sage -> Focus -> Think -> Plan -> Confirm -> Act Sandbox -> Short Report
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
6. **Confirm**  
   Enforces explicit approval before execution (default deny in non-interactive mode).
7. **Act Sandbox**  
   Writes simulated execution artifacts under run-scoped sandbox path.
8. **Short Report**  
   Produces one sentence `pillow_note`.

## Output contract

Each run writes:

```text
.bedagent/runs/<run_id>/manifest.json
```

The manifest includes all stage outputs and is intended to be the seed contract
for future protocol stabilization (`sage`, `action manifest`, `blanket`,
`pillow_note`).

## Current limitations

- No speech input/output yet.
- No external model API; stage reasoning is heuristic.
- No real command execution yet; Hands is simulated.
- No persistent memory consolidation yet.

## Next implementation steps

1. Introduce explicit `blanket` policy file and deterministic risk rules.
2. Add optional sandbox runner abstraction (worktree/container adapters).
3. Add lightweight memory append-only journal.
4. Add voice adapter as optional input/output layer.
