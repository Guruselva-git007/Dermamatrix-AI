"""Local image evidence stays image-specific and separate from diagnosis."""

from __future__ import annotations

import io
import os
import sys
import unittest

from PIL import Image, ImageDraw

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import app
from nail_classifier import weights_available as nail_weights_available


def photo(kind: str) -> bytes:
    image = Image.new("RGB", (640, 640), "#b9826a")
    draw = ImageDraw.Draw(image)
    if kind == "striped":
        for x in range(0, 640, 12):
            draw.rectangle((x, 0, x + 4, 639), fill="#302028")
    else:
        draw.rectangle((100, 100, 540, 540), fill="#eee4ca")
    output = io.BytesIO()
    image.save(output, "JPEG")
    return output.getvalue()


class NativeImageFindingsTests(unittest.TestCase):
    def test_hair_and_nail_uploads_return_independent_measured_evidence(self):
        for area, context in (("Hair", "scalp"), ("Nails", "fingernail")):
            results = []
            for kind in ("striped", "block"):
                response = app.test_client().post("/api/assessments", data={
                    "image": (io.BytesIO(photo(kind)), "upload.jpg"),
                    "area": area, "image_context": context, "image_consent": "true",
                }, content_type="multipart/form-data")
                self.assertEqual(response.status_code, 200)
                result = response.get_json()
                findings = result["image_findings"]
                self.assertEqual(findings["assessment_mode"], "IMAGE_FINDINGS")
                self.assertEqual(findings["source"], "local_pixel_analysis")
                self.assertTrue(findings["observations"])
                self.assertEqual(result["assessment_completeness"]["status"], "complete_available_evidence")
                if area == "Hair" or not nail_weights_available():
                    self.assertFalse(result["assessment_result"]["condition"]["available"])
                else:
                    self.assertTrue(result["research_classifier"]["available"])
                    self.assertEqual(result["assessment_result"]["status"]["code"], "RESEARCH_ONLY")
                self.assertEqual(result["assessment_result"]["image_findings"], findings)
                results.append(findings["measurements"])
            self.assertNotEqual(results[0]["adjacent_pixel_change"], results[1]["adjacent_pixel_change"])
            self.assertNotEqual(results[0]["color_deviation"], results[1]["color_deviation"])


if __name__ == "__main__":
    unittest.main()
