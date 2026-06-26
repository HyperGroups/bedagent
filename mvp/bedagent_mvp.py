#!/usr/bin/env python3
"""bedagent MVP: minimal closed-loop controller prototype.

Flow:
Capture -> Sage -> Focus -> Think -> Plan -> Confirm -> Act Sandbox -> Report
"""

from __future__ import annotations

import argparse
import json
import re
import textwrap
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RED_KEYWORDS = {
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

YELLOW_KEYWORDS = {
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
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


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
    lowered = value.lower()
    red_hits = sorted(k for k in RED_KEYWORDS if k in lowered)
    yellow_hits = sorted(k for k in YELLOW_KEYWORDS if k in lowered)
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


def stage_think(capture: dict[str, Any], sage: dict[str, Any]) -> dict[str, Any]:
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
    risk = classify_risk(capture["idea"])
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


def stage_confirm(plan: dict[str, Any], auto_confirm: bool, non_interactive: bool) -> dict[str, Any]:
    risk_level = plan["risk"]["level"]
    if auto_confirm:
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


def stage_act(ctx: RunContext, plan: dict[str, Any], confirm: dict[str, Any]) -> dict[str, Any]:
    hands_dir = ctx.run_dir / "hands"
    hands_dir.mkdir(parents=True, exist_ok=True)

    if not confirm["approved"]:
        return {
            "status": "skipped",
            "reason": "execution not approved",
            "sandbox_path": str(hands_dir),
        }

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
    return {"status": "simulated_success", "sandbox_path": str(hands_dir), "receipt": receipt}


def stage_report(act: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    if act["status"] == "simulated_success":
        sentence = "Closed loop completed: plan approved, sandbox execution simulated, report delivered."
    else:
        sentence = "Closed loop paused: waiting for explicit execution approval."
    return {"pillow_note": sentence, "risk_level": plan["risk"]["level"]}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run_closed_loop(idea: str, output_root: Path, auto_confirm: bool, non_interactive: bool) -> dict[str, Any]:
    run_id = build_run_id()
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    ctx = RunContext(run_id=run_id, run_dir=run_dir, idea=idea)

    capture = stage_capture(ctx)
    sage = stage_sage(capture)
    focus = stage_focus(capture, sage)
    think = stage_think(capture, sage)
    plan = stage_plan(sage, think)
    confirm = stage_confirm(plan, auto_confirm=auto_confirm, non_interactive=non_interactive)
    act = stage_act(ctx, plan, confirm)
    report = stage_report(act, plan)

    manifest = {
        "run_id": run_id,
        "generated_at": now_iso(),
        "flow": "Capture -> Sage -> Focus -> Think -> Plan -> Confirm -> Act Sandbox -> Short Report",
        "capture": capture,
        "sage": sage,
        "focus": focus,
        "think": think,
        "plan": plan,
        "confirm": confirm,
        "act": act,
        "report": report,
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
