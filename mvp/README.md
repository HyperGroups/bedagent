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
- memory semantic search command for retrieving similar prior runs;
- policy explain chain in run manifest (Blanket -> Confirm -> Act);
- policy explain contract validator command for manifest checks;
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

Memory semantic search:

```bash
python3 mvp/bedagent_mvp.py memory-search \
  --query "billing rollout plan" \
  --memory-journal .bedagent/memory/journal.ndjson \
  --risk-level yellow \
  --act-status worktree_created \
  --since 2026-06-26T00:00:00Z \
  --min-score 0.2 \
  --explain \
  --top-k 3
```

Validate explain schema in a manifest:

```bash
python3 mvp/bedagent_mvp.py validate-explain \
  --manifest /tmp/bedagent-v07/20260626T150348.716111Z-1e51df/manifest.json \
  --expected-schema 1.0.0
```

Diff two run explains:

```bash
python3 mvp/bedagent_mvp.py explain-diff \
  --left .bedagent/runs/<id-a>/manifest.json \
  --right .bedagent/runs/<id-b>/manifest.json
```

Story search (CJK-aware):

```bash
python3 mvp/bedagent_mvp.py story search --query "维修AI 冬眠舰" --top-k 3
```

Resume latest session, expand a chapter, and unified search:

```bash
python3 mvp/bedagent_mvp.py story resume
python3 mvp/bedagent_mvp.py story draft --resume --expand --use-llm
python3 mvp/bedagent_mvp.py story characters --resume
python3 mvp/bedagent_mvp.py search --query "林澜 冬眠舰" --top-k 5
```

List managed worktrees:

```bash
python3 mvp/bedagent_mvp.py worktree list --worktree-root .bedagent/worktrees
python3 mvp/bedagent_mvp.py worktree list --worktree-root .bedagent/worktrees --run-id-prefix 20260626T15 --since 2026-06-26T00:00:00Z
```

Cleanup a specific worktree:

```bash
python3 mvp/bedagent_mvp.py worktree cleanup \
  --run-id <run_id> \
  --git-repo-root . \
  --blanket-policy mvp/blanket_policy.json \
  --worktree-root .bedagent/worktrees \
  --allow-side-effects \
  --force
```

Cleanup by retention policy (TTL + max_keep):

```bash
python3 mvp/bedagent_mvp.py worktree cleanup \
  --apply-retention \
  --blanket-policy mvp/blanket_policy.json \
  --git-repo-root . \
  --worktree-root .bedagent/worktrees \
  --allow-side-effects \
  --force
```

Retention dry-run report (no deletion):

```bash
python3 mvp/bedagent_mvp.py worktree retention-report \
  --blanket-policy mvp/blanket_policy.json \
  --worktree-root .bedagent/worktrees \
  --output-json .bedagent/reports/retention-report.json
```

Oral storytelling (vibe storytelling — lie in bed and tell the story piece by piece):

```bash
# Interactive oral loop (multi-line fragment, blank line to send)
python3 mvp/bedagent_mvp.py story tell --title "会做梦的维修AI"

# Resume an existing session
python3 mvp/bedagent_mvp.py story tell --story-id <session-id>

# Seed first fragment, then continue interactively
python3 mvp/bedagent_mvp.py story tell \
  --title "会做梦的维修AI" \
  --seed-file mvp/sample_story_seed.txt

# Single fragment (script-friendly)
python3 mvp/bedagent_mvp.py story once \
  --title "会做梦的维修AI" \
  --fragment-file mvp/sample_story_seed.txt \
  --auto-confirm

# Answer Sage alignment questions
python3 mvp/bedagent_mvp.py story answer \
  --story-id <session-id> \
  --answer-file mvp/sample_story_answer.txt

# Generate chapter sketch + outline (Act sandbox)
python3 mvp/bedagent_mvp.py story draft --story-id <session-id>

# Export markdown bible + transcript
python3 mvp/bedagent_mvp.py story export --story-id <session-id>

# List sessions
python3 mvp/bedagent_mvp.py story list
```

Interactive commands inside `story tell`:

- `/answer` — reply to Sage open questions
- `/draft` — write `drafts/chapter-NN-sketch.md` and `drafts/outline.md`
- `/expand` — expand the sketch into `drafts/chapter-NN-prose.md`
- `/characters` — print character cards (role / desire / conflict)
- `/export` — write `exports/story-bible.md` and `exports/transcript.md`
- `/questions` — show pending alignment questions
- `/recap` — bedside recap

Story sessions are written to:

```text
.bedagent/stories/<session-id>/
  bible.json
  fragments.ndjson
  turns.ndjson
  session.json
  drafts/
  exports/
```

Blanket policy for major story pivots: `mvp/story_blanket_policy.json`

Voice (DashScope 百炼 ASR/TTS):

```bash
pip install -r mvp/requirements-voice.txt
export DASHSCOPE_API_KEY="sk-..."

# Transcribe / speak
python3 mvp/bedagent_mvp.py voice transcribe --audio-file input.wav
python3 mvp/bedagent_mvp.py voice speak --text "收到，继续讲。" --output reply.wav

# Story voice loop
python3 mvp/bedagent_mvp.py story voice-once \
  --title "会做梦的维修AI" \
  --audio-file input.wav \
  --auto-confirm

python3 mvp/bedagent_mvp.py story voice --title "会做梦的维修AI" --mic --play-reply
python3 mvp/bedagent_mvp.py story voice-once --resume --audio-file input.wav --quiet --auto-confirm --stream --vad
python3 mvp/bedagent_mvp.py voice transcribe --audio-file input.wav --stream --vad
python3 mvp/bedagent_mvp.py voice speak --text "收到。继续讲。" --stream
python3 mvp/bedagent_mvp.py voice status
python3 mvp/bedagent_mvp.py voice recap --resume
```

Simulated voice (no DashScope ASR/TTS call):

```bash
# Sidecar transcript: oral-turn1.wav + oral-turn1.transcript.txt
export BEDAGENT_TTS_SIMULATE=1
python3 mvp/bedagent_mvp.py story voice-once \
  --title "模拟语音闭环" \
  --audio-file mvp/fixtures/voice/oral-turn1.wav \
  --auto-confirm

# Closed-loop test suite
python3 -m unittest mvp.test_voice_story_closed_loop -v
```

Flow: **audio fixture → simulated ASR → Story Sage/Focus → simulated TTS → voice artifacts**

Web Agent UI (GitHub Pages + optional local API):

```bash
# Static site includes Agent entry at site/agent/
# Local dev with API (MVP run + DashScope voice):
python3 mvp/bedagent_web.py --port 8765
# open http://127.0.0.1:8765/agent/
```

## Key runtime flags

- `--blanket-policy`: blanket policy JSON file path.
- `--sandbox-adapter`: `simulated`, `worktree-dry-run`, or `worktree-live`.
- `--memory-journal`: append-only NDJSON journal file.
- `--git-repo-root`: git repository root used by worktree dry-run adapter.
- `--allow-side-effects`: required for `worktree-live`.
- `worktree` subcommand: lifecycle operations (`list`, `cleanup`) with optional policy retention cleanup.
- `recap` subcommand: memory playback with topic/status summary.
- `memory-search` subcommand: weighted multi-field TF-IDF cosine retrieval over recent journal entries.
- `memory-search` supports `--risk-level`, `--act-status`, `--since` pre-filters.
- `memory-search` supports `--min-score` and `--explain` for result control.
- `validate-explain` subcommand: validates `policy_explain` schema and required fields.
- `explain-diff` subcommand: diffs `policy_explain` between two manifests.
- `story` subcommand: oral storytelling loop (`tell`, `voice`, `voice-once`, `once`, `recap`, `answer`, `draft`, `export`, `list`, `search`, `resume`, `characters`) with bible, blanket, draft sandbox, DashScope voice, optional Qwen Sage, chapter expansion, and memory journal sync.
- `voice` subcommand: DashScope / local ASR-TTS (`transcribe`, `speak`, `status`, `recap`); `--stream` emits ASR partials or sentence TTS; `--vad` splits utterances; `--quiet` / `BEDAGENT_TTS_QUIET=1` shortens night TTS.
- `search` subcommand: unified TF-IDF search across memory journal and story sessions.
- `--use-llm` / `BEDAGENT_LLM=1`: optional DashScope Qwen enhancement (`BEDAGENT_LLM_SIMULATE=1` for offline), including `story draft --expand`.

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
- `worktree cleanup --apply-retention` uses `worktree_retention.ttl_hours` and `max_keep`.
- `worktree retention-report` previews retention cleanup without side effects.
- run manifest includes `policy_explain.schema_version` for explain contract tracking.
- High-risk ideas require stronger explicit confirmation (`YES`) in interactive mode.
- `--auto-confirm` does not bypass red-risk policy when `allow_auto_confirm_red` is `false`.
