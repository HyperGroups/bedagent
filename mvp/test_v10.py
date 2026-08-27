import json
import os
import tempfile
import threading
import unittest
import urllib.parse
import urllib.request
from pathlib import Path
from unittest import mock

from bedagent_mvp import unified_search
from bedagent_web import BedagentWebHandler, PRODUCT_MILESTONE, ThreadingHTTPServer
from llm_adapter import simulate_chapter_expansion
from story_session import (
    build_chapter_prose,
    build_character_sheet,
    build_night_pillow_note,
    build_story_drafts,
    empty_bible,
    latest_story_session,
    process_fragment,
    resolve_resume_story_id,
    resolve_story_paths,
)
from voice_adapter import (
    apply_quiet_config,
    build_tts_summary,
    load_voice_config,
    map_voice_command,
    wav_silence_ratio,
    write_silent_wav,
)


class StoryResumeAndMemoryTests(unittest.TestCase):
    def test_latest_and_resume_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = resolve_story_paths(root, None, "first")
            first.root.mkdir(parents=True)
            process_fragment(
                first,
                "主角名叫林澜，她在冬眠舰上维护梦境日志。",
                {"title": "first", "turn_count": 0, "fragment_count": 0},
                empty_bible("first"),
                auto_confirm=True,
            )
            second = resolve_story_paths(root, None, "second")
            second.root.mkdir(parents=True)
            process_fragment(
                second,
                "这是一个厨房喜剧。",
                {"title": "second", "turn_count": 0, "fragment_count": 0},
                empty_bible("second"),
                auto_confirm=True,
            )
            latest = latest_story_session(root)
            self.assertIsNotNone(latest)
            assert latest is not None
            self.assertEqual(latest["story_id"], second.root.name)
            self.assertEqual(resolve_resume_story_id(root, None, True), second.root.name)
            self.assertIsNone(resolve_resume_story_id(root, None, False))

    def test_story_turn_appends_memory_journal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = resolve_story_paths(root, None, "journaled")
            paths.root.mkdir(parents=True)
            journal = root / "journal.ndjson"
            result = process_fragment(
                paths,
                "主角名叫林澜，她想要找回被删掉的童年。",
                {"title": "journaled", "turn_count": 0, "fragment_count": 0},
                empty_bible("journaled"),
                auto_confirm=True,
                memory_journal_path=journal,
            )
            self.assertTrue(journal.exists())
            entry = json.loads(journal.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(entry["kind"], "story")
            self.assertEqual(entry["story_id"], paths.root.name)
            self.assertEqual(entry["act_status"], "applied")
            self.assertIn("林澜", entry["idea"])
            self.assertIsNotNone(result["memory"])

    def test_unified_search_mixes_memory_and_story(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            journal = root / "journal.ndjson"
            story_root = root / "stories"
            paths = resolve_story_paths(story_root, None, "梦境舰")
            paths.root.mkdir(parents=True)
            process_fragment(
                paths,
                "主角是一个维修AI，它在冬眠舰上偷听人类的梦。",
                {"title": "梦境舰", "turn_count": 0, "fragment_count": 0},
                empty_bible("梦境舰"),
                auto_confirm=True,
                memory_journal_path=journal,
            )
            hits = unified_search("维修AI 冬眠舰", journal, story_root, top_k=5)
            self.assertTrue(hits)
            sources = {hit["source"] for hit in hits}
            self.assertTrue(sources & {"memory", "story"})


class DraftExpandAndCharacterTests(unittest.TestCase):
    def test_character_extras_and_sheet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_story_paths(Path(tmp), None, "chars")
            paths.root.mkdir(parents=True)
            result = process_fragment(
                paths,
                "主角名叫林澜，她想要找回被删掉的童年。",
                {"title": "chars", "turn_count": 0, "fragment_count": 0},
                empty_bible("chars"),
                auto_confirm=True,
            )
            names = [item["name"] for item in result["bible"]["characters"]]
            self.assertIn("林澜", names)
            lin = next(item for item in result["bible"]["characters"] if item["name"] == "林澜")
            self.assertEqual(lin.get("role"), "protagonist")
            self.assertIn("找回", lin.get("desire", ""))
            sheet = build_character_sheet(result["bible"])
            self.assertIn("林澜", sheet)
            self.assertIn("主角", sheet)

    def test_expand_writes_prose_with_simulated_llm(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_story_paths(Path(tmp), None, "expand")
            paths.root.mkdir(parents=True)
            bible = empty_bible("expand")
            bible["main_thread"] = "维修AI 偷听人类的梦"
            bible["recent_recap"] = "日志灯闪了一下"
            session = {"title": "expand", "turn_count": 1}
            with mock.patch.dict(os.environ, {"BEDAGENT_LLM": "1", "BEDAGENT_LLM_SIMULATE": "1"}, clear=False):
                result = build_story_drafts(paths, bible, session, expand=True, use_llm=True)
            self.assertTrue(Path(result["prose_path"]).exists())
            prose = result["prose"]
            self.assertIn("扩写", prose)
            self.assertTrue(result["llm"]["used"])
            self.assertEqual(result["llm"]["model"], "simulated-qwen")

    def test_night_pillow_is_short(self) -> None:
        bible = empty_bible("night")
        bible["main_thread"] = "维修AI 在冬眠舰上偷听人类的梦，并且开始怀疑自己不是机器。"
        bible["open_questions"] = ["Q1?", "Q2?"]
        note = build_night_pillow_note(bible, {"turn_count": 3})
        self.assertIn("待对齐 2 条", note)
        self.assertLessEqual(len(note), 80)

    def test_heuristic_prose_mentions_main_thread(self) -> None:
        bible = empty_bible("prose")
        bible["main_thread"] = "冬眠舰上的维修 AI 学会做梦"
        text = build_chapter_prose(bible, 1)
        self.assertIn("维修", text)
        self.assertIn("第 1 章扩写", text)

    def test_simulate_chapter_expansion_keeps_limit(self) -> None:
        text = simulate_chapter_expansion({"main_thread": "主线", "recent_recap": "刚才"}, "草图", max_chars=240)
        self.assertLessEqual(len(text), 240)
        self.assertIn("扩写正文", text)


class QuietVoiceTests(unittest.TestCase):
    def test_quiet_tts_is_shorter(self) -> None:
        config = load_voice_config(Path(__file__).with_name("voice_config.json"))
        reply = "我听懂了：AI 开始做梦并且把整段日志都复述了一遍\n\n当前主线：梦境日志异常而且很长很长很长很长"
        normal = build_tts_summary(reply, config)
        with mock.patch.dict(os.environ, {"BEDAGENT_TTS_QUIET": "1"}, clear=False):
            quiet = build_tts_summary(reply, config)
        self.assertLessEqual(len(quiet), len(normal))
        self.assertLessEqual(len(quiet), 72)

    def test_map_voice_command_expand_and_quiet(self) -> None:
        config = load_voice_config(Path(__file__).with_name("voice_config.json"))
        self.assertEqual(map_voice_command("扩写", config), "/expand")
        self.assertEqual(map_voice_command("夜间模式", config), "/quiet")
        self.assertEqual(map_voice_command("人物卡", config), "/characters")
        self.assertEqual(map_voice_command("生成草稿", config), "/draft")

    def test_silent_wav_ratio(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            audio = Path(tmp) / "silence.wav"
            write_silent_wav(audio, seconds=0.2)
            self.assertGreater(wav_silence_ratio(audio), 0.9)

    def test_apply_quiet_config_lowers_limit(self) -> None:
        config = load_voice_config(Path(__file__).with_name("voice_config.json"))
        quiet = apply_quiet_config(config, quiet=True)
        self.assertTrue(quiet["quiet_mode"])
        self.assertLessEqual(int(quiet["max_tts_chars"]), 72)


class WebV10Tests(unittest.TestCase):
    def start_server(self) -> ThreadingHTTPServer:
        server = ThreadingHTTPServer(("127.0.0.1", 0), BedagentWebHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server

    def test_health_milestone(self) -> None:
        server = self.start_server()
        port = server.server_address[1]
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=3) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(payload["product_milestone"], PRODUCT_MILESTONE)
            self.assertIn("story-expand", payload["features"])
        finally:
            server.shutdown()

    def test_latest_draft_and_unified_search(self) -> None:
        server = self.start_server()
        port = server.server_address[1]
        try:
            body = json.dumps(
                {"fragment": "主角名叫林澜，她在冬眠舰上维护梦境日志。", "title": "v10-web"}
            ).encode("utf-8")
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/story/fragment",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                created = json.loads(resp.read().decode("utf-8"))
            story_id = created["story_id"]

            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/story/latest", timeout=5) as resp:
                latest = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(latest["story_id"], story_id)

            draft_body = json.dumps({"story_id": story_id, "expand": True}).encode("utf-8")
            draft_req = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/story/draft",
                data=draft_body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(draft_req, timeout=5) as resp:
                draft = json.loads(resp.read().decode("utf-8"))
            self.assertIn("sketch", draft)
            self.assertIn("prose", draft)
            self.assertIn("林澜", draft.get("characters", "") + draft.get("sketch", ""))

            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/api/search?q={urllib.parse.quote('林澜')}",
                timeout=5,
            ) as resp:
                search = json.loads(resp.read().decode("utf-8"))
            self.assertIn("hits", search)
        finally:
            server.shutdown()

    def test_agent_page_has_new_actions(self) -> None:
        server = self.start_server()
        port = server.server_address[1]
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/agent/", timeout=3) as resp:
                html = resp.read().decode("utf-8")
            self.assertIn("生成草稿", html)
            self.assertIn("扩写", html)
            self.assertIn("朗读", html)
            self.assertIn("夜间朗读", html)
        finally:
            server.shutdown()


if __name__ == "__main__":
    unittest.main()
