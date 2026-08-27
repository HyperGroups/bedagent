import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from bedagent_web import BedagentWebHandler, PRODUCT_MILESTONE, ThreadingHTTPServer
from story_session import empty_bible, load_story_state, resolve_story_paths, run_voice_story_once
from voice_adapter import (
    map_voice_command,
    split_transcript_partials,
    transcribe_stream,
    voice_status,
    wav_silence_ratio,
    write_silent_wav,
)

FIXTURES = Path(__file__).with_name("fixtures") / "voice"


class VoiceStreamTests(unittest.TestCase):
    def test_split_partials_grows_chinese(self) -> None:
        parts = split_transcript_partials("主角是一个维修AI，它在冬眠舰上偷听人类的梦。", step=8)
        self.assertGreaterEqual(len(parts), 3)
        self.assertEqual(parts[-1], "主角是一个维修AI，它在冬眠舰上偷听人类的梦。")
        self.assertTrue(all(len(parts[i]) <= len(parts[i + 1]) for i in range(len(parts) - 1)))

    def test_stream_simulated_sidecar_emits_partials(self) -> None:
        result = transcribe_stream(FIXTURES / "oral-turn1.wav")
        self.assertEqual(result.model, "simulated-asr")
        self.assertFalse(result.skipped)
        self.assertGreaterEqual(len(result.partials), 2)
        self.assertIn("维修AI", result.text)
        self.assertEqual(result.partials[-1]["text"], result.text)

    def test_silence_without_sidecar_is_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            audio = Path(tmp) / "quiet.wav"
            write_silent_wav(audio, seconds=0.3)
            self.assertGreater(wav_silence_ratio(audio), 0.9)
            result = transcribe_stream(audio)
            self.assertTrue(result.skipped)
            self.assertEqual(result.skip_reason, "silence")
            self.assertEqual(result.text, "")

    def test_voice_command_answer_and_resume(self) -> None:
        config = {"voice_commands": {"answer": ["我来回答"], "resume": ["接着上次"], "recap": ["汇报一下"]}}
        self.assertEqual(map_voice_command("我来回答", config), "/answer")
        self.assertEqual(map_voice_command("接着上次", config), "/resume")

    def test_voice_status_keys(self) -> None:
        status = voice_status()
        self.assertIn("asr_model", status)
        self.assertIn("has_key", status)
        self.assertIn("quiet", status)


class VoiceStorySkipTests(unittest.TestCase):
    def test_voice_once_skips_silence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_story_paths(Path(tmp), None, "silence-skip")
            paths.root.mkdir(parents=True)
            session, bible = load_story_state(paths, "silence-skip")
            audio = Path(tmp) / "quiet.wav"
            write_silent_wav(audio, seconds=0.2)
            with mock.patch.dict(os.environ, {"BEDAGENT_TTS_SIMULATE": "1"}, clear=False):
                payload = run_voice_story_once(paths, audio, session, bible, auto_confirm=True)
            self.assertTrue(payload["skipped"])
            self.assertEqual(payload["skip_reason"], "silence")
            self.assertFalse(payload["applied"])
            self.assertEqual(payload["bible"].get("fragment_count", 0), empty_bible()["fragment_count"])


class VoiceWebV11Tests(unittest.TestCase):
    def start_server(self) -> ThreadingHTTPServer:
        server = ThreadingHTTPServer(("127.0.0.1", 0), BedagentWebHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server

    def test_voice_status_and_story_loop(self) -> None:
        server = self.start_server()
        port = server.server_address[1]
        try:
            import urllib.request

            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/voice/status", timeout=3) as resp:
                status = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(status["ok"])
            self.assertEqual(PRODUCT_MILESTONE, "v0.12.0-mvp")

            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=3) as resp:
                health = json.loads(resp.read().decode("utf-8"))
            self.assertIn("voice-story-loop", health["features"])

            body = (
                "--boundary\r\n"
                'Content-Disposition: form-data; name="simulate_transcript"\r\n\r\n'
                "主角是一个维修AI，它在冬眠舰上偷听人类的梦。\r\n"
                "--boundary\r\n"
                'Content-Disposition: form-data; name="title"\r\n\r\nv11-voice\r\n'
                "--boundary\r\n"
                'Content-Disposition: form-data; name="include_audio"\r\n\r\n0\r\n'
                "--boundary--\r\n"
            ).encode("utf-8")
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/voice/story",
                data=body,
                headers={"Content-Type": "multipart/form-data; boundary=boundary"},
                method="POST",
            )
            with mock.patch.dict(os.environ, {"BEDAGENT_TTS_SIMULATE": "1"}, clear=False):
                with urllib.request.urlopen(req, timeout=10) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(payload["applied"])
            self.assertIn("维修AI", payload["transcript"])
            self.assertTrue(payload.get("partials"))
            self.assertIn("agent_reply", payload)

            with urllib.request.urlopen(f"http://127.0.0.1:{port}/agent/", timeout=3) as resp:
                html = resp.read().decode("utf-8")
            self.assertIn("说完即闭环", html)
            self.assertIn("按住说话", html)
        finally:
            server.shutdown()

    def test_transcribe_stream_simulate_partials(self) -> None:
        server = self.start_server()
        port = server.server_address[1]
        try:
            import urllib.request

            body = (
                "--boundary\r\n"
                'Content-Disposition: form-data; name="simulate_transcript"\r\n\r\n'
                "主角在冬眠舰上维护梦境日志。\r\n"
                "--boundary\r\n"
                'Content-Disposition: form-data; name="stream"\r\n\r\n1\r\n'
                "--boundary--\r\n"
            ).encode("utf-8")
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/voice/transcribe",
                data=body,
                headers={"Content-Type": "multipart/form-data; boundary=boundary"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            self.assertIn("partials", payload)
            self.assertGreaterEqual(len(payload["partials"]), 2)
        finally:
            server.shutdown()


if __name__ == "__main__":
    unittest.main()
