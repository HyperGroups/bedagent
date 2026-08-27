"""DashScope (百炼) voice adapter: ASR + TTS for bedagent."""

from __future__ import annotations

import json
import math
import os
import re
import shlex
import shutil
import struct
import subprocess
import wave
from dataclasses import dataclass, field
from http import HTTPStatus
from pathlib import Path
from typing import Any, Callable

DEFAULT_VOICE_CONFIG_PATH = Path(__file__).with_name("voice_config.json")

AUDIO_FORMAT_BY_SUFFIX = {
    ".wav": "wav",
    ".mp3": "mp3",
    ".pcm": "pcm",
    ".opus": "opus",
    ".speex": "speex",
    ".aac": "aac",
    ".amr": "amr",
}


class VoiceAdapterError(RuntimeError):
    """Raised when voice adapter configuration or provider calls fail."""


@dataclass
class TranscribeResult:
    text: str
    model: str
    audio_path: str
    request_id: str
    raw_sentence: Any


@dataclass
class SpeakResult:
    text: str
    output_path: str
    model: str
    voice: str
    byte_size: int


@dataclass
class TranscribeStreamResult:
    text: str
    model: str
    audio_path: str
    request_id: str
    partials: list[dict[str, Any]]
    skipped: bool = False
    skip_reason: str = ""
    silence_ratio: float = 0.0
    command: str | None = None


@dataclass
class VadSegment:
    index: int
    start_ms: int
    end_ms: int
    start_frame: int
    end_frame: int
    energy: float
    path: str = ""


@dataclass
class TranscribeVadResult:
    text: str
    model: str
    audio_path: str
    skipped: bool
    skip_reason: str
    silence_ratio: float
    segments: list[VadSegment]
    utterances: list[TranscribeStreamResult]
    command: str | None = None
    joined_text: str = ""


@dataclass
class SpeakStreamResult:
    text: str
    sentences: list[SpeakResult] = field(default_factory=list)
    output_paths: list[str] = field(default_factory=list)
    model: str = ""
    voice: str = ""


def load_voice_config(path: Path | None = None) -> dict[str, Any]:
    config_path = path or DEFAULT_VOICE_CONFIG_PATH
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    payload.setdefault("asr_model", "fun-asr-realtime")
    payload.setdefault("tts_model", "cosyvoice-v3-flash")
    payload.setdefault("tts_voice", "longxiaochun")
    payload.setdefault("sample_rate", 16000)
    payload.setdefault("max_tts_chars", 220)
    payload.setdefault("quiet_mode", False)
    payload.setdefault("quiet_max_tts_chars", 72)
    payload.setdefault("secret_block_keywords", [])
    payload.setdefault("region", "cn-beijing")
    payload.setdefault("workspace_id", "")
    payload.setdefault("mic_seconds", 8)
    payload.setdefault("stream_partial_chars", 8)
    payload.setdefault("silence_skip_ratio", 0.97)
    payload.setdefault("stream_frame_bytes", 3200)
    payload.setdefault("provider", "auto")
    payload.setdefault("vad_frame_ms", 30)
    payload.setdefault("vad_energy_threshold", 500)
    payload.setdefault("vad_min_speech_ms", 180)
    payload.setdefault("vad_max_silence_ms", 400)
    payload.setdefault("vad_padding_ms", 80)
    payload.setdefault("local_asr_command", "")
    payload.setdefault("local_tts_command", "")
    return payload


def tts_quiet_enabled(config: dict[str, Any] | None = None, quiet: bool | None = None) -> bool:
    if quiet is True:
        return True
    if os.environ.get("BEDAGENT_TTS_QUIET", "").lower() in {"1", "true", "yes"}:
        return True
    return bool((config or {}).get("quiet_mode"))


def apply_quiet_config(config: dict[str, Any] | None, quiet: bool | None = None) -> dict[str, Any]:
    payload = dict(config or load_voice_config())
    if tts_quiet_enabled(payload, quiet=quiet):
        payload["quiet_mode"] = True
        quiet_limit = int(payload.get("quiet_max_tts_chars", 72))
        payload["max_tts_chars"] = min(int(payload.get("max_tts_chars", 220)), quiet_limit)
    return payload


def require_dashscope():
    try:
        import dashscope  # type: ignore
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise VoiceAdapterError(
            "dashscope SDK not installed. Run: pip install -r mvp/requirements-voice.txt"
        ) from exc
    return dashscope


def get_api_key() -> str:
    key = os.environ.get("DASHSCOPE_API_KEY", "").strip()
    if not key:
        raise VoiceAdapterError(
            "DASHSCOPE_API_KEY is not set. Export your 百炼 API Key before using voice commands."
        )
    return key


def configure_dashscope(config: dict[str, Any]) -> None:
    dashscope = require_dashscope()
    dashscope.api_key = get_api_key()
    workspace_id = os.environ.get("DASHSCOPE_WORKSPACE_ID", "").strip() or str(
        config.get("workspace_id", "")
    ).strip()
    if workspace_id:
        region = config.get("region", "cn-beijing")
        dashscope.base_websocket_api_url = (
            f"wss://{workspace_id}.{region}.maas.aliyuncs.com/api-ws/v1/inference"
        )


def detect_audio_format(audio_path: Path) -> str:
    suffix = audio_path.suffix.lower()
    if suffix not in AUDIO_FORMAT_BY_SUFFIX:
        raise VoiceAdapterError(
            f"Unsupported audio format '{suffix}'. Supported: {', '.join(sorted(AUDIO_FORMAT_BY_SUFFIX))}"
        )
    return AUDIO_FORMAT_BY_SUFFIX[suffix]


def extract_transcript_sentence(sentence: Any) -> str:
    if sentence is None:
        return ""
    if isinstance(sentence, str):
        return sentence.strip()
    if isinstance(sentence, dict):
        if "text" in sentence:
            return clean_text(str(sentence.get("text") or ""))
        for key in ("sentence", "result"):
            value = sentence.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""
    if isinstance(sentence, list):
        parts: list[str] = []
        for item in sentence:
            part = extract_transcript_sentence(item)
            if part:
                parts.append(part)
        return clean_text(" ".join(parts))
    return clean_text(str(sentence))


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def simulated_transcript_sidecar(audio_path: Path) -> Path:
    return audio_path.with_name(f"{audio_path.stem}.transcript.txt")


def transcribe_simulated(audio_path: Path) -> TranscribeResult | None:
    path = audio_path.expanduser().resolve()
    sidecar = simulated_transcript_sidecar(path)
    if not sidecar.exists():
        return None
    text = sidecar.read_text(encoding="utf-8").strip()
    if not text:
        raise VoiceAdapterError(f"Simulated transcript sidecar is empty: {sidecar}")
    return TranscribeResult(
        text=text,
        model="simulated-asr",
        audio_path=str(path),
        request_id="simulated",
        raw_sentence={"text": text, "simulated": True},
    )


def transcribe_file(
    audio_path: Path,
    config: dict[str, Any] | None = None,
    config_path: Path | None = None,
) -> TranscribeResult:
    path = audio_path.expanduser().resolve()
    if not path.exists():
        raise VoiceAdapterError(f"Audio file not found: {path}")

    simulated = transcribe_simulated(path)
    if simulated is not None:
        return simulated

    config = config or load_voice_config(config_path)
    provider = resolve_asr_provider(config)
    if provider == "local" or (
        provider == "auto" and not os.environ.get("DASHSCOPE_API_KEY", "").strip()
    ):
        local = transcribe_local(path, config=config)
        if local is not None:
            return local
        if provider == "local":
            raise VoiceAdapterError(
                "Local ASR is not available. Set BEDAGENT_WHISPER_CMD or install whisper."
            )

    configure_dashscope(config)
    from dashscope.audio.asr import Recognition

    recognition = Recognition(
        model=config["asr_model"],
        format=detect_audio_format(path),
        sample_rate=int(config["sample_rate"]),
        callback=None,
    )
    result = recognition.call(str(path))
    if result.status_code != HTTPStatus.OK:
        message = getattr(result, "message", "unknown ASR error")
        raise VoiceAdapterError(f"DashScope ASR failed: {message}")

    text = extract_transcript_sentence(result.get_sentence())
    if not text:
        raise VoiceAdapterError("DashScope ASR returned empty transcript.")

    return TranscribeResult(
        text=text,
        model=config["asr_model"],
        audio_path=str(path),
        request_id=str(getattr(recognition, "get_last_request_id", lambda: "")() or ""),
        raw_sentence=result.get_sentence(),
    )


def split_transcript_partials(text: str, step: int = 8) -> list[str]:
    cleaned = clean_text(text)
    if not cleaned:
        return []
    step = max(2, int(step))
    partials: list[str] = []
    if re.search(r"[\u4e00-\u9fff]", cleaned) or " " not in cleaned:
        for end in range(step, len(cleaned), step):
            partials.append(cleaned[:end])
        partials.append(cleaned)
    else:
        words = cleaned.split()
        acc: list[str] = []
        for word in words:
            acc.append(word)
            if len(acc) % max(1, step // 4) == 0 or word == words[-1]:
                partials.append(" ".join(acc))
        if not partials or partials[-1] != cleaned:
            partials.append(cleaned)
    unique: list[str] = []
    for item in partials:
        if item and (not unique or item != unique[-1]):
            unique.append(item)
    if unique[-1] != cleaned:
        unique.append(cleaned)
    return unique


def iter_wav_pcm_chunks(audio_path: Path, frame_bytes: int = 3200) -> list[bytes]:
    path = audio_path.expanduser().resolve()
    with wave.open(str(path), "rb") as handle:
        raw = handle.readframes(handle.getnframes())
    size = max(640, int(frame_bytes))
    return [raw[index : index + size] for index in range(0, len(raw), size)] if raw else []


def voice_status(config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = apply_quiet_config(config or load_voice_config())
    return {
        "provider": resolve_asr_provider(config),
        "asr_model": config.get("asr_model"),
        "tts_model": config.get("tts_model"),
        "tts_voice": config.get("tts_voice"),
        "has_key": bool(os.environ.get("DASHSCOPE_API_KEY", "").strip()),
        "tts_simulate": os.environ.get("BEDAGENT_TTS_SIMULATE", "").lower() in {"1", "true", "yes"},
        "quiet": bool(config.get("quiet_mode")),
        "stream_partial_chars": int(config.get("stream_partial_chars", 8)),
        "silence_skip_ratio": float(config.get("silence_skip_ratio", 0.97)),
        "vad_frame_ms": int(config.get("vad_frame_ms", 30)),
        "vad_energy_threshold": int(config.get("vad_energy_threshold", 500)),
        "vad_min_speech_ms": int(config.get("vad_min_speech_ms", 180)),
        "vad_max_silence_ms": int(config.get("vad_max_silence_ms", 400)),
        "local_asr": local_asr_available(config),
        "local_tts": local_tts_available(config),
    }


def resolve_asr_provider(config: dict[str, Any] | None = None) -> str:
    config = config or load_voice_config()
    raw = str(os.environ.get("BEDAGENT_VOICE_PROVIDER") or config.get("provider") or "auto").strip().lower()
    if raw in {"dashscope", "local", "simulated"}:
        return raw
    if os.environ.get("DASHSCOPE_API_KEY", "").strip():
        return "dashscope"
    if local_asr_available(config):
        return "local"
    return "auto"


def local_asr_available(config: dict[str, Any] | None = None) -> bool:
    config = config or {}
    if str(config.get("local_asr_command") or os.environ.get("BEDAGENT_WHISPER_CMD") or "").strip():
        return True
    return any(shutil.which(name) for name in ("whisper", "whisper-cli", "faster-whisper"))


def local_tts_available(config: dict[str, Any] | None = None) -> bool:
    config = config or {}
    if str(config.get("local_tts_command") or os.environ.get("BEDAGENT_PIPER_CMD") or "").strip():
        return True
    return shutil.which("piper") is not None


def transcribe_stream(
    audio_path: Path,
    config: dict[str, Any] | None = None,
    config_path: Path | None = None,
    on_partial: Callable[[str, bool], None] | None = None,
    stream: bool = True,
) -> TranscribeStreamResult:
    path = audio_path.expanduser().resolve()
    if not path.exists():
        raise VoiceAdapterError(f"Audio file not found: {path}")
    config = apply_quiet_config(config or load_voice_config(config_path))
    silence_ratio = 0.0
    try:
        silence_ratio = wav_silence_ratio(path)
    except Exception:
        silence_ratio = 0.0

    def emit(text: str, is_final: bool, model: str, request_id: str, skipped: bool = False, reason: str = "", command: str | None = None, extra_partials: list[str] | None = None) -> TranscribeStreamResult:
        step = int(config.get("stream_partial_chars", 8))
        parts = extra_partials if extra_partials is not None else (split_transcript_partials(text, step) if text else [])
        partials = [{"index": idx, "text": item, "is_final": bool(is_final and item == parts[-1])} for idx, item in enumerate(parts, start=1)]
        if on_partial:
            for item in partials:
                on_partial(item["text"], bool(item["is_final"]))
        return TranscribeStreamResult(
            text=text,
            model=model,
            audio_path=str(path),
            request_id=request_id,
            partials=partials,
            skipped=skipped,
            skip_reason=reason,
            silence_ratio=round(silence_ratio, 4),
            command=command,
        )

    simulated = transcribe_simulated(path)
    if simulated is not None:
        mapped = map_voice_command(simulated.text, config)
        return emit(
            simulated.text,
            True,
            simulated.model,
            simulated.request_id,
            skipped=bool(mapped),
            reason=f"command:{mapped}" if mapped else "",
            command=mapped,
        )

    skip_ratio = float(config.get("silence_skip_ratio", 0.97))
    if silence_ratio >= skip_ratio:
        return emit("", True, "silence-gate", "silence", skipped=True, reason="silence", extra_partials=[])

    if stream:
        try:
            live = _transcribe_dashscope_stream(path, config, on_partial)
            if live is not None:
                mapped = map_voice_command(live.text, config)
                live.command = mapped
                if mapped:
                    live.skipped = True
                    live.skip_reason = f"command:{mapped}"
                live.silence_ratio = round(silence_ratio, 4)
                return live
        except Exception:
            pass

    try:
        final = transcribe_file(path, config=config, config_path=config_path)
    except VoiceAdapterError:
        local = transcribe_local(path, config=config)
        if local is None:
            raise
        final = local
    mapped = map_voice_command(final.text, config)
    return emit(
        final.text,
        True,
        final.model,
        final.request_id,
        skipped=bool(mapped),
        reason=f"command:{mapped}" if mapped else "",
        command=mapped,
    )


def _transcribe_dashscope_stream(
    audio_path: Path,
    config: dict[str, Any],
    on_partial: Callable[[str, bool], None] | None,
) -> TranscribeStreamResult | None:
    if not os.environ.get("DASHSCOPE_API_KEY", "").strip():
        return None
    if detect_audio_format(audio_path) != "wav":
        return None
    configure_dashscope(config)
    from dashscope.audio.asr import Recognition, RecognitionCallback

    collected: list[str] = []
    errors: list[str] = []

    class PartialCallback(RecognitionCallback):
        def on_event(self, result) -> None:  # noqa: ANN001
            payload = result.get_sentence() if hasattr(result, "get_sentence") else result
            text = extract_transcript_sentence(payload)
            if not text:
                return
            collected.append(text)
            if on_partial:
                is_final = bool(getattr(result, "is_sentence_end", lambda: False)())
                on_partial(text, is_final)

        def on_error(self, result) -> None:  # noqa: ANN001
            errors.append(str(getattr(result, "message", result)))

    recognition = Recognition(
        model=config["asr_model"],
        format="pcm",
        sample_rate=int(config["sample_rate"]),
        callback=PartialCallback(),
    )
    recognition.start()
    try:
        for chunk in iter_wav_pcm_chunks(audio_path, int(config.get("stream_frame_bytes", 3200))):
            recognition.send_audio_frame(chunk)
    finally:
        recognition.stop()
    if errors and not collected:
        raise VoiceAdapterError(errors[0])
    if not collected:
        return None
    unique: list[str] = []
    for item in collected:
        if not unique or item != unique[-1]:
            unique.append(item)
    final = unique[-1]
    partials = [{"index": idx, "text": item, "is_final": item == final} for idx, item in enumerate(unique, start=1)]
    return TranscribeStreamResult(
        text=final,
        model=config["asr_model"],
        audio_path=str(audio_path),
        request_id=str(getattr(recognition, "get_last_request_id", lambda: "")() or ""),
        partials=partials,
    )


def sanitize_tts_text(text: str, config: dict[str, Any]) -> str:
    cleaned = clean_text(text)
    lowered = cleaned.lower()
    for keyword in config.get("secret_block_keywords", []):
        if keyword.lower() in lowered:
            return "收到。详情请查看屏幕摘要，这里不朗读敏感内容。"
    max_chars = int(config.get("max_tts_chars", 220))
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 3].rstrip() + "..."


def build_tts_summary(agent_reply: str, config: dict[str, Any] | None = None) -> str:
    config = apply_quiet_config(config or load_voice_config())
    lines = [line.strip() for line in agent_reply.splitlines() if line.strip()]
    if not lines:
        return "收到。"
    preferred: list[str] = []
    for line in lines:
        if line.startswith("我听懂了：") or line.startswith("收到对齐："):
            preferred.append(line.split("：", 1)[-1])
            break
    if not preferred and lines:
        preferred.append(lines[0])
    for line in lines:
        if line.startswith("当前主线："):
            preferred.append(line.split("：", 1)[-1])
            break
    summary = "。".join(item for item in preferred if item)
    if not summary:
        summary = lines[0]
    if tts_quiet_enabled(config):
        summary = preferred[0] if preferred else lines[0]
    return sanitize_tts_text(summary, config)


def synthesize_speech(
    text: str,
    output_path: Path,
    config: dict[str, Any] | None = None,
    config_path: Path | None = None,
) -> SpeakResult:
    config = apply_quiet_config(config or load_voice_config(config_path))
    speak_text = sanitize_tts_text(text, config)
    if not speak_text:
        raise VoiceAdapterError("TTS text is empty after sanitization.")

    out = output_path.expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    if os.environ.get("BEDAGENT_TTS_SIMULATE", "").lower() in {"1", "true", "yes"}:
        write_silent_wav(out, seconds=0.25)
        data = out.read_bytes()
        return SpeakResult(
            text=speak_text,
            output_path=str(out),
            model="simulated-tts",
            voice="simulated",
            byte_size=len(data),
        )

    provider = resolve_asr_provider(config)
    if provider == "local" or (provider == "auto" and not os.environ.get("DASHSCOPE_API_KEY", "").strip()):
        local = synthesize_local(speak_text, out, config)
        if local is not None:
            return local

    configure_dashscope(config)
    from dashscope.audio.tts_v2 import SpeechSynthesizer

    synthesizer = SpeechSynthesizer(
        model=config["tts_model"],
        voice=config["tts_voice"],
    )
    audio = synthesizer.call(speak_text)
    if audio is None:
        local = synthesize_local(speak_text, out, config)
        if local is not None:
            return local
        raise VoiceAdapterError("DashScope TTS returned empty audio.")

    out.write_bytes(audio)

    return SpeakResult(
        text=speak_text,
        output_path=str(out),
        model=config["tts_model"],
        voice=config["tts_voice"],
        byte_size=len(audio),
    )


SLASH_BY_COMMAND = {
    "recap": "/recap",
    "quit": "/quit",
    "pause": "/pause",
    "cancel": "/quit",
    "continue": "/continue",
    "draft": "/draft",
    "export": "/export",
    "expand": "/expand",
    "quiet": "/quiet",
    "characters": "/characters",
    "answer": "/answer",
    "resume": "/resume",
}


def map_voice_command(text: str, config: dict[str, Any]) -> str | None:
    normalized = clean_text(text).lower()
    if not normalized:
        return None
    if normalized.startswith("/"):
        return normalized.split()[0]
    commands = config.get("voice_commands", {})
    for command, phrases in commands.items():
        for phrase in phrases:
            if normalized == phrase.lower() or normalized.startswith(phrase.lower()):
                return SLASH_BY_COMMAND.get(command, f"/{command}")
    return None


def transcribe_local(audio_path: Path, config: dict[str, Any] | None = None) -> TranscribeResult | None:
    path = audio_path.expanduser().resolve()
    simulated = transcribe_simulated(path)
    if simulated is not None:
        return TranscribeResult(
            text=simulated.text,
            model="local-whisper-simulated",
            audio_path=simulated.audio_path,
            request_id="local-simulated",
            raw_sentence={"text": simulated.text, "simulated": True, "local": True},
        )
    command = str(
        os.environ.get("BEDAGENT_WHISPER_CMD") or (config or {}).get("local_asr_command") or ""
    ).strip()
    if command:
        rendered = command.format(audio=str(path), input=str(path))
        completed = subprocess.run(
            shlex.split(rendered),
            check=False,
            capture_output=True,
            text=True,
        )
        text = clean_text(completed.stdout or "")
        if completed.returncode != 0 and not text:
            raise VoiceAdapterError(clean_text(completed.stderr or "local ASR command failed"))
        if not text:
            return None
        return TranscribeResult(
            text=text,
            model="local-whisper",
            audio_path=str(path),
            request_id="local",
            raw_sentence={"text": text, "local": True},
        )
    binary = next((name for name in ("whisper", "whisper-cli") if shutil.which(name)), None)
    if not binary:
        return None
    completed = subprocess.run(
        [binary, str(path), "--language", "zh", "--output_format", "txt", "--output_dir", str(path.parent)],
        check=False,
        capture_output=True,
        text=True,
    )
    sidecar = path.with_suffix(".txt")
    text = sidecar.read_text(encoding="utf-8").strip() if sidecar.exists() else clean_text(completed.stdout or "")
    if not text:
        return None
    return TranscribeResult(
        text=text,
        model="local-whisper",
        audio_path=str(path),
        request_id="local",
        raw_sentence={"text": text, "local": True},
    )


def synthesize_local(text: str, output_path: Path, config: dict[str, Any]) -> SpeakResult | None:
    out = output_path.expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    command = str(os.environ.get("BEDAGENT_PIPER_CMD") or config.get("local_tts_command") or "").strip()
    if command:
        rendered = command.format(output=str(out), text=text)
        completed = subprocess.run(
            shlex.split(rendered) + ([text] if "{text}" not in command else []),
            check=False,
            capture_output=True,
            text=True,
            input=text if "{text}" not in command else None,
        )
        if completed.returncode != 0 and not out.exists():
            raise VoiceAdapterError(clean_text(completed.stderr or "local TTS command failed"))
        if out.exists():
            data = out.read_bytes()
            return SpeakResult(
                text=text,
                output_path=str(out),
                model="local-piper",
                voice="local",
                byte_size=len(data),
            )
        return None
    if not shutil.which("piper"):
        return None
    completed = subprocess.run(
        ["piper", "--output_file", str(out)],
        check=False,
        capture_output=True,
        text=True,
        input=text,
    )
    if completed.returncode != 0 and not out.exists():
        return None
    if not out.exists():
        return None
    data = out.read_bytes()
    return SpeakResult(
        text=text,
        output_path=str(out),
        model="local-piper",
        voice="local",
        byte_size=len(data),
    )


def split_tts_sentences(text: str) -> list[str]:
    cleaned = clean_text(text)
    if not cleaned:
        return []
    parts = [item.strip() for item in re.split(r"(?<=[。！？!?；;])\s*", cleaned) if item.strip()]
    return parts or [cleaned]


def synthesize_speech_stream(
    text: str,
    output_dir: Path,
    config: dict[str, Any] | None = None,
    config_path: Path | None = None,
    stem: str = "sentence",
) -> SpeakStreamResult:
    config = apply_quiet_config(config or load_voice_config(config_path))
    speak_text = sanitize_tts_text(text, config)
    sentences = split_tts_sentences(speak_text)
    if not sentences:
        raise VoiceAdapterError("TTS text is empty after sanitization.")
    target = output_dir.expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)
    results: list[SpeakResult] = []
    for index, sentence in enumerate(sentences, start=1):
        out = target / f"{stem}-{index:02d}.wav"
        results.append(synthesize_speech(sentence, out, config=config))
    return SpeakStreamResult(
        text=speak_text,
        sentences=results,
        output_paths=[item.output_path for item in results],
        model=results[0].model,
        voice=results[0].voice,
    )


def split_text_for_segments(text: str, count: int) -> list[str]:
    cleaned = clean_text(text)
    if count <= 1:
        return [cleaned]
    parts = [item.strip() for item in re.split(r"(?<=[。！？!?])\s*", cleaned) if item.strip()]
    if not parts:
        return [cleaned] + [""] * (count - 1)
    if len(parts) == count:
        return parts
    if len(parts) > count:
        return parts[: count - 1] + [clean_text(" ".join(parts[count - 1 :]))]
    return parts + [""] * (count - len(parts))


def read_wav_pcm16(audio_path: Path) -> tuple[list[int], int]:
    path = audio_path.expanduser().resolve()
    with wave.open(str(path), "rb") as handle:
        channels = max(1, handle.getnchannels())
        width = handle.getsampwidth()
        rate = handle.getframerate()
        frames = handle.getnframes()
        raw = handle.readframes(frames)
    if width != 2 or frames <= 0:
        return [], rate or 16000
    sample_count = frames * channels
    samples = list(struct.unpack("<" + "h" * sample_count, raw[: sample_count * 2]))
    if channels == 1:
        return samples, rate
    mixed: list[int] = []
    for index in range(0, len(samples), channels):
        mixed.append(int(sum(samples[index : index + channels]) / channels))
    return mixed, rate


def write_wav_pcm16(output_path: Path, samples: list[int], sample_rate: int = 16000) -> Path:
    out = output_path.expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    clipped = [max(-32768, min(32767, int(sample))) for sample in samples]
    payload = struct.pack("<" + "h" * len(clipped), *clipped) if clipped else b"\x00\x00"
    with wave.open(str(out), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(payload)
    return out


def write_tone_wav(
    output_path: Path,
    seconds: float = 0.4,
    freq: float = 440.0,
    sample_rate: int = 16000,
    amplitude: int = 9000,
) -> Path:
    frame_count = max(1, int(sample_rate * seconds))
    samples = [
        int(amplitude * math.sin(2 * math.pi * freq * index / sample_rate))
        for index in range(frame_count)
    ]
    return write_wav_pcm16(output_path, samples, sample_rate=sample_rate)


def concat_wav_pcm16(output_path: Path, parts: list[Path], sample_rate: int | None = None) -> Path:
    samples: list[int] = []
    rate = sample_rate or 16000
    for part in parts:
        chunk, chunk_rate = read_wav_pcm16(part)
        rate = chunk_rate or rate
        samples.extend(chunk)
    return write_wav_pcm16(output_path, samples, sample_rate=rate)


def extract_wav_slice(
    audio_path: Path,
    output_path: Path,
    start_frame: int,
    end_frame: int,
) -> Path:
    samples, rate = read_wav_pcm16(audio_path)
    start = max(0, int(start_frame))
    end = min(len(samples), max(start + 1, int(end_frame)))
    return write_wav_pcm16(output_path, samples[start:end], sample_rate=rate)


def vad_segments(
    audio_path: Path,
    config: dict[str, Any] | None = None,
) -> list[VadSegment]:
    config = config or load_voice_config()
    samples, rate = read_wav_pcm16(audio_path)
    if not samples or rate <= 0:
        return []
    frame_ms = max(10, int(config.get("vad_frame_ms", 30)))
    frame_len = max(1, int(rate * frame_ms / 1000))
    threshold = int(config.get("vad_energy_threshold", 500))
    min_speech_ms = int(config.get("vad_min_speech_ms", 180))
    max_silence_ms = int(config.get("vad_max_silence_ms", 400))
    padding_ms = int(config.get("vad_padding_ms", 80))
    peak = max(abs(sample) for sample in samples)
    adaptive = max(threshold, int(peak * 0.12)) if peak else threshold

    energies: list[float] = []
    for index in range(0, len(samples), frame_len):
        frame = samples[index : index + frame_len]
        if not frame:
            continue
        rms = math.sqrt(sum(sample * sample for sample in frame) / len(frame))
        energies.append(rms)

    flags = [energy >= adaptive for energy in energies]
    hangover = max(1, int(max_silence_ms / frame_ms))
    min_frames = max(1, int(min_speech_ms / frame_ms))
    pad_frames = max(0, int(padding_ms / frame_ms))

    raw: list[tuple[int, int]] = []
    in_speech = False
    start = 0
    silence_run = 0
    for index, spoken in enumerate(flags):
        if spoken:
            if not in_speech:
                in_speech = True
                start = index
            silence_run = 0
        elif in_speech:
            silence_run += 1
            if silence_run >= hangover:
                end = index - silence_run + 1
                if end - start >= min_frames:
                    raw.append((start, end))
                in_speech = False
                silence_run = 0
    if in_speech:
        end = len(flags) - silence_run
        if end - start >= min_frames:
            raw.append((start, max(end, start + min_frames)))

    segments: list[VadSegment] = []
    for index, (start_frame, end_frame) in enumerate(raw, start=1):
        padded_start = max(0, start_frame - pad_frames)
        padded_end = min(len(flags), end_frame + pad_frames)
        sample_start = padded_start * frame_len
        sample_end = min(len(samples), padded_end * frame_len)
        window = samples[sample_start:sample_end] or [0]
        energy = math.sqrt(sum(sample * sample for sample in window) / len(window))
        segments.append(
            VadSegment(
                index=index,
                start_ms=int(sample_start * 1000 / rate),
                end_ms=int(sample_end * 1000 / rate),
                start_frame=sample_start,
                end_frame=sample_end,
                energy=round(energy, 2),
            )
        )
    return segments


def transcribe_vad(
    audio_path: Path,
    config: dict[str, Any] | None = None,
    config_path: Path | None = None,
    output_dir: Path | None = None,
    on_partial: Callable[[str, bool], None] | None = None,
) -> TranscribeVadResult:
    path = audio_path.expanduser().resolve()
    if not path.exists():
        raise VoiceAdapterError(f"Audio file not found: {path}")
    config = apply_quiet_config(config or load_voice_config(config_path))
    silence_ratio = 0.0
    try:
        silence_ratio = wav_silence_ratio(path)
    except Exception:
        silence_ratio = 0.0

    segments = vad_segments(path, config)
    parent_sidecar = transcribe_simulated(path)
    if not segments:
        stream = transcribe_stream(path, config=config, config_path=config_path, on_partial=on_partial)
        return TranscribeVadResult(
            text=stream.text,
            model=stream.model,
            audio_path=str(path),
            skipped=stream.skipped,
            skip_reason=stream.skip_reason or ("silence" if not stream.text else ""),
            silence_ratio=round(silence_ratio, 4),
            segments=[],
            utterances=[stream] if stream.text or stream.skipped else [],
            command=stream.command,
            joined_text=stream.text,
        )

    target = (output_dir or path.parent / f"{path.stem}-vad").expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)
    slice_paths: list[Path] = []
    for segment in segments:
        slice_path = target / f"seg-{segment.index:02d}.wav"
        extract_wav_slice(path, slice_path, segment.start_frame, segment.end_frame)
        segment.path = str(slice_path)
        slice_paths.append(slice_path)

    if parent_sidecar is not None:
        parts = split_text_for_segments(parent_sidecar.text, len(slice_paths))
        for slice_path, part in zip(slice_paths, parts):
            if part:
                simulated_transcript_sidecar(slice_path).write_text(part + "\n", encoding="utf-8")

    utterances: list[TranscribeStreamResult] = []
    for slice_path in slice_paths:
        sidecar = simulated_transcript_sidecar(slice_path)
        if not sidecar.exists() and parent_sidecar is not None:
            continue
        utterances.append(
            transcribe_stream(slice_path, config=config, config_path=config_path, on_partial=on_partial)
        )

    spoken = [item for item in utterances if item.text and not (item.skipped and item.skip_reason == "silence")]
    joined = clean_text(" ".join(item.text for item in spoken))
    command = next((item.command for item in utterances if item.command), None)
    skipped = not spoken
    skip_reason = ""
    if skipped:
        skip_reason = command or "silence"
    model = spoken[0].model if spoken else (utterances[0].model if utterances else "vad")
    return TranscribeVadResult(
        text=joined,
        model=model,
        audio_path=str(path),
        skipped=skipped,
        skip_reason=skip_reason if skipped else "",
        silence_ratio=round(silence_ratio, 4),
        segments=segments,
        utterances=utterances,
        command=command if skipped else None,
        joined_text=joined,
    )


def wav_silence_ratio(audio_path: Path, threshold: int = 400) -> float:
    path = audio_path.expanduser().resolve()
    with wave.open(str(path), "rb") as handle:
        channels = max(1, handle.getnchannels())
        width = handle.getsampwidth()
        frames = handle.getnframes()
        raw = handle.readframes(frames)
    sample_count = frames * channels
    if sample_count <= 0 or width != 2 or len(raw) < sample_count * 2:
        return 1.0 if sample_count <= 0 else 0.0
    samples = struct.unpack("<" + "h" * sample_count, raw[: sample_count * 2])
    silent = sum(1 for sample in samples if abs(sample) < threshold)
    return silent / sample_count


def record_microphone_wav(
    output_path: Path,
    seconds: float,
    sample_rate: int = 16000,
) -> Path:
    try:
        import sounddevice as sd
        import soundfile as sf
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise VoiceAdapterError(
            "Microphone recording requires sounddevice and soundfile. "
            "Run: pip install -r mvp/requirements-voice.txt"
        ) from exc

    duration = max(1.0, float(seconds))
    frames = int(duration * sample_rate)
    audio = sd.rec(frames, samplerate=sample_rate, channels=1, dtype="float32")
    sd.wait()
    out = output_path.expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out), audio, sample_rate, subtype="PCM_16")
    return out


def write_silent_wav(output_path: Path, sample_rate: int = 16000, seconds: float = 0.2) -> Path:
    out = output_path.expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    frame_count = max(1, int(sample_rate * seconds))
    with wave.open(str(out), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(b"\x00\x00" * frame_count)
    return out


def play_audio_file(audio_path: Path) -> bool:
    path = audio_path.expanduser().resolve()
    if not path.exists():
        return False
    try:
        import sounddevice as sd
        import soundfile as sf
    except ImportError:
        return False
    data, sample_rate = sf.read(str(path), dtype="float32")
    sd.play(data, sample_rate)
    sd.wait()
    return True


def voice_turn_paths(voice_dir: Path, turn_number: int) -> dict[str, Path]:
    voice_dir.mkdir(parents=True, exist_ok=True)
    stem = f"turn-{turn_number:03d}"
    return {
        "input": voice_dir / f"{stem}-input.wav",
        "transcript": voice_dir / f"{stem}-transcript.txt",
        "reply_text": voice_dir / f"{stem}-reply.txt",
        "reply_audio": voice_dir / f"{stem}-reply.wav",
        "partials": voice_dir / f"{stem}-partials.json",
        "vad": voice_dir / f"{stem}-vad.json",
        "sentences": voice_dir / f"{stem}-sentences.json",
    }


def persist_voice_turn_artifacts(
    paths: dict[str, Path],
    transcript: str,
    agent_reply: str,
    input_audio: Path | None = None,
    partials: list[dict[str, Any]] | None = None,
    vad: dict[str, Any] | None = None,
    sentences: list[dict[str, Any]] | None = None,
) -> None:
    if input_audio and input_audio.exists():
        paths["input"].write_bytes(input_audio.read_bytes())
    paths["transcript"].write_text(transcript + "\n", encoding="utf-8")
    paths["reply_text"].write_text(agent_reply + "\n", encoding="utf-8")
    if partials is not None and "partials" in paths:
        paths["partials"].write_text(
            json.dumps({"partials": partials}, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    if vad is not None and "vad" in paths:
        paths["vad"].write_text(json.dumps(vad, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if sentences is not None and "sentences" in paths:
        paths["sentences"].write_text(
            json.dumps({"sentences": sentences}, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
