"""Keep optional inference libraries off ordinary web requests."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import unittest


BACKEND_DIR = Path(__file__).resolve().parents[1]


class RuntimeEfficiencyTests(unittest.TestCase):
    def test_flask_import_does_not_load_inference_libraries(self):
        environment = {**os.environ, "PYTHONPATH": str(BACKEND_DIR)}
        result = subprocess.run(
            [sys.executable, "-c", "import app, sys; assert 'torch' not in sys.modules; assert 'numpy' not in sys.modules"],
            cwd=BACKEND_DIR,
            env=environment,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_public_assets_revalidate_without_caching_private_responses(self):
        from app import app

        client = app.test_client()
        stylesheet = client.get("/studio.css")
        self.assertEqual(stylesheet.status_code, 200)
        self.assertEqual(stylesheet.headers["Cache-Control"], "private, no-cache")
        self.assertTrue(stylesheet.headers.get("ETag"))
        revalidated = client.get("/studio.css", headers={"If-None-Match": stylesheet.headers["ETag"]})
        self.assertEqual(revalidated.status_code, 304)
        stylesheet.close()
        revalidated.close()

        for path in ("/", "/api/model-registry"):
            response = client.get(path)
            self.assertIn("no-store", response.headers["Cache-Control"])
            response.close()


if __name__ == "__main__":
    unittest.main()
