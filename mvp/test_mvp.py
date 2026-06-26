import json
import tempfile
import unittest
from pathlib import Path

from bedagent_mvp import build_recap, build_run_id, run_closed_loop


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
            manifest = self.run_with_defaults(tmp)
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


if __name__ == "__main__":
    unittest.main()
