"""Regression checks for the macOS local-server recovery path."""

from __future__ import annotations

from pathlib import Path
import unittest


APP_ROOT = Path(__file__).resolve().parents[2]


class LocalLauncherTests(unittest.TestCase):
    def test_file_opening_redirects_to_the_loopback_app(self):
        frontend = (APP_ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
        self.assertIn("window.location.replace('http://127.0.0.1:8000/')", frontend)

    def test_macos_launcher_and_service_are_loopback_only(self):
        launcher = (APP_ROOT / "Start DermaMatrix.command").read_text(encoding="utf-8")
        installer = (APP_ROOT / "scripts" / "install_macos_local_service.sh").read_text(encoding="utf-8")
        self.assertIn("http://127.0.0.1:8000/api/health", launcher)
        self.assertIn("install_macos_local_service.sh", launcher)
        self.assertIn("DERMAMATRIX_PORT", installer)
        self.assertIn("com.dermamatrix.local-server", installer)
        self.assertIn("${BACKEND_DIR}/scripts/run_app.sh", installer)
        self.assertIn('/bin/launchctl enable "${SERVICE_NAME}"', installer)
        self.assertIn("bootstrap_local_service()", installer)
        self.assertIn("for attempt in 1 2 3", installer)
        self.assertIn("bootstrap_status=$?", installer)
        self.assertTrue((APP_ROOT / "Start DermaMatrix.command").stat().st_mode & 0o111)
        self.assertTrue((APP_ROOT / "scripts" / "install_macos_local_service.sh").stat().st_mode & 0o111)

    def test_presentation_preflight_checks_the_canonical_runtime(self):
        preflight = (APP_ROOT / "backend" / "scripts" / "check_local_stack.sh").read_text(encoding="utf-8")
        self.assertIn("presentation preflight", preflight)
        self.assertIn("status --porcelain", preflight)
        self.assertIn("ham10000_resnet34_research.ptw", preflight)
        self.assertIn("api/model-registry", preflight)
        self.assertIn("listener on port", preflight)

    def test_assessment_progress_uses_the_four_rendered_stages(self):
        frontend = (APP_ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
        markup = (APP_ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
        for stage in ("Choose area", "Upload or answer", "Add context", "Review result"):
            self.assertIn(stage, markup)
        self.assertIn("STEP 1 OF 4", markup)
        self.assertNotIn("STEP 1 OF 3", markup)
        self.assertIn("const ASSESSMENT_STAGE_COUNT = 4;", frontend)
        self.assertIn("`STEP ${activeStep} OF ${ASSESSMENT_STAGE_COUNT}`", frontend)
        self.assertNotIn("STEP 1 OF 2", frontend)
        self.assertNotIn("STEP 1 OF 3", frontend)
        self.assertNotIn("STEP 2 OF 3", frontend)
        self.assertNotIn("STEP 3 OF 3", frontend)

    def test_model_limitations_are_not_presented_as_bad_photos(self):
        frontend = (APP_ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
        self.assertIn("const modelLimitedReview", frontend)
        self.assertIn("Your screening summary is ready", frontend)
        self.assertIn("Your research screening review is ready", frontend)
        self.assertIn("has no condition classifier for that area", frontend)
        self.assertIn("Keep track of meaningful changes", frontend)
        self.assertIn("Start another check", frontend)
