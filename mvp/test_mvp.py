import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from bedagent_mvp import (
    build_retention_report,
    build_recap,
    build_run_id,
    evaluate_live_policy,
    list_managed_worktrees,
    run_closed_loop,
    select_worktree_cleanup_candidates,
    semantic_memory_search,
)


class BedagentMvpTests(unittest.TestCase):
    def run_with_defaults(self, tmp: str, **kwargs):
        out = Path(tmp) / "runs"
        return run_closed_loop(
            idea=kwargs.get("idea", "Draft a design note for better report format."),
            output_root=out,
            auto_confirm=kwargs.get("auto_confirm", False),
            non_interactive=kwargs.get("non_interactive", True),
            blanket_policy_path=Path(
                kwargs.get(
                    "blanket_policy_path",
                    Path(__file__).with_name("blanket_policy.json"),
                )
            ),
            sandbox_adapter=kwargs.get("sandbox_adapter", "simulated"),
            memory_journal_path=Path(kwargs.get("memory_journal_path", Path(tmp) / "journal.ndjson")),
            git_repo_root=Path(kwargs.get("git_repo_root", ".")),
            allow_side_effects=kwargs.get("allow_side_effects", False),
        )

    def test_build_run_id_is_unique(self) -> None:
        first = build_run_id()
        second = build_run_id()
        self.assertNotEqual(first, second)

    def test_non_interactive_denies_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self.run_with_defaults(
                tmp, idea="Update design note for better report format."
            )
            self.assertFalse(manifest["confirm"]["approved"])
            self.assertEqual(manifest["act"]["status"], "skipped")
            self.assertTrue(manifest["memory"]["entry_appended"])

    def test_auto_confirm_executes_simulation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "runs"
            manifest = self.run_with_defaults(
                tmp,
                idea="Implement a tiny feature and update docs.",
                auto_confirm=True,
                non_interactive=False,
            )
            self.assertTrue(manifest["confirm"]["approved"])
            self.assertEqual(manifest["act"]["status"], "simulated_success")
            run_dir = out / manifest["run_id"]
            self.assertTrue((run_dir / "manifest.json").exists())
            payload = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertIn("report", payload)
            self.assertIn("policy_explain", payload)

    def test_worktree_dry_run_generates_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "runs"
            manifest = self.run_with_defaults(
                tmp,
                idea="Implement feature branch flow and update docs.",
                auto_confirm=True,
                non_interactive=False,
                sandbox_adapter="worktree-dry-run",
                git_repo_root=".",
            )
            self.assertEqual(manifest["act"]["status"], "dry_run_ready")
            self.assertTrue(
                Path(manifest["act"]["dry_run_plan_path"]).exists(),
                "expected dry-run plan file to be generated",
            )
            run_dir = out / manifest["run_id"]
            self.assertTrue((run_dir / "manifest.json").exists())

    def test_worktree_live_requires_side_effect_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self.run_with_defaults(
                tmp,
                idea="Prepare branch execution for docs update.",
                auto_confirm=True,
                non_interactive=False,
                sandbox_adapter="worktree-live",
                allow_side_effects=False,
            )
            self.assertEqual(manifest["act"]["status"], "policy_blocked_side_effects")

    def test_custom_policy_can_block_auto_confirm(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            policy_path = Path(tmp) / "policy.json"
            policy_path.write_text(
                json.dumps(
                    {
                        "red_keywords": ["docs"],
                        "yellow_keywords": [],
                        "allow_auto_confirm_red": False,
                        "require_confirmation_by_risk": {"green": False, "yellow": True, "red": True},
                    }
                ),
                encoding="utf-8",
            )
            manifest = self.run_with_defaults(
                tmp,
                idea="Update docs for new rollout plan.",
                auto_confirm=True,
                non_interactive=False,
                blanket_policy_path=policy_path,
            )
            self.assertFalse(manifest["confirm"]["approved"])
            self.assertEqual(manifest["confirm"]["mode"], "policy_blocked_auto_confirm_red")

    def test_memory_recap_reads_recent_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            journal = Path(tmp) / "journal.ndjson"
            self.run_with_defaults(
                tmp,
                idea="Update docs and notes.",
                auto_confirm=True,
                non_interactive=False,
                memory_journal_path=journal,
            )
            self.run_with_defaults(
                tmp,
                idea="Prepare safe branch execution plan.",
                auto_confirm=True,
                non_interactive=False,
                sandbox_adapter="worktree-dry-run",
                memory_journal_path=journal,
            )
            recap = build_recap(journal_path=journal, limit=5)
            self.assertEqual(recap["total_loaded"], 2)
            self.assertIsNotNone(recap["latest"])
            self.assertIn("summary", recap)
            self.assertIn("status_counts", recap["summary"])

    def test_custom_policy_can_block_live_adapter_by_risk(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            policy_path = Path(tmp) / "policy.json"
            policy_path.write_text(
                json.dumps(
                    {
                        "allow_live_adapter_by_risk": {"green": True, "yellow": False, "red": False},
                        "live_adapter_block_keywords": [],
                    }
                ),
                encoding="utf-8",
            )
            manifest = self.run_with_defaults(
                tmp,
                idea="Update docs summary and links.",
                auto_confirm=True,
                non_interactive=False,
                sandbox_adapter="worktree-live",
                allow_side_effects=True,
                blanket_policy_path=policy_path,
            )
            self.assertEqual(manifest["act"]["status"], "policy_blocked_live_risk")

    def test_list_managed_worktrees_reads_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "worktrees"
            (root / "run-a").mkdir(parents=True)
            (root / "run-b").mkdir(parents=True)
            items = list_managed_worktrees(root)
            self.assertEqual(len(items), 2)
            self.assertEqual(items[0]["run_id"], "run-a")

    def test_live_policy_explain_reports_keyword_block(self) -> None:
        policy = {
            "allow_live_adapter_by_risk": {"green": True, "yellow": True, "red": False},
            "live_adapter_block_keywords": ["docs"],
        }
        explain = evaluate_live_policy(
            risk_level="green",
            idea="Update docs and links",
            policy=policy,
            allow_side_effects=True,
        )
        self.assertFalse(explain["allowed"])
        self.assertIn("docs", explain["blocked_keywords"])

    def test_semantic_memory_search_finds_relevant_entry(self) -> None:
        entries = [
            {"run_id": "1", "idea": "prepare billing rollout", "pillow_note": "note a"},
            {"run_id": "2", "idea": "write docs navigation", "pillow_note": "note b"},
        ]
        hits = semantic_memory_search(entries=entries, query="billing plan", top_k=1)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["entry"]["run_id"], "1")

    def test_select_worktree_cleanup_candidates_by_ttl_and_max_keep(self) -> None:
        now = datetime(2026, 6, 26, 14, 0, 0, tzinfo=timezone.utc)
        items = [
            {
                "run_id": "20260626T135000.000000Z-aaaaaa",
                "path": "/tmp/w1",
                "mtime_epoch": now.timestamp() - 60,
            },
            {
                "run_id": "20260625T120000.000000Z-bbbbbb",
                "path": "/tmp/w2",
                "mtime_epoch": now.timestamp() - 3600,
            },
            {
                "run_id": "20260624T120000.000000Z-cccccc",
                "path": "/tmp/w3",
                "mtime_epoch": now.timestamp() - 7200,
            },
        ]
        candidates = select_worktree_cleanup_candidates(items=items, now=now, ttl_hours=24, max_keep=1)
        paths = {item["path"] for item in candidates}
        self.assertIn("/tmp/w2", paths)
        self.assertIn("/tmp/w3", paths)

    def test_build_retention_report_contains_candidates(self) -> None:
        now = datetime(2026, 6, 26, 14, 0, 0, tzinfo=timezone.utc)
        policy = {"worktree_retention": {"ttl_hours": 1, "max_keep": 1}}
        items = [
            {"run_id": "20260626T135900.000000Z-aaaaaa", "path": "/tmp/w1", "mtime_epoch": now.timestamp()},
            {"run_id": "20260626T120000.000000Z-bbbbbb", "path": "/tmp/w2", "mtime_epoch": now.timestamp() - 7200},
        ]
        report = build_retention_report(items=items, policy=policy, now=now)
        self.assertEqual(report["candidate_count"], 1)
        self.assertEqual(report["candidates"][0]["path"], "/tmp/w2")

    def test_policy_explain_chain_includes_act_live_checks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self.run_with_defaults(
                tmp,
                idea="Prepare docs branch plan.",
                auto_confirm=True,
                non_interactive=False,
                sandbox_adapter="worktree-live",
                allow_side_effects=False,
            )
            explain = manifest["policy_explain"]
            gates = [item["gate"] for item in explain["gates"]]
            self.assertIn("blanket", gates)
            self.assertIn("confirm", gates)
            self.assertIn("act-live-policy", gates)


if __name__ == "__main__":
    unittest.main()
