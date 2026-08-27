# MVP closed-loop implementation

```text
Design Version: D0.1
Product Milestone: v0.12.0-mvp (prototype)
Status: implemented (VAD utterance split, local voice fallback, sentence TTS, silence auto-stop web)
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
15. **Retention Report Export**  
   `worktree retention-report --output-json <path>` exports report for automation.
16. **Retrieval Filters**  
   `memory-search` supports `risk_level` / `act_status` / `since` filters.
17. **Explain Schema Contract**  
   run-level `policy_explain` now includes `schema_version`.
18. **Explain Validator**  
   `validate-explain` validates schema version and required fields in manifest.
19. **Story / Voice / Web Agent**  
   Oral storytelling, DashScope ASR/TTS, and `site/agent/` entry (v0.8 follow-on).
20. **Optional LLM Sage**  
   `--use-llm` / `BEDAGENT_LLM=1` enhances story questions via DashScope Qwen (simulated fallback).
21. **Story Search**  
   `story search` retrieves across bibles/fragments with CJK-aware TF-IDF.
22. **Manifest Schema**  
   run `manifest.json` includes top-level `schema_version`.
23. **Explain Diff**  
   `explain-diff` compares two manifests' policy_explain chains.
24. **Web Story Persistence**  
   local API stores sessions under `.bedagent/stories/` with list/search endpoints.
25. **Chapter Expansion**  
   `story draft --expand` writes prose in the draft sandbox (heuristic, optional Qwen).
26. **Story Resume**  
   `story resume` / `--resume` reopens the latest session.
27. **Story Memory Sync**  
   oral turns append to the memory journal (`kind=story`) for unified retrieval.
28. **Unified Search**  
   `search` / `/api/search` ranks memory + story hits together.
29. **Quiet / Night TTS**  
   `--quiet` / `BEDAGENT_TTS_QUIET=1` shortens speech and skips auto-play.
30. **Character Sheet**  
   `story characters` / `/characters` with role / desire / conflict extras.
31. **Web Draft / Speak**  
   Agent UI can generate drafts, expand, resume latest, and speak replies.
32. **Streaming ASR partials**  
   `voice transcribe --stream` / `transcribe_stream()` emit growing transcripts (simulated sidecar or DashScope `send_audio_frame`).
33. **Silence gate**  
   Near-silent recordings skip bible writes instead of inventing text.
34. **Voice story API**  
   `POST /api/voice/story` runs ASR → Sage → TTS in one bedside round trip.
35. **Voice status / recap**  
   `voice status` and `voice recap` (speak night pillow of latest session).
36. **Hold-to-talk Web**  
   Agent voice mode: press-and-release recording, barge-in stops TTS, optional auto closed-loop.
37. **VAD utterance split**  
   Energy-based VAD splits a long recording into turns (`voice transcribe --vad`, `story voice-once --vad`).
38. **Sentence TTS**  
   `voice speak --stream` / `--tts-stream` synthesizes one wav per sentence.
39. **Local voice fallback**  
   `provider: auto` can use sidecar / Whisper / Piper when DashScope is unavailable.
40. **Voice memory**  
   Voice turns append `kind=voice` to the memory journal.
41. **Web silence auto-stop**  
   Agent voice mode can stop recording after ~1.2s of post-speech silence.

## Output contract

Each run writes:

```text
.bedagent/runs/<run_id>/manifest.json
```

The manifest includes all stage outputs and is intended to be the seed contract
for future protocol stabilization (`sage`, `action manifest`, `blanket`,
`pillow_note`).

## New v0.7 runtime options

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
  --risk-level yellow \
  --act-status worktree_created \
  --since 2026-06-26T00:00:00Z \
  --min-score 0.2 \
  --explain \
  --limit 100 \
  --top-k 3

python3 mvp/bedagent_mvp.py validate-explain \
  --manifest /tmp/bedagent-v07/20260626T150348.716111Z-1e51df/manifest.json \
  --expected-schema 1.0.0
```

Worktree lifecycle commands:

```bash
python3 mvp/bedagent_mvp.py worktree list --worktree-root .bedagent/worktrees
python3 mvp/bedagent_mvp.py worktree list --worktree-root .bedagent/worktrees --run-id-prefix 20260626T15 --since 2026-06-26T00:00:00Z
python3 mvp/bedagent_mvp.py worktree cleanup --run-id <run_id> --allow-side-effects --force
python3 mvp/bedagent_mvp.py worktree cleanup --apply-retention --blanket-policy mvp/blanket_policy.json --allow-side-effects --force
python3 mvp/bedagent_mvp.py worktree retention-report --blanket-policy mvp/blanket_policy.json --worktree-root .bedagent/worktrees --output-json .bedagent/reports/retention-report.json
```

## Current limitations

- Speech exists as an optional DashScope adapter with local Whisper/Piper fallback; GitHub Pages still needs local API for ASR/TTS.
- Sage reasoning is heuristic by default; DashScope Qwen is opt-in (`--use-llm` / `BEDAGENT_LLM=1`).
- Chapter expansion stays in the draft sandbox; it does not rewrite the bible without a later oral turn.
- No container executor yet; live execution currently focuses on git worktree path.
- Memory retrieval is weighted lexical-semantic (TF-IDF, CJK-aware) with pre-filters; no embedding/rerank pipeline yet.
- Browser VAD auto-stop is energy-based, not a continuous open-mic session.

## Next implementation steps

1. Add embedding-backed retrieval and rerank for memory/story search.
2. Add scheduled/automatic retention enforcement using existing report/export path.
3. Add container/VM adapters behind the same side-effect gate.
4. Add continuous open-mic VAD that keeps the mic open across turns without a hold button.
