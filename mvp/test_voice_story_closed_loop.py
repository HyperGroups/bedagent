"""Closed-loop tests: simulated voice input -> ASR text -> Story -> TTS."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from story_session import (
    build_story_drafts,
    export_story,
    load_story_blanket_policy,
    load_story_state,
    process_answer,
    resolve_story_paths,
    run_voice_story_once,
)
from voice_adapter import (
    transcribe_file,
    transcribe_simulated,
    write_silent_wav,
)

FIXTURES = Path(__file__).with_name("fixtures") / "voice"


class VoiceStoryClosedLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        self._env_patch = mock.patch.dict(
            os.environ,
            {"BEDAGENT_TTS_SIMULATE": "1"},
            clear=False,
        )
        self._env_patch.start()

    def tearDown(self) -> None:
        self._env_patch.stop()

    def test_simulated_asr_reads_sidecar_transcript(self) -> None:
        audio = FIXTURES / "oral-turn1.wav"
        result = transcribe_file(audio)
        self.assertEqual(result.model, "simulated-asr")
        self.assertIn("维修AI", result.text)
        self.assertIsNotNone(transcribe_simulated(audio))

    def test_voice_story_closed_loop_single_turn(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_story_paths(Path(tmp), None, "语音闭环测试")
            paths.root.mkdir(parents=True)
            session, bible = load_story_state(paths, "语音闭环测试")
            policy = load_story_blanket_policy(Path(__file__).with_name("story_blanket_policy.json"))

            payload = run_voice_story_once(
                paths,
                FIXTURES / "oral-turn1.wav",
                session,
                bible,
                policy=policy,
                auto_confirm=True,
            )

            self.assertTrue(payload["applied"])
            self.assertIn("维修AI", payload["transcript"])
            self.assertIn("我听懂了", payload["agent_reply"])
            self.assertEqual(payload["asr_model"], "simulated-asr")
            self.assertEqual(payload["tts_model"], "simulated-tts")

            reply_audio = Path(payload["reply_audio"])
            self.assertTrue(reply_audio.exists())
            self.assertGreater(reply_audio.stat().st_size, 0)

            transcript_file = Path(payload["artifacts"]["transcript"])
            self.assertTrue(transcript_file.exists())
            self.assertIn("维修AI", transcript_file.read_text(encoding="utf-8"))

            bible_path = paths.bible
            self.assertTrue(bible_path.exists())
            bible_data = json.loads(bible_path.read_text(encoding="utf-8"))
            self.assertIn("维修AI", bible_data["main_thread"])

    def test_voice_story_closed_loop_multi_turn_with_answer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_story_paths(Path(tmp), None, "语音多轮闭环")
            paths.root.mkdir(parents=True)
            session, bible = load_story_state(paths, "语音多轮闭环")
            policy = load_story_blanket_policy(Path(__file__).with_name("story_blanket_policy.json"))

            first = run_voice_story_once(
                paths,
                FIXTURES / "oral-turn1.wav",
                session,
                bible,
                policy=policy,
                auto_confirm=True,
            )
            session, bible = first["session"], first["bible"]

            answer = process_answer(
                paths,
                "这是现在发生的，不是回忆。梦境日志是 AI 自己在写。",
                session,
                bible,
            )
            session, bible = answer["session"], answer["bible"]

            second = run_voice_story_once(
                paths,
                FIXTURES / "oral-turn2.wav",
                session,
                bible,
                policy=policy,
                auto_confirm=True,
            )

            self.assertEqual(second["session"]["turn_count"], 3)
            self.assertIn("触摸世界", second["transcript"])
            self.assertGreater(len(list(paths.voice.glob("turn-*-reply.wav"))), 1)

            export = export_story(paths, second["bible"], second["session"])
            self.assertTrue(Path(export["transcript_path"]).exists())
            transcript_md = Path(export["transcript_path"]).read_text(encoding="utf-8")
            self.assertIn("维修AI", transcript_md)
            self.assertIn("触摸世界", transcript_md)

            draft = build_story_drafts(paths, second["bible"], second["session"])
            self.assertTrue(Path(draft["chapter_sketch_path"]).exists())

    def test_cli_voice_once_closed_loop_subprocess(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            story_root = Path(tmp) / "stories"
            repo_root = Path(__file__).resolve().parent.parent
            env = os.environ.copy()
            env["BEDAGENT_TTS_SIMULATE"] = "1"
            cmd = [
                sys.executable,
                str(repo_root / "mvp" / "bedagent_mvp.py"),
                "story",
                "voice-once",
                "--title",
                "CLI语音闭环",
                "--story-root",
                str(story_root),
                "--audio-file",
                str(FIXTURES / "oral-turn1.wav"),
                "--auto-confirm",
            ]
            proc = subprocess.run(cmd, cwd=repo_root, env=env, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
            self.assertIn("asr_model: simulated-asr", proc.stdout)
            self.assertIn("transcript:", proc.stdout)
            self.assertIn("reply_audio:", proc.stdout)

            sessions = list(story_root.iterdir())
            self.assertEqual(len(sessions), 1)
            voice_dir = sessions[0] / "voice"
            self.assertTrue(any(voice_dir.glob("turn-*-transcript.txt")))


if __name__ == "__main__":
    unittest.main()
