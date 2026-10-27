"""Truthful bounded PDF scope using synthetic data and the real PDF renderer."""

from __future__ import annotations

import copy
import unittest
from unittest.mock import patch

from reportlab.platypus import Paragraph, SimpleDocTemplate, Table

from report_service import build_assessment_report_pdf, build_history_report_pdf


class HistoryPdfScopeTests(unittest.TestCase):
    def test_pdf_discloses_limits_and_preserves_the_bounded_recent_summary(self):
        account = {"full_name": "Synthetic account", "patient_id": "DMX-SYNTHETIC",
                   "email_address": "synthetic@example.test",
                   "past_history": "Past synthetic history", "current_history": "Current synthetic history"}
        analyses = [{"created_at": "2026-10-22", "area": "Skin",
                     "summary": {"assessment_result": {"consumer": {"primary_result": {
                         "title": f"Synthetic assessment {index}"}}}}} for index in range(51)]
        routines = [{"condition_label": "Synthetic context", "routine_name": f"Synthetic routine {index}",
                     "start_date": "2026-10-22", "checkin_count": index} for index in range(51)]
        checkins = [{"checkin_date": "2026-10-22", "condition_label": f"Synthetic checkin {index}",
                     "reported_trend": "unchanged", "priority_score": 30} for index in range(101)]
        before = copy.deepcopy((account, analyses, routines, checkins))
        captured = {}
        original_build = SimpleDocTemplate.build

        def capture_and_build(document, story, *args, **kwargs):
            captured["paragraphs"] = [item.getPlainText() for item in story if isinstance(item, Paragraph)]
            captured["tables"] = [copy.deepcopy(item._cellvalues) for item in story if isinstance(item, Table)]
            return original_build(document, story, *args, **kwargs)

        with patch.object(SimpleDocTemplate, "build", new=capture_and_build):
            pdf = build_history_report_pdf(account=account, analyses=analyses,
                                           routines=routines, checkins=checkins)

        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 1000)
        copy_text = " ".join(captured["paragraphs"])
        self.assertIn("50 saved assessments, 50 routines, and 100 check-ins", copy_text)
        self.assertIn("not a complete account-data export", copy_text)
        self.assertIn("Derived assessment and reported health information", copy_text)
        self.assertIn("does not mean that a clinician has been assigned", copy_text)
        profile, assessments, routine_table, checkin_table = captured["tables"]
        self.assertEqual(len(profile), 5)
        self.assertEqual(len(assessments), 51)  # header + 50, from 51 supplied
        self.assertEqual(len(routine_table), 51)
        self.assertEqual(len(checkin_table), 101)  # header + 100, from 101 supplied
        self.assertEqual(assessments[-1][2].getPlainText(), "Synthetic assessment 49")
        self.assertEqual(routine_table[-1][1].getPlainText(), "Synthetic routine 49")
        self.assertEqual(checkin_table[-1][1].getPlainText(), "Synthetic checkin 99")
        self.assertEqual((account, analyses, routines, checkins), before)

    def test_empty_account_history_remains_a_valid_pdf(self):
        pdf = build_history_report_pdf(account={}, analyses=[], routines=[], checkins=[])
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 1000)

    def test_assessment_brief_does_not_imply_completed_clinician_review(self):
        paragraphs = []
        original_build = SimpleDocTemplate.build

        def capture_and_build(document, story, *args, **kwargs):
            paragraphs.extend(item.getPlainText() for item in story if isinstance(item, Paragraph))
            return original_build(document, story, *args, **kwargs)

        with patch.object(SimpleDocTemplate, "build", new=capture_and_build):
            pdf = build_assessment_report_pdf(account={"full_name": "Synthetic account"},
                                               assessment={"area": "Skin", "summary": {}})
        self.assertTrue(pdf.startswith(b"%PDF"))
        text = " ".join(paragraphs)
        self.assertIn("does not mean that a clinician has been assigned", text)
        self.assertIn("do not establish regulatory classification or clinical readiness", text)
        self.assertIn("Possible conditions and associated symptoms", text)
        self.assertIn("Causes, triggers and care", text)


if __name__ == "__main__":
    unittest.main()
