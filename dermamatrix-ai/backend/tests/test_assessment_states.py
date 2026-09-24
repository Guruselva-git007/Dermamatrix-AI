"""Regression tests for the normalized patient-facing assessment state."""

from __future__ import annotations

import unittest
from io import BytesIO

from PIL import Image, ImageDraw

from assessment_contract import (
    ASSESSMENT_RESULT_VERSION,
    TERMINAL_RESULT_STATES,
    build_assessment_result,
    determine_assessment_state,
    determine_terminal_result_state,
)
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
        self.assertEqual(healthy["result_state"], "healthy")
        self.assertFalse(healthy["condition"]["available"])

        unsupported = build_assessment_result(_response(classifier={"available": False, "reason": "No model configured."}))
        self.assertEqual(unsupported["status"]["state"], "UNCERTAIN")
        self.assertEqual(unsupported["result_state"], "uncertain")
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
        self.assertEqual(condition["result_state"], "condition_detected")
        self.assertTrue(condition["condition"]["available"])

        conflicting = {**classifier, "normal_appearance": _validated_normal_classifier()["normal_appearance"]}
        conflict = build_assessment_result(_response(classifier=conflicting, finding={"name": "Test condition"}))
        self.assertEqual(conflict["status"]["state"], "UNCERTAIN")
        self.assertEqual(conflict["result_state"], "uncertain")
        self.assertFalse(conflict["condition"]["available"])

    def test_consumer_result_keeps_confidence_separate_from_image_evidence(self):
        response = _response(classifier={"available": False}, quality={"status": "GOOD", "label": "Clear", "issues": []})
        response["image_findings"] = {"available": True, "summary": "Measured tone variation in this photo.", "observations": [
            {"finding": "Tone variation", "visible_evidence": "Brightness spans 40–180 in the central crop."},
        ]}
        response["pirs"] = {"score": 42, "band": "MODERATE"}
        response["assessment_risk"] = {"score": 68, "level": "HIGH"}
        response["severity"] = {"level": "MILD"}
        result = build_assessment_result(response)["consumer"]
        self.assertEqual(result["state"], "image_observation")
        self.assertIsNone(result["primary_result"]["confidence"])
        self.assertEqual(result["primary_result"]["evidence_strength"], "Low")
        self.assertEqual(result["pirs"]["score"], 42)
        self.assertEqual(result["concern"]["score"], 68)
        self.assertEqual(result["severity"]["label"], "MILD")
        self.assertEqual(result["possible_conditions"], [])
        self.assertIn("Measured tone variation", result["why_this_result"][0])
        self.assertIn("Brightness spans", result["visible_findings"][0]["detail"])

        response["quality"] = {"status": "LOW_QUALITY", "label": "Retake", "issues": ["Too blurry"]}
        limited = build_assessment_result(response)["consumer"]
        self.assertEqual(limited["state"], "quality_limited")
        self.assertFalse(limited["visible_findings"])
        self.assertTrue(limited["image_quality"]["retake_guidance"])

    def test_terminal_result_state_is_closed_and_evidence_based(self):
        cases = (
            ({"status": "LOW_QUALITY"}, {"status": "LOW_QUALITY"}, {}, {"state": "UNCERTAIN"}, "poor_quality"),
            ({"status": "GOOD"}, {"status": "VALID", "relevance_status": "CATEGORY_MISMATCH"}, {}, {"state": "UNCERTAIN"}, "category_mismatch"),
            ({"status": "GOOD"}, {"status": "VALID"}, {"uncertainty": {"ood_status": "OUT_OF_DISTRIBUTION"}}, {"state": "UNCERTAIN"}, "unsupported_image"),
            ({"status": "GOOD"}, {"status": "VALID"}, {}, {"state": "CONDITION"}, "condition_detected"),
            ({"status": "GOOD"}, {"status": "VALID"}, {}, {"state": "HEALTHY"}, "healthy"),
            ({"status": "GOOD"}, {"status": "VALID_RELEVANT", "relevance_status": "USER_DECLARED_CONTEXT_NOT_AUTOMATICALLY_VERIFIED"}, {}, {"state": "UNCERTAIN"}, "uncertain"),
        )
        observed = set()
        for quality, validation, classifier, assessment_state, expected in cases:
            terminal = determine_terminal_result_state(
                input_type="image", quality=quality, validation=validation,
                classifier=classifier, assessment_state=assessment_state,
            )
            self.assertEqual(terminal["state"], expected)
            self.assertIn(terminal["state"], TERMINAL_RESULT_STATES)
            observed.add(terminal["state"])
        self.assertEqual(observed, TERMINAL_RESULT_STATES)

    def test_rejected_image_contract_has_an_input_terminal_state(self):
        from assessment_contract import build_rejected_image_result

        category = build_rejected_image_result(
            area="Nails", result_state="category_mismatch", notice="Choose a nail image type.",
        )
        unsupported = build_rejected_image_result(
            area="Hair", result_state="unsupported_image", notice="Use a supported image file.",
        )
        self.assertEqual(category["result_state"], "category_mismatch")
        self.assertEqual(category["status"]["code"], "CATEGORY_MISMATCH")
        self.assertEqual(unsupported["result_state"], "unsupported_image")
        self.assertEqual(unsupported["status"]["code"], "INPUT_UNSUITABLE")

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

    def test_real_photo_can_show_general_categories_without_condition_products(self):
        evidence = {
            "image_quality": {"status": "GOOD"},
            "image_findings": {"available": True},
            "assessment_risk": {"available": True, "score": 12, "urgency": "SELF_CARE_MONITOR"},
        }
        low_concern = build_recommendations("Skin", None, assessment_state="UNCERTAIN", canonical_evidence=evidence)
        self.assertEqual(low_concern["products"], [])
        self.assertTrue(low_concern["general_care_categories"])
        self.assertIn("only the area you selected", low_concern["general_care_notice"])
        self.assertIn("skin", low_concern["routine"]["morning"][0].lower())
        self.assertIn("scalp", build_recommendations("Hair", None, assessment_state="UNCERTAIN", canonical_evidence=evidence)["routine"]["morning"][0].lower())
        self.assertIn("nails", build_recommendations("Nails", None, assessment_state="UNCERTAIN", canonical_evidence=evidence)["routine"]["morning"][0].lower())

        for override in (
            {"assessment_risk": {"available": True, "score": 65, "urgency": "URGENT_EVALUATION"}},
            {"image_quality": {"status": "LOW_QUALITY"}},
            {"image_findings": {"available": False}},
        ):
            with self.subTest(override=override):
                limited = build_recommendations("Skin", None, assessment_state="UNCERTAIN", canonical_evidence={**evidence, **override})
                self.assertEqual(limited["general_care_categories"], [])

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
            self.assertEqual(result["assessment_result"]["result_state"], "uncertain")
            self.assertEqual(result["model_metadata"]["model_id"], model_id)
            self.assertEqual(result["input_validation"]["classification_status"], "NO_COMPATIBLE_CLASSIFIER_CONFIGURED")
            self.assertEqual(result["recommendations"]["products"], [])
            self.assertIn("No medicine", result["recommendations"]["medicine_policy"])
