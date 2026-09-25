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
    def test_unmapped_photo_with_presentation_enabled_stays_a_standard_assessment(self):
        from app import app

        image = Image.new("RGB", (640, 640), (210, 195, 180))
        ImageDraw.Draw(image).rectangle((150, 150, 490, 490), fill=(95, 85, 75))
        payload = BytesIO()
        image.save(payload, format="JPEG")
        response = app.test_client().post("/api/assessments", data={
            "image": (BytesIO(payload.getvalue()), "ordinary.jpg"),
            "area": "Skin", "image_context": "face_skin", "image_consent": "true",
            "presentation_case_enabled": "true",
        }, content_type="multipart/form-data")
        self.assertEqual(response.status_code, 200)
        result = response.get_json()
        self.assertEqual(result["presentation_case"]["status"], "NO_EXACT_MATCH")
        self.assertFalse(result["presentation_case"]["matched"])
        self.assertFalse(result["assessment_result"]["presentation"]["is_reference_case"])
        self.assertFalse(result["research_classifier"]["available"])
        self.assertFalse(result["assessment_result"]["condition"]["available"])

    def test_case_lookup_requires_an_exact_digest_and_matching_area(self):
        digest = "f229ef0cf5e9318dea63fd500ca3a72d0f9bd7709cbd76912773e8614a2e5733"
        case = presentation_case_for_digest(digest, "Skin")
        self.assertTrue(case["matched"])
        self.assertEqual(case["topic_id"], "acne")
        self.assertEqual(case["matching_method"], "EXACT_FILE_SHA256")
        self.assertIsNone(presentation_case_for_digest(digest, "Hair"))
        self.assertIsNone(presentation_case_for_digest("0" * 64, "Skin"))

    def test_all_cases_are_prelabelled_education_not_model_records(self):
        self.assertGreaterEqual(len(PRESENTATION_CASES), 20)
        for digest, case in PRESENTATION_CASES.items():
            matched = presentation_case_for_digest(digest, case["area"])
            self.assertIn("not AI inference", matched["notice"])
            self.assertFalse(matched["medication_notice"].lower().startswith("prescribe"))

    def test_additional_review_references_are_exact_match_only(self):
        dandruff = presentation_case_for_digest("6e48c9bfdee255672a7fcb764741a6a2474c40f119f68ac57790c4c5c3147532", "Hair")
        pigmentation = presentation_case_for_digest("8dba72dfc134e89a05525a309b2d02cf063219958d45517c9ca76aedca0b775f", "Skin")
        chart = presentation_case_for_digest("e6add51030e175563c8c43cdfad7bf4bde1d90cd320837e7f2cf25eb8465b292", "Skin")
        avif_acne = presentation_case_for_digest("882c972469595ed23ca031c18eb6498ad152e68b6c9c41ef1654c22ea473237d", "Skin")
        self.assertEqual(dandruff["topic_id"], "seborrheic-dermatitis")
        self.assertEqual(pigmentation["topic_id"], "hyperpigmentation")
        self.assertIn("several different concerns", chart["teaching_summary"])
        self.assertTrue(chart["common_contributors"])
        self.assertEqual(avif_acne["topic_id"], "acne")

    def test_reference_metadata_keeps_the_shared_risk_pipeline_label_independent(self):
        from app import app

        image = Image.new("RGB", (640, 640), color=(225, 235, 245))
        draw = ImageDraw.Draw(image)
        for point in range(20, 620, 40):
            draw.ellipse((point, point, point + 14, point + 14), fill=(130, 70, 70))
        payload = BytesIO(); image.save(payload, format="PNG")
        case = presentation_case_for_digest(
            "f229ef0cf5e9318dea63fd500ca3a72d0f9bd7709cbd76912773e8614a2e5733", "Skin"
        )
        with patch("app.presentation_case_for_image", side_effect=lambda _image, _area, enabled: case if enabled else None):
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
        self.assertTrue(result["assessment_risk"]["available"])
        self.assertIsInstance(result["assessment_risk"]["score"], int)
        self.assertEqual(result["assessment_risk"]["condition_profile"]["key"], "undifferentiated-skin")
        self.assertEqual(result["assessment_risk"]["condition_profile"]["condition_source"], "No condition label used")
        self.assertTrue(result["assessment_result"]["presentation"]["is_reference_case"])
        self.assertEqual(result["recommendations"]["medication_information"]["status"], "NO_MEDICATION_RECOMMENDATION")
        self.assertNotIn("teaching", result["assessment_result"]["consumer"]["primary_result"]["title"].lower())
        self.assertTrue(result["assessment_result"]["consumer"]["technical_details"]["reference_case"])
        self.assertTrue(result["recommendations"]["diet"])

    def test_checkbox_combinations_do_not_suppress_reference_risk(self):
        from app import app

        image = Image.new("RGB", (640, 640), color=(225, 235, 245))
        draw = ImageDraw.Draw(image)
        draw.rectangle((180, 180, 430, 430), fill=(90, 45, 45))
        payload = BytesIO(); image.save(payload, format="PNG")
        case = presentation_case_for_digest(
            "f229ef0cf5e9318dea63fd500ca3a72d0f9bd7709cbd76912773e8614a2e5733", "Skin"
        )

        def submit(*, presentation: bool, prompt: bool):
            with patch("app.presentation_case_for_image", side_effect=lambda _image, _area, enabled: case if enabled else None):
                return app.test_client().post("/api/assessments", data={
                    "image": (BytesIO(payload.getvalue()), "review.png"), "area": "Skin",
                    "image_context": "face_skin", "image_consent": "true",
                    "presentation_case_enabled": str(presentation).lower(), "urgent_concern": str(prompt).lower(),
                    "duration": "0", "discomfort": "0", "change": "0",
                }, content_type="multipart/form-data").get_json()

        standard = submit(presentation=False, prompt=False)
        reference = submit(presentation=True, prompt=False)
        prompt_standard = submit(presentation=False, prompt=True)
        prompt_reference = submit(presentation=True, prompt=True)
        repeated_prompt_reference = submit(presentation=True, prompt=True)
        for result in (standard, reference, prompt_standard, prompt_reference):
            self.assertTrue(result["assessment_risk"]["available"])
            self.assertIsInstance(result["assessment_risk"]["score"], int)
            self.assertGreaterEqual(result["assessment_risk"]["score"], 0)
            self.assertLessEqual(result["assessment_risk"]["score"], 100)
        self.assertTrue(reference["presentation_case"]["matched"])
        self.assertEqual(reference["assessment_risk"]["score"], standard["assessment_risk"]["score"])
        self.assertEqual(prompt_standard["assessment_risk"]["urgency"], "URGENT_EVALUATION")
        self.assertEqual(prompt_reference["assessment_risk"]["urgency"], "URGENT_EVALUATION")
        self.assertEqual(prompt_reference["assessment_risk"]["score"], prompt_standard["assessment_risk"]["score"])
        self.assertEqual(prompt_reference["assessment_risk"]["score"], repeated_prompt_reference["assessment_risk"]["score"])


if __name__ == "__main__":
    unittest.main()
