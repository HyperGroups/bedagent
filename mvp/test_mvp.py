import json
import tempfile
import unittest
from pathlib import Path

from bedagent_mvp import run_closed_loop


class BedagentMvpTests(unittest.TestCase):
    def test_non_interactive_denies_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "runs"
            manifest = run_closed_loop(
                idea="Draft a design note for better report format.",
                output_root=out,
                auto_confirm=False,
                non_interactive=True,
            )
            self.assertFalse(manifest["confirm"]["approved"])
            self.assertEqual(manifest["act"]["status"], "skipped")

    def test_auto_confirm_executes_simulation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "runs"
            manifest = run_closed_loop(
                idea="Implement a tiny feature and update docs.",
                output_root=out,
                auto_confirm=True,
                non_interactive=False,
            )
            self.assertTrue(manifest["confirm"]["approved"])
            self.assertEqual(manifest["act"]["status"], "simulated_success")
            run_dir = out / manifest["run_id"]
            self.assertTrue((run_dir / "manifest.json").exists())
            payload = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertIn("report", payload)


if __name__ == "__main__":
    unittest.main()
