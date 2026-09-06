"""Focused regression coverage for the assessment domain boundaries."""

from __future__ import annotations

import os
import sys
import unittest
from io import BytesIO
from unittest.mock import Mock

from PIL import Image, ImageDraw


BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from calibration_service import calibrated_probabilities, prediction_uncertainty
from assessment_router import route_image_assessment
from clinical_intelligence_service import clinical_decision_support, normalise_symptoms, patient_context_snapshot, reported_symptom_severity
from condition_knowledge import KNOWLEDGE_VERSION, build_assessment_intelligence, model_capability_matrix
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
    def test_account_data_requires_the_matching_signed_session(self):
        from app import app, user_for_patient

        connection = Mock()
        with app.test_request_context("/"):
            self.assertIsNone(user_for_patient(connection, "DMX-OTHER"))
        connection.cursor.assert_not_called()

        with app.test_request_context("/"):
            from flask import session

            session["user_id"] = 7
            session["patient_id"] = "DMX-OWNER"
            self.assertIsNone(user_for_patient(connection, "DMX-OTHER"))
        connection.cursor.assert_not_called()

    def test_local_css_is_not_cached_after_a_live_update(self):
        from app import app

        response = app.test_client().get("/experience.css")
        try:
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers.get("Cache-Control"), "no-store, max-age=0")
        finally:
            response.close()

    def test_oversized_upload_is_rejected_before_analysis(self):
        from app import MAX_FILE_BYTES, app

        response = app.test_client().post(
            "/api/assessments",
            data={"image": (BytesIO(b"x" * (MAX_FILE_BYTES + 1)), "too-large.png")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.get_json()["error"], "The image is larger than 10 MB.")

    def test_health_area_router_never_routes_general_images_to_lesion_classifier(self):
        clear_image = {"status": "GOOD", "usable_for_research_model": True}
        skin = route_image_assessment(area="Skin", image_context="face_skin", dermoscopy_attested=False, image_features=clear_image)
        hair = route_image_assessment(area="Hair", image_context="scalp", dermoscopy_attested=False, image_features=clear_image)
        nail = route_image_assessment(area="Nails", image_context="toenail", dermoscopy_attested=False, image_features=clear_image)
        self.assertTrue(skin["accepted"])
        self.assertFalse(skin["run_research_classifier"])
        self.assertFalse(hair["run_research_classifier"])
        self.assertFalse(nail["run_research_classifier"])
        self.assertEqual(skin["relevance_status"], "USER_DECLARED_CONTEXT_NOT_AUTOMATICALLY_VERIFIED")

    def test_only_attested_dermoscopic_skin_route_can_enter_research_classifier(self):
        route = route_image_assessment(
            area="Skin", image_context="dermoscopic_lesion", dermoscopy_attested=True,
            image_features={"status": "GOOD", "usable_for_research_model": True},
        )
        self.assertTrue(route["accepted"])
        self.assertTrue(route["run_research_classifier"])
        self.assertEqual(route["classification_status"], "ELIGIBLE_FOR_SCOPED_RESEARCH_CLASSIFIER")

    def test_router_rejects_an_image_context_from_the_wrong_area(self):
        route = route_image_assessment(
            area="Nails", image_context="face_skin", dermoscopy_attested=False,
            image_features={"status": "GOOD", "usable_for_research_model": True},
        )
        self.assertFalse(route["accepted"])
        self.assertEqual(route["status"], "UNSUPPORTED")

    def test_temperature_calibration_produces_probability_only_with_valid_artifact(self):
        calibration = {"available": True, "temperature": 2.0, "calibration_version": "qa-cal-v1"}
        likelihoods = calibrated_probabilities([2.0, 0.0], calibration)
        self.assertAlmostEqual(sum(likelihoods), 1.0)
        self.assertLess(likelihoods[0], 0.9)  # softer than the raw softmax at temperature 1
        self.assertIsNone(calibrated_probabilities([2.0, 0.0], {"available": False}))

    def test_condition_intelligence_keeps_research_ranking_separate_from_likelihood_and_priority(self):
        priority = normalise_reported_priority(45)
        severity = reported_symptom_severity(discomfort=6, change=8, symptoms=["itching"], urgent_selected=False)
        context = patient_context_snapshot(area="Skin", symptoms=["itching"], previous_treatment="gentle cleanser")
        cdss = clinical_decision_support(
            area="Skin", risk=priority, severity=severity, input_validation={"status": "VALID"},
            classifier={"uncertainty": {"status": "NOT_APPLICABLE_NO_CLASSIFIER"}}, context=context, urgent_selected=False,
        )
        intelligence = build_assessment_intelligence(
            area="Skin",
            classifier={
                "available": True,
                "top_predictions": [{"code": "mel", "label": "Melanoma", "relative_score": 0.73}],
                "top_prediction": {"relative_score": 0.73},
                "condition_likelihood": {"available": False, "notice": "Calibration is not configured."},
                "uncertainty": {"status": "UNCERTAIN"},
            },
            priority=priority,
            severity=severity,
            input_validation={"status": "VALID"},
            context=context,
            cdss=cdss,
            recommendations={"products": [], "product_guidance": "DEFER_PRODUCT_DECISIONS"},
        )
        self.assertEqual(intelligence["knowledge_version"], KNOWLEDGE_VERSION)
        self.assertEqual(intelligence["finding"]["status"], "MODEL_SUPPORTED_RESEARCH_RANKING_ONLY")
        self.assertIsNone(intelligence["finding"]["estimated_likelihood"])
        self.assertEqual(intelligence["reported_concern_priority"]["score"], 45)
        self.assertEqual(intelligence["doctor"]["specialty"], "Dermatologist")
        self.assertTrue(any("Melanoma" in reference["title"] for reference in intelligence["knowledge"]["references"]))

    def test_unconfigured_modalities_do_not_receive_ontology_conditions_or_simulated_models(self):
        priority = normalise_reported_priority(28)
        severity = reported_symptom_severity(discomfort=0, change=0, symptoms=[], urgent_selected=False)
        context = patient_context_snapshot(area="Hair", symptoms=[], previous_treatment="")
        cdss = clinical_decision_support(
            area="Hair", risk=priority, severity=severity, input_validation={"status": "VALID"},
            classifier={"uncertainty": {"status": "NOT_APPLICABLE_NO_CLASSIFIER"}}, context=context, urgent_selected=False,
        )
        intelligence = build_assessment_intelligence(
            area="Hair", classifier={"available": False, "uncertainty": {"status": "NOT_APPLICABLE_NO_CLASSIFIER"}},
            priority=priority, severity=severity, input_validation={"status": "VALID"}, context=context, cdss=cdss,
            recommendations={"products": [], "product_guidance": "GENERAL_SELF_CARE_ONLY"},
        )
        matrix = {item["health_area"]: item for item in model_capability_matrix()}
        self.assertEqual(intelligence["finding"]["status"], "NO_MODEL_SUPPORTED_FINDING")
        self.assertFalse(intelligence["knowledge"]["condition_available"])
        self.assertEqual(matrix["Hair"]["model_supported_conditions"], [])
        self.assertEqual(matrix["Sweat"]["xai"], "Questionnaire contribution summary; not SHAP")

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
        self.assertEqual(result["condition_intelligence"]["finding"]["status"], "NO_MODEL_SUPPORTED_FINDING")

    def test_clear_declared_hair_photo_returns_quality_context_not_a_disease_label(self):
        from app import app

        image = Image.new("RGB", (640, 640), color=(222, 232, 246))
        draw = ImageDraw.Draw(image)
        for coordinate in range(0, 640, 16):
            draw.line((coordinate, 0, coordinate, 639), fill=(56, 100, 170), width=3)
            draw.line((0, coordinate, 639, coordinate), fill=(56, 100, 170), width=3)
        payload = BytesIO()
        image.save(payload, format="PNG")

        response = app.test_client().post("/api/assessments", data={
            "image": (BytesIO(payload.getvalue()), "clear-hair-context.png"),
            "area": "Hair",
            "image_context": "scalp",
            "image_consent": "true",
            "duration": "0",
            "discomfort": "0",
            "change": "0",
        }, content_type="multipart/form-data")
        result = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertIn(result["input_validation"]["status"], {"VALID", "ACCEPTABLE"})
        self.assertEqual(result["input_validation"]["relevance_status"], "USER_DECLARED_CONTEXT_NOT_AUTOMATICALLY_VERIFIED")
        self.assertEqual(result["input_validation"]["classification_status"], "NO_COMPATIBLE_CLASSIFIER_CONFIGURED")
        self.assertFalse(result["research_classifier"]["available"])
        self.assertFalse(result["research_classifier"]["condition_likelihood"]["available"])
        self.assertEqual(result["model_pipeline"]["classification"], "Hair/scalp disorder classifier not configured")

    def test_sweat_path_is_questionnaire_only(self):
        from app import app

        response = app.test_client().post("/api/sweat-assessments", json={"questionnaire_consent": True, "pattern": "usual", "frequency": 0, "duration": 0})
        result = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(result["input_type"], "questionnaire")
        self.assertFalse(result["research_classifier"]["available"])
        self.assertEqual(result["model_pipeline"]["attention_map"], "not applicable")
        self.assertEqual(result["condition_intelligence"]["finding"]["status"], "NO_MODEL_SUPPORTED_FINDING")

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
            "condition_intelligence": {"knowledge_version": "knowledge-v1", "finding": {"status": "NO_MODEL_SUPPORTED_FINDING"}},
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
        self.assertEqual(summary["condition_intelligence"]["knowledge_version"], "knowledge-v1")


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
