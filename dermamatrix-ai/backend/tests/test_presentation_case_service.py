"""Tests for the opt-in, exact-file viva teaching-case boundary."""

from __future__ import annotations

import os
import sys
import unittest
from io import BytesIO
from unittest.mock import patch

from PIL import Image, ImageDraw


BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from presentation_case_service import PRESENTATION_CASES, presentation_case_for_digest


class PresentationCaseTests(unittest.TestCase):
    def test_case_lookup_requires_an_exact_digest_and_matching_area(self):
        digest = "f229ef0cf5e9318dea63fd500ca3a72d0f9bd7709cbd76912773e8614a2e5733"
        case = presentation_case_for_digest(digest, "Skin")
        self.assertTrue(case["matched"])
        self.assertEqual(case["topic_id"], "acne")
        self.assertEqual(case["matching_method"], "EXACT_FILE_SHA256")
        self.assertIsNone(presentation_case_for_digest(digest, "Hair"))
        self.assertIsNone(presentation_case_for_digest("0" * 64, "Skin"))

    def test_all_cases_are_prelabelled_education_not_model_records(self):
        self.assertEqual(len(PRESENTATION_CASES), 12)
        for digest, case in PRESENTATION_CASES.items():
            matched = presentation_case_for_digest(digest, case["area"])
            self.assertIn("not AI inference", matched["notice"])
            self.assertFalse(matched["medication_notice"].lower().startswith("prescribe"))

    def test_assessment_exposes_case_only_through_opt_in_matcher(self):
        from app import app

        image = Image.new("RGB", (640, 640), color=(225, 235, 245))
        draw = ImageDraw.Draw(image)
        for point in range(20, 620, 40):
            draw.ellipse((point, point, point + 14, point + 14), fill=(130, 70, 70))
        payload = BytesIO(); image.save(payload, format="PNG")
        case = presentation_case_for_digest(
            "f229ef0cf5e9318dea63fd500ca3a72d0f9bd7709cbd76912773e8614a2e5733", "Skin"
        )
        with patch("app.presentation_case_for_image", return_value=case):
            response = app.test_client().post("/api/assessments", data={
                "image": (BytesIO(payload.getvalue()), "teaching.png"), "area": "Skin",
                "image_context": "face_skin", "image_consent": "true",
                "presentation_case_enabled": "true", "duration": "0", "discomfort": "0", "change": "0",
            }, content_type="multipart/form-data")
        result = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(result["presentation_case"]["matched"])
        self.assertEqual(result["research_classifier"]["available"], False)
        self.assertEqual(result["assessment_result"]["condition"]["available"], False)
        self.assertEqual(result["recommendations"]["medication_information"]["status"], "EDUCATIONAL_DISCUSSION_ONLY")
        self.assertTrue(result["recommendations"]["diet"])


if __name__ == "__main__":
    unittest.main()
