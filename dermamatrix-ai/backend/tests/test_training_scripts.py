"""Regression checks for optional offline research tooling."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"


class TrainingScriptTests(unittest.TestCase):
    def test_skin_lesion_runner_starts_without_missing_research_dependencies(self):
        """``--help`` imports the plotting and ML modules without reading data."""
        completed = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "run_skin_lesion_experiment.py"), "--help"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("leakage-aware dermatoscopy research experiment", completed.stdout)

    def test_three_class_dermoscopy_runner_starts_without_missing_research_dependencies(self):
        """The local-source runner must remain an offline-only utility."""
        completed = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "run_three_class_dermoscopy_experiment.py"), "--help"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("leakage-aware three-class dermoscopy research experiment", completed.stdout)

    def test_research_asset_inventory_starts_without_reading_or_modifying_data(self):
        """Asset intake must stay separate from experiment preparation and training."""
        completed = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "audit_research_asset_roots.py"), "--help"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("read-only inventory", completed.stdout)


if __name__ == "__main__":
    unittest.main()
