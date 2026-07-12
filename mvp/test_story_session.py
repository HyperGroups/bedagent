import json
import tempfile
import unittest
from pathlib import Path

from story_session import (
    build_agent_reply,
    build_story_recap,
    empty_bible,
    process_fragment,
    resolve_story_paths,
    run_story_tell,
    stage_story_focus,
    stage_story_sage,
    stage_story_synthesize,
)


class StorySessionTests(unittest.TestCase):
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
            result = process_fragment(paths, fragment, session, bible)
            self.assertTrue(paths.bible.exists())
            self.assertTrue(paths.turns.exists())
            self.assertEqual(result["bible"]["fragment_count"], 1)
            self.assertIn("林澜", json.dumps(result["bible"], ensure_ascii=False))
            self.assertIn("我听懂了", result["agent_reply"])

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
        updated = stage_story_synthesize(fragment, sage, focus, bible)
        actions = {item["action"] for item in focus["decisions"]}
        self.assertIn("park", actions)
        self.assertTrue(updated["plot_threads"])
        reply = build_agent_reply(sage, focus, updated)
        self.assertIn("Focus", reply)


if __name__ == "__main__":
    unittest.main()
