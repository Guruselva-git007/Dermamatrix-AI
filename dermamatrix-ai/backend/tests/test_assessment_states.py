"""Regression tests for the normalized patient-facing assessment state."""

from __future__ import annotations

import unittest
from io import BytesIO

from PIL import Image, ImageDraw

from assessment_contract import ASSESSMENT_RESULT_VERSION, build_assessment_result, determine_assessment_state
from recommendation_service import build_recommendations


def _response(*, classifier: dict, finding: dict | None = None, quality: dict | None = None,
              validation: dict | None = None, input_type: str = "image") -> dict:
    return {
        "area": "Skin",
        "input_type": input_type,
        "quality": quality or {"status": "GOOD", "label": "Suitable for visual review", "issues": []},
        "input_validation": validation or {"status": "VALID_RELEVANT"},
        "research_classifier": classifier,
        "condition_intelligence": {"finding": finding or {}, "reported_context_factors": [], "model_scope": {}},
        "risk": {}, "assessment_risk": {}, "severity": {}, "clinical_decision_support": {},
        "segmentation": {}, "candidate_region": {}, "recommendations": {}, "care_plan": {},
    }


def _validated_normal_classifier() -> dict:
    return {
        "available": True,
        "uncertainty": {"status": "CALIBRATED_OUTPUT", "ood_status": "IN_DISTRIBUTION"},
        "normal_appearance": {
            "available": True,
            "status": "VALIDATED_NORMAL_APPEARANCE",
            "validated": True,
            "is_normal": True,
            "condition_signal": "NONE",
            "confidence": 0.91,
            "minimum_confidence": 0.8,
        },
    }


class AssessmentStateTests(unittest.TestCase):
    def test_healthy_requires_explicit_validated_normal_evidence(self):
        healthy = build_assessment_result(_response(classifier=_validated_normal_classifier()))
        self.assertEqual(healthy["contract_version"], ASSESSMENT_RESULT_VERSION)
        self.assertEqual(healthy["status"]["state"], "HEALTHY")
        self.assertEqual(healthy["status"]["code"], "NORMAL_APPEARANCE")
        self.assertFalse(healthy["condition"]["available"])

        unsupported = build_assessment_result(_response(classifier={"available": False, "reason": "No model configured."}))
        self.assertEqual(unsupported["status"]["state"], "UNCERTAIN")
        self.assertNotEqual(unsupported["status"]["state"], "HEALTHY")

    def test_condition_and_conflicting_normal_signals_are_distinct(self):
        classifier = {
            "available": True,
            "top_prediction": {"condition": "Test condition", "relative_score": 0.7},
            "uncertainty": {"status": "CALIBRATED_OUTPUT", "ood_status": "IN_DISTRIBUTION"},
            "condition_likelihood": {"available": True, "estimated_likelihood": 0.6},
        }
        condition = build_assessment_result(_response(classifier=classifier, finding={"name": "Test condition"}))
        self.assertEqual(condition["status"]["state"], "CONDITION")
        self.assertTrue(condition["condition"]["available"])

        conflicting = {**classifier, "normal_appearance": _validated_normal_classifier()["normal_appearance"]}
        conflict = build_assessment_result(_response(classifier=conflicting, finding={"name": "Test condition"}))
        self.assertEqual(conflict["status"]["state"], "UNCERTAIN")
        self.assertFalse(conflict["condition"]["available"])

    def test_invalid_low_quality_and_questionnaire_never_become_healthy(self):
        for kwargs in (
            {"input_type": "image", "quality": {"status": "LOW_QUALITY"}, "validation": {"status": "LOW_QUALITY"}},
            {"input_type": "questionnaire", "quality": {}, "validation": {"status": "VALID_RELEVANT"}},
        ):
            state = determine_assessment_state(classifier=_validated_normal_classifier(), **kwargs)
            self.assertEqual(state["state"], "UNCERTAIN")

    def test_recommendations_are_state_aware(self):
        uncertain = build_recommendations("Skin", None, assessment_state="UNCERTAIN")
        self.assertEqual(uncertain["products"], [])
        self.assertEqual(uncertain["product_guidance"], "DEFER_PRODUCT_DECISIONS")
        self.assertIn("No medicine", uncertain["medicine_policy"])

        healthy = build_recommendations("Hair", _validated_normal_classifier(), assessment_state="HEALTHY")
        self.assertEqual(healthy["product_guidance"], "HEALTHY_MAINTENANCE_ONLY")
        self.assertTrue(healthy["products"])
        self.assertIn("No treatment or medicine", healthy["medicine_policy"])

    def test_clear_hair_and_nail_images_return_a_real_non_diagnostic_result(self):
        from app import app

        image = Image.new("RGB", (640, 640), color=(222, 232, 246))
        draw = ImageDraw.Draw(image)
        for coordinate in range(0, 640, 16):
            draw.line((coordinate, 0, coordinate, 639), fill=(56, 100, 170), width=3)
            draw.line((0, coordinate, 639, coordinate), fill=(56, 100, 170), width=3)
        payload = BytesIO()
        image.save(payload, format="PNG")

        for area, image_context, model_id in (
            ("Hair", "scalp", "hair-model-adapter"),
            ("Nails", "nail_close_up", "nail-model-adapter"),
        ):
            response = app.test_client().post("/api/assessments", data={
                "image": (BytesIO(payload.getvalue()), f"clear-{area.lower()}-context.png"),
                "area": area, "image_context": image_context, "image_consent": "true",
                "duration": "0", "discomfort": "0", "change": "0",
            }, content_type="multipart/form-data")
            result = response.get_json()

            self.assertEqual(response.status_code, 200)
            self.assertEqual(result["assessment_result"]["status"]["state"], "UNCERTAIN")
            self.assertEqual(result["assessment_result"]["status"]["code"], "MODEL_UNAVAILABLE")
            self.assertEqual(result["model_metadata"]["model_id"], model_id)
            self.assertEqual(result["input_validation"]["classification_status"], "NO_COMPATIBLE_CLASSIFIER_CONFIGURED")
            self.assertEqual(result["recommendations"]["products"], [])
            self.assertIn("No medicine", result["recommendations"]["medicine_policy"])
