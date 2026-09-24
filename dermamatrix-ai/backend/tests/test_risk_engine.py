"""Focused regression tests for the versioned assessment concern indicator."""

from __future__ import annotations

import os
import sys
import unittest


BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from assessment_contract import build_assessment_result
from risk_engine import RISK_ENGINE_VERSION, calculate_assessment_risk


def indicator(**overrides):
    payload = {
        "area": "Skin", "condition_name": None, "condition_source": None,
        "model_confidence": None, "severity": {"score": 0, "level": "MILD"},
        "duration": 0, "discomfort": 0, "recent_change": 0, "symptoms": [],
        "urgent_selected": False, "image_quality": 86, "quality_status": "GOOD",
        "uncertainty_status": "NOT_APPLICABLE_NO_CLASSIFIER", "input_validation_status": "VALID_RELEVANT",
    }
    payload.update(overrides)
    return calculate_assessment_risk(**payload)


class AssessmentRiskEngineTests(unittest.TestCase):
    def test_low_score_is_deterministic_and_versioned(self):
        first = indicator()
        second = indicator()
        self.assertEqual(first["score"], second["score"])
        self.assertEqual(first["level"], "LOW")
        self.assertEqual(first["methodology_version"], RISK_ENGINE_VERSION)
        self.assertEqual(first["validation_status"], "not_clinically_validated")

    def test_change_symptoms_and_severity_raise_the_indicator(self):
        low = indicator()
        raised = indicator(
            severity={"score": 62}, duration=12, discomfort=28, recent_change=24,
            symptoms=["pain", "bleeding", "spreading"],
        )
        self.assertGreater(raised["score"], low["score"])
        self.assertIn(raised["level"], {"HIGH", "VERY_HIGH"})
        self.assertIn("PROMPT_MEDICAL_EVALUATION", raised["urgency"])

    def test_prompt_care_selection_sets_urgent_path_without_becoming_probability(self):
        result = indicator(urgent_selected=True)
        self.assertEqual(result["urgency"], "URGENT_EVALUATION")
        self.assertGreaterEqual(result["score"], 30)
        self.assertIn("not a disease probability", result["explanation"].lower())

    def test_reliability_context_does_not_inflate_score(self):
        clear = indicator(model_confidence=0.91, image_quality=92, uncertainty_status="CALIBRATED_OUTPUT")
        uncertain = indicator(model_confidence=None, image_quality=None, quality_status="LOW_QUALITY", uncertainty_status="UNCERTAIN")
        self.assertEqual(clear["score"], uncertain["score"])
        self.assertIn("image-quality score", uncertain["calculation_inputs"]["missing_optional"])

    def test_only_validated_segmented_extent_contributes_to_concern(self):
        without_region = indicator(condition_name="Acne", condition_source="calibrated scoped research classifier fixture")
        contrast_region = indicator(
            condition_name="Acne", condition_source="calibrated scoped research classifier fixture",
            affected_area_percent=12.0, affected_area_source="contrast-based visual candidate-region extraction",
        )
        smaller_region = indicator(
            condition_name="Acne", condition_source="calibrated scoped research classifier fixture",
            affected_area_percent=12.0, affected_area_source="trained model segmentation",
        )
        larger_region = indicator(
            condition_name="Acne", condition_source="calibrated scoped research classifier fixture",
            affected_area_percent=52.0, affected_area_source="trained model segmentation",
        )
        self.assertEqual(contrast_region["score"], without_region["score"])
        self.assertGreater(smaller_region["score"], without_region["score"])
        self.assertGreater(larger_region["score"], smaller_region["score"])
        self.assertIn("trained model segmentation", larger_region["calculation_inputs"]["used"])
        self.assertIn("not a disease probability", larger_region["explanation"].lower())

    def test_sweat_remains_questionnaire_only(self):
        result = indicator(
            area="Sweat", severity={"score": 22}, duration=3, symptoms=["excessive_sweating", "daily_impact"],
            image_quality=None, quality_status=None, uncertainty_status="NOT_AVAILABLE_NO_VALIDATED_TABULAR_MODEL",
            questionnaire={"pattern": "excessive", "frequency": 4, "duration": 3, "daily_impact": True, "medication_change": False},
        )
        self.assertEqual(result["condition_profile"]["key"], "undifferentiated-sweat")
        self.assertIn("sweat questionnaire responses", result["calculation_inputs"]["used"])
        self.assertNotIn("image inference", str(result).lower())

    def test_contract_keeps_likelihood_risk_and_severity_separate(self):
        risk = indicator(severity={"score": 48}, duration=8, recent_change=12, symptoms=["itching"])
        result = build_assessment_result({
            "area": "Skin", "input_type": "image", "quality": {"label": "Suitable for visual review"},
            "input_validation": {"status": "VALID_RELEVANT"}, "risk": {"score": 19, "level": "LOW"},
            "assessment_risk": risk, "severity": {"score": 48, "level": "MODERATE"},
            "clinical_decision_support": {"status": "VALID_ASSESSMENT", "next_step": "Track meaningful change."},
            "research_classifier": {"available": False}, "condition_intelligence": {"finding": {}, "reported_context_factors": [], "model_scope": {}},
            "segmentation": {}, "candidate_region": {}, "recommendations": {}, "care_plan": {},
        })
        self.assertFalse(result["disease_risk"]["available"])
        self.assertEqual(result["assessment_risk"]["score"], risk["score"])
        self.assertEqual(result["severity"]["score"], 48)


if __name__ == "__main__":
    unittest.main()
