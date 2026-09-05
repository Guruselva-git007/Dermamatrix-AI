"""Focused regression coverage for the assessment domain boundaries."""

from __future__ import annotations

import os
import sys
import unittest


BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

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
