import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from llm_adapter import llm_status, parse_questions_from_text, simulate_story_questions
from story_session import empty_bible, process_fragment, resolve_story_paths, search_stories
from bedagent_mvp import diff_policy_explain, run_closed_loop


class LlmAdapterTests(unittest.TestCase):
    def test_simulate_story_questions_keeps_limit(self) -> None:
        qs = simulate_story_questions("主角是维修AI。", ["启发式问题？"], max_questions=3)
        self.assertEqual(len(qs), 3)
        self.assertTrue(any("维修AI" in item or "不可逆" in item for item in qs))

    def test_parse_questions_from_text(self) -> None:
        raw = "1. 动机是什么？\n2. 这是回忆吗？\nnot a question"
        parsed = parse_questions_from_text(raw, ["fallback?"], 3)
        self.assertEqual(len(parsed), 2)

    def test_llm_status_simulate(self) -> None:
        with mock.patch.dict(os.environ, {"BEDAGENT_LLM": "1", "BEDAGENT_LLM_SIMULATE": "1"}, clear=False):
            status = llm_status()
            self.assertTrue(status["usable"])
            self.assertEqual(status["model"], "simulated-qwen")

    def test_process_fragment_uses_simulated_llm(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_story_paths(Path(tmp), None, "llm-test")
            paths.root.mkdir(parents=True)
            session = {"title": "llm-test", "turn_count": 0, "fragment_count": 0}
            bible = empty_bible("llm-test")
            with mock.patch.dict(os.environ, {"BEDAGENT_LLM": "1", "BEDAGENT_LLM_SIMULATE": "1"}, clear=False):
                result = process_fragment(
                    paths,
                    "主角名叫林澜，她在冬眠舰上维护梦境日志。",
                    session,
                    bible,
                    auto_confirm=True,
                    use_llm=True,
                )
            self.assertTrue(result["turn"]["sage"]["llm"]["used"])
            self.assertEqual(result["turn"]["sage"]["llm"]["model"], "simulated-qwen")


class StorySearchTests(unittest.TestCase):
    def test_search_stories_finds_chinese_main_thread(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = resolve_story_paths(root, None, "梦境舰")
            first.root.mkdir(parents=True)
            process_fragment(
                first,
                "主角是一个维修AI，它在冬眠舰上偷听人类的梦。",
                {"title": "梦境舰", "turn_count": 0, "fragment_count": 0},
                empty_bible("梦境舰"),
                auto_confirm=True,
            )
            second = resolve_story_paths(root, None, "厨房喜剧")
            second.root.mkdir(parents=True)
            process_fragment(
                second,
                "这是一个关于厨师比赛的轻松喜剧。",
                {"title": "厨房喜剧", "turn_count": 0, "fragment_count": 0},
                empty_bible("厨房喜剧"),
                auto_confirm=True,
            )
            hits = search_stories(root, "维修AI 冬眠舰", top_k=2)
            self.assertTrue(hits)
            self.assertIn("维修", hits[0]["entry"]["main_thread"])


class ManifestAndExplainDiffTests(unittest.TestCase):
    def test_manifest_has_schema_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = run_closed_loop(
                idea="Draft a design note for schema versioning.",
                output_root=Path(tmp) / "runs",
                auto_confirm=True,
                non_interactive=False,
                blanket_policy_path=Path(__file__).with_name("blanket_policy.json"),
                sandbox_adapter="simulated",
                memory_journal_path=Path(tmp) / "journal.ndjson",
                git_repo_root=Path("."),
                allow_side_effects=False,
            )
            self.assertEqual(manifest["schema_version"], "1.0.0")

    def test_diff_policy_explain_detects_status_change(self) -> None:
        left = {"policy_explain": {"schema_version": "1.0.0", "final_status": "skipped", "gates": [{"gate": "confirm", "approved": False}]}}
        right = {"policy_explain": {"schema_version": "1.0.0", "final_status": "simulated_success", "gates": [{"gate": "confirm", "approved": True}]}}
        diff = diff_policy_explain(left, right)
        self.assertTrue(diff["changed"])
        fields = {item["field"] for item in diff["changes"]}
        self.assertIn("final_status", fields)
        self.assertIn("confirm.approved", fields)
