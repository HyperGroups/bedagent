# bedagent MVP (minimal closed loop)

This directory contains an executable prototype for the first bedagent loop:

```text
Capture -> Sage -> Focus -> Think -> Plan -> Confirm -> Act Sandbox -> Short Report
```

## Why this exists

The repository has completed design exploration (D0.1).  
This MVP turns the design into a runnable local controller with:

- structured stage outputs (`manifest.json`);
- explicit confirmation step before execution;
- sandbox-only execution (simulated in MVP);
- one-line short report (`pillow_note`).

## Quick start

From repository root:

```bash
python3 mvp/bedagent_mvp.py run \
  --idea "Implement docs index update and verify links" \
  --auto-confirm
```

Or using an input file:

```bash
python3 mvp/bedagent_mvp.py run --idea-file mvp/sample_idea.txt --non-interactive
```

## Output artifacts

Every run is written to:

```text
.bedagent/runs/<run_id>/
```

Main artifact:

- `manifest.json`: full flow output for all stages.

When execution is approved, the sandbox subfolder also includes:

- `hands/TASKS.md`
- `hands/execution_receipt.json`

## Notes

- This MVP intentionally uses heuristic logic (no model API required).
- `Act Sandbox` is simulated by writing artifacts only; no external side effects.
- High-risk ideas require stronger explicit confirmation (`YES`) in interactive mode.
