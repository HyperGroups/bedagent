import json
import tempfile
import unittest
from pathlib import Path

from story_session import (
    build_agent_reply,
    build_chapter_sketch,
    build_story_drafts,
    build_story_recap,
    classify_story_blanket_risk,
    empty_bible,
    export_story,
    list_story_sessions,
    load_story_blanket_policy,
    process_answer,
    process_fragment,
    resolve_story_paths,
    run_story_tell,
    stage_story_focus,
    stage_story_sage,
    stage_story_synthesize,
)


class StorySessionTests(unittest.TestCase):
    def policy(self) -> dict:
        return load_story_blanket_policy(Path(__file__).with_name("story_blanket_policy.json"))

    def test_stage_story_sage_sets_main_thread_on_first_fragment(self) -> None:
        bible = empty_bible()
        fragment = "主角是一个会偷听梦境的维修AI，它以为自己只是机器。"
        sage = stage_story_sage(fragment, bible)
        self.assertIn("维修", sage["main_thread"])
        self.assertEqual(sage["category"], "character")

    def test_process_fragment_updates_bible_and_writes_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_story_paths(Path(tmp), None, "测试故事")
            paths.root.mkdir(parents=True)
            session = {"title": "测试故事", "turn_count": 0, "fragment_count": 0}
            bible = empty_bible("测试故事")
            fragment = "主角名叫林澜，她在冬眠舰上负责维护梦境日志；然后她发现日志里出现了自己的童年。"
            result = process_fragment(
                paths,
                fragment,
                session,
                bible,
                policy=self.policy(),
                auto_confirm=True,
            )
            self.assertTrue(result["applied"])
            self.assertTrue(paths.bible.exists())
            self.assertTrue(paths.turns.exists())
            self.assertEqual(result["bible"]["fragment_count"], 1)
            self.assertIn("林澜", json.dumps(result["bible"], ensure_ascii=False))
            self.assertIn("我听懂了", result["agent_reply"])

    def test_blanket_blocks_main_thread_pivot_without_confirm(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_story_paths(Path(tmp), None, "pivot-test")
            paths.root.mkdir(parents=True)
            session = {"title": "pivot-test", "turn_count": 2, "fragment_count": 2}
            bible = empty_bible("pivot-test")
            bible["main_thread"] = "冬眠舰上的维修 AI 学会做梦"
            bible["turn_count"] = 2
            fragment = "其实整个故事发生在虚拟现实里，没有飞船。"
            result = process_fragment(
                paths,
                fragment,
                session,
                bible,
                policy=self.policy(),
                non_interactive=True,
            )
            self.assertFalse(result["applied"])
            self.assertIn(result["blanket"]["risk_level"], {"yellow", "red"})
            self.assertIn("未写入", result["agent_reply"])

    def test_process_answer_resolves_open_questions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_story_paths(Path(tmp), None, "answer-test")
            paths.root.mkdir(parents=True)
            session = {"title": "answer-test", "turn_count": 1, "fragment_count": 1}
            bible = empty_bible("answer-test")
            bible["open_questions"] = ["Q1?", "Q2?", "Q3?"]
            result = process_answer(paths, "这是现在的回忆，不是未来。", session, bible)
            self.assertEqual(len(result["resolved_questions"]), 3)
            self.assertEqual(result["bible"]["open_questions"], [])
            self.assertIn("收到对齐", result["agent_reply"])

    def test_build_story_drafts_writes_chapter_sketch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_story_paths(Path(tmp), None, "draft-test")
            paths.root.mkdir(parents=True)
            session = {"title": "draft-test", "turn_count": 2}
            bible = empty_bible("draft-test")
            bible["main_thread"] = "AI 偷听梦境"
            bible["plot_threads"] = [{"label": "梦境日志异常", "status": "active", "notes": []}]
            result = build_story_drafts(paths, bible, session)
            self.assertTrue(Path(result["chapter_sketch_path"]).exists())
            self.assertTrue(Path(result["outline_path"]).exists())
            sketch = Path(result["chapter_sketch_path"]).read_text(encoding="utf-8")
            self.assertIn("第 1 章草图", sketch)

    def test_export_story_writes_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_story_paths(Path(tmp), None, "export-test")
            paths.root.mkdir(parents=True)
            session = {"title": "export-test", "turn_count": 1}
            bible = empty_bible("export-test")
            bible["main_thread"] = "测试主线"
            result = export_story(paths, bible, session)
            self.assertTrue(Path(result["story_bible_path"]).exists())
            self.assertTrue(Path(result["transcript_path"]).exists())

    def test_list_story_sessions_reads_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            one = root / "session-a"
            one.mkdir()
            (one / "session.json").write_text(
                json.dumps({"title": "A", "turn_count": 2, "updated_at": "2026-07-12T10:00:00+00:00"}),
                encoding="utf-8",
            )
            (one / "bible.json").write_text(
                json.dumps({"main_thread": "主线A"}),
                encoding="utf-8",
            )
            items = list_story_sessions(root)
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0]["story_id"], "session-a")

    def test_run_story_tell_non_interactive_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inputs = iter(
                [
                    "其实反派不是外星人，是过去的她自己。",
                    "",
                    "/quit",
                ]
            )
            outputs: list[str] = []

            def fake_input(_: str) -> str:
                return next(inputs)

            recap = run_story_tell(
                story_root=Path(tmp),
                title="口述测试",
                seed_fragment="主角在梦里学会了写字。",
                policy=self.policy(),
                auto_confirm=True,
                input_fn=fake_input,
                output_fn=outputs.append,
            )
            self.assertEqual(recap["turn_count"], 2)
            self.assertIn("main_thread", recap)
            joined = "\n".join(outputs)
            self.assertIn("Sage 想和你对齐", joined)

    def test_build_story_recap_contains_open_questions(self) -> None:
        bible = empty_bible("recap测试")
        bible["open_questions"] = ["这是现在还是回忆？"]
        bible["main_thread"] = "梦境日志出现童年"
        session = {"title": "recap测试", "turn_count": 1}
        recap = build_story_recap(bible, session)
        self.assertEqual(recap["turn_count"], 1)
        self.assertEqual(len(recap["open_questions"]), 1)

    def test_stage_story_synthesize_parks_low_value_threads(self) -> None:
        bible = empty_bible()
        fragment = "也许以后再加一个平行宇宙；突然，主角发现了真相。"
        sage = stage_story_sage(fragment, bible)
        focus = stage_story_focus(fragment, sage)
        updated = stage_story_synthesize(fragment, sage, focus, bible, turn_number=1)
        actions = {item["action"] for item in focus["decisions"]}
        self.assertIn("park", actions)
        self.assertTrue(updated["plot_threads"])
        reply = build_agent_reply(sage, focus, updated)
        self.assertIn("Focus", reply)

    def test_classify_story_blanket_risk_detects_red_keywords(self) -> None:
        bible = empty_bible()
        risk = classify_story_blanket_risk("我决定删除角色并重写全书", bible, "新主线", self.policy())
        self.assertEqual(risk["level"], "red")

    def test_build_chapter_sketch_includes_active_threads(self) -> None:
        bible = empty_bible("sketch")
        bible["main_thread"] = "主线"
        bible["plot_threads"] = [{"label": "线索A", "status": "active", "notes": []}]
        text = build_chapter_sketch(bible, 2)
        self.assertIn("第 2 章草图", text)
        self.assertIn("线索A", text)


if __name__ == "__main__":
    unittest.main()
