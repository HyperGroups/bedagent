#!/usr/bin/env python3
"""bedagent MVP: minimal closed-loop controller prototype."""

from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import textwrap
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


DEFAULT_RED_KEYWORDS = {
    "delete",
    "drop",
    "destroy",
    "deploy",
    "production",
    "prod",
    "payment",
    "billing",
    "credential",
    "password",
    "token",
    "secret",
    "key",
    "merge",
    "push",
}

DEFAULT_YELLOW_KEYWORDS = {
    "write",
    "modify",
    "change",
    "edit",
    "create",
    "update",
    "refactor",
    "rename",
    "migrate",
    "commit",
}


@dataclass
class RunContext:
    run_id: str
    run_dir: Path
    idea: str


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def build_run_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    suffix = uuid.uuid4().hex[:6]
    return f"{ts}-{suffix}"


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def first_sentence(value: str, max_len: int = 120) -> str:
    text = clean_text(value)
    if not text:
        return "No idea provided."
    parts = re.split(r"[.!?]", text)
    summary = parts[0].strip() if parts else text
    if len(summary) <= max_len:
        return summary
    return summary[: max_len - 3].rstrip() + "..."


def detect_intent(value: str) -> str:
    lower = value.lower()
    if any(k in lower for k in ("bug", "fix", "error", "failure")):
        return "debug_or_fix"
    if any(k in lower for k in ("doc", "readme", "write", "note")):
        return "documentation"
    if any(k in lower for k in ("refactor", "cleanup", "optimize")):
        return "improvement"
    if any(k in lower for k in ("feature", "implement", "build", "add")):
        return "feature_delivery"
    return "exploration"


def extract_branches(value: str) -> list[str]:
    raw = re.split(r"[\n;,]+", value)
    cleaned = [clean_text(item) for item in raw if clean_text(item)]
    if cleaned:
        return cleaned[:6]
    return [clean_text(value)] if clean_text(value) else ["(empty)"]


def classify_focus_action(branch: str, main_thread: str) -> str:
    branch_l = branch.lower()
    main_l = main_thread.lower()
    if len(branch_l) < 10:
        return "prune"
    if any(k in branch_l for k in ("maybe", "someday", "later", "optional")):
        return "park"
    shared = set(re.findall(r"[a-zA-Z]{4,}", branch_l)) & set(
        re.findall(r"[a-zA-Z]{4,}", main_l)
    )
    if len(shared) >= 2:
        return "expand"
    if len(shared) == 1:
        return "merge"
    if any(k in branch_l for k in ("risk", "blocker", "test")):
        return "expand"
    return "park"


def classify_risk(value: str) -> dict[str, str]:
    return classify_risk_with_policy(
        value=value,
        red_keywords=DEFAULT_RED_KEYWORDS,
        yellow_keywords=DEFAULT_YELLOW_KEYWORDS,
    )


def classify_risk_with_policy(
    value: str, red_keywords: set[str], yellow_keywords: set[str]
) -> dict[str, str]:
    lowered = value.lower()
    red_hits = sorted(k for k in red_keywords if k in lowered)
    yellow_hits = sorted(k for k in yellow_keywords if k in lowered)
    if red_hits:
        return {"level": "red", "reason": f"high-impact keywords: {', '.join(red_hits)}"}
    if yellow_hits:
        return {"level": "yellow", "reason": f"change keywords: {', '.join(yellow_hits)}"}
    return {"level": "green", "reason": "no high-risk keywords detected"}


def stage_capture(ctx: RunContext) -> dict[str, Any]:
    return {"idea": clean_text(ctx.idea), "captured_at": now_iso()}


def stage_sage(capture: dict[str, Any]) -> dict[str, Any]:
    idea = capture["idea"]
    main_thread = first_sentence(idea)
    intent = detect_intent(idea)
    questions = [
        "What is the smallest proof this is moving forward?",
        "What must not break while doing this?",
        "What evidence will be used to confirm success?",
    ]
    confidence = 0.6 if intent == "exploration" else 0.75
    return {
        "main_thread": main_thread,
        "intent": intent,
        "key_questions": questions,
        "confidence": confidence,
    }


def stage_focus(capture: dict[str, Any], sage: dict[str, Any]) -> dict[str, Any]:
    branches = extract_branches(capture["idea"])
    decisions = []
    for branch in branches:
        decisions.append(
            {
                "branch": branch,
                "action": classify_focus_action(branch, sage["main_thread"]),
            }
        )
    return {"decisions": decisions}


def stage_think(capture: dict[str, Any], sage: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    intent = sage["intent"]
    if intent == "debug_or_fix":
        options = [
            "Reproduce issue and capture failing evidence",
            "Patch smallest surface area first",
            "Add regression test before broader cleanup",
        ]
    elif intent == "feature_delivery":
        options = [
            "Define strict MVP boundary",
            "Implement one thin vertical slice",
            "Add quick verification command and short report",
        ]
    else:
        options = [
            "Clarify objective and boundaries",
            "Create minimal executable artifact",
            "Collect validation evidence and summarize",
        ]
    risk = classify_risk_with_policy(
        capture["idea"], set(policy["red_keywords"]), set(policy["yellow_keywords"])
    )
    return {"options": options, "risk_preview": risk}


def stage_plan(sage: dict[str, Any], think: dict[str, Any]) -> dict[str, Any]:
    tasks = [
        {"id": "task-1", "title": "Clarify scope and acceptance checks"},
        {"id": "task-2", "title": "Implement minimal artifact in sandbox-first way"},
        {"id": "task-3", "title": "Run verification and produce short report"},
    ]
    return {
        "tasks": tasks,
        "handoff_summary": f"{sage['intent']} via minimal closed-loop execution",
        "risk": think["risk_preview"],
    }


def stage_blanket(plan: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    risk_level = plan["risk"]["level"]
    confirmation = policy["require_confirmation_by_risk"].get(risk_level, True)
    return {
        "risk_level": risk_level,
        "risk_reason": plan["risk"]["reason"],
        "requires_confirmation": confirmation,
        "allow_auto_confirm_red": policy["allow_auto_confirm_red"],
        "allow_live_adapter_by_risk": policy["allow_live_adapter_by_risk"],
        "worktree_retention": policy["worktree_retention"],
    }


def stage_confirm(
    blanket: dict[str, Any],
    auto_confirm: bool,
    non_interactive: bool,
) -> dict[str, Any]:
    risk_level = blanket["risk_level"]
    if not blanket["requires_confirmation"]:
        return {"approved": True, "mode": "policy_no_confirmation", "risk_level": risk_level}
    if auto_confirm:
        if risk_level == "red" and not blanket["allow_auto_confirm_red"]:
            return {
                "approved": False,
                "mode": "policy_blocked_auto_confirm_red",
                "risk_level": risk_level,
            }
        return {"approved": True, "mode": "auto_confirm", "risk_level": risk_level}
    if non_interactive:
        return {"approved": False, "mode": "non_interactive_default_deny", "risk_level": risk_level}

    print("")
    print("=== bedagent confirm ===")
    print(f"Risk level: {risk_level}")
    print("Tasks:")
    for task in plan["tasks"]:
        print(f"- {task['id']}: {task['title']}")

    if risk_level == "red":
        print('Type "YES" to continue high-risk execution: ', end="", flush=True)
        approved = input().strip() == "YES"
    else:
        print("Approve execution? [y/N]: ", end="", flush=True)
        approved = input().strip().lower() == "y"
    return {"approved": approved, "mode": "interactive", "risk_level": risk_level}


def detect_git_context(repo_root: Path) -> dict[str, str]:
    try:
        top = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        branch = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--abbrev-ref", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        return {"repo_root": top, "branch": branch}
    except subprocess.CalledProcessError:
        return {}


def act_with_simulated_adapter(hands_dir: Path, plan: dict[str, Any]) -> dict[str, Any]:
    task_md = ["# Hands task list", ""]
    for task in plan["tasks"]:
        task_md.append(f"- [ ] {task['id']}: {task['title']}")
    task_md.append("")
    task_md.append("Generated by bedagent MVP sandbox execution.")

    (hands_dir / "TASKS.md").write_text("\n".join(task_md), encoding="utf-8")
    receipt = {
        "executed_at": now_iso(),
        "status": "simulated_success",
        "notes": "Sandbox execution is simulated in MVP.",
    }
    (hands_dir / "execution_receipt.json").write_text(
        json.dumps(receipt, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"status": "simulated_success", "adapter": "simulated", "receipt": receipt}


def act_with_worktree_dry_run_adapter(
    hands_dir: Path, repo_root: Path, run_id: str, plan: dict[str, Any]
) -> dict[str, Any]:
    git_ctx = detect_git_context(repo_root)
    if not git_ctx:
        return {
            "status": "adapter_error",
            "adapter": "worktree-dry-run",
            "reason": f"'{repo_root}' is not a git repository",
        }

    target_branch = f"bedagent/run-{run_id.replace('.', '-').lower()}"
    relative_worktree = f".bedagent/worktrees/{run_id}"
    plan_lines = [
        "# Worktree dry-run plan",
        "",
        "This adapter does not execute commands. It only writes a dry-run plan.",
        "",
        f"- Repo root: {git_ctx['repo_root']}",
        f"- Current branch: {git_ctx['branch']}",
        f"- Suggested target branch: {target_branch}",
        f"- Suggested worktree path: {relative_worktree}",
        "",
        "## Proposed commands",
        "```bash",
        f"git -C \"{git_ctx['repo_root']}\" worktree add -b \"{target_branch}\" \"{relative_worktree}\" \"{git_ctx['branch']}\"",
        f"git -C \"{relative_worktree}\" status --short --branch",
        "```",
        "",
        "## Planned tasks",
    ]
    for task in plan["tasks"]:
        plan_lines.append(f"- [ ] {task['id']}: {task['title']}")
    (hands_dir / "WORKTREE_DRY_RUN_PLAN.md").write_text("\n".join(plan_lines), encoding="utf-8")

    return {
        "status": "dry_run_ready",
        "adapter": "worktree-dry-run",
        "dry_run_plan_path": str(hands_dir / "WORKTREE_DRY_RUN_PLAN.md"),
        "git_context": git_ctx,
    }


def run_command(command: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(command, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def evaluate_live_policy(
    risk_level: str, idea: str, policy: dict[str, Any], allow_side_effects: bool
) -> dict[str, Any]:
    checks = []
    live_by_risk = policy["allow_live_adapter_by_risk"]
    risk_allowed = bool(live_by_risk.get(risk_level, False))
    checks.append(
        {
            "check": "risk_gate",
            "pass": risk_allowed,
            "detail": f"risk={risk_level}, allowed={risk_allowed}",
        }
    )

    blocked_keywords = {k.lower() for k in policy.get("live_adapter_block_keywords", [])}
    lowered_idea = idea.lower()
    hit = sorted(k for k in blocked_keywords if k in lowered_idea)
    keyword_ok = not hit
    checks.append(
        {
            "check": "keyword_gate",
            "pass": keyword_ok,
            "detail": "no blocked keywords matched" if keyword_ok else f"blocked keywords: {', '.join(hit)}",
        }
    )

    side_effect_ok = bool(allow_side_effects)
    checks.append(
        {
            "check": "side_effect_flag",
            "pass": side_effect_ok,
            "detail": "allow-side-effects enabled" if side_effect_ok else "missing --allow-side-effects",
        }
    )
    allowed = risk_allowed and keyword_ok and side_effect_ok
    return {"allowed": allowed, "checks": checks, "blocked_keywords": hit}


def act_with_worktree_live_adapter(
    hands_dir: Path,
    repo_root: Path,
    run_id: str,
    plan: dict[str, Any],
    allow_side_effects: bool,
    risk_level: str,
    policy: dict[str, Any],
    idea: str,
) -> dict[str, Any]:
    explain = evaluate_live_policy(
        risk_level=risk_level, idea=idea, policy=policy, allow_side_effects=allow_side_effects
    )
    if not explain["checks"][0]["pass"]:
        return {
            "status": "policy_blocked_live_risk",
            "adapter": "worktree-live",
            "reason": f"live adapter is disabled for risk level '{risk_level}'",
            "policy_explain": explain,
        }
    if not explain["checks"][1]["pass"]:
        return {
            "status": "policy_blocked_live_keyword",
            "adapter": "worktree-live",
            "reason": f"live adapter blocked by keywords: {', '.join(explain['blocked_keywords'])}",
            "policy_explain": explain,
        }
    if not explain["checks"][2]["pass"]:
        return {
            "status": "policy_blocked_side_effects",
            "adapter": "worktree-live",
            "reason": "use --allow-side-effects to enable real worktree execution",
            "policy_explain": explain,
        }

    git_ctx = detect_git_context(repo_root)
    if not git_ctx:
        return {
            "status": "adapter_error",
            "adapter": "worktree-live",
            "reason": f"'{repo_root}' is not a git repository",
            "policy_explain": explain,
        }

    target_branch = f"bedagent/run-{run_id.replace('.', '-').lower()}"
    worktree_dir = Path(git_ctx["repo_root"]) / ".bedagent" / "worktrees" / run_id
    worktree_dir.parent.mkdir(parents=True, exist_ok=True)

    add_cmd = [
        "git",
        "-C",
        git_ctx["repo_root"],
        "worktree",
        "add",
        "-b",
        target_branch,
        str(worktree_dir),
        git_ctx["branch"],
    ]
    add_code, add_out, add_err = run_command(add_cmd)

    transcript = [
        "# Worktree live adapter transcript",
        "",
        f"- repo_root: {git_ctx['repo_root']}",
        f"- source_branch: {git_ctx['branch']}",
        f"- target_branch: {target_branch}",
        f"- worktree_path: {worktree_dir}",
        "",
        "## command",
        "```bash",
        " ".join(add_cmd),
        "```",
        "",
        f"exit_code: {add_code}",
        "",
        "### stdout",
        "```text",
        add_out.rstrip(),
        "```",
        "",
        "### stderr",
        "```text",
        add_err.rstrip(),
        "```",
        "",
        "## Planned tasks",
    ]
    for task in plan["tasks"]:
        transcript.append(f"- [ ] {task['id']}: {task['title']}")
    (hands_dir / "WORKTREE_LIVE_TRANSCRIPT.md").write_text("\n".join(transcript), encoding="utf-8")

    if add_code != 0:
        return {
            "status": "adapter_error",
            "adapter": "worktree-live",
            "reason": "git worktree add failed",
            "target_branch": target_branch,
            "worktree_path": str(worktree_dir),
            "transcript_path": str(hands_dir / "WORKTREE_LIVE_TRANSCRIPT.md"),
            "policy_explain": explain,
        }

    status_cmd = ["git", "-C", str(worktree_dir), "status", "--short", "--branch"]
    status_code, status_out, status_err = run_command(status_cmd)
    return {
        "status": "worktree_created",
        "adapter": "worktree-live",
        "target_branch": target_branch,
        "worktree_path": str(worktree_dir),
        "status_command_exit_code": status_code,
        "status_output": status_out.strip(),
        "status_error": status_err.strip(),
        "transcript_path": str(hands_dir / "WORKTREE_LIVE_TRANSCRIPT.md"),
        "policy_explain": explain,
    }


def stage_act(
    ctx: RunContext,
    plan: dict[str, Any],
    blanket: dict[str, Any],
    confirm: dict[str, Any],
    sandbox_adapter: str,
    git_repo_root: Path,
    allow_side_effects: bool,
    policy: dict[str, Any],
) -> dict[str, Any]:
    hands_dir = ctx.run_dir / "hands"
    hands_dir.mkdir(parents=True, exist_ok=True)

    if not confirm["approved"]:
        return {
            "status": "skipped",
            "reason": "execution not approved",
            "sandbox_path": str(hands_dir),
        }

    if sandbox_adapter == "simulated":
        result = act_with_simulated_adapter(hands_dir, plan)
    elif sandbox_adapter == "worktree-dry-run":
        result = act_with_worktree_dry_run_adapter(
            hands_dir=hands_dir, repo_root=git_repo_root, run_id=ctx.run_id, plan=plan
        )
    elif sandbox_adapter == "worktree-live":
        result = act_with_worktree_live_adapter(
            hands_dir=hands_dir,
            repo_root=git_repo_root,
            run_id=ctx.run_id,
            plan=plan,
            allow_side_effects=allow_side_effects,
            risk_level=blanket["risk_level"],
            policy=policy,
            idea=ctx.idea,
        )
    else:
        result = {"status": "adapter_error", "adapter": sandbox_adapter, "reason": "unknown adapter"}
    result["sandbox_path"] = str(hands_dir)
    return result


def stage_report(act: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    if act["status"] == "simulated_success":
        sentence = "Closed loop completed: plan approved, sandbox execution simulated, report delivered."
    elif act["status"] == "dry_run_ready":
        sentence = "Closed loop completed: plan approved, worktree dry-run plan generated."
    elif act["status"] == "worktree_created":
        sentence = "Closed loop completed: plan approved, worktree was created with side effects enabled."
    elif act["status"] == "policy_blocked_side_effects":
        sentence = "Closed loop paused: side effects are blocked without explicit allow-side-effects."
    elif act["status"] == "policy_blocked_live_risk":
        sentence = "Closed loop paused: live adapter is blocked for this risk level by policy."
    elif act["status"] == "policy_blocked_live_keyword":
        sentence = "Closed loop paused: live adapter blocked by policy keyword."
    else:
        sentence = "Closed loop paused: waiting for explicit execution approval."
    return {"pillow_note": sentence, "risk_level": plan["risk"]["level"]}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_blanket_policy(policy_path: Path) -> dict[str, Any]:
    default_policy = {
        "red_keywords": sorted(DEFAULT_RED_KEYWORDS),
        "yellow_keywords": sorted(DEFAULT_YELLOW_KEYWORDS),
        "allow_auto_confirm_red": False,
        "require_confirmation_by_risk": {"green": False, "yellow": True, "red": True},
        "allow_live_adapter_by_risk": {"green": True, "yellow": True, "red": False},
        "live_adapter_block_keywords": ["production", "prod", "billing", "payment"],
        "worktree_retention": {"ttl_hours": 24, "max_keep": 5},
    }
    if not policy_path.exists():
        return default_policy
    loaded = json.loads(policy_path.read_text(encoding="utf-8"))
    merged = dict(default_policy)
    merged.update(loaded)
    merged["require_confirmation_by_risk"] = {
        **default_policy["require_confirmation_by_risk"],
        **loaded.get("require_confirmation_by_risk", {}),
    }
    merged["allow_live_adapter_by_risk"] = {
        **default_policy["allow_live_adapter_by_risk"],
        **loaded.get("allow_live_adapter_by_risk", {}),
    }
    merged["worktree_retention"] = {
        **default_policy["worktree_retention"],
        **loaded.get("worktree_retention", {}),
    }
    return merged


def append_memory_entry(journal_path: Path, entry: dict[str, Any]) -> dict[str, Any]:
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(entry, ensure_ascii=False)
    with journal_path.open("a", encoding="utf-8") as fp:
        fp.write(line + "\n")
    return {"journal_path": str(journal_path), "entry_appended": True}


def stage_memory(
    journal_path: Path, run_id: str, capture: dict[str, Any], report: dict[str, Any], act: dict[str, Any]
) -> dict[str, Any]:
    entry = {
        "recorded_at": now_iso(),
        "run_id": run_id,
        "idea": capture["idea"],
        "risk_level": report["risk_level"],
        "act_status": act["status"],
        "pillow_note": report["pillow_note"],
    }
    result = append_memory_entry(journal_path=journal_path, entry=entry)
    result["entry"] = entry
    return result


def read_memory_entries(journal_path: Path, limit: int) -> list[dict[str, Any]]:
    if not journal_path.exists():
        return []
    lines = [line for line in journal_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    entries: list[dict[str, Any]] = []
    for raw in lines[-limit:]:
        try:
            entries.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
    return entries


def summarize_recent_entries(entries: list[dict[str, Any]]) -> dict[str, Any]:
    stopwords = {
        "the",
        "and",
        "for",
        "with",
        "that",
        "this",
        "from",
        "into",
        "need",
        "update",
        "implement",
        "prepare",
    }
    counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    for entry in entries:
        status = str(entry.get("act_status", "unknown"))
        status_counts[status] = status_counts.get(status, 0) + 1
        idea = str(entry.get("idea", "")).lower()
        for token in re.findall(r"[a-z]{4,}", idea):
            if token in stopwords:
                continue
            counts[token] = counts.get(token, 0) + 1
    top_topics = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:5]
    return {"top_topics": [{"token": k, "count": v} for k, v in top_topics], "status_counts": status_counts}


def tokenize_text(value: str) -> list[str]:
    return re.findall(r"[a-z]{3,}", value.lower())


def compute_idf(doc_tokens: list[list[str]]) -> dict[str, float]:
    n = len(doc_tokens)
    if n == 0:
        return {}
    df: dict[str, int] = {}
    for tokens in doc_tokens:
        for token in set(tokens):
            df[token] = df.get(token, 0) + 1
    return {token: math.log((1 + n) / (1 + count)) + 1 for token, count in df.items()}


def vectorize(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    tf: dict[str, int] = {}
    for token in tokens:
        tf[token] = tf.get(token, 0) + 1
    total = sum(tf.values()) or 1
    return {token: (count / total) * idf.get(token, 0.0) for token, count in tf.items()}


def cosine_similarity(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(left[k] * right.get(k, 0.0) for k in left)
    lnorm = math.sqrt(sum(v * v for v in left.values()))
    rnorm = math.sqrt(sum(v * v for v in right.values()))
    if lnorm == 0 or rnorm == 0:
        return 0.0
    return dot / (lnorm * rnorm)


def semantic_memory_search(entries: list[dict[str, Any]], query: str, top_k: int) -> list[dict[str, Any]]:
    if not entries:
        return []
    docs = [tokenize_text(str(entry.get("idea", "")) + " " + str(entry.get("pillow_note", ""))) for entry in entries]
    query_tokens = tokenize_text(query)
    idf = compute_idf(docs + [query_tokens])
    qvec = vectorize(query_tokens, idf)
    ranked = []
    for entry, tokens in zip(entries, docs):
        dvec = vectorize(tokens, idf)
        score = cosine_similarity(qvec, dvec)
        ranked.append({"score": round(score, 6), "entry": entry})
    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked[: max(1, top_k)]


def build_recap(journal_path: Path, limit: int) -> dict[str, Any]:
    entries = read_memory_entries(journal_path, limit=limit)
    by_risk: dict[str, int] = {"green": 0, "yellow": 0, "red": 0}
    for entry in entries:
        risk = entry.get("risk_level", "unknown")
        by_risk[risk] = by_risk.get(risk, 0) + 1
    latest = entries[-1] if entries else None
    return {
        "journal_path": str(journal_path),
        "total_loaded": len(entries),
        "risk_breakdown": by_risk,
        "summary": summarize_recent_entries(entries),
        "latest": latest,
        "recent": entries,
    }


def list_managed_worktrees(worktree_root: Path) -> list[dict[str, Any]]:
    if not worktree_root.exists():
        return []
    items: list[dict[str, Any]] = []
    for child in sorted(worktree_root.iterdir()):
        if not child.is_dir():
            continue
        items.append(
            {
                "run_id": child.name,
                "path": str(child),
                "has_git_dir": (child / ".git").exists(),
                "mtime_epoch": child.stat().st_mtime,
            }
        )
    return items


def parse_run_id_datetime(run_id: str) -> datetime | None:
    match = re.match(r"^(\d{8}T\d{6})\.\d{6}Z-[0-9a-f]{6}$", run_id)
    if not match:
        return None
    try:
        base = datetime.strptime(match.group(1), "%Y%m%dT%H%M%S")
        return base.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def select_worktree_cleanup_candidates(
    items: list[dict[str, Any]], now: datetime, ttl_hours: int, max_keep: int
) -> list[dict[str, Any]]:
    if not items:
        return []
    with_dt = []
    for item in items:
        dt = parse_run_id_datetime(item["run_id"])
        if dt is None:
            dt = datetime.fromtimestamp(item["mtime_epoch"], tz=timezone.utc)
        with_dt.append({**item, "run_dt": dt})

    sorted_items = sorted(with_dt, key=lambda item: item["run_dt"], reverse=True)
    keep_set = {item["path"] for item in sorted_items[: max(0, max_keep)]}
    cutoff = now - timedelta(hours=max(0, ttl_hours))

    candidates = []
    for item in with_dt:
        ttl_expired = item["run_dt"] < cutoff
        over_max = item["path"] not in keep_set
        if ttl_expired or over_max:
            item["cleanup_reason"] = {
                "ttl_expired": ttl_expired,
                "over_max_keep": over_max,
            }
            candidates.append(item)
    return sorted(candidates, key=lambda item: item["run_dt"])


def remove_worktree(repo_root: Path, worktree_path: Path, force: bool) -> tuple[int, str, str]:
    command = ["git", "-C", str(repo_root), "worktree", "remove"]
    if force:
        command.append("--force")
    command.append(str(worktree_path))
    return run_command(command)


def run_closed_loop(
    idea: str,
    output_root: Path,
    auto_confirm: bool,
    non_interactive: bool,
    blanket_policy_path: Path,
    sandbox_adapter: str,
    memory_journal_path: Path,
    git_repo_root: Path,
    allow_side_effects: bool,
) -> dict[str, Any]:
    run_id = build_run_id()
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    ctx = RunContext(run_id=run_id, run_dir=run_dir, idea=idea)
    policy = load_blanket_policy(blanket_policy_path)

    capture = stage_capture(ctx)
    sage = stage_sage(capture)
    focus = stage_focus(capture, sage)
    think = stage_think(capture, sage, policy=policy)
    plan = stage_plan(sage, think)
    blanket = stage_blanket(plan, policy)
    confirm = stage_confirm(
        blanket=blanket, auto_confirm=auto_confirm, non_interactive=non_interactive
    )
    act = stage_act(
        ctx,
        plan,
        blanket,
        confirm,
        sandbox_adapter=sandbox_adapter,
        git_repo_root=git_repo_root,
        allow_side_effects=allow_side_effects,
        policy=policy,
    )
    report = stage_report(act, plan)
    memory = stage_memory(
        journal_path=memory_journal_path,
        run_id=run_id,
        capture=capture,
        report=report,
        act=act,
    )

    manifest = {
        "run_id": run_id,
        "generated_at": now_iso(),
        "flow": (
            "Capture -> Sage -> Focus -> Think -> Plan -> Blanket -> Confirm -> "
            "Act Sandbox -> Short Report -> Memory"
        ),
        "config": {
            "blanket_policy_path": str(blanket_policy_path),
            "sandbox_adapter": sandbox_adapter,
            "memory_journal_path": str(memory_journal_path),
            "git_repo_root": str(git_repo_root),
            "allow_side_effects": allow_side_effects,
        },
        "capture": capture,
        "sage": sage,
        "focus": focus,
        "think": think,
        "plan": plan,
        "blanket": blanket,
        "confirm": confirm,
        "act": act,
        "report": report,
        "memory": memory,
    }
    write_json(run_dir / "manifest.json", manifest)
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="bedagent-mvp",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent(
            """\
            Run bedagent minimal closed-loop MVP.
            Example:
              python3 mvp/bedagent_mvp.py run --idea "Implement docs index and verify site links" --auto-confirm
            """
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="run minimal closed-loop")
    run.add_argument("--idea", help="input thought/idea text")
    run.add_argument("--idea-file", help="path to text file containing idea")
    run.add_argument(
        "--output-root",
        default=".bedagent/runs",
        help="directory where run artifacts are written",
    )
    run.add_argument(
        "--auto-confirm",
        action="store_true",
        help="approve execution automatically",
    )
    run.add_argument(
        "--non-interactive",
        action="store_true",
        help="never ask for prompt; deny execution unless --auto-confirm is given",
    )
    run.add_argument(
        "--blanket-policy",
        default="mvp/blanket_policy.json",
        help="path to blanket policy JSON",
    )
    run.add_argument(
        "--sandbox-adapter",
        choices=["simulated", "worktree-dry-run", "worktree-live"],
        default="simulated",
        help="sandbox adapter for Act stage",
    )
    run.add_argument(
        "--memory-journal",
        default=".bedagent/memory/journal.ndjson",
        help="append-only memory journal path",
    )
    run.add_argument(
        "--git-repo-root",
        default=".",
        help="repository root path for worktree-dry-run adapter",
    )
    run.add_argument(
        "--allow-side-effects",
        action="store_true",
        help="allow side effects for adapters that mutate git state (e.g. worktree-live)",
    )

    recap = sub.add_parser("recap", help="show memory recap from journal")
    recap.add_argument(
        "--memory-journal",
        default=".bedagent/memory/journal.ndjson",
        help="append-only memory journal path",
    )
    recap.add_argument(
        "--limit",
        default=5,
        type=int,
        help="number of recent entries to include",
    )

    memory_search = sub.add_parser("memory-search", help="semantic search in memory journal")
    memory_search.add_argument("--query", required=True, help="query text for memory retrieval")
    memory_search.add_argument(
        "--memory-journal",
        default=".bedagent/memory/journal.ndjson",
        help="append-only memory journal path",
    )
    memory_search.add_argument(
        "--limit",
        default=50,
        type=int,
        help="how many recent journal entries to search",
    )
    memory_search.add_argument(
        "--top-k",
        default=3,
        type=int,
        help="number of results to return",
    )

    worktree = sub.add_parser("worktree", help="manage bedagent-managed worktrees")
    worktree.add_argument(
        "action",
        choices=["list", "cleanup"],
        help="list or cleanup managed worktrees",
    )
    worktree.add_argument(
        "--git-repo-root",
        default=".",
        help="repository root path for git worktree operations",
    )
    worktree.add_argument(
        "--blanket-policy",
        default="mvp/blanket_policy.json",
        help="policy file used for retention settings",
    )
    worktree.add_argument(
        "--worktree-root",
        default=".bedagent/worktrees",
        help="managed worktree root path",
    )
    worktree.add_argument(
        "--run-id",
        help="specific run id to cleanup (required unless --all is set)",
    )
    worktree.add_argument(
        "--all",
        action="store_true",
        help="cleanup all managed worktrees",
    )
    worktree.add_argument(
        "--force",
        action="store_true",
        help="use --force when removing worktrees",
    )
    worktree.add_argument(
        "--allow-side-effects",
        action="store_true",
        help="required to run cleanup actions",
    )
    worktree.add_argument(
        "--apply-retention",
        action="store_true",
        help="cleanup by retention policy (uses TTL and max_keep from blanket policy)",
    )

    return parser.parse_args()


def load_idea(args: argparse.Namespace) -> str:
    if bool(args.idea) == bool(args.idea_file):
        raise ValueError("Provide exactly one of --idea or --idea-file.")
    if args.idea:
        return args.idea
    path = Path(args.idea_file)
    return path.read_text(encoding="utf-8")


def main() -> int:
    args = parse_args()
    if args.command == "recap":
        recap = build_recap(Path(args.memory_journal), limit=max(1, args.limit))
        print("")
        print("=== bedagent memory recap ===")
        print(f"journal: {recap['journal_path']}")
        print(f"loaded: {recap['total_loaded']}")
        print(f"risk_breakdown: {json.dumps(recap['risk_breakdown'], ensure_ascii=False)}")
        print(f"status_counts: {json.dumps(recap['summary']['status_counts'], ensure_ascii=False)}")
        top_tokens = [f"{item['token']}:{item['count']}" for item in recap["summary"]["top_topics"]]
        print(f"top_topics: {', '.join(top_tokens) if top_tokens else '-'}")
        latest = recap["latest"]
        if latest:
            print(f"latest_run: {latest.get('run_id', '-')}")
            print(f"latest_note: {latest.get('pillow_note', '-')}")
        else:
            print("latest_run: none")
        return 0

    if args.command == "memory-search":
        entries = read_memory_entries(Path(args.memory_journal), limit=max(1, args.limit))
        hits = semantic_memory_search(entries=entries, query=args.query, top_k=max(1, args.top_k))
        print("")
        print("=== bedagent memory semantic search ===")
        print(f"journal: {args.memory_journal}")
        print(f"query: {args.query}")
        print(f"scanned: {len(entries)}")
        print(f"returned: {len(hits)}")
        for idx, hit in enumerate(hits, start=1):
            entry = hit["entry"]
            print(
                f"{idx}. score={hit['score']} run_id={entry.get('run_id', '-')}"
                f" risk={entry.get('risk_level', '-')} status={entry.get('act_status', '-')}"
            )
            print(f"   idea: {entry.get('idea', '-')}")
        return 0

    if args.command == "worktree":
        repo_root = Path(args.git_repo_root)
        worktree_root = Path(args.worktree_root)
        policy = load_blanket_policy(Path(args.blanket_policy))
        if args.action == "list":
            items = list_managed_worktrees(worktree_root)
            print("")
            print("=== bedagent managed worktrees ===")
            print(f"root: {worktree_root}")
            print(f"count: {len(items)}")
            for item in items:
                print(f"- {item['run_id']}: {item['path']}")
            return 0

        if args.action == "cleanup":
            if not args.allow_side_effects:
                print("Policy block: pass --allow-side-effects to cleanup worktrees.")
                return 2
            if not args.apply_retention and not args.all and not args.run_id:
                print("Input error: provide --run-id or --all for cleanup.")
                return 2
            targets = []
            if args.apply_retention:
                items = list_managed_worktrees(worktree_root)
                retention = policy["worktree_retention"]
                candidates = select_worktree_cleanup_candidates(
                    items=items,
                    now=datetime.now(timezone.utc),
                    ttl_hours=int(retention["ttl_hours"]),
                    max_keep=int(retention["max_keep"]),
                )
                targets = [Path(item["path"]) for item in candidates]
                print("")
                print("=== bedagent worktree retention plan ===")
                print(
                    f"ttl_hours={retention['ttl_hours']} max_keep={retention['max_keep']}"
                    f" candidates={len(targets)}"
                )
                for item in candidates:
                    reason = item["cleanup_reason"]
                    print(
                        f"- candidate: {item['path']} "
                        f"(ttl_expired={reason['ttl_expired']}, over_max_keep={reason['over_max_keep']})"
                    )
            elif args.all:
                targets = [Path(item["path"]) for item in list_managed_worktrees(worktree_root)]
            else:
                targets = [worktree_root / args.run_id]
            removed = []
            failed = []
            for target in targets:
                code, out, err = remove_worktree(repo_root=repo_root, worktree_path=target, force=args.force)
                if code == 0:
                    removed.append({"path": str(target), "stdout": out.strip()})
                else:
                    failed.append({"path": str(target), "stderr": err.strip(), "stdout": out.strip()})
            print("")
            print("=== bedagent worktree cleanup ===")
            print(f"removed: {len(removed)}")
            print(f"failed: {len(failed)}")
            for item in removed:
                print(f"- removed: {item['path']}")
            for item in failed:
                print(f"- failed: {item['path']} ({item['stderr'] or 'unknown error'})")
            return 0 if not failed else 1

        raise ValueError(f"Unsupported worktree action: {args.action}")

    if args.command != "run":
        raise ValueError(f"Unsupported command: {args.command}")

    try:
        idea = load_idea(args)
    except Exception as exc:  # pragma: no cover - CLI guardrail
        print(f"Input error: {exc}")
        return 2

    manifest = run_closed_loop(
        idea=idea,
        output_root=Path(args.output_root),
        auto_confirm=args.auto_confirm,
        non_interactive=args.non_interactive,
        blanket_policy_path=Path(args.blanket_policy),
        sandbox_adapter=args.sandbox_adapter,
        memory_journal_path=Path(args.memory_journal),
        git_repo_root=Path(args.git_repo_root),
        allow_side_effects=args.allow_side_effects,
    )

    print("")
    print("=== bedagent MVP result ===")
    print(f"run_id: {manifest['run_id']}")
    print(f"risk: {manifest['plan']['risk']['level']}")
    print(f"approved: {manifest['confirm']['approved']}")
    print(f"act_status: {manifest['act']['status']}")
    print(f"pillow_note: {manifest['report']['pillow_note']}")
    print(f"manifest: {Path(args.output_root) / manifest['run_id'] / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
