"""bedagent story session: oral dictation loop with Sage dialogue."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

STORY_FLOW = (
    "Oral Capture -> Sage -> Focus -> Blanket -> Synthesize -> Dialogue -> "
    "Draft Sandbox -> Bible -> Memory"
)
BIBLE_SCHEMA_VERSION = "1.0.0"
DEFAULT_STORY_POLICY_PATH = Path(__file__).with_name("story_blanket_policy.json")

STORY_CATEGORIES = ("character", "plot", "world", "dialogue", "theme", "misc")

CATEGORY_HINTS: dict[str, tuple[str, ...]] = {
    "character": (
        "主角",
        "角色",
        "名叫",
        "性格",
        "他",
        "她",
        "protagonist",
        "character",
        "hero",
        "villain",
    ),
    "plot": (
        "然后",
        "突然",
        "结局",
        "转折",
        "冲突",
        "发现",
        "twist",
        "conflict",
        "because",
        "then",
        "finally",
    ),
    "world": (
        "世界",
        "背景",
        "时代",
        "设定",
        "文明",
        "星球",
        "world",
        "setting",
        "planet",
        "city",
        "future",
    ),
    "dialogue": ('"', "'", "说", "道", "问", "回答", "said", "asked", "whisper"),
    "theme": ("主题", "隐喻", "象征", "意义", "theme", "metaphor", "meaning"),
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def normalize_fragment(value: str) -> str:
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in value.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def first_sentence(value: str, max_len: int = 140) -> str:
    text = clean_text(value)
    if not text:
        return "（尚未口述）"
    parts = re.split(r"[。！？.!?]", text)
    summary = parts[0].strip() if parts else text
    if len(summary) <= max_len:
        return summary
    return summary[: max_len - 3].rstrip() + "..."


def token_set(value: str) -> set[str]:
    return set(re.findall(r"[\u4e00-\u9fff]{2,}|[a-zA-Z]{4,}", value.lower()))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def append_ndjson(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default.copy()
    return json.loads(path.read_text(encoding="utf-8"))


def load_story_blanket_policy(path: Path | None = None) -> dict[str, Any]:
    policy_path = path or DEFAULT_STORY_POLICY_PATH
    payload = json.loads(policy_path.read_text(encoding="utf-8"))
    payload.setdefault("red_keywords", [])
    payload.setdefault("yellow_keywords", [])
    payload.setdefault("require_confirmation_by_risk", {"green": False, "yellow": True, "red": True})
    payload.setdefault("require_confirmation_on_main_thread_pivot", True)
    payload.setdefault("main_thread_pivot_min_turns", 2)
    payload.setdefault("allow_auto_confirm_red", False)
    return payload


def empty_bible(title: str = "未命名故事") -> dict[str, Any]:
    return {
        "schema_version": BIBLE_SCHEMA_VERSION,
        "title": title,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "main_thread": "（等待第一段口述）",
        "characters": [],
        "plot_threads": [],
        "setting": {"time": "", "place": "", "notes": []},
        "timeline": [],
        "open_questions": [],
        "resolved_questions": [],
        "recent_recap": "",
        "fragment_count": 0,
        "turn_count": 0,
        "drafts": {"chapter_count": 0, "last_draft_at": "", "last_export_at": ""},
    }


def ensure_bible_schema(bible: dict[str, Any]) -> dict[str, Any]:
    merged = empty_bible(bible.get("title", "未命名故事"))
    merged.update(bible)
    if not merged.get("setting"):
        merged["setting"] = {"time": "", "place": "", "notes": []}
    if not merged.get("drafts"):
        merged["drafts"] = {"chapter_count": 0, "last_draft_at": "", "last_export_at": ""}
    merged["schema_version"] = BIBLE_SCHEMA_VERSION
    return merged


def default_session(title: str = "未命名故事") -> dict[str, Any]:
    return {
        "title": title,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "mode": "oral_dictation",
        "flow": STORY_FLOW,
        "turn_count": 0,
        "fragment_count": 0,
    }


def detect_story_category(fragment: str) -> str:
    lower = fragment.lower()
    scores: dict[str, int] = {key: 0 for key in STORY_CATEGORIES}
    for category, hints in CATEGORY_HINTS.items():
        for hint in hints:
            if hint.lower() in lower:
                scores[category] += 1
    best = max(scores.items(), key=lambda item: item[1])
    if best[1] == 0:
        return "misc"
    return best[0]


def extract_story_threads(fragment: str) -> list[str]:
    raw = re.split(r"[\n]+|；|;", fragment)
    cleaned = [clean_text(item) for item in raw if clean_text(item)]
    if cleaned:
        return cleaned[:8]
    text = clean_text(fragment)
    return [text] if text else ["（空片段）"]


def extract_character_hints(fragment: str) -> list[str]:
    hints: list[str] = []
    patterns = [
        r"名叫([\u4e00-\u9fffA-Za-z·]{1,12})",
        r"叫([\u4e00-\u9fffA-Za-z·]{1,12})",
        r"([\u4e00-\u9fffA-Za-z·]{1,12})是主角",
        r"protagonist ([A-Za-z·]{2,20})",
        r"character ([A-Za-z·]{2,20})",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, fragment, flags=re.IGNORECASE):
            name = clean_text(match.group(1))
            if name and name not in hints:
                hints.append(name)
    return hints[:5]


def classify_story_focus_action(thread: str, main_thread: str) -> str:
    thread_l = thread.lower()
    main_l = main_thread.lower()
    if len(thread_l) < 8:
        return "prune"
    if any(k in thread_l for k in ("也许", "可能", "或者", "maybe", "perhaps", "someday")):
        return "park"
    shared = token_set(thread_l) & token_set(main_l)
    if len(shared) >= 2:
        return "expand"
    if len(shared) == 1:
        return "merge"
    if any(k in thread_l for k in ("冲突", "转折", "秘密", "真相", "twist", "conflict", "secret")):
        return "expand"
    return "park"


def propose_main_thread(fragment: str, bible: dict[str, Any], category: str) -> str:
    recap = first_sentence(fragment)
    current = bible.get("main_thread") or "（等待第一段口述）"
    if current.startswith("（等待"):
        return recap
    if category in {"plot", "character", "theme"}:
        return recap
    return current


def detect_main_thread_pivot(old_thread: str, new_thread: str) -> bool:
    if old_thread.startswith("（等待"):
        return False
    old_tokens = token_set(old_thread)
    new_tokens = token_set(new_thread)
    if not old_tokens or not new_tokens:
        return False
    overlap = len(old_tokens & new_tokens) / max(len(old_tokens | new_tokens), 1)
    return overlap < 0.25


def classify_story_blanket_risk(
    fragment: str,
    bible: dict[str, Any],
    proposed_main_thread: str,
    policy: dict[str, Any],
) -> dict[str, Any]:
    lowered = fragment.lower()
    red_hits = sorted(k for k in policy["red_keywords"] if k.lower() in lowered)
    yellow_hits = sorted(k for k in policy["yellow_keywords"] if k.lower() in lowered)
    pivot = False
    oral_main = first_sentence(fragment)
    if policy.get("require_confirmation_on_main_thread_pivot") and int(bible.get("turn_count", 0)) >= int(
        policy.get("main_thread_pivot_min_turns", 2)
    ):
        pivot = detect_main_thread_pivot(bible.get("main_thread", ""), oral_main) or detect_main_thread_pivot(
            bible.get("main_thread", ""), proposed_main_thread
        )

    if red_hits:
        level = "red"
        reason = f"story-breaking keywords: {', '.join(red_hits)}"
    elif yellow_hits or pivot:
        level = "yellow"
        parts = []
        if yellow_hits:
            parts.append(f"change keywords: {', '.join(yellow_hits)}")
        if pivot:
            parts.append("main thread pivot detected")
        reason = "; ".join(parts)
    else:
        level = "green"
        reason = "routine oral fragment"

    return {
        "level": level,
        "reason": reason,
        "red_hits": red_hits,
        "yellow_hits": yellow_hits,
        "main_thread_pivot": pivot,
        "proposed_main_thread": proposed_main_thread,
    }


def stage_story_blanket(risk: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    level = risk["level"]
    confirmation = policy["require_confirmation_by_risk"].get(level, True)
    return {
        "risk_level": level,
        "risk_reason": risk["reason"],
        "requires_confirmation": confirmation,
        "allow_auto_confirm_red": policy.get("allow_auto_confirm_red", False),
        "main_thread_pivot": risk["main_thread_pivot"],
    }


def confirm_story_blanket(
    blanket: dict[str, Any],
    risk: dict[str, Any],
    auto_confirm: bool,
    non_interactive: bool,
    input_fn: Callable[[str], str] = input,
) -> dict[str, Any]:
    level = blanket["risk_level"]
    if not blanket["requires_confirmation"]:
        return {"approved": True, "mode": "policy_no_confirmation", "risk_level": level}
    if auto_confirm:
        if level == "red" and not blanket["allow_auto_confirm_red"]:
            return {
                "approved": False,
                "mode": "policy_blocked_auto_confirm_red",
                "risk_level": level,
            }
        return {"approved": True, "mode": "auto_confirm", "risk_level": level}
    if non_interactive:
        return {"approved": False, "mode": "non_interactive_default_deny", "risk_level": level}

    print("")
    print("=== bedagent story blanket ===")
    print(f"Risk level: {level}")
    print(f"Reason: {blanket['risk_reason']}")
    if risk.get("main_thread_pivot"):
        print(f"Proposed main thread: {risk['proposed_main_thread']}")
    if level == "red":
        print('大改需要明确确认。Type "YES" to continue: ', end="", flush=True)
        approved = input_fn("").strip() == "YES"
    else:
        print("Apply this story change? [y/N]: ", end="", flush=True)
        approved = input_fn("").strip().lower() == "y"
    return {"approved": approved, "mode": "interactive", "risk_level": level}


def stage_story_sage(fragment: str, bible: dict[str, Any]) -> dict[str, Any]:
    category = detect_story_category(fragment)
    recap = first_sentence(fragment)
    main_thread = propose_main_thread(fragment, bible, category)

    questions = [
        "这段口述改变了主线冲突吗？",
        "这是现在发生，还是回忆/伏笔？",
        "读者此刻最需要知道的一个细节是什么？",
    ]
    if category == "character":
        questions[0] = "这个角色的动机是什么，为什么现在出现？"
    elif category == "world":
        questions[0] = "这个设定会如何限制或推动人物选择？"
    elif category == "dialogue":
        questions[0] = "这句对白是在掩饰、试探，还是坦白？"

    return {
        "category": category,
        "recap": recap,
        "main_thread": main_thread,
        "key_questions": questions,
        "confidence": 0.72 if category != "misc" else 0.55,
    }


def stage_story_focus(fragment: str, sage: dict[str, Any]) -> dict[str, Any]:
    threads = extract_story_threads(fragment)
    decisions = []
    for thread in threads:
        decisions.append(
            {
                "thread": thread,
                "category": detect_story_category(thread),
                "action": classify_story_focus_action(thread, sage["main_thread"]),
            }
        )
    return {"decisions": decisions}


def infer_character_extras(fragment: str, name: str) -> dict[str, str]:
    extras = {"role": "", "desire": "", "conflict": ""}
    if any(key in fragment for key in ("主角", "主人公", "protagonist")):
        extras["role"] = "protagonist"
    elif any(key in fragment for key in ("反派", "对手", "villain", "antagonist")):
        extras["role"] = "antagonist"
    elif any(key in fragment for key in ("同伴", "搭档", "盟友", "ally")):
        extras["role"] = "ally"
    escaped = re.escape(name)
    desire = re.search(
        rf"{escaped}.{{0,16}}(?:想要|渴望|想)([^。！？\n]{{2,30}})",
        fragment,
    )
    if desire:
        extras["desire"] = clean_text(desire.group(1))
    conflict = re.search(
        rf"{escaped}.{{0,16}}(?:害怕|瞒着|冲突|对抗)([^。！？\n]{{2,30}})",
        fragment,
    )
    if conflict:
        extras["conflict"] = clean_text(conflict.group(1))
    return extras


def upsert_character(
    bible: dict[str, Any],
    name: str,
    note: str,
    extras: dict[str, str] | None = None,
) -> None:
    extras = extras or {}
    for item in bible["characters"]:
        if item["name"] == name:
            if note and note not in item["notes"]:
                item["notes"].append(note)
            for key in ("role", "desire", "conflict"):
                if extras.get(key) and not item.get(key):
                    item[key] = extras[key]
            return
    bible["characters"].append(
        {
            "name": name,
            "notes": [note] if note else [],
            "role": extras.get("role", ""),
            "desire": extras.get("desire", ""),
            "conflict": extras.get("conflict", ""),
        }
    )


def upsert_plot_thread(bible: dict[str, Any], label: str, action: str, note: str) -> None:
    status = "active" if action == "expand" else "parked" if action == "park" else "merged"
    for item in bible["plot_threads"]:
        if item["label"] == label:
            item["status"] = status
            if note and note not in item["notes"]:
                item["notes"].append(note)
            return
    bible["plot_threads"].append({"label": label, "status": status, "notes": [note] if note else []})


def stage_story_synthesize(
    fragment: str,
    sage: dict[str, Any],
    focus: dict[str, Any],
    bible: dict[str, Any],
    turn_number: int,
) -> dict[str, Any]:
    updated = ensure_bible_schema(json.loads(json.dumps(bible, ensure_ascii=False)))
    updated["main_thread"] = sage["main_thread"]
    updated["updated_at"] = now_iso()
    updated["recent_recap"] = sage["recap"]
    updated["fragment_count"] = int(updated.get("fragment_count", 0)) + 1
    updated["turn_count"] = turn_number

    for name in extract_character_hints(fragment):
        upsert_character(updated, name, sage["recap"], infer_character_extras(fragment, name))

    for decision in focus["decisions"]:
        if decision["action"] != "prune":
            upsert_plot_thread(updated, decision["thread"], decision["action"], sage["recap"])

    category = sage["category"]
    if category == "world":
        if not updated["setting"]["place"]:
            updated["setting"]["place"] = first_sentence(fragment, max_len=80)
        if sage["recap"] not in updated["setting"]["notes"]:
            updated["setting"]["notes"].append(sage["recap"])
            updated["setting"]["notes"] = updated["setting"]["notes"][-8:]

    timeline = list(updated.get("timeline", []))
    timeline.append(
        {
            "turn": turn_number,
            "recorded_at": now_iso(),
            "kind": "fragment",
            "category": category,
            "text": sage["recap"],
        }
    )
    updated["timeline"] = timeline[-40:]

    open_questions = list(updated.get("open_questions", []))
    for question in sage["key_questions"]:
        if question not in open_questions:
            open_questions.append(question)
    updated["open_questions"] = open_questions[-12:]

    return updated


def format_focus_line(focus: dict[str, Any]) -> str:
    groups: dict[str, list[str]] = {"expand": [], "park": [], "merge": [], "prune": []}
    for decision in focus["decisions"]:
        action = decision["action"]
        label = first_sentence(decision["thread"], max_len=36)
        groups[action].append(f"「{label}」")
    parts = []
    if groups["expand"]:
        parts.append("展开 " + " · ".join(groups["expand"]))
    if groups["park"]:
        parts.append("暂存 " + " · ".join(groups["park"]))
    if groups["merge"]:
        parts.append("合并 " + " · ".join(groups["merge"]))
    if groups["prune"]:
        parts.append("剪掉 " + " · ".join(groups["prune"]))
    return " · ".join(parts) if parts else "（暂无分支变化）"


def build_agent_reply(
    sage: dict[str, Any],
    focus: dict[str, Any],
    bible: dict[str, Any],
    blanket: dict[str, Any] | None = None,
    confirm: dict[str, Any] | None = None,
) -> str:
    lines = [f"我听懂了：{sage['recap']}", ""]
    if blanket and blanket["risk_level"] != "green":
        lines.append(f"Blanket：{blanket['risk_level']} — {blanket['risk_reason']}")
        if confirm and not confirm.get("approved"):
            lines.append("（改动未写入 bible，请确认后重试或使用 /answer 对齐）")
            lines.append("")
            return "\n".join(lines)

    lines.append("Sage 想和你对齐：")
    for idx, question in enumerate(sage["key_questions"], start=1):
        lines.append(f"  {idx}. {question}")
    lines.extend(
        [
            "",
            f"Focus：{format_focus_line(focus)}",
            "",
            f"当前主线：{bible['main_thread']}",
        ]
    )
    if bible.get("characters"):
        names = "、".join(item["name"] for item in bible["characters"][:6])
        lines.append(f"人物卡：{names}")
    if bible.get("open_questions"):
        lines.append(f"待回答：{len(bible['open_questions'])} 条（可用 /answer 回复）")
    lines.append("命令：/answer /draft /expand /characters /export /recap /questions /quit")
    return "\n".join(lines)


@dataclass
class StoryPaths:
    root: Path

    @property
    def session(self) -> Path:
        return self.root / "session.json"

    @property
    def bible(self) -> Path:
        return self.root / "bible.json"

    @property
    def fragments(self) -> Path:
        return self.root / "fragments.ndjson"

    @property
    def turns(self) -> Path:
        return self.root / "turns.ndjson"

    @property
    def drafts(self) -> Path:
        return self.root / "drafts"

    @property
    def exports(self) -> Path:
        return self.root / "exports"

    @property
    def voice(self) -> Path:
        return self.root / "voice"


def resolve_story_paths(story_root: Path, story_id: str | None, title: str | None) -> StoryPaths:
    if story_id:
        return StoryPaths(story_root / story_id)
    slug = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", (title or "untitled")).strip("-").lower()
    if not slug:
        slug = "untitled"
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    return StoryPaths(story_root / f"{ts}-{slug[:24]}")


def latest_story_session(story_root: Path) -> dict[str, Any] | None:
    items = list_story_sessions(story_root)
    return items[0] if items else None


def resolve_resume_story_id(story_root: Path, story_id: str | None, resume: bool) -> str | None:
    if story_id:
        return story_id
    if not resume:
        return None
    latest = latest_story_session(story_root)
    return latest["story_id"] if latest else None


def append_story_memory(
    journal_path: Path | None,
    paths: StoryPaths,
    turn: dict[str, Any],
    bible: dict[str, Any],
) -> dict[str, Any] | None:
    if journal_path is None:
        return None
    from bedagent_mvp import append_memory_entry

    entry = {
        "recorded_at": turn.get("recorded_at") or now_iso(),
        "run_id": f"story:{paths.root.name}:turn:{turn.get('turn', 0)}",
        "kind": "story",
        "story_id": paths.root.name,
        "title": bible.get("title", ""),
        "idea": turn.get("fragment") or turn.get("answer") or "",
        "risk_level": (turn.get("blanket") or {}).get("risk_level", "green"),
        "act_status": "applied" if turn.get("applied") else "parked",
        "pillow_note": first_sentence(bible.get("main_thread", ""), max_len=100),
    }
    result = append_memory_entry(journal_path=journal_path, entry=entry)
    result["entry"] = entry
    return result


def load_story_state(paths: StoryPaths, title: str | None) -> tuple[dict[str, Any], dict[str, Any]]:
    session = load_json(paths.session, default_session(title or "未命名故事"))
    bible = ensure_bible_schema(load_json(paths.bible, empty_bible(session.get("title", title or "未命名故事"))))
    if title:
        session["title"] = title
        bible["title"] = title
    return session, bible


def load_turns(paths: StoryPaths) -> list[dict[str, Any]]:
    if not paths.turns.exists():
        return []
    rows = []
    for line in paths.turns.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def process_fragment(
    paths: StoryPaths,
    fragment: str,
    session: dict[str, Any],
    bible: dict[str, Any],
    policy: dict[str, Any] | None = None,
    auto_confirm: bool = False,
    non_interactive: bool = False,
    input_fn: Callable[[str], str] = input,
    use_llm: bool = False,
    memory_journal_path: Path | None = None,
) -> dict[str, Any]:
    text = normalize_fragment(fragment)
    if not text:
        raise ValueError("口述片段不能为空。")

    policy = policy or load_story_blanket_policy()
    bible = ensure_bible_schema(bible)
    sage = stage_story_sage(text, bible)
    try:
        from llm_adapter import enhance_story_sage

        sage = enhance_story_sage(text, bible, sage, explicit=use_llm if use_llm else None)
    except Exception:
        sage["llm"] = {"used": False, "model": "heuristic", "provider": "none", "reason": "adapter unavailable"}
    focus = stage_story_focus(text, sage)
    risk = classify_story_blanket_risk(text, bible, sage["main_thread"], policy)
    blanket = stage_story_blanket(risk, policy)
    confirm = confirm_story_blanket(blanket, risk, auto_confirm, non_interactive, input_fn=input_fn)

    turn_number = int(session.get("turn_count", 0)) + 1
    if confirm["approved"]:
        updated_bible = stage_story_synthesize(text, sage, focus, bible, turn_number)
    else:
        updated_bible = bible

    agent_reply = build_agent_reply(sage, focus, updated_bible, blanket=blanket, confirm=confirm)

    turn = {
        "turn": turn_number,
        "recorded_at": now_iso(),
        "kind": "fragment",
        "fragment": text,
        "sage": sage,
        "focus": focus,
        "blanket": blanket,
        "confirm": confirm,
        "agent_reply": agent_reply,
        "main_thread_after": updated_bible["main_thread"],
        "applied": confirm["approved"],
    }

    session["updated_at"] = now_iso()
    if confirm["approved"]:
        session["turn_count"] = turn_number
        session["fragment_count"] = updated_bible["fragment_count"]
        append_ndjson(paths.fragments, {"recorded_at": turn["recorded_at"], "fragment": text})
        write_json(paths.bible, updated_bible)
    else:
        session["turn_count"] = turn_number

    append_ndjson(paths.turns, turn)
    write_json(paths.session, session)
    memory = append_story_memory(memory_journal_path, paths, turn, updated_bible)

    return {
        "turn": turn,
        "session": session,
        "bible": updated_bible,
        "agent_reply": agent_reply,
        "blanket": blanket,
        "confirm": confirm,
        "applied": confirm["approved"],
        "memory": memory,
        "paths": {
            "root": str(paths.root),
            "session": str(paths.session),
            "bible": str(paths.bible),
        },
    }


def process_answer(
    paths: StoryPaths,
    answer: str,
    session: dict[str, Any],
    bible: dict[str, Any],
    resolve_count: int = 3,
    memory_journal_path: Path | None = None,
) -> dict[str, Any]:
    text = normalize_fragment(answer)
    if not text:
        raise ValueError("对齐回答不能为空。")

    bible = ensure_bible_schema(bible)
    open_questions = list(bible.get("open_questions", []))
    if not open_questions:
        raise ValueError("当前没有待对齐问题。")

    to_resolve = open_questions[-resolve_count:]
    resolved_rows = list(bible.get("resolved_questions", []))
    for question in to_resolve:
        resolved_rows.append(
            {"question": question, "answer": text, "resolved_at": now_iso(), "turn": session.get("turn_count", 0) + 1}
        )
    bible["resolved_questions"] = resolved_rows[-30:]
    bible["open_questions"] = [q for q in open_questions if q not in to_resolve]
    bible["updated_at"] = now_iso()

    for name in extract_character_hints(text):
        upsert_character(bible, name, text, infer_character_extras(text, name))

    turn_number = int(session.get("turn_count", 0)) + 1
    timeline = list(bible.get("timeline", []))
    timeline.append(
        {
            "turn": turn_number,
            "recorded_at": now_iso(),
            "kind": "answer",
            "category": "alignment",
            "text": first_sentence(text),
        }
    )
    bible["timeline"] = timeline[-40:]
    bible["turn_count"] = turn_number
    bible["recent_recap"] = first_sentence(text)

    agent_reply = "\n".join(
        [
            f"收到对齐：{first_sentence(text)}",
            "",
            f"已消化 {len(to_resolve)} 条待对齐问题。",
            f"剩余待回答：{len(bible['open_questions'])} 条",
            "",
            f"当前主线：{bible['main_thread']}",
        ]
    )

    turn = {
        "turn": turn_number,
        "recorded_at": now_iso(),
        "kind": "answer",
        "answer": text,
        "resolved_questions": to_resolve,
        "agent_reply": agent_reply,
        "applied": True,
    }

    session["updated_at"] = now_iso()
    session["turn_count"] = turn_number
    append_ndjson(paths.turns, turn)
    write_json(paths.bible, bible)
    write_json(paths.session, session)
    memory = append_story_memory(memory_journal_path, paths, turn, bible)

    return {
        "turn": turn,
        "session": session,
        "bible": bible,
        "agent_reply": agent_reply,
        "resolved_questions": to_resolve,
        "paths": {"root": str(paths.root), "bible": str(paths.bible)},
        "memory": memory,
    }


def build_chapter_sketch(bible: dict[str, Any], chapter_number: int) -> str:
    title = bible.get("title", "未命名故事")
    active = [item for item in bible.get("plot_threads", []) if item.get("status") == "active"]
    parked = [item for item in bible.get("plot_threads", []) if item.get("status") == "parked"]

    lines = [
        f"# {title} — 第 {chapter_number} 章草图",
        "",
        f"> 生成于 {now_iso()}",
        "",
        "## 本章目标",
        f"- 推进主线：{bible.get('main_thread', '')}",
        "",
        "## 建议场景",
    ]
    if active:
        for idx, item in enumerate(active[:5], start=1):
            lines.append(f"{idx}. {item['label']}")
    else:
        lines.append("- （尚无活跃线索，继续口述一段情节）")

    lines.extend(["", "## 人物状态"])
    if bible.get("characters"):
        for item in bible["characters"][:8]:
            note = "；".join(item.get("notes", [])[:2]) or "待补充"
            lines.append(f"- **{item['name']}**：{note}")
    else:
        lines.append("- （尚未建立人物卡）")

    if parked:
        lines.extend(["", "## 可埋伏笔（暂存）"])
        for item in parked[:4]:
            lines.append(f"- {item['label']}")

    if bible.get("open_questions"):
        lines.extend(["", "## 写之前先对齐"])
        for question in bible["open_questions"][-5:]:
            lines.append(f"- {question}")

    lines.extend(["", "## 口述续写提示", "- 下一段可以直接从这里接着讲：场景、冲突、对白。"])
    return "\n".join(lines) + "\n"


def build_night_pillow_note(bible: dict[str, Any], session: dict[str, Any] | None = None) -> str:
    open_n = len(bible.get("open_questions") or [])
    turns = (session or {}).get("turn_count", bible.get("turn_count", 0))
    thread = first_sentence(bible.get("main_thread", ""), max_len=48)
    return f"{thread} 回合 {turns}。待对齐 {open_n} 条。"


def build_character_sheet(bible: dict[str, Any]) -> str:
    title = bible.get("title", "未命名故事")
    lines = [f"# {title} — 人物卡", "", f"> 生成于 {now_iso()}", ""]
    characters = bible.get("characters") or []
    if not characters:
        lines.append("（尚未建立人物卡。口述时可以说「名叫…」或「主角叫…」。）")
        return "\n".join(lines) + "\n"
    role_labels = {
        "protagonist": "主角",
        "antagonist": "对手",
        "ally": "同伴",
        "": "未标注",
    }
    for item in characters:
        role = role_labels.get(item.get("role", ""), item.get("role") or "未标注")
        lines.append(f"## {item.get('name', '未命名')}（{role}）")
        if item.get("desire"):
            lines.append(f"- 欲望：{item['desire']}")
        if item.get("conflict"):
            lines.append(f"- 冲突：{item['conflict']}")
        notes = item.get("notes") or []
        if notes:
            lines.append("- 笔记：")
            for note in notes[-4:]:
                lines.append(f"  - {note}")
        else:
            lines.append("- 笔记：待补充")
        lines.append("")
    return "\n".join(lines) + "\n"


def build_chapter_prose(bible: dict[str, Any], chapter_number: int) -> str:
    title = bible.get("title", "未命名故事")
    main = bible.get("main_thread", "")
    recap = bible.get("recent_recap") or main
    characters = bible.get("characters") or []
    names = "、".join(item.get("name", "") for item in characters[:4] if item.get("name")) or "还没点名的人"
    setting = bible.get("setting") or {}
    place = setting.get("place") or "尚未标明的场景"
    active = [item for item in bible.get("plot_threads", []) if item.get("status") == "active"]
    parked = [item for item in bible.get("plot_threads", []) if item.get("status") == "parked"]
    questions = bible.get("open_questions") or []

    paragraphs = [
        f"{recap}空气还没散。{names}停在{place}里，谁也不先把下一句说完。",
        f"这一章必须碰到主线：{main}。旁支可以亮一下，但不能把镜头抢走。",
    ]
    if active:
        labels = "；".join(first_sentence(item["label"], 40) for item in active[:3])
        paragraphs.append(f"眼前先处理：{labels}。")
    if parked:
        labels = "；".join(first_sentence(item["label"], 36) for item in parked[:3])
        paragraphs.append(f"可以先不碰的伏笔：{labels}。")
    if characters:
        desire = next((item for item in characters if item.get("desire")), None)
        if desire:
            paragraphs.append(f"{desire['name']}想要{desire['desire']}。这个欲望现在必须付出代价，或者被当场挡住。")
    if questions:
        paragraphs.append(f"写下去之前还差一个答案：{questions[-1]}")
    paragraphs.append("下一段口述从冲突落地处接着讲：谁先动，谁先瞒，谁先付出代价。")

    lines = [
        f"# {title} — 第 {chapter_number} 章扩写",
        "",
        f"> 生成于 {now_iso()} · Draft Sandbox",
        "",
    ]
    for para in paragraphs:
        lines.append(para)
        lines.append("")
    return "\n".join(lines)


def expand_chapter_draft(
    bible: dict[str, Any],
    chapter_number: int,
    sketch: str,
    use_llm: bool = False,
) -> dict[str, Any]:
    heuristic = build_chapter_prose(bible, chapter_number)
    payload = {
        "text": heuristic,
        "llm": {"used": False, "model": "heuristic", "provider": "none", "reason": "heuristic expansion"},
    }
    try:
        from llm_adapter import expand_story_chapter

        enhanced = expand_story_chapter(
            bible=bible,
            sketch=sketch,
            heuristic=heuristic,
            explicit=use_llm if use_llm else None,
        )
        payload["text"] = enhanced.get("text") or heuristic
        payload["llm"] = enhanced.get("llm") or payload["llm"]
    except Exception as exc:  # pragma: no cover - adapter guardrail
        payload["llm"]["reason"] = f"adapter unavailable: {exc}"
    return payload


def build_outline_markdown(bible: dict[str, Any], session: dict[str, Any]) -> str:
    title = bible.get("title", session.get("title", "未命名故事"))
    lines = [
        f"# {title} — 故事大纲",
        "",
        f"- 回合：{session.get('turn_count', 0)}",
        f"- 更新时间：{bible.get('updated_at', '')}",
        "",
        "## 主线",
        bible.get("main_thread", ""),
        "",
    ]

    setting = bible.get("setting", {})
    if setting.get("place") or setting.get("time") or setting.get("notes"):
        lines.extend(["## 世界", ""])
        if setting.get("time"):
            lines.append(f"- 时间：{setting['time']}")
        if setting.get("place"):
            lines.append(f"- 地点：{setting['place']}")
        for note in setting.get("notes", [])[:6]:
            lines.append(f"- {note}")
        lines.append("")

    if bible.get("characters"):
        lines.extend(["## 人物", ""])
        for item in bible["characters"]:
            note = "；".join(item.get("notes", [])) or "待补充"
            lines.append(f"- **{item['name']}**：{note}")
        lines.append("")

    threads = bible.get("plot_threads", [])
    if threads:
        lines.extend(["## 线索", ""])
        for status in ("active", "parked", "merged"):
            group = [item for item in threads if item.get("status") == status]
            if not group:
                continue
            label = {"active": "活跃", "parked": "暂存", "merged": "已合并"}[status]
            lines.append(f"### {label}")
            for item in group[:10]:
                lines.append(f"- {item['label']}")
            lines.append("")

    if bible.get("timeline"):
        lines.extend(["## 时间线（口述摘要）", ""])
        for item in bible["timeline"][-12:]:
            kind = "口述" if item.get("kind") == "fragment" else "对齐"
            lines.append(f"- [回合 {item.get('turn', '?')}/{kind}] {item.get('text', '')}")
        lines.append("")

    resolved = bible.get("resolved_questions", [])
    if resolved:
        lines.extend(["## 已对齐", ""])
        for item in resolved[-8:]:
            lines.append(f"- Q: {item['question']}")
            lines.append(f"  A: {item['answer']}")
        lines.append("")

    if bible.get("open_questions"):
        lines.extend(["## 待对齐", ""])
        for question in bible["open_questions"]:
            lines.append(f"- {question}")

    return "\n".join(lines) + "\n"


def build_transcript_markdown(paths: StoryPaths, session: dict[str, Any]) -> str:
    turns = load_turns(paths)
    title = session.get("title", "未命名故事")
    lines = [f"# {title} — 口述 transcript", "", f"共 {len(turns)} 条记录", ""]
    for turn in turns:
        kind = turn.get("kind", "fragment")
        lines.append(f"## 回合 {turn.get('turn', '?')} · {kind}")
        lines.append(f"*{turn.get('recorded_at', '')}*")
        lines.append("")
        if kind == "fragment":
            lines.append("**你：**")
            lines.append("")
            lines.append(turn.get("fragment", ""))
        else:
            lines.append("**对齐：**")
            lines.append("")
            lines.append(turn.get("answer", ""))
        lines.append("")
        lines.append("**Agent：**")
        lines.append("")
        lines.append(turn.get("agent_reply", ""))
        lines.append("")
    return "\n".join(lines) + "\n"


def build_story_drafts(
    paths: StoryPaths,
    bible: dict[str, Any],
    session: dict[str, Any],
    expand: bool = False,
    use_llm: bool = False,
    night: bool = False,
) -> dict[str, Any]:
    bible = ensure_bible_schema(bible)
    paths.drafts.mkdir(parents=True, exist_ok=True)

    chapter_number = int(bible.get("drafts", {}).get("chapter_count", 0)) + 1
    outline_path = paths.drafts / "outline.md"
    chapter_path = paths.drafts / f"chapter-{chapter_number:02d}-sketch.md"
    pillow_path = paths.drafts / "pillow_note.txt"
    characters_path = paths.drafts / "characters.md"
    sketch = build_chapter_sketch(bible, chapter_number)
    pillow = (
        build_night_pillow_note(bible, session)
        if night
        else first_sentence(bible.get("main_thread", ""), max_len=100)
    )

    outline_path.write_text(build_outline_markdown(bible, session), encoding="utf-8")
    chapter_path.write_text(sketch, encoding="utf-8")
    pillow_path.write_text(pillow + "\n", encoding="utf-8")
    characters_path.write_text(build_character_sheet(bible), encoding="utf-8")

    prose_path = ""
    expansion: dict[str, Any] | None = None
    if expand:
        expansion = expand_chapter_draft(bible, chapter_number, sketch, use_llm=use_llm)
        prose_file = paths.drafts / f"chapter-{chapter_number:02d}-prose.md"
        prose_file.write_text(expansion["text"], encoding="utf-8")
        prose_path = str(prose_file)

    bible["drafts"] = {
        "chapter_count": chapter_number,
        "last_draft_at": now_iso(),
        "last_export_at": bible.get("drafts", {}).get("last_export_at", ""),
        "last_expand_at": now_iso() if expand else bible.get("drafts", {}).get("last_expand_at", ""),
        "expanded": bool(expand),
    }
    write_json(paths.bible, bible)

    payload = {
        "chapter_number": chapter_number,
        "outline_path": str(outline_path),
        "chapter_sketch_path": str(chapter_path),
        "pillow_note_path": str(pillow_path),
        "characters_path": str(characters_path),
        "pillow_note": pillow,
        "outline": outline_path.read_text(encoding="utf-8"),
        "sketch": sketch,
        "characters": characters_path.read_text(encoding="utf-8"),
    }
    if prose_path and expansion:
        payload["prose_path"] = prose_path
        payload["prose"] = expansion["text"]
        payload["llm"] = expansion["llm"]
    return payload


def load_latest_draft_texts(paths: StoryPaths, bible: dict[str, Any]) -> dict[str, str]:
    bible = ensure_bible_schema(bible)
    chapter = int(bible.get("drafts", {}).get("chapter_count", 0))
    payload: dict[str, str] = {}
    outline = paths.drafts / "outline.md"
    pillow = paths.drafts / "pillow_note.txt"
    characters = paths.drafts / "characters.md"
    if outline.exists():
        payload["outline"] = outline.read_text(encoding="utf-8")
    if pillow.exists():
        payload["pillow_note"] = pillow.read_text(encoding="utf-8")
    if characters.exists():
        payload["characters"] = characters.read_text(encoding="utf-8")
    if chapter:
        sketch = paths.drafts / f"chapter-{chapter:02d}-sketch.md"
        prose = paths.drafts / f"chapter-{chapter:02d}-prose.md"
        if sketch.exists():
            payload["sketch"] = sketch.read_text(encoding="utf-8")
        if prose.exists():
            payload["prose"] = prose.read_text(encoding="utf-8")
    return payload


def export_story(paths: StoryPaths, bible: dict[str, Any], session: dict[str, Any]) -> dict[str, str]:
    paths.exports.mkdir(parents=True, exist_ok=True)
    bible = ensure_bible_schema(bible)

    outline = paths.exports / "story-bible.md"
    transcript = paths.exports / "transcript.md"
    outline.write_text(build_outline_markdown(bible, session), encoding="utf-8")
    transcript.write_text(build_transcript_markdown(paths, session), encoding="utf-8")

    bible["drafts"]["last_export_at"] = now_iso()
    write_json(paths.bible, bible)

    return {"story_bible_path": str(outline), "transcript_path": str(transcript)}


def list_story_sessions(story_root: Path) -> list[dict[str, Any]]:
    if not story_root.exists():
        return []
    items: list[dict[str, Any]] = []
    for entry in sorted(story_root.iterdir()):
        if not entry.is_dir():
            continue
        session_path = entry / "session.json"
        bible_path = entry / "bible.json"
        if not session_path.exists():
            continue
        session = json.loads(session_path.read_text(encoding="utf-8"))
        main_thread = ""
        if bible_path.exists():
            bible = json.loads(bible_path.read_text(encoding="utf-8"))
            main_thread = bible.get("main_thread", "")
        items.append(
            {
                "story_id": entry.name,
                "title": session.get("title", entry.name),
                "turn_count": session.get("turn_count", 0),
                "updated_at": session.get("updated_at", ""),
                "main_thread": main_thread,
                "_mtime": entry.stat().st_mtime,
            }
        )
    items.sort(
        key=lambda item: (str(item.get("updated_at") or ""), float(item.get("_mtime") or 0.0), str(item.get("story_id") or "")),
        reverse=True,
    )
    for item in items:
        item.pop("_mtime", None)
    return items


def tokenize_story_text(value: str) -> list[str]:
    from bedagent_mvp import tokenize_text

    return tokenize_text(value)


def collect_story_search_entries(story_root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for item in list_story_sessions(story_root):
        paths = StoryPaths(story_root / item["story_id"])
        bible = load_json(paths.bible, {})
        fragments: list[str] = []
        if paths.fragments.exists():
            for line in paths.fragments.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                fragments.append(str(payload.get("fragment", "")))
        characters = [c.get("name", "") for c in bible.get("characters", [])]
        entries.append(
            {
                "story_id": item["story_id"],
                "title": item.get("title", ""),
                "main_thread": bible.get("main_thread", item.get("main_thread", "")),
                "recent_recap": bible.get("recent_recap", ""),
                "characters": " ".join(name for name in characters if name),
                "fragments": " ".join(fragments[-8:]),
                "turn_count": item.get("turn_count", 0),
            }
        )
    return entries


def search_stories(
    story_root: Path,
    query: str,
    top_k: int = 3,
    min_score: float = 0.0,
) -> list[dict[str, Any]]:
    from bedagent_mvp import apply_min_score, compute_idf, cosine_similarity, vectorize

    entries = collect_story_search_entries(story_root)
    if not entries:
        return []
    field_weights = {
        "title": 0.15,
        "main_thread": 0.35,
        "recent_recap": 0.15,
        "characters": 0.1,
        "fragments": 0.25,
    }
    query_tokens = tokenize_story_text(query)
    docs = {field: [tokenize_story_text(str(entry.get(field, ""))) for entry in entries] for field in field_weights}
    all_tokens = [query_tokens]
    for field in field_weights:
        all_tokens.extend(docs[field])
    idf = compute_idf(all_tokens)
    qvec = vectorize(query_tokens, idf)
    ranked = []
    for idx, entry in enumerate(entries):
        score = 0.0
        detail = {}
        for field, weight in field_weights.items():
            part = cosine_similarity(qvec, vectorize(docs[field][idx], idf))
            detail[field] = round(part, 6)
            score += weight * part
        ranked.append({"score": round(score, 6), "entry": entry, "detail": detail})
    ranked.sort(key=lambda item: item["score"], reverse=True)
    return apply_min_score(ranked[: max(1, top_k)], min_score)


def build_story_recap(bible: dict[str, Any], session: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": bible.get("title", session.get("title", "未命名故事")),
        "turn_count": session.get("turn_count", 0),
        "main_thread": bible.get("main_thread", ""),
        "recent_recap": bible.get("recent_recap", ""),
        "characters": bible.get("characters", []),
        "plot_threads": bible.get("plot_threads", []),
        "setting": bible.get("setting", {}),
        "open_questions": bible.get("open_questions", []),
        "resolved_questions": bible.get("resolved_questions", []),
        "timeline": bible.get("timeline", []),
        "drafts": bible.get("drafts", {}),
    }


def print_story_recap(recap: dict[str, Any]) -> None:
    print("")
    print("=== bedagent story recap ===")
    print(f"标题: {recap['title']}")
    print(f"回合: {recap['turn_count']}")
    print(f"主线: {recap['main_thread']}")
    if recap.get("recent_recap"):
        print(f"最近口述: {recap['recent_recap']}")
    if recap.get("characters"):
        print("人物:")
        for item in recap["characters"][:8]:
            notes = "；".join(item.get("notes", [])[:2])
            print(f"- {item['name']}: {notes or '（待补充）'}")
    active_threads = [item for item in recap.get("plot_threads", []) if item.get("status") == "active"]
    if active_threads:
        print("活跃线索:")
        for item in active_threads[:8]:
            print(f"- {item['label']}")
    if recap.get("open_questions"):
        print("待对齐:")
        for question in recap["open_questions"][-5:]:
            print(f"- {question}")
    if recap.get("drafts", {}).get("last_draft_at"):
        print(f"最近草稿: {recap['drafts']['last_draft_at']} (chapter {recap['drafts'].get('chapter_count', 0)})")


def read_multiline_fragment(prompt: str, input_fn: Callable[[str], str] = input) -> str | None:
    print(prompt)
    lines: list[str] = []
    while True:
        try:
            line = input_fn("> ")
        except EOFError:
            break
        stripped = line.strip()
        if not lines and stripped.startswith("/"):
            return stripped
        if not line.strip() and lines:
            break
        if line.strip():
            lines.append(line.rstrip())
    if not lines:
        return None
    return "\n".join(lines)


def run_story_tell(
    story_root: Path,
    story_id: str | None = None,
    title: str | None = None,
    seed_fragment: str | None = None,
    policy: dict[str, Any] | None = None,
    auto_confirm: bool = False,
    non_interactive: bool = False,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
    use_llm: bool = False,
    memory_journal_path: Path | None = None,
) -> dict[str, Any]:
    paths = resolve_story_paths(story_root, story_id, title)
    paths.root.mkdir(parents=True, exist_ok=True)
    session, bible = load_story_state(paths, title)
    policy = policy or load_story_blanket_policy()

    output_fn("")
    output_fn("=== bedagent story · 口述模式 ===")
    output_fn(f"故事目录: {paths.root}")
    output_fn(f"story_id: {paths.root.name}")
    output_fn(f"标题: {session['title']} | 回合: {session.get('turn_count', 0)}")
    output_fn("像 vibe coding 一样讲：碎片、跳跃、重复都没关系。")
    output_fn("多行口述，空行发送。")
    output_fn("命令: /answer /draft /expand /characters /export /recap /questions /help /quit")
    output_fn("")

    last_result: dict[str, Any] | None = None

    def handle_fragment(raw: str) -> dict[str, Any] | None:
        nonlocal session, bible, last_result
        result = process_fragment(
            paths,
            raw,
            session,
            bible,
            policy=policy,
            auto_confirm=auto_confirm,
            non_interactive=non_interactive,
            input_fn=input_fn,
            use_llm=use_llm,
            memory_journal_path=memory_journal_path,
        )
        session = result["session"]
        bible = result["bible"]
        last_result = result
        output_fn("")
        output_fn(result["agent_reply"])
        output_fn("")
        return result

    def handle_answer(raw: str) -> None:
        nonlocal session, bible, last_result
        try:
            result = process_answer(paths, raw, session, bible, memory_journal_path=memory_journal_path)
        except ValueError as exc:
            output_fn(f"（{exc}）")
            return
        session = result["session"]
        bible = result["bible"]
        last_result = result
        output_fn("")
        output_fn(result["agent_reply"])
        output_fn("")

    if seed_fragment:
        handle_fragment(seed_fragment)

    while True:
        fragment = read_multiline_fragment(
            "继续口述或 /answer /draft /expand /characters /export /recap /questions /quit:",
            input_fn=input_fn,
        )
        if fragment is None:
            output_fn("（空输入，继续等待）")
            continue
        if fragment == "/quit":
            break
        if fragment == "/recap":
            print_story_recap(build_story_recap(bible, session))
            continue
        if fragment == "/questions":
            open_q = bible.get("open_questions", [])
            output_fn("")
            output_fn("=== 待对齐问题 ===")
            if not open_q:
                output_fn("（暂无）")
            else:
                for idx, question in enumerate(open_q, start=1):
                    output_fn(f"{idx}. {question}")
            output_fn("")
            continue
        if fragment == "/help":
            output_fn("口述 → Sage 追问 → Focus 剪枝 → Blanket 大改确认 → bible 更新")
            output_fn("/answer — 回复 Sage 追问  /draft — 章节草图  /expand — 扩写正文  /characters — 人物卡  /export — 导出 markdown")
            continue
        if fragment == "/draft":
            result = build_story_drafts(paths, bible, session)
            bible = ensure_bible_schema(load_json(paths.bible, bible))
            output_fn("")
            output_fn("=== bedagent story draft ===")
            output_fn(f"chapter: {result['chapter_number']}")
            output_fn(f"outline: {result['outline_path']}")
            output_fn(f"sketch: {result['chapter_sketch_path']}")
            output_fn(f"pillow: {result['pillow_note_path']}")
            output_fn("")
            continue
        if fragment == "/expand":
            result = build_story_drafts(paths, bible, session, expand=True, use_llm=use_llm)
            bible = ensure_bible_schema(load_json(paths.bible, bible))
            output_fn("")
            output_fn("=== bedagent story expand ===")
            output_fn(f"chapter: {result['chapter_number']}")
            output_fn(f"prose: {result.get('prose_path', '')}")
            output_fn("")
            continue
        if fragment == "/characters":
            sheet = build_character_sheet(bible)
            output_fn("")
            output_fn(sheet)
            continue
        if fragment == "/export":
            result = export_story(paths, bible, session)
            bible = ensure_bible_schema(load_json(paths.bible, bible))
            output_fn("")
            output_fn("=== bedagent story export ===")
            output_fn(f"bible: {result['story_bible_path']}")
            output_fn(f"transcript: {result['transcript_path']}")
            output_fn("")
            continue
        if fragment == "/answer":
            answer = read_multiline_fragment("对齐回答（空行发送）:", input_fn=input_fn)
            if answer and not answer.startswith("/"):
                handle_answer(answer)
            continue
        handle_fragment(fragment)

    output_fn("")
    output_fn("=== bedagent story session ended ===")
    output_fn(f"story_id: {paths.root.name}")
    output_fn(f"turns: {session.get('turn_count', 0)}")
    output_fn(f"bible: {paths.bible}")
    recap = build_story_recap(bible, session)
    recap["story_id"] = paths.root.name
    recap["paths"] = {
        "root": str(paths.root),
        "bible": str(paths.bible),
        "turns": str(paths.turns),
        "drafts": str(paths.drafts),
        "exports": str(paths.exports),
    }
    if last_result:
        recap["last_turn"] = last_result["turn"]["turn"]
    return recap


def run_voice_story_once(
    paths: StoryPaths,
    audio_path: Path,
    session: dict[str, Any],
    bible: dict[str, Any],
    policy: dict[str, Any] | None = None,
    voice_config: dict[str, Any] | None = None,
    voice_config_path: Path | None = None,
    auto_confirm: bool = False,
    non_interactive: bool = False,
    use_llm: bool = False,
    memory_journal_path: Path | None = None,
    quiet: bool = False,
) -> dict[str, Any]:
    """Voice closed loop: ASR (or simulated sidecar) -> Story -> TTS reply."""
    from voice_adapter import (
        apply_quiet_config,
        build_tts_summary,
        load_voice_config,
        persist_voice_turn_artifacts,
        synthesize_speech,
        transcribe_file,
        voice_turn_paths,
    )

    policy = policy or load_story_blanket_policy()
    voice_config = apply_quiet_config(voice_config or load_voice_config(voice_config_path), quiet=quiet)

    transcript = transcribe_file(audio_path, config=voice_config, config_path=voice_config_path)
    result = process_fragment(
        paths,
        transcript.text,
        session,
        bible,
        policy=policy,
        auto_confirm=auto_confirm,
        non_interactive=non_interactive,
        use_llm=use_llm,
        memory_journal_path=memory_journal_path,
    )

    turn_no = result["turn"]["turn"]
    artifacts = voice_turn_paths(paths.voice, turn_no)
    persist_voice_turn_artifacts(
        artifacts,
        transcript=transcript.text,
        agent_reply=result["agent_reply"],
        input_audio=audio_path,
    )
    tts_text = build_tts_summary(result["agent_reply"], voice_config)
    speak = synthesize_speech(tts_text, artifacts["reply_audio"], config=voice_config)

    return {
        "story_id": paths.root.name,
        "transcript": transcript.text,
        "asr_model": transcript.model,
        "result": result,
        "applied": result["applied"],
        "agent_reply": result["agent_reply"],
        "tts_model": speak.model,
        "reply_audio": speak.output_path,
        "reply_text": speak.text,
        "artifacts": {key: str(value) for key, value in artifacts.items()},
        "session": result["session"],
        "bible": result["bible"],
        "quiet": bool(voice_config.get("quiet_mode")),
    }


def run_story_voice_tell(
    story_root: Path,
    story_id: str | None = None,
    title: str | None = None,
    seed_audio: Path | None = None,
    policy: dict[str, Any] | None = None,
    voice_config: dict[str, Any] | None = None,
    voice_config_path: Path | None = None,
    auto_confirm: bool = False,
    non_interactive: bool = False,
    use_mic: bool = False,
    play_reply: bool = False,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
    use_llm: bool = False,
    memory_journal_path: Path | None = None,
    quiet: bool = False,
) -> dict[str, Any]:
    from voice_adapter import (
        apply_quiet_config,
        build_tts_summary,
        load_voice_config,
        map_voice_command,
        persist_voice_turn_artifacts,
        play_audio_file,
        record_microphone_wav,
        synthesize_speech,
        transcribe_file,
        voice_turn_paths,
    )

    paths = resolve_story_paths(story_root, story_id, title)
    paths.root.mkdir(parents=True, exist_ok=True)
    session, bible = load_story_state(paths, title)
    policy = policy or load_story_blanket_policy()
    voice_config = apply_quiet_config(voice_config or load_voice_config(voice_config_path), quiet=quiet)

    output_fn("")
    output_fn("=== bedagent story · 语音口述模式 ===")
    output_fn(f"故事目录: {paths.root}")
    output_fn(f"story_id: {paths.root.name}")
    output_fn(f"标题: {session['title']} | 回合: {session.get('turn_count', 0)}")
    output_fn(f"ASR: {voice_config['asr_model']} | TTS: {voice_config['tts_model']} / {voice_config['tts_voice']}")
    output_fn("提供音频文件路径，输入 mic 录音，或口述文本路径 fallback。")
    output_fn("语音口令：暂停 / 继续 / 取消 / 汇报一下 / 扩写 / 夜间模式")
    output_fn("命令: /text /answer /draft /expand /characters /export /recap /quiet /questions /help /quit")
    output_fn("")

    last_result: dict[str, Any] | None = None

    def resolve_audio_input(raw: str) -> Path | None:
        value = clean_text(raw)
        if not value:
            if use_mic:
                turn_no = int(session.get("turn_count", 0)) + 1
                target = voice_turn_paths(paths.voice, turn_no)["input"]
                output_fn(f"录音 {voice_config.get('mic_seconds', 8)} 秒...")
                return record_microphone_wav(
                    target,
                    seconds=float(voice_config.get("mic_seconds", 8)),
                    sample_rate=int(voice_config.get("sample_rate", 16000)),
                )
            return None
        if value.lower() == "mic":
            turn_no = int(session.get("turn_count", 0)) + 1
            target = voice_turn_paths(paths.voice, turn_no)["input"]
            output_fn(f"录音 {voice_config.get('mic_seconds', 8)} 秒...")
            return record_microphone_wav(
                target,
                seconds=float(voice_config.get("mic_seconds", 8)),
                sample_rate=int(voice_config.get("sample_rate", 16000)),
            )
        path = Path(value).expanduser()
        if path.exists():
            return path
        output_fn(f"（找不到音频文件: {path}）")
        return None

    def handle_voice_turn(audio_path: Path) -> dict[str, Any] | None:
        nonlocal session, bible, last_result
        transcript = transcribe_file(audio_path, config=voice_config, config_path=voice_config_path)
        mapped = map_voice_command(transcript.text, voice_config)
        if mapped:
            return {"command": mapped, "transcript": transcript.text}

        output_fn("")
        output_fn(f"转写：{transcript.text}")
        result = process_fragment(
            paths,
            transcript.text,
            session,
            bible,
            policy=policy,
            auto_confirm=auto_confirm,
            non_interactive=non_interactive,
            input_fn=input_fn,
            use_llm=use_llm,
            memory_journal_path=memory_journal_path,
        )
        session = result["session"]
        bible = result["bible"]
        last_result = result

        turn_no = result["turn"]["turn"]
        artifacts = voice_turn_paths(paths.voice, turn_no)
        persist_voice_turn_artifacts(
            artifacts,
            transcript=transcript.text,
            agent_reply=result["agent_reply"],
            input_audio=audio_path,
        )
        tts_text = build_tts_summary(result["agent_reply"], voice_config)
        speak = synthesize_speech(tts_text, artifacts["reply_audio"], config=voice_config)
        output_fn("")
        output_fn(result["agent_reply"])
        output_fn("")
        output_fn(f"TTS: {speak.output_path} ({speak.byte_size} bytes)")
        if play_reply and not voice_config.get("quiet_mode"):
            played = play_audio_file(Path(speak.output_path))
            if not played:
                output_fn("（未安装播放依赖，跳过自动播放）")
        elif voice_config.get("quiet_mode"):
            output_fn("（夜间模式：不自动播放）")
        output_fn("")
        return result

    def handle_fragment(raw: str) -> dict[str, Any] | None:
        nonlocal session, bible, last_result
        result = process_fragment(
            paths,
            raw,
            session,
            bible,
            policy=policy,
            auto_confirm=auto_confirm,
            non_interactive=non_interactive,
            input_fn=input_fn,
            use_llm=use_llm,
            memory_journal_path=memory_journal_path,
        )
        session = result["session"]
        bible = result["bible"]
        last_result = result
        output_fn("")
        output_fn(result["agent_reply"])
        output_fn("")
        return result

    if seed_audio:
        handle_voice_turn(seed_audio.expanduser().resolve())

    while True:
        raw = input_fn("音频路径 / mic / /text / /quit: ").strip()
        if not raw:
            if use_mic:
                audio = resolve_audio_input("mic")
                if audio is None:
                    continue
                outcome = handle_voice_turn(audio)
            else:
                output_fn("（空输入，继续等待）")
                continue
        elif raw.startswith("/"):
            outcome = {"command": raw}
        else:
            mapped = map_voice_command(raw, voice_config)
            if mapped:
                outcome = {"command": mapped}
            elif raw.lower() == "mic" or Path(raw).expanduser().exists():
                audio = resolve_audio_input(raw)
                if audio is None:
                    continue
                outcome = handle_voice_turn(audio)
            else:
                output_fn("（请输入有效音频路径、mic 或 /command）")
                continue

        if isinstance(outcome, dict) and outcome.get("command"):
            command = outcome["command"]
            if command == "/quit":
                break
            if command == "/recap":
                print_story_recap(build_story_recap(bible, session))
                continue
            if command == "/questions":
                open_q = bible.get("open_questions", [])
                output_fn("")
                output_fn("=== 待对齐问题 ===")
                if not open_q:
                    output_fn("（暂无）")
                else:
                    for idx, question in enumerate(open_q, start=1):
                        output_fn(f"{idx}. {question}")
                output_fn("")
                continue
            if command == "/help":
                output_fn("语音口述：DashScope ASR 转写 → Sage/Focus → CosyVoice TTS 短反馈")
                output_fn("/text 切到文本口述  /answer /draft /expand /characters /export /recap /quiet /quit")
                continue
            if command == "/draft":
                result = build_story_drafts(paths, bible, session, night=bool(voice_config.get("quiet_mode")))
                bible = ensure_bible_schema(load_json(paths.bible, bible))
                output_fn(f"draft: {result['chapter_sketch_path']}")
                continue
            if command == "/expand":
                result = build_story_drafts(
                    paths, bible, session, expand=True, use_llm=use_llm, night=bool(voice_config.get("quiet_mode"))
                )
                bible = ensure_bible_schema(load_json(paths.bible, bible))
                output_fn(f"expand: {result.get('prose_path', result['chapter_sketch_path'])}")
                continue
            if command == "/characters":
                output_fn(build_character_sheet(bible))
                continue
            if command == "/quiet":
                voice_config["quiet_mode"] = not bool(voice_config.get("quiet_mode"))
                voice_config = apply_quiet_config(voice_config, quiet=bool(voice_config["quiet_mode"]))
                output_fn("夜间模式：" + ("开" if voice_config.get("quiet_mode") else "关"))
                continue
            if command == "/export":
                result = export_story(paths, bible, session)
                bible = ensure_bible_schema(load_json(paths.bible, bible))
                output_fn(f"export: {result['story_bible_path']}")
                continue
            if command == "/text":
                fragment = read_multiline_fragment("文本口述（空行发送）:", input_fn=input_fn)
                if fragment and not fragment.startswith("/"):
                    handle_fragment(fragment)
                continue
            if command == "/answer":
                answer = read_multiline_fragment("对齐回答（空行发送）:", input_fn=input_fn)
                if answer and not answer.startswith("/"):
                    try:
                        ans = process_answer(
                            paths, answer, session, bible, memory_journal_path=memory_journal_path
                        )
                        session = ans["session"]
                        bible = ans["bible"]
                        output_fn(ans["agent_reply"])
                    except ValueError as exc:
                        output_fn(f"（{exc}）")
                continue
            if command in {"/pause", "/continue"}:
                output_fn("（已收到语音控制口令）")
                continue
            output_fn(f"（未知命令: {command}）")
            continue

    output_fn("")
    output_fn("=== bedagent story voice session ended ===")
    output_fn(f"story_id: {paths.root.name}")
    output_fn(f"voice_dir: {paths.voice}")
    recap = build_story_recap(bible, session)
    recap["story_id"] = paths.root.name
    recap["voice_dir"] = str(paths.voice)
    if last_result:
        recap["last_turn"] = last_result["turn"]["turn"]
    return recap
