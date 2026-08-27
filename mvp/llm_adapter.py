"""Optional DashScope Qwen adapter for Sage question enhancement."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

DEFAULT_LLM_CONFIG_PATH = Path(__file__).with_name("llm_config.json")


def load_llm_config(path: Path | None = None) -> dict[str, Any]:
    config_path = path or DEFAULT_LLM_CONFIG_PATH
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    payload.setdefault("provider", "dashscope")
    payload.setdefault("model", "qwen-plus")
    payload.setdefault("timeout_seconds", 20)
    payload.setdefault("max_questions", 3)
    payload.setdefault("enabled_by_default", False)
    return payload


def llm_simulate_enabled() -> bool:
    return os.environ.get("BEDAGENT_LLM_SIMULATE", "").lower() in {"1", "true", "yes"}


def llm_requested(explicit: bool | None = None) -> bool:
    if explicit is True:
        return True
    if explicit is False:
        return False
    flag = os.environ.get("BEDAGENT_LLM", "").lower()
    if flag in {"1", "true", "yes"}:
        return True
    if flag in {"0", "false", "no"}:
        return False
    return False


def has_dashscope_key() -> bool:
    return bool(os.environ.get("DASHSCOPE_API_KEY", "").strip())


def llm_status(config: dict[str, Any] | None = None, explicit: bool | None = None) -> dict[str, Any]:
    config = config or load_llm_config()
    simulate = llm_simulate_enabled()
    requested = llm_requested(explicit)
    usable = requested and (simulate or has_dashscope_key())
    return {
        "requested": requested,
        "simulate": simulate,
        "has_key": has_dashscope_key(),
        "usable": usable,
        "model": "simulated-qwen" if simulate else config.get("model", "qwen-plus"),
        "provider": config.get("provider", "dashscope"),
    }


def simulate_story_questions(fragment: str, heuristic: list[str], max_questions: int = 3) -> list[str]:
    recap = re.split(r"[。！？.!?]", fragment.strip())[0].strip() or fragment[:40]
    extra = [
        f"「{recap[:36]}」之后，下一个不可逆选择是什么？",
        "这段口述里，谁的欲望和谁的规则在打架？",
        "如果删掉这句话，读者还会不会继续往下看？",
    ]
    merged: list[str] = []
    for item in list(heuristic) + extra:
        if item and item not in merged:
            merged.append(item)
        if len(merged) >= max_questions:
            break
    return merged[:max_questions]


def call_dashscope_generation(prompt: str, config: dict[str, Any]) -> str:
    try:
        import dashscope
        from dashscope import Generation
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("dashscope SDK not installed") from exc

    dashscope.api_key = os.environ.get("DASHSCOPE_API_KEY", "").strip()
    response = Generation.call(model=config.get("model", "qwen-plus"), prompt=prompt)
    if getattr(response, "status_code", 200) != 200:
        raise RuntimeError(getattr(response, "message", "DashScope generation failed"))
    output = getattr(response, "output", None)
    if isinstance(output, dict):
        text = output.get("text") or ""
        if not text and "choices" in output:
            text = output["choices"][0].get("message", {}).get("content", "")
        return str(text).strip()
    return str(output or "").strip()


def parse_questions_from_text(raw: str, fallback: list[str], max_questions: int) -> list[str]:
    lines = []
    for line in raw.splitlines():
        cleaned = re.sub(r"^[\s\-\d\.、)）]+", "", line).strip()
        if cleaned.endswith("?") or cleaned.endswith("？") or "？" in cleaned or "?" in cleaned:
            if cleaned not in lines:
                lines.append(cleaned)
    if len(lines) >= 2:
        return lines[:max_questions]
    return fallback[:max_questions]


def enhance_story_sage(
    fragment: str,
    bible: dict[str, Any],
    sage: dict[str, Any],
    config: dict[str, Any] | None = None,
    explicit: bool | None = None,
) -> dict[str, Any]:
    config = config or load_llm_config()
    status = llm_status(config, explicit=explicit)
    enhanced = dict(sage)
    enhanced["llm"] = {
        "used": False,
        "model": "heuristic",
        "provider": "none",
        "reason": "llm not requested",
    }
    if not status["usable"]:
        if status["requested"] and not status["has_key"] and not status["simulate"]:
            enhanced["llm"]["reason"] = "DASHSCOPE_API_KEY missing"
        return enhanced

    max_q = int(config.get("max_questions", 3))
    heuristic = list(sage.get("key_questions") or [])
    if status["simulate"]:
        questions = simulate_story_questions(fragment, heuristic, max_q)
        enhanced["key_questions"] = questions
        enhanced["llm"] = {
            "used": True,
            "model": "simulated-qwen",
            "provider": "simulated",
            "reason": "BEDAGENT_LLM_SIMULATE",
        }
        return enhanced

    prompt = (
        "你是 bedagent 的 Sage。根据口述片段和当前故事主线，提出最多 "
        f"{max_q} 个短问题，帮助作者对齐动机、时间线和冲突。只输出问题，每行一个。\n"
        f"主线：{bible.get('main_thread', '')}\n"
        f"口述：{fragment}\n"
        f"启发式问题：{heuristic}"
    )
    try:
        raw = call_dashscope_generation(prompt, config)
        questions = parse_questions_from_text(raw, heuristic, max_q)
        enhanced["key_questions"] = questions
        enhanced["llm"] = {
            "used": True,
            "model": config.get("model", "qwen-plus"),
            "provider": "dashscope",
            "reason": "generation",
        }
    except Exception as exc:  # pragma: no cover - network guardrail
        enhanced["llm"] = {
            "used": False,
            "model": "heuristic",
            "provider": "dashscope",
            "reason": f"fallback: {exc}",
        }
    return enhanced
