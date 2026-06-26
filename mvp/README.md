# bedagent MVP (minimal closed loop)

This directory contains an executable prototype for the first bedagent loop:

```text
Capture -> Sage -> Focus -> Think -> Plan -> Blanket -> Confirm -> Act Sandbox -> Short Report -> Memory
```

## Why this exists

The repository has completed design exploration (D0.1).  
This MVP turns the design into a runnable local controller with:

- structured stage outputs (`manifest.json`);
- policy-driven blanket risk gate (`mvp/blanket_policy.json`);
- explicit confirmation step before execution;
- pluggable sandbox adapters (`simulated`, `worktree-dry-run`, `worktree-live`);
- append-only memory journal;
- memory recap command for quick bedside review;
- one-line short report (`pillow_note`).

## Quick start

From repository root:

```bash
python3 mvp/bedagent_mvp.py run \
  --idea "Implement docs index update and verify links" \
  --auto-confirm
```

Using worktree dry-run adapter:

```bash
python3 mvp/bedagent_mvp.py run \
  --idea "Prepare safe branch execution plan" \
  --sandbox-adapter worktree-dry-run \
  --auto-confirm
```

Or using an input file:

```bash
python3 mvp/bedagent_mvp.py run --idea-file mvp/sample_idea.txt --non-interactive
```

Memory recap:

```bash
python3 mvp/bedagent_mvp.py recap --memory-journal .bedagent/memory/journal.ndjson --limit 5
```

List managed worktrees:

```bash
python3 mvp/bedagent_mvp.py worktree list --worktree-root .bedagent/worktrees
```

Cleanup a specific worktree:

```bash
python3 mvp/bedagent_mvp.py worktree cleanup \
  --run-id <run_id> \
  --git-repo-root . \
  --worktree-root .bedagent/worktrees \
  --allow-side-effects \
  --force
```

## Key runtime flags

- `--blanket-policy`: blanket policy JSON file path.
- `--sandbox-adapter`: `simulated`, `worktree-dry-run`, or `worktree-live`.
- `--memory-journal`: append-only NDJSON journal file.
- `--git-repo-root`: git repository root used by worktree dry-run adapter.
- `--allow-side-effects`: required for `worktree-live`.
- `worktree` subcommand: lifecycle operations (`list`, `cleanup`).
- `recap` subcommand: memory playback with topic/status summary.

## Output artifacts

Every run is written to:

```text
.bedagent/runs/<run_id>/
```

Main artifact:

- `manifest.json`: full flow output for all stages.
- `memory` stage appends one record to the journal file.

When execution is approved, the sandbox subfolder also includes:

- for `simulated`: `hands/TASKS.md`, `hands/execution_receipt.json`
- for `worktree-dry-run`: `hands/WORKTREE_DRY_RUN_PLAN.md`
- for `worktree-live`: `hands/WORKTREE_LIVE_TRANSCRIPT.md`

## Notes

- This MVP intentionally uses heuristic logic (no model API required).
- `worktree-dry-run` does not run git commands; it only emits a plan file.
- `worktree-live` is blocked unless `--allow-side-effects` is explicitly set.
- `worktree-live` is also gated by blanket policy risk/keyword rules.
- High-risk ideas require stronger explicit confirmation (`YES`) in interactive mode.
- `--auto-confirm` does not bypass red-risk policy when `allow_auto_confirm_red` is `false`.
