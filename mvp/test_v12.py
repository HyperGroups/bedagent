import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from bedagent_web import BedagentWebHandler, PRODUCT_MILESTONE, ThreadingHTTPServer
from story_session import load_story_state, resolve_story_paths, run_voice_story_once
from voice_adapter import (
    concat_wav_pcm16,
    local_asr_available,
    split_text_for_segments,
    split_tts_sentences,
    synthesize_speech_stream,
    transcribe_local,
    transcribe_vad,
    vad_segments,
    voice_status,
    write_silent_wav,
    write_tone_wav,
)


class VadSplitTests(unittest.TestCase):
    def test_two_tones_split_into_utterances(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            silence = write_silent_wav(root / "s.wav", seconds=0.3)
            a = write_tone_wav(root / "a.wav", seconds=0.4, freq=440)
            gap = write_silent_wav(root / "g.wav", seconds=0.5)
            b = write_tone_wav(root / "b.wav", seconds=0.4, freq=660)
            tail = write_silent_wav(root / "t.wav", seconds=0.3)
            audio = concat_wav_pcm16(root / "two-turns.wav", [silence, a, gap, b, tail])
            (root / "two-turns.transcript.txt").write_text(
                "主角是维修AI。它在冬眠舰上偷听人类的梦。\n",
                encoding="utf-8",
            )
            segments = vad_segments(audio)
            self.assertGreaterEqual(len(segments), 2)
            result = transcribe_vad(audio, output_dir=root / "vad")
            self.assertGreaterEqual(len(result.segments), 2)
            self.assertGreaterEqual(len(result.utterances), 2)
            self.assertIn("维修AI", result.text)
            self.assertIn("冬眠舰", result.text)
            self.assertFalse(result.skipped)

    def test_silence_only_skips(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            audio = write_silent_wav(Path(tmp) / "quiet.wav", seconds=0.4)
            result = transcribe_vad(audio, output_dir=Path(tmp) / "vad")
            self.assertTrue(result.skipped)
            self.assertIn(result.skip_reason, {"silence", ""})


class TtsSentenceTests(unittest.TestCase):
    def test_split_and_stream_simulate(self) -> None:
        parts = split_tts_sentences("收到。主线已对齐。继续讲。")
        self.assertEqual(parts, ["收到。", "主线已对齐。", "继续讲。"])
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"BEDAGENT_TTS_SIMULATE": "1"}, clear=False):
                spoken = synthesize_speech_stream("收到。继续讲。", Path(tmp))
            self.assertEqual(len(spoken.sentences), 2)
            self.assertTrue(all(Path(path).exists() for path in spoken.output_paths))

    def test_split_text_for_segments_merges_extra(self) -> None:
        parts = split_text_for_segments("第一句。第二句。第三句。", 2)
        self.assertEqual(len(parts), 2)
        self.assertIn("第三句", parts[1])


class LocalFallbackTests(unittest.TestCase):
    def test_local_uses_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            audio = write_silent_wav(Path(tmp) / "local.wav", seconds=0.2)
            audio.with_name("local.transcript.txt").write_text("本地回退转写。\n", encoding="utf-8")
            result = transcribe_local(audio, config={})
            self.assertIsNotNone(result)
            self.assertEqual(result.text, "本地回退转写。")
            self.assertEqual(result.model, "local-whisper-simulated")

    def test_status_exposes_vad_and_local_flags(self) -> None:
        status = voice_status()
        self.assertIn("vad_frame_ms", status)
        self.assertIn("local_asr", status)
        self.assertIn("local_tts", status)
        self.assertIsInstance(local_asr_available({}), bool)


class VoiceStoryVadTests(unittest.TestCase):
    def test_voice_once_vad_writes_two_turns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = resolve_story_paths(root / "stories", None, "vad-story")
            paths.root.mkdir(parents=True)
            session, bible = load_story_state(paths, "vad-story")
            silence = write_silent_wav(root / "s.wav", seconds=0.25)
            a = write_tone_wav(root / "a.wav", seconds=0.35)
            gap = write_silent_wav(root / "g.wav", seconds=0.5)
            b = write_tone_wav(root / "b.wav", seconds=0.35)
            audio = concat_wav_pcm16(root / "story.wav", [silence, a, gap, b])
            audio.with_name("story.transcript.txt").write_text(
                "主角名叫林澜。她在冬眠舰上维护梦境日志。\n",
                encoding="utf-8",
            )
            journal = root / "journal.ndjson"
            with mock.patch.dict(os.environ, {"BEDAGENT_TTS_SIMULATE": "1"}, clear=False):
                payload = run_voice_story_once(
                    paths,
                    audio,
                    session,
                    bible,
                    auto_confirm=True,
                    vad=True,
                    tts_stream=True,
                    memory_journal_path=journal,
                )
            self.assertTrue(payload.get("vad"))
            self.assertGreaterEqual(len(payload.get("turns") or []), 2)
            self.assertTrue(payload["applied"])
            self.assertGreaterEqual(payload["session"]["turn_count"], 2)
            self.assertTrue(journal.exists())
            kinds = [json.loads(line)["kind"] for line in journal.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertIn("voice", kinds)
            self.assertIn("story", kinds)
            self.assertTrue(payload.get("tts_sentences") or payload["turns"][-1].get("tts_sentences"))


class VoiceWebV12Tests(unittest.TestCase):
    def start_server(self) -> ThreadingHTTPServer:
        server = ThreadingHTTPServer(("127.0.0.1", 0), BedagentWebHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server

    def test_health_vad_feature_and_story_vad(self) -> None:
        server = self.start_server()
        port = server.server_address[1]
        try:
            import urllib.request

            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=3) as resp:
                health = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(health["product_milestone"], PRODUCT_MILESTONE)
            self.assertEqual(PRODUCT_MILESTONE, "v0.12.0-mvp")
            self.assertIn("voice-vad", health["features"])
            self.assertIn("tts-sentences", health["features"])

            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/voice/status", timeout=3) as resp:
                status = json.loads(resp.read().decode("utf-8"))
            self.assertIn("vad_frame_ms", status)

            body = (
                "--boundary\r\n"
                'Content-Disposition: form-data; name="simulate_transcript"\r\n\r\n'
                "主角是维修AI。它偷听人类的梦。\r\n"
                "--boundary\r\n"
                'Content-Disposition: form-data; name="title"\r\n\r\nv12-vad\r\n'
                "--boundary\r\n"
                'Content-Disposition: form-data; name="include_audio"\r\n\r\n0\r\n'
                "--boundary\r\n"
                'Content-Disposition: form-data; name="vad"\r\n\r\n1\r\n'
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

            transcribe = (
                "--boundary\r\n"
                'Content-Disposition: form-data; name="simulate_transcript"\r\n\r\n'
                "第一句。第二句。\r\n"
                "--boundary\r\n"
                'Content-Disposition: form-data; name="vad"\r\n\r\n1\r\n'
                "--boundary--\r\n"
            ).encode("utf-8")
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/voice/transcribe",
                data=transcribe,
                headers={"Content-Type": "multipart/form-data; boundary=boundary"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                transcribed = json.loads(resp.read().decode("utf-8"))
            self.assertGreaterEqual(len(transcribed.get("segments") or []), 2)

            with urllib.request.urlopen(f"http://127.0.0.1:{port}/agent/", timeout=3) as resp:
                html = resp.read().decode("utf-8")
            self.assertIn("静音自动停", html)
            self.assertIn("自动分轮", html)
        finally:
            server.shutdown()


if __name__ == "__main__":
    unittest.main()
