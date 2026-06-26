import json
import tempfile
import unittest
from pathlib import Path

from bedagent_mvp import build_run_id, run_closed_loop


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


if __name__ == "__main__":
    unittest.main()
