"""bedagent story session: oral dictation loop with Sage dialogue."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

STORY_FLOW = "Oral Capture -> Sage -> Focus -> Synthesize -> Dialogue -> Bible -> Memory"

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
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


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


def empty_bible(title: str = "未命名故事") -> dict[str, Any]:
    return {
        "title": title,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "main_thread": "（等待第一段口述）",
        "characters": [],
        "plot_threads": [],
        "setting": {"time": "", "place": "", "notes": []},
        "open_questions": [],
        "recent_recap": "",
        "fragment_count": 0,
        "turn_count": 0,
    }


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
    shared = set(re.findall(r"[\u4e00-\u9fff]{2,}|[a-zA-Z]{4,}", thread_l)) & set(
        re.findall(r"[\u4e00-\u9fff]{2,}|[a-zA-Z]{4,}", main_l)
    )
    if len(shared) >= 2:
        return "expand"
    if len(shared) == 1:
        return "merge"
    if any(k in thread_l for k in ("冲突", "转折", "秘密", "真相", "twist", "conflict", "secret")):
        return "expand"
    return "park"


def stage_story_sage(fragment: str, bible: dict[str, Any]) -> dict[str, Any]:
    category = detect_story_category(fragment)
    recap = first_sentence(fragment)
    main_thread = bible.get("main_thread") or "（等待第一段口述）"
    if main_thread.startswith("（等待"):
        main_thread = recap
    elif category in {"plot", "character", "theme"}:
        main_thread = recap

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


def upsert_character(bible: dict[str, Any], name: str, note: str) -> None:
    for item in bible["characters"]:
        if item["name"] == name:
            if note and note not in item["notes"]:
                item["notes"].append(note)
            return
    bible["characters"].append({"name": name, "notes": [note] if note else []})


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
    fragment: str, sage: dict[str, Any], focus: dict[str, Any], bible: dict[str, Any]
) -> dict[str, Any]:
    updated = json.loads(json.dumps(bible, ensure_ascii=False))
    updated["main_thread"] = sage["main_thread"]
    updated["updated_at"] = now_iso()
    updated["recent_recap"] = sage["recap"]
    updated["fragment_count"] = int(updated.get("fragment_count", 0)) + 1
    updated["turn_count"] = int(updated.get("turn_count", 0)) + 1

    for name in extract_character_hints(fragment):
        upsert_character(updated, name, sage["recap"])

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


def build_agent_reply(sage: dict[str, Any], focus: dict[str, Any], bible: dict[str, Any]) -> str:
    lines = [
        f"我听懂了：{sage['recap']}",
        "",
        "Sage 想和你对齐：",
    ]
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
        lines.append(f"待回答：{len(bible['open_questions'])} 条")
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


def resolve_story_paths(story_root: Path, story_id: str | None, title: str | None) -> StoryPaths:
    if story_id:
        return StoryPaths(story_root / story_id)
    slug = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", (title or "untitled")).strip("-").lower()
    if not slug:
        slug = "untitled"
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    return StoryPaths(story_root / f"{ts}-{slug[:24]}")


def load_story_state(paths: StoryPaths, title: str | None) -> tuple[dict[str, Any], dict[str, Any]]:
    session = load_json(paths.session, default_session(title or "未命名故事"))
    bible = load_json(paths.bible, empty_bible(session.get("title", title or "未命名故事")))
    if title:
        session["title"] = title
        bible["title"] = title
    return session, bible


def process_fragment(
    paths: StoryPaths,
    fragment: str,
    session: dict[str, Any],
    bible: dict[str, Any],
) -> dict[str, Any]:
    text = normalize_fragment(fragment)
    if not text:
        raise ValueError("口述片段不能为空。")

    sage = stage_story_sage(text, bible)
    focus = stage_story_focus(text, sage)
    updated_bible = stage_story_synthesize(text, sage, focus, bible)
    agent_reply = build_agent_reply(sage, focus, updated_bible)

    turn = {
        "turn": int(session.get("turn_count", 0)) + 1,
        "recorded_at": now_iso(),
        "fragment": text,
        "sage": sage,
        "focus": focus,
        "agent_reply": agent_reply,
        "main_thread_after": updated_bible["main_thread"],
    }

    session["updated_at"] = now_iso()
    session["turn_count"] = turn["turn"]
    session["fragment_count"] = updated_bible["fragment_count"]

    append_ndjson(paths.fragments, {"recorded_at": turn["recorded_at"], "fragment": text})
    append_ndjson(paths.turns, turn)
    write_json(paths.session, session)
    write_json(paths.bible, updated_bible)

    return {
        "turn": turn,
        "session": session,
        "bible": updated_bible,
        "agent_reply": agent_reply,
        "paths": {
            "root": str(paths.root),
            "session": str(paths.session),
            "bible": str(paths.bible),
        },
    }


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
    active_threads = [
        item for item in recap.get("plot_threads", []) if item.get("status") == "active"
    ]
    if active_threads:
        print("活跃线索:")
        for item in active_threads[:8]:
            print(f"- {item['label']}")
    if recap.get("open_questions"):
        print("待对齐:")
        for question in recap["open_questions"][-5:]:
            print(f"- {question}")


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
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> dict[str, Any]:
    paths = resolve_story_paths(story_root, story_id, title)
    paths.root.mkdir(parents=True, exist_ok=True)
    session, bible = load_story_state(paths, title)

    output_fn("")
    output_fn("=== bedagent story · 口述模式 ===")
    output_fn(f"故事目录: {paths.root}")
    output_fn(f"标题: {session['title']} | 回合: {session.get('turn_count', 0)}")
    output_fn("像 vibe coding 一样讲：碎片、跳跃、重复都没关系。")
    output_fn("多行口述，空行发送。命令: /quit /recap /help")
    output_fn("")

    last_result: dict[str, Any] | None = None

    def handle_fragment(raw: str) -> dict[str, Any] | None:
        nonlocal session, bible, last_result
        result = process_fragment(paths, raw, session, bible)
        session = result["session"]
        bible = result["bible"]
        last_result = result
        output_fn("")
        output_fn(result["agent_reply"])
        output_fn("")
        return result

    if seed_fragment:
        handle_fragment(seed_fragment)

    while True:
        fragment = read_multiline_fragment(
            "继续口述（空行发送；/quit 退出，/recap 回顾）:",
            input_fn=input_fn,
        )
        if fragment is None:
            output_fn("（空输入，继续等待口述）")
            continue
        if fragment == "/quit":
            break
        if fragment == "/recap":
            print_story_recap(build_story_recap(bible, session))
            continue
        if fragment == "/help":
            output_fn("口述模式：躺着把故事讲出来，Sage 帮你对齐、Focus 帮你剪枝。")
            output_fn("命令: /recap 回顾 · /quit 退出")
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
    }
    if last_result:
        recap["last_turn"] = last_result["turn"]["turn"]
    return recap
