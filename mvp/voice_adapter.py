"""DashScope (百炼) voice adapter: ASR + TTS for bedagent."""

from __future__ import annotations

import json
import os
import re
import wave
from dataclasses import dataclass
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


def load_voice_config(path: Path | None = None) -> dict[str, Any]:
    config_path = path or DEFAULT_VOICE_CONFIG_PATH
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    payload.setdefault("asr_model", "fun-asr-realtime")
    payload.setdefault("tts_model", "cosyvoice-v3-flash")
    payload.setdefault("tts_voice", "longxiaochun")
    payload.setdefault("sample_rate", 16000)
    payload.setdefault("max_tts_chars", 220)
    payload.setdefault("secret_block_keywords", [])
    payload.setdefault("region", "cn-beijing")
    payload.setdefault("workspace_id", "")
    payload.setdefault("mic_seconds", 8)
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


def transcribe_file(
    audio_path: Path,
    config: dict[str, Any] | None = None,
    config_path: Path | None = None,
) -> TranscribeResult:
    config = config or load_voice_config(config_path)
    configure_dashscope(config)
    from dashscope.audio.asr import Recognition

    path = audio_path.expanduser().resolve()
    if not path.exists():
        raise VoiceAdapterError(f"Audio file not found: {path}")

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
    config = config or load_voice_config()
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
    return sanitize_tts_text(summary, config)


def synthesize_speech(
    text: str,
    output_path: Path,
    config: dict[str, Any] | None = None,
    config_path: Path | None = None,
) -> SpeakResult:
    config = config or load_voice_config(config_path)
    configure_dashscope(config)
    from dashscope.audio.tts_v2 import SpeechSynthesizer

    speak_text = sanitize_tts_text(text, config)
    if not speak_text:
        raise VoiceAdapterError("TTS text is empty after sanitization.")

    synthesizer = SpeechSynthesizer(
        model=config["tts_model"],
        voice=config["tts_voice"],
    )
    audio = synthesizer.call(speak_text)
    if audio is None:
        raise VoiceAdapterError("DashScope TTS returned empty audio.")

    out = output_path.expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(audio)

    return SpeakResult(
        text=speak_text,
        output_path=str(out),
        model=config["tts_model"],
        voice=config["tts_voice"],
        byte_size=len(audio),
    )


def map_voice_command(text: str, config: dict[str, Any]) -> str | None:
    normalized = clean_text(text).lower()
    if not normalized:
        return None
    if normalized.startswith("/"):
        return normalized
    commands = config.get("voice_commands", {})
    for command, phrases in commands.items():
        for phrase in phrases:
            if normalized == phrase.lower() or normalized.startswith(phrase.lower()):
                if command == "recap":
                    return "/recap"
                if command == "quit":
                    return "/quit"
                if command == "pause":
                    return "/pause"
                if command == "cancel":
                    return "/quit"
                if command == "continue":
                    return "/continue"
    return None


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
    }


def persist_voice_turn_artifacts(
    paths: dict[str, Path],
    transcript: str,
    agent_reply: str,
    input_audio: Path | None = None,
) -> None:
    if input_audio and input_audio.exists():
        paths["input"].write_bytes(input_audio.read_bytes())
    paths["transcript"].write_text(transcript + "\n", encoding="utf-8")
    paths["reply_text"].write_text(agent_reply + "\n", encoding="utf-8")
