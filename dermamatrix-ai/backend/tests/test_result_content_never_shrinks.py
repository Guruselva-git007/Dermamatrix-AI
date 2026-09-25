"""The consumer contract stays deep while evidence certainty and topic change."""

from __future__ import annotations

import unittest

from assessment_contract import ASSESSMENT_RESULT_VERSION, build_assessment_result
from recommendation_service import build_recommendations
from result_quality import validate_result_content


MAJOR_FIELDS = frozenset({
    "primary_result", "image_quality", "pirs", "concern", "severity", "why_this_result",
    "visible_findings", "possible_conditions", "differential_status", "condition_information",
    "common_symptoms", "possible_causes", "cause_sections", "care_sections",
    "treatment_sections", "medication_information", "routine_sections", "nutrition_sections",
    "lifestyle_sections", "products", "professional_support", "monitoring", "technical_details",
})


def fixture(area: str, *, label: str | None = None, certainty: str = "MODERATE",
            ood: str = "OOD_NOT_EVALUATED", normal: bool = False,
            reference_topic: str | None = None, symptoms: list[str] | None = None) -> dict:
    classifier = {"available": bool(label or normal), "uncertainty": {"certainty": certainty, "status": "LOW_CONFIDENCE" if certainty == "LOW" else "RAW_MODEL_RANKING", "ood_status": ood, "margin": 0.21}}
    if label:
        classifier.update({"top_prediction": {"condition": label, "relative_score": 0.53},
                           "top_predictions": [{"label": label, "relative_score": 0.53},
                                               {"label": "Other research class", "relative_score": 0.27}]})
    if normal:
        classifier["normal_appearance"] = {"available": True, "status": "VALIDATED_NORMAL_APPEARANCE", "validated": True,
                                            "is_normal": True, "condition_signal": "NONE", "confidence": 0.91, "minimum_confidence": 0.8}
    evidence = {"image_quality": {"status": "GOOD", "label": "Suitable"},
                "reported_context": {"symptoms": symptoms or []},
                "image_findings": {"available": True, "summary": "Local frame variation recorded.", "observations": [
                    {"finding": "Tone variation", "visible_evidence": "Measured in the central crop; no cause inferred."}]},
                "severity": {"level": "MILD"}, "assessment_risk": {"available": True, "score": 16, "level": "LOW", "urgency_label": "Routine monitoring"},
                "candidate_region": {}, "segmentation": {}}
    reference = {"matched": True, "topic_id": reference_topic, "case_id": "fixture-reference"} if reference_topic else {}
    state = "HEALTHY" if normal else "CONDITION" if label else "UNCERTAIN"
    return {"area": area, "input_type": "image", "quality": evidence["image_quality"],
            "input_validation": {"status": "VALID_RELEVANT"}, "research_classifier": classifier,
            "condition_intelligence": {"finding": {"name": label} if label else {}, "doctor": {"specialty": "Dermatologist", "appointment": "Review persistent or changing concerns."}},
            "canonical_evidence": evidence, "image_findings": evidence["image_findings"],
            "pirs": {"score": 12, "band": "LOW"}, "assessment_risk": evidence["assessment_risk"],
            "severity": evidence["severity"], "risk": {}, "clinical_decision_support": {},
            "presentation_case": reference,
            "recommendations": build_recommendations(area, classifier, assessment_state=state,
                                                     canonical_evidence=evidence, presentation_case=reference)}


class ResultContentNeverShrinks(unittest.TestCase):
    def test_result_content_never_shrinks(self):
        cases = [
            ("Skin", {"normal": True}, "normal"), ("Skin", {"label": "Eczema / dermatitis"}, "known"),
            ("Skin", {"label": "Eczema / dermatitis", "certainty": "LOW"}, "low"),
            ("Skin", {"label": "Eczema / dermatitis", "ood": "OUT_OF_DISTRIBUTION"}, "ood"),
            ("Hair", {"normal": True}, "normal"), ("Hair", {"symptoms": ["scalp_scaling"]}, "reported"),
            ("Hair", {"reference_topic": "alopecia-areata"}, "low"),
            ("Hair", {"symptoms": ["hair_loss"], "ood": "OUT_OF_DISTRIBUTION"}, "ood"),
            ("Nails", {"normal": True}, "normal"), ("Nails", {"label": "Pitting"}, "known"),
            ("Nails", {"label": "Pitting", "certainty": "LOW"}, "low"),
            ("Nails", {"label": "Pitting", "ood": "OUT_OF_DISTRIBUTION"}, "ood"),
        ]
        for area, options, name in cases:
            with self.subTest(area=area, case=name):
                result = build_assessment_result(fixture(area, **options))
                consumer = result["consumer"]
                self.assertEqual(result["contract_version"], ASSESSMENT_RESULT_VERSION)
                self.assertTrue(MAJOR_FIELDS <= consumer.keys())
                self.assertEqual(result["content_quality"]["status"], "complete")
                self.assertTrue(consumer["products"])
                self.assertTrue(all(product["domain"] == area for product in consumer["products"]))
                self.assertTrue(consumer["treatment_sections"])
                self.assertTrue(consumer["routine_sections"])
                self.assertTrue(consumer["nutrition_sections"])
                self.assertTrue(consumer["monitoring"]["what_to_track"])
                if name in {"low", "ood"}:
                    self.assertNotEqual(consumer["primary_result"]["evidence_strength"], "High")
                if name == "normal":
                    self.assertFalse(consumer["medication_information"]["common_options"])

    def test_topic_changes_content_without_changing_structure(self):
        topic_cases = {
            "Skin": [{"label": label} for label in ("Eczema / dermatitis", "Folliculitis / acne-like", "Psoriasis / papulosquamous")],
            "Hair": [{"reference_topic": topic} for topic in ("seborrheic-dermatitis", "pattern-hair-loss", "alopecia-areata")],
            "Nails": [{"reference_topic": topic} for topic in ("onychomycosis", "nail-psoriasis", "blue-nails")],
        }
        for area, scenarios in topic_cases.items():
            results = [build_assessment_result(fixture(area, **scenario))["consumer"] for scenario in scenarios]
            self.assertEqual(len({result["condition_information"]["id"] for result in results}), 3)
            self.assertEqual(len({tuple(result["common_symptoms"]) for result in results}), 3)
            self.assertEqual(len({tuple(result["possible_causes"]) for result in results}), 3)
            self.assertEqual(len({tuple(product["id"] for product in result["products"]) for result in results}), 3)
            self.assertTrue(all(MAJOR_FIELDS <= result.keys() for result in results))

    def test_presentation_and_partial_failure_keep_the_contract(self):
        base = fixture("Hair", symptoms=["scalp_scaling"])
        reference = fixture("Hair", reference_topic="seborrheic-dermatitis", symptoms=["scalp_scaling"])
        for response in (base, reference):
            response["canonical_evidence"]["component_status"] = {"classifier": "failed"}
            result = build_assessment_result(response)
            self.assertEqual(result["content_quality"]["status"], "complete")
            self.assertEqual(MAJOR_FIELDS & result["consumer"].keys(), MAJOR_FIELDS)
        self.assertEqual(base["pirs"], reference["pirs"])

    def test_low_quality_photo_keeps_care_and_states_why_match_strength_is_unavailable(self):
        response = fixture("Skin", reference_topic="acne")
        response["quality"] = {"status": "LOW_QUALITY", "label": "Retake recommended", "issues": ["Image is too small"]}
        response["canonical_evidence"]["image_quality"] = response["quality"]
        response["input_validation"]["status"] = "LOW_QUALITY"
        result = build_assessment_result(response)
        self.assertEqual(result["result_state"], "poor_quality")
        self.assertEqual(result["content_quality"]["status"], "complete")
        self.assertIsNone(result["consumer"]["primary_result"]["confidence"])
        self.assertTrue(result["consumer"]["treatment_sections"])
        self.assertTrue(result["consumer"]["products"])

    def test_validator_detects_semantic_collapse(self):
        result = build_assessment_result(fixture("Hair", symptoms=["scalp_scaling"]))
        result["consumer"]["routine_sections"] = []
        result["consumer"]["products"] = []
        quality = validate_result_content(result)
        self.assertEqual(quality["status"], "incomplete")
        self.assertIn("routine", quality["missing"])
        self.assertIn("products", quality["missing"])

    def test_history_summary_keeps_the_same_consumer_contract(self):
        from app import stored_analysis_summary

        response = fixture("Nails", label="Onychogryphosis")
        response.update({"assessment_id": "fixture-1", "created_at": "2026-09-25T00:00:00Z",
                         "screening": {}, "manual_context": {}, "patient_context": {},
                         "quality": {"status": "GOOD"}, "risk": {}, "model_pipeline": {},
                         "model_metadata": {}, "clinical_decision_support": {},
                         "assessment_result": build_assessment_result(response)})
        saved = stored_analysis_summary(response)
        self.assertEqual(saved["assessment_result"]["consumer"], response["assessment_result"]["consumer"])
        self.assertEqual(saved["assessment_result"]["content_quality"]["status"], "complete")
        self.assertEqual(saved["assessment_result"]["consumer"]["condition_information"]["id"], "onychogryphosis")


if __name__ == "__main__":
    unittest.main()
