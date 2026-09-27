import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from bedagent_web import BedagentWebHandler, PRODUCT_MILESTONE, ThreadingHTTPServer
from story_session import load_story_state, resolve_story_paths, run_open_mic_story
from voice_adapter import (
    OpenMicState,
    apply_open_mic_command,
    concat_wav_pcm16,
    map_voice_command,
    transcribe_file,
    write_silent_wav,
    write_tone_wav,
)


class OpenMicCommandTests(unittest.TestCase):
    def test_listen_mute_quit(self) -> None:
        config = {
            "voice_commands": {
                "listen": ["开始听", "开麦"],
                "mute": ["关麦", "别听了"],
                "quit": ["退出"],
            }
        }
        self.assertEqual(map_voice_command("开麦", config), "/listen")
        self.assertEqual(map_voice_command("关麦", config), "/mute")
        state = apply_open_mic_command("/mute", OpenMicState())
        self.assertTrue(state.paused)
        self.assertTrue(state.listening)
        state = apply_open_mic_command("/listen", state)
        self.assertFalse(state.paused)
        state = apply_open_mic_command("/quit", state)
        self.assertFalse(state.listening)
        self.assertEqual(state.stop_reason, "/quit")


class OpenMicStoryTests(unittest.TestCase):
    def test_open_mic_splits_and_stops_on_quit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = resolve_story_paths(root / "stories", None, "open-mic")
            paths.root.mkdir(parents=True)
            session, bible = load_story_state(paths, "open-mic")
            silence = write_silent_wav(root / "s.wav", seconds=0.25)
            a = write_tone_wav(root / "a.wav", seconds=0.35)
            gap = write_silent_wav(root / "g.wav", seconds=0.5)
            b = write_tone_wav(root / "b.wav", seconds=0.35)
            first = concat_wav_pcm16(root / "session.wav", [silence, a, gap, b])
            first.with_name("session.transcript.txt").write_text(
                "主角名叫林澜。她在冬眠舰上维护梦境日志。\n",
                encoding="utf-8",
            )
            quit_audio = write_silent_wav(root / "quit.wav", seconds=0.2)
            quit_audio.with_name("quit.transcript.txt").write_text("退出\n", encoding="utf-8")
            journal = root / "journal.ndjson"
            with mock.patch.dict(os.environ, {"BEDAGENT_TTS_SIMULATE": "1"}, clear=False):
                payload = run_open_mic_story(
                    paths,
                    [first, quit_audio],
                    session,
                    bible,
                    auto_confirm=True,
                    memory_journal_path=journal,
                )
            self.assertTrue(payload["open_mic"])
            self.assertFalse(payload["listening"])
            self.assertEqual(payload["stop_reason"], "/quit")
            self.assertGreaterEqual(payload["applied_count"], 2)
            self.assertGreaterEqual(payload["session"]["turn_count"], 2)
            self.assertIn("林澜", payload["transcript"])

    def test_dashscope_helpers_can_be_patched_without_sdk(self) -> None:
        recognition = mock.Mock()
        instance = recognition.return_value
        result = mock.Mock()
        result.status_code = 200
        result.get_sentence.return_value = {"text": "无 SDK 也可测"}
        instance.call.return_value = result
        instance.get_last_request_id.return_value = "req"
        with tempfile.TemporaryDirectory() as tmp:
            audio = write_silent_wav(Path(tmp) / "x.wav", seconds=0.1)
            with mock.patch.dict(os.environ, {"DASHSCOPE_API_KEY": "k"}, clear=False):
                with mock.patch("voice_adapter.configure_dashscope"):
                    with mock.patch("voice_adapter.dashscope_recognition_class", return_value=recognition):
                        out = transcribe_file(audio, config={"asr_model": "fun-asr-realtime", "sample_rate": 16000})
            self.assertEqual(out.text, "无 SDK 也可测")


class VoiceWebV13Tests(unittest.TestCase):
    def start_server(self) -> ThreadingHTTPServer:
        server = ThreadingHTTPServer(("127.0.0.1", 0), BedagentWebHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server

    def test_open_mic_api_and_ui(self) -> None:
        server = self.start_server()
        port = server.server_address[1]
        try:
            import urllib.request

            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=3) as resp:
                health = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(health["product_milestone"], PRODUCT_MILESTONE)
            self.assertEqual(PRODUCT_MILESTONE, "v0.13.0-mvp")
            self.assertIn("voice-open-mic", health["features"])

            body = (
                "--boundary\r\n"
                'Content-Disposition: form-data; name="simulate_transcript"\r\n\r\n'
                "主角是维修AI。它偷听人类的梦。\r\n"
                "--boundary\r\n"
                'Content-Disposition: form-data; name="title"\r\n\r\nv13-open\r\n'
                "--boundary\r\n"
                'Content-Disposition: form-data; name="include_audio"\r\n\r\n0\r\n'
                "--boundary\r\n"
                'Content-Disposition: form-data; name="open_mic"\r\n\r\n1\r\n'
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
            self.assertTrue(payload.get("open_mic"))
            self.assertIn("维修AI", payload["transcript"])

            with urllib.request.urlopen(f"http://127.0.0.1:{port}/agent/", timeout=3) as resp:
                html = resp.read().decode("utf-8")
            self.assertIn("持续开麦", html)
        finally:
            server.shutdown()


if __name__ == "__main__":
    unittest.main()
