"""Focused regression coverage for the assessment domain boundaries."""

from __future__ import annotations

import os
import sys
import unittest
from io import BytesIO

from PIL import Image


BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from calibration_service import calibrated_probabilities, prediction_uncertainty
from clinical_intelligence_service import clinical_decision_support, normalise_symptoms, patient_context_snapshot, reported_symptom_severity
from longitudinal_service import build_progress_comparison
from dataset_registry import DATASET_REGISTRY
from ml_evaluation import multiclass_metrics, validate_grouped_splits, validate_patient_level_splits
from model_metadata import model_metadata
from pirs_service import calculate_pirs
from report_service import build_assessment_report_pdf, build_history_report_pdf
from risk_service import normalise_reported_priority
from sweat_service import sweat_questionnaire_result


class RiskAndPirsTests(unittest.TestCase):
    def test_priority_normalisation_has_stable_severity_boundaries(self):
        self.assertEqual(normalise_reported_priority(39)["severity"], "LOW")
        self.assertEqual(normalise_reported_priority(40)["severity"], "MODERATE")
        self.assertEqual(normalise_reported_priority(65)["severity"], "HIGH")
        self.assertEqual(normalise_reported_priority(12, urgent_selected=True)["severity"], "URGENT")

    def test_pirs_is_explicitly_non_validated_and_uses_normalised_input(self):
        priority = normalise_reported_priority(47)
        result = calculate_pirs(area="Skin", priority=priority, image_quality=86, reported_factors=["itching"])
        self.assertEqual(result["score"], 47)
        self.assertEqual(result["band"], "MODERATE")
        self.assertEqual(result["validation_status"], "not_clinically_validated")
        self.assertTrue(any(factor["name"] == "Reported factor" for factor in result["factors"]))

    def test_sweat_engine_is_transparent_rule_based_not_mock_ml(self):
        result = sweat_questionnaire_result({"pattern": "excessive", "frequency": 4, "duration": 3, "stress": 2, "heat": 1, "daily_impact": True})
        self.assertEqual(result["engine"]["status"], "rule_based_prototype")
        self.assertEqual(result["explainability"]["method"], "Questionnaire input-contribution summary")
        self.assertGreaterEqual(result["risk_score"], 18)


class MlContractTests(unittest.TestCase):
    def test_temperature_calibration_produces_probability_only_with_valid_artifact(self):
        calibration = {"available": True, "temperature": 2.0, "calibration_version": "qa-cal-v1"}
        likelihoods = calibrated_probabilities([2.0, 0.0], calibration)
        self.assertAlmostEqual(sum(likelihoods), 1.0)
        self.assertLess(likelihoods[0], 0.9)  # softer than the raw softmax at temperature 1
        self.assertIsNone(calibrated_probabilities([2.0, 0.0], {"available": False}))

    def test_probability_is_not_reported_concern_priority(self):
        likelihood = calibrated_probabilities([2.0, 0.0], {"available": True, "temperature": 2.0})[0]
        priority = normalise_reported_priority(65)
        self.assertNotEqual(round(likelihood * 100), priority["score"])
        self.assertEqual(priority["label"], "Reported-concern priority, not condition likelihood or disease risk.")

    def test_missing_calibration_or_ood_detector_yields_uncertain_contract(self):
        uncertainty = prediction_uncertainty(None)
        self.assertEqual(uncertainty["status"], "UNCERTAIN")
        self.assertEqual(uncertainty["ood_status"], "OOD_NOT_EVALUATED")
        self.assertEqual(uncertainty["certainty"], "NOT_AVAILABLE")

    def test_patient_split_leakage_is_detected(self):
        errors = validate_patient_level_splits([
            {"patient_id": "p1", "split": "train"},
            {"patient_id": "p1", "split": "test"},
        ])
        self.assertEqual(len(errors), 1)

    def test_case_group_splits_are_checked_without_claiming_patient_ids(self):
        errors = validate_grouped_splits([
            {"group_id": "scin-case-1", "split": "train"},
            {"group_id": "scin-case-1", "split": "test"},
        ], "group_id")
        self.assertEqual(len(errors), 1)
        self.assertIn("group_id scin-case-1", errors[0])

    def test_rejected_scin_experiment_cannot_appear_as_a_runtime_model(self):
        experiment = DATASET_REGISTRY["experiments"]["scin_clinical_resnet18_20260906"]
        metadata = model_metadata("scin-clinical-resnet18-experiment")
        self.assertEqual(experiment["decision"], "REJECTED_FOR_APPLICATION_INFERENCE")
        self.assertEqual(metadata["status"], "REJECTED_FOR_APPLICATION_INFERENCE")
        self.assertIn("not loaded", metadata["limitations"])

    def test_evaluation_metrics_include_calibration_and_per_class_values(self):
        metrics = multiclass_metrics([0, 1, 0, 1], [[.8, .2], [.1, .9], [.7, .3], [.2, .8]], ["a", "b"])
        self.assertIn("expected_calibration_error", metrics)
        self.assertIn("specificity", metrics["per_class"]["a"])

    def test_general_or_low_quality_image_has_no_fabricated_condition_likelihood(self):
        from app import app

        image = Image.new("RGB", (32, 32), color=(140, 140, 140))
        payload = BytesIO()
        image.save(payload, format="PNG")
        client = app.test_client()
        response = client.post("/api/assessments", data={
            "image": (BytesIO(payload.getvalue()), "qa.png"), "area": "Skin", "image_context": "general_photo",
            "image_consent": "true", "duration": "0", "discomfort": "0", "change": "0",
        }, content_type="multipart/form-data")
        result = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(result["input_validation"]["status"], "LOW_QUALITY")
        self.assertFalse(result["research_classifier"]["available"])
        self.assertFalse(result["research_classifier"]["condition_likelihood"]["available"])
        self.assertEqual(result["input_validation"]["normal_appearance"], "NOT_ASSESSED")
        self.assertIn("No medicine", result["recommendations"]["medicine_policy"])

    def test_sweat_path_is_questionnaire_only(self):
        from app import app

        response = app.test_client().post("/api/sweat-assessments", json={"questionnaire_consent": True, "pattern": "usual", "frequency": 0, "duration": 0})
        result = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(result["input_type"], "questionnaire")
        self.assertFalse(result["research_classifier"]["available"])
        self.assertEqual(result["model_pipeline"]["attention_map"], "not applicable")

    def test_context_uses_only_area_relevant_symptoms_and_not_history_as_model_features(self):
        symptoms = normalise_symptoms("Hair", ["hair_loss", "itching", "scalp_pain"])
        context = patient_context_snapshot(area="Hair", symptoms=symptoms, previous_treatment="gentle cleanser", history={"past_history": "reported", "current_history": "reported"})
        self.assertEqual(symptoms, ["hair_loss", "scalp_pain"])
        self.assertNotIn("past_history", context)
        self.assertIn("unimodal", context["image_model_context"])

    def test_cdss_defers_products_for_uncertain_input(self):
        severity = reported_symptom_severity(discomfort=0, change=0, symptoms=[], urgent_selected=False)
        context = patient_context_snapshot(area="Skin", symptoms=[], previous_treatment="")
        cdss = clinical_decision_support(
            area="Skin", risk=normalise_reported_priority(28), severity=severity,
            input_validation={"status": "LOW_QUALITY"}, classifier={"uncertainty": {"status": "UNCERTAIN"}}, context=context, urgent_selected=False,
        )
        self.assertEqual(cdss["status"], "UNCERTAIN")
        self.assertEqual(cdss["product_guidance"], "DEFER_PRODUCT_DECISIONS")

    def test_longitudinal_likelihood_requires_matching_model_and_calibration_lineage(self):
        old_summary = {
            "risk": {"score": 55, "version": "reported-concern-priority-v1.2"},
            "classification": {"model_id": "skin", "model_version": "v1", "pipeline_version": "p1", "calibration": {"calibration_version": "c1"}, "condition_likelihood": {"available": True, "estimated_likelihood": 0.6}},
        }
        current = {
            "assessment_id": "new", "created_at": "2026-09-06T10:00:00Z", "risk": {"score": 31, "version": "reported-concern-priority-v1.2"},
            "research_classifier": {"model_id": "skin", "model_version": "v2", "pipeline_version": "p1", "calibration": {"calibration_version": "c1"}, "condition_likelihood": {"available": True, "estimated_likelihood": 0.4}},
        }
        comparison = build_progress_comparison(user_id=7, area="Skin", current=current, historical=[{"assessment_id": "old", "created_at": "2026-09-01T10:00:00Z", "summary": old_summary}])
        self.assertEqual(comparison["comparison"]["risk_change"], -24)
        self.assertFalse(comparison["comparison"]["model_lineage_compatible"])
        self.assertIsNone(comparison["comparison"]["likelihood_change"])

    def test_assessment_summary_retains_model_and_calibration_lineage(self):
        from app import stored_analysis_summary

        summary = stored_analysis_summary({
            "created_at": "2026-09-06T10:00:00Z", "area": "Skin", "input_type": "image",
            "quality": {"score": 88}, "input_validation": {}, "risk": {}, "pirs": {},
            "screening": {}, "manual_context": {}, "candidate_region": {}, "segmentation": {},
            "recommendations": {}, "care_plan": {}, "explainability": {},
            "model_metadata": {"model_version": "model-v1", "dataset_version": "dataset-v1"},
            "model_pipeline": {"model_lineage": {"pipeline_version": "pipeline-v1"}},
            "research_classifier": {
                "available": True, "model_id": "skin-test", "model_version": "model-v1",
                "dataset_version": "dataset-v1", "pipeline_version": "pipeline-v1",
                "calibration": {"calibration_version": "calibration-v1"},
            },
        })
        saved = summary["classification"]
        self.assertEqual(saved["model_version"], "model-v1")
        self.assertEqual(saved["calibration"]["calibration_version"], "calibration-v1")
        self.assertEqual(summary["model_pipeline"]["model_lineage"]["pipeline_version"], "pipeline-v1")


class ReportTests(unittest.TestCase):
    def test_report_is_a_real_pdf_document(self):
        pdf = build_assessment_report_pdf(
            account={"full_name": "Test Account"},
            assessment={
                "assessment_id": "dmx-test-001",
                "area": "Skin",
                "created_at": "2026-09-06T10:00:00Z",
                "summary": {
                    "input_type": "image",
                    "quality": {"label": "Suitable for visual review"},
                    "risk": {"score": 32, "level": "TRACK AND REVISIT"},
                    "pirs": {"score": 32, "band": "LOW"},
                    "screening": {"title": "A lower-priority screening snapshot", "summary": "Track changes and seek professional advice if needed."},
                    "classification": {"available": False},
                    "segmentation": {"status": "not_run"},
                    "recommendations": {"routine": {"morning": ["Keep care gentle."], "evening": ["Stop products that irritate."]}, "diet": ["Eat regular meals."]},
                    "care_plan": {"next_step": "Track the concern and discuss it with a clinician if it changes."},
                },
            },
        )
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 1000)

    def test_history_export_is_a_real_pdf_without_images(self):
        pdf = build_history_report_pdf(
            account={"full_name": "Test Account", "patient_id": "DMX-TEST", "email_address": "test@example.test", "past_history": "None recorded", "current_history": "Tracking a concern"},
            analyses=[{"created_at": "2026-09-06T10:00:00Z", "area": "Skin", "summary": {"risk": {"score": 32, "level": "LOW"}, "classification": {"available": False}}}],
            routines=[{"condition_label": "Clinician-recorded concern", "routine_name": "Gentle routine", "start_date": "2026-09-01", "checkin_count": 1}],
            checkins=[{"checkin_date": "2026-09-06", "condition_label": "Clinician-recorded concern", "reported_trend": "improving", "priority_score": 18}],
        )
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 1000)


if __name__ == "__main__":
    unittest.main()
