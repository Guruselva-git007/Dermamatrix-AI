"""The optional photo review must use image pixels and separate consent."""

from __future__ import annotations

import base64
import io
import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

from PIL import Image, ImageDraw

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import app
from clinical_skin_classifier import weights_available as clinical_skin_weights_available
from visual_review_service import review_skin_photo


def example_photo() -> bytes:
    image = Image.new("RGB", (720, 720), "#c28a67")
    draw = ImageDraw.Draw(image)
    for x in range(0, 720, 18):
        draw.line((x, 0, x, 719), fill="#775542", width=2)
    output = io.BytesIO()
    image.save(output, "JPEG")
    return output.getvalue()


class VisualReviewTests(unittest.TestCase):
    def test_ordinary_photo_uses_native_findings_without_external_review(self):
        photo = example_photo()
        response = app.test_client().post("/api/assessments", data={
            "image": (io.BytesIO(photo), "original.jpg"), "area": "Skin",
            "image_context": "face_skin", "image_consent": "true",
        }, content_type="multipart/form-data")
        self.assertEqual(response.status_code, 200)
        result = response.get_json()
        self.assertEqual(result["image_findings"]["assessment_mode"], "IMAGE_FINDINGS")
        self.assertTrue(result["image_findings"]["observations"])
        self.assertEqual(result["assessment_result"]["status"]["code"], "RESEARCH_ONLY" if clinical_skin_weights_available() else "MODEL_UNAVAILABLE")
        if clinical_skin_weights_available():
            self.assertEqual(result["research_classifier"]["model_id"], "clinical-skin-efficientnet-research")
        self.assertEqual(result["assessment_completeness"]["status"], "complete_available_evidence")

    def test_vision_request_contains_actual_pixels_and_does_not_store_response(self):
        photo = example_photo()
        result = {"summary": "Uneven visible color.", "observations": [
            {"area": "cheek", "finding": "Small darker marks", "visible_evidence": "Several brown spots are visible.", "certainty": "clear"},
        ], "not_assessable": ["Cause of the marks"], "photo_limitations": ["One lighting angle"]}
        api_response = {"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(result)}]}]}
        reply = MagicMock()
        reply.__enter__.return_value.read.return_value = json.dumps(api_response).encode()
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}), patch("visual_review_service.urllib.request.urlopen", return_value=reply) as send:
            reviewed = review_skin_photo(photo, image_context="face_skin")
        self.assertEqual(reviewed["status"], "completed")
        self.assertEqual(reviewed["observations"][0]["finding"], "Small darker marks")
        request = send.call_args.args[0]
        body = json.loads(request.data)
        self.assertFalse(body["store"])
        image_url = body["input"][1]["content"][1]["image_url"]
        self.assertTrue(image_url.startswith("data:image/jpeg;base64,"))
        with Image.open(io.BytesIO(base64.b64decode(image_url.split(",", 1)[1]))) as sent_image:
            self.assertEqual(sent_image.size, (720, 720))
            self.assertFalse(sent_image.getexif())


if __name__ == "__main__":
    unittest.main()
