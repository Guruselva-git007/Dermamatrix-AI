"""Failure isolation and provenance checks for the real upload endpoint."""

from __future__ import annotations

import io
import os
import sys
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import app


def upload(*, area: str = "Hair", context: str = "scalp", dermoscopy: bool = False):
    image = Image.new("RGB", (620, 620), "#9e725f")
    draw = ImageDraw.Draw(image)
    for x in range(0, 620, 13):
        draw.line((x, 0, x, 619), fill="#43332e", width=3)
    data = io.BytesIO()
    image.save(data, "PNG")
    fields = {
        "image": (io.BytesIO(data.getvalue()), "photo.png"),
        "area": area, "image_context": context, "image_consent": "true",
    }
    if dermoscopy:
        fields["dermoscopy_attestation"] = "true"
    return app.test_client().post("/api/assessments", data=fields, content_type="multipart/form-data")


class CanonicalEvidenceTests(unittest.TestCase):
    def test_ordinary_photo_contrast_is_not_affected_anatomy(self):
        result = upload().get_json()
        evidence = result["canonical_evidence"]
        self.assertTrue(evidence["candidate_region"]["available"])
        self.assertFalse(result["visual_evidence"]["available"])
        self.assertIsNone(result["visual_evidence"]["affected_area_percent"])
        self.assertNotIn("visual_extent", [factor["key"] for factor in evidence["assessment_risk"]["factors"]])

    def test_independent_component_failures_keep_real_findings(self):
        for component, name in (
            ("reported_symptom_severity", "severity"),
            ("calculate_pirs", "pirs"),
            ("extract_visual_candidate_region", "candidate_region"),
            ("assess_condition_evidence", "condition_evidence"),
        ):
            with self.subTest(component=component), patch(f"app.{component}", side_effect=RuntimeError("test failure")):
                result = upload().get_json()
                evidence = result["canonical_evidence"]
                self.assertEqual(evidence["component_status"][name], "failed")
                self.assertEqual(evidence["assessment_type"], "IMAGE_FINDINGS")
                self.assertEqual(evidence["input_domain"], "ORDINARY_PHOTO")
                self.assertEqual(evidence["condition_evidence"]["status"], "FAILED" if name == "condition_evidence" else "INSUFFICIENT_MEASURED_EVIDENCE")
                self.assertEqual(evidence["condition_evidence"]["possible_concerns"], [])
                self.assertIsNone(evidence["condition_evidence"]["evidence_strength"])
                self.assertTrue(evidence["visible_findings"])
                self.assertEqual(result["assessment_result"]["canonical_evidence"], evidence)
                if name == "severity":
                    self.assertIsNone(result["assessment_result"]["severity"]["score"])
                if name == "pirs":
                    self.assertEqual(evidence["pirs"], {})
                if name == "condition_evidence":
                    self.assertEqual(evidence["condition_evidence"]["possible_concerns"], [])
                    self.assertIsNone(evidence["condition_evidence"]["evidence_strength"])

    def test_image_processing_failure_does_not_fabricate_findings(self):
        with patch("app.analyze_native_image", side_effect=RuntimeError("test failure")):
            result = upload().get_json()
        evidence = result["canonical_evidence"]
        self.assertEqual(evidence["component_status"]["image_processing"], "failed")
        self.assertEqual(evidence["visible_findings"], [])
        self.assertEqual(evidence["measurements"], {})
        self.assertEqual(evidence["assessment_type"], "LIMITED_EVIDENCE")

    def test_scoped_model_and_segmentation_fail_independently(self):
        with patch("app.segment_dermoscopic_lesion", side_effect=RuntimeError("test failure")), patch("app.classify_dermoscopic_lesion", side_effect=RuntimeError("test failure")):
            result = upload(area="Skin", context="dermoscopic_lesion", dermoscopy=True).get_json()
        evidence = result["canonical_evidence"]
        self.assertNotEqual(result["quality"]["status"], "LOW_QUALITY")
        self.assertEqual(evidence["component_status"]["segmentation"], "failed")
        self.assertEqual(evidence["component_status"]["classification"], "failed")
        self.assertIsNone(evidence["classification"]["condition"])
        self.assertTrue(evidence["visible_findings"])

    def test_uncalibrated_research_ranking_is_preserved_without_inventing_a_class(self):
        ranking = {
            "available": True, "model_id": "test-research-model",
            "top_prediction": {"condition": "Research class", "relative_score": 0.8},
            "top_predictions": [{"label": "Research class", "relative_score": 0.8}],
            "condition_likelihood": {"available": False, "estimated_likelihood": None},
            "calibration": {"available": False},
            "uncertainty": {"status": "UNCERTAIN", "certainty": "NOT_AVAILABLE"},
        }
        with patch("app.classify_dermoscopic_lesion", return_value=ranking):
            response = upload(area="Skin", context="dermoscopic_lesion", dermoscopy=True)
        self.assertEqual(response.status_code, 200)
        result = response.get_json()
        evidence = result["canonical_evidence"]
        self.assertEqual(evidence["assessment_type"], "CLASSIFICATION_SUPPORTED")
        self.assertEqual(evidence["classification"]["score_kind"], "relative_model_score")
        self.assertEqual(evidence["classification"]["confidence"], 0.8)
        # An unknown model class still must not be mapped to a fabricated condition.
        self.assertFalse(result["assessment_result"]["condition"]["available"])


if __name__ == "__main__":
    unittest.main()
