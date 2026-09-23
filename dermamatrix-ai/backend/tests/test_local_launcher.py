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
        self.assertTrue((APP_ROOT / "Start DermaMatrix.command").stat().st_mode & 0o111)
        self.assertTrue((APP_ROOT / "scripts" / "install_macos_local_service.sh").stat().st_mode & 0o111)
