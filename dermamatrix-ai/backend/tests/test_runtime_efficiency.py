"""Keep optional inference libraries off ordinary web requests."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import unittest
from io import BytesIO

from PIL import Image, ImageDraw


BACKEND_DIR = Path(__file__).resolve().parents[1]


class RuntimeEfficiencyTests(unittest.TestCase):
    def test_reused_decode_preserves_image_evidence_and_exif_orientation(self):
        from app import _image_quality_from_decoded, _opened_image, image_quality
        from native_image_findings import analyze_native_image
        from segmentation_service import extract_visual_candidate_region

        image = Image.new("RGB", (900, 700), (220, 210, 200))
        ImageDraw.Draw(image).ellipse((200, 150, 650, 550), fill=(55, 65, 70))
        exif = image.getexif()
        exif[274] = 6
        output = BytesIO()
        image.save(output, format="JPEG", exif=exif)
        payload = output.getvalue()
        decoded, image_format, width, height = _opened_image(payload, "sample.jpg")

        self.assertEqual(
            image_quality(payload, "sample.jpg"),
            _image_quality_from_decoded(decoded, image_format, width, height),
        )
        self.assertEqual(
            extract_visual_candidate_region(payload),
            extract_visual_candidate_region(payload, decoded_image=decoded),
        )
        self.assertEqual(
            analyze_native_image(payload, area="Skin", quality_status="GOOD"),
            analyze_native_image(payload, area="Skin", quality_status="GOOD", decoded_image=decoded),
        )

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
