"""Do not accept CLI exit success as evidence of a completed browser workflow."""
import importlib.util
import json
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("browser_runner", Path(__file__).resolve().parents[2] / "frontend/tests/run_browser_regressions.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class BrowserEvidenceTests(unittest.TestCase):
    def test_valid_evidence_preserves_actual_checks(self):
        value = {"checks": ["account isolation", "real download"], "errors": []}
        self.assertEqual(runner.verified_result(json.dumps(value), 2), value)

    def test_exit_zero_cli_error_is_not_success(self):
        with self.assertRaises(ValueError):
            runner.verified_result("### Error\nTimeoutError", 1)

    def test_truncated_result_is_not_success(self):
        with self.assertRaises(ValueError):
            runner.verified_result('{"checks": [', 1)

    def test_missing_error_status_is_not_success(self):
        with self.assertRaises(ValueError):
            runner.verified_result('{"checks": ["rendered"]}', 1)

    def test_incomplete_workflow_is_not_success(self):
        with self.assertRaises(ValueError):
            runner.verified_result('{"checks": ["first step"], "errors": []}', 2)

    def test_uncaught_browser_error_is_not_success(self):
        with self.assertRaises(ValueError):
            runner.verified_result('{"checks": ["rendered"], "errors": ["uncaught"]}', 1)

    def test_invalid_check_labels_are_not_success(self):
        for checks in [[""], [True], "not an array"]:
            with self.subTest(checks=checks), self.assertRaises(ValueError):
                runner.verified_result(json.dumps({"checks": checks, "errors": []}), 1)
