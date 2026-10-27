"""Purpose/version evidence and safe prototype behavior using isolated routes."""

from contextlib import ExitStack
from io import BytesIO
import unittest
from unittest.mock import patch

from flask import Request
from werkzeug.datastructures import MultiDict

from isolated_application import load_isolated_application
from processing_notices import PROCESSING_NOTICES, consent_record_purpose
import test_consent_boundaries as consent_fixtures

MISSING = consent_fixtures.MISSING
TransactionalFake = consent_fixtures.TransactionalFake
USER = consent_fixtures.USER


class ProcessingNoticeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_isolated_application("_dermamatrix_notice_test_app")
        cls.photo = consent_fixtures.synthetic_photo()

    setUp = consent_fixtures.ConsentBoundaryTests.setUp
    persistence = consent_fixtures.ConsentBoundaryTests.persistence
    sign_in = consent_fixtures.ConsentBoundaryTests.sign_in
    registration_payload = consent_fixtures.ConsentBoundaryTests.registration_payload
    profile_request = consent_fixtures.ConsentBoundaryTests.profile_request

    def image_fields(self, version=MISSING):
        fields = MultiDict([("image", (BytesIO(self.photo), "synthetic.png")),
                            ("area", "Hair"), ("image_context", "scalp"),
                            ("image_consent", "true"), ("patient_id", "DMX-FORGED")])
        if version is not MISSING:
            for entry in version if isinstance(version, list) else [version]:
                fields.add("consent_notice_version", entry)
        return fields

    def send_assessment(self, purpose, version=MISSING):
        if purpose == "image_assessment":
            return self.client.post("/api/assessments", data=self.image_fields(version), content_type="multipart/form-data")
        payload = {"questionnaire_consent": True, "pattern": "usual", "patient_id": "DMX-FORGED"}
        if version is not MISSING:
            payload["consent_notice_version"] = version
        return self.client.post("/api/sweat-assessments", json=payload)

    def test_public_notices_are_server_owned_factual_and_available_without_signin(self):
        with patch.object(self.module, "database", side_effect=AssertionError("Public notices must not read accounts")):
            response = self.client.get("/api/processing-notices")
        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response.headers["Cache-Control"])
        payload = response.get_json()
        self.assertTrue(payload["operator_review_required"])
        self.assertFalse(payload["contact_available"])
        self.assertEqual(payload["notice_kind"], "factual_prototype_processing_information")
        self.assertEqual(set(payload["notices"]), set(PROCESSING_NOTICES))
        for purpose, notice in payload["notices"].items():
            self.assertEqual(notice["version"], PROCESSING_NOTICES[purpose]["version"])
            self.assertTrue(all(notice[key] for key in ("title", "summary", "retained", "guest_behavior", "limitations")))
            self.assertNotIn("legacy_version", notice)
            self.assertNotIn("record_purpose", notice)

    def test_registration_legacy_and_current_notice_evidence_and_retry(self):
        for version in (MISSING, PROCESSING_NOTICES["account"]["version"]):
            with self.subTest(version=version):
                connection = TransactionalFake()
                payload = self.registration_payload()
                if version is not MISSING:
                    payload.update(consent_notice_version=version, consent_purpose="forged", accepted_at="forged")
                with self.persistence(connection):
                    response = self.client.post("/api/auth/register", json=payload)
                    retry = self.client.post("/api/auth/register", json=payload)
                self.assertEqual(response.status_code, 201)
                self.assertEqual(retry.status_code, 409)
                evidence = [args for table, args in connection.committed if table == "consent_records"]
                self.assertEqual(len(evidence), 1)
                self.assertEqual(evidence[0][0], USER["id"])
                self.assertEqual(evidence[0][1], PROCESSING_NOTICES["account"]["legacy_version"] if version is MISSING else version)
                self.assertEqual(evidence[0][2], consent_record_purpose("account"))
                self.assertNotEqual(evidence[0][3], "forged")

    def test_profile_notice_version_is_checked_before_update_and_links_exact_history(self):
        for path in ("/api/profile", "/api/profiles"):
            for version in (MISSING, PROCESSING_NOTICES["health_history"]["version"]):
                with self.subTest(path=path, version=version):
                    connection = TransactionalFake()
                    payload = {"past_history": "Synthetic past", "current_history": "Synthetic current", "health_data_consent": True}
                    if version is not MISSING:
                        payload["consent_notice_version"] = version
                    with self.persistence(connection):
                        response = self.profile_request(path, payload)
                    self.assertEqual(response.status_code, 200)
                    history = next(args for table, args in connection.committed if table == "medical_histories")
                    evidence = next(args for table, args in connection.committed if table == "consent_records")
                    self.assertEqual(evidence[0], USER["id"])
                    self.assertEqual(evidence[1], PROCESSING_NOTICES["health_history"]["legacy_version"] if version is MISSING else version)
                    self.assertEqual(evidence[2], consent_record_purpose("health_history", history_id=USER["id"]))
                    self.assertEqual(evidence[3], history[3])
                    self.assertEqual(connection.commits, 1)

    def test_unsupported_json_notice_versions_never_authorize_database_writes(self):
        invalid = (None, False, True, 1, 0, [], {}, "", "stale-v0", "prototype-account-notice-v1 ", "legacy-image-acknowledgement-v1")
        for path, purpose in (("/api/auth/register", "account"), ("/api/profile", "health_history"), ("/api/profiles", "health_history")):
            for version in invalid:
                with self.subTest(path=path, version=version):
                    connection = TransactionalFake()
                    payload = self.registration_payload() if purpose == "account" else {"past_history": "Synthetic past", "current_history": "Synthetic current", "health_data_consent": True}
                    payload["consent_notice_version"] = version
                    with self.persistence(connection):
                        response = self.client.post(path, json=payload) if purpose == "account" else self.profile_request(path, payload)
                    self.assertEqual(response.status_code, 400)
                    self.assertEqual(response.get_json()["code"], "UNSUPPORTED_CONSENT_NOTICE_VERSION")
                    self.assertEqual(response.get_json()["consent_purpose"], purpose)
                    self.assertEqual(response.get_json()["current_notice_version"], PROCESSING_NOTICES[purpose]["version"])
                    self.assertEqual(connection.statements, [])
                    self.assertEqual(connection.commits, 0)

    def test_unsupported_image_notice_stops_before_content_read_and_processing(self):
        current = PROCESSING_NOTICES["image_assessment"]["version"]
        for value in ("", "null", "false", "stale-v0", "prototype-account-notice-v1", [current, current], [current, "stale-v0"]):
            for mode in ("true", "false"):
                with self.subTest(value=value, presentation=mode), ExitStack() as stack:
                    fields = self.image_fields(value); fields.add("presentation_case_enabled", mode)
                    probes = [stack.enter_context(patch.object(self.module, name, side_effect=AssertionError(name)))
                              for name in ("_opened_image", "_image_quality_from_decoded", "presentation_case_for_image", "run_screening_model", "database")]
                    streams = []
                    def file_stream(*_args, **_kwargs):
                        stream = consent_fixtures.ReadProbe(); streams.append(stream); return stream
                    stack.enter_context(patch.object(Request, "_get_file_stream", side_effect=file_stream))
                    response = self.client.post("/api/assessments", data=fields, content_type="multipart/form-data")
                    self.assertEqual(response.status_code, 400)
                    self.assertEqual(response.get_json()["code"], "UNSUPPORTED_CONSENT_NOTICE_VERSION")
                    self.assertTrue(streams)
                    self.assertTrue(all(stream.read_calls == 0 for stream in streams))
                    for probe in probes:
                        probe.assert_not_called()

    def test_questionnaire_unsupported_version_never_runs_engine_or_storage(self):
        for version in (None, True, 1, [], {}, "stale", PROCESSING_NOTICES["account"]["version"]):
            with self.subTest(version=version), patch.object(self.module, "sweat_questionnaire_result") as engine, patch.object(self.module, "database") as storage:
                response = self.send_assessment("questionnaire_assessment", version)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.get_json()["code"], "UNSUPPORTED_CONSENT_NOTICE_VERSION")
                engine.assert_not_called(); storage.assert_not_called()

    def test_assessment_evidence_is_atomic_owned_versioned_and_linked_on_each_submission(self):
        self.sign_in()
        for purpose in ("image_assessment", "questionnaire_assessment"):
            for version in (MISSING, PROCESSING_NOTICES[purpose]["version"]):
                with self.subTest(purpose=purpose, version=version):
                    connection = TransactionalFake()
                    with self.persistence(connection), patch.object(self.module, "versioned_progress_summary", return_value={"journey": None}):
                        for _ in range(2):
                            response = self.send_assessment(purpose, version)
                            self.assertEqual(response.status_code, 200, response.get_json())
                    self.assertEqual(connection.commits, 2)
                    evidence = [args for table, args in connection.committed if table == "consent_records"]
                    assessments = [args for table, args in connection.committed if table == "assessments"]
                    self.assertEqual(len(evidence), 2)
                    self.assertNotEqual(assessments[0][0], assessments[1][0])
                    for saved, consent in zip(assessments, evidence):
                        self.assertEqual(saved[1], USER["id"])
                        self.assertEqual(consent[0], USER["id"])
                        self.assertEqual(consent[1], PROCESSING_NOTICES[purpose]["legacy_version"] if version is MISSING else version)
                        self.assertEqual(consent[2], consent_record_purpose(purpose, assessment_id=saved[0]))
                        self.assertEqual(consent[3], saved[6])

    def test_assessment_storage_failure_leaves_no_orphan_consent_or_assessment(self):
        self.sign_in()
        for purpose in ("image_assessment", "questionnaire_assessment"):
            for table in ("assessments", "analysis_records", "consent_records", "commit"):
                with self.subTest(purpose=purpose, failed_table=table):
                    connection = TransactionalFake(fail_table=table)
                    with self.persistence(connection), patch.object(self.module, "versioned_progress_summary", return_value={"journey": None}):
                        response = self.send_assessment(purpose, PROCESSING_NOTICES[purpose]["version"])
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.get_json()["persistence"], "not-persisted-mysql-unavailable")
                    self.assertEqual(connection.commits, 0)
                    self.assertEqual(connection.rollbacks, 1)
                    self.assertEqual(connection.pending, [])
                    self.assertEqual(connection.committed, [])
                    self.assertEqual(connection.closes, 1)

    def test_current_notice_guests_still_do_not_persist(self):
        for purpose in ("image_assessment", "questionnaire_assessment"):
            with self.subTest(purpose=purpose), patch.object(self.module, "database", side_effect=AssertionError("No guest persistence")) as database:
                response = self.send_assessment(purpose, PROCESSING_NOTICES[purpose]["version"])
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.get_json()["persistence"], "not-persisted-guest")
                database.assert_not_called()

    def test_clinical_review_request_is_owner_checked_and_unassigned(self):
        connection = TransactionalFake()
        connection.existing_account = True
        with self.persistence(connection):
            response = self.client.post("/api/clinical-review-requests", json={"assessment_id": "synthetic-1", "user_id": 999})
        self.assertEqual(response.status_code, 201)
        payload = response.get_json()
        self.assertEqual(payload["status"], "awaiting_rmp_review")
        self.assertEqual(payload["review_state"], "request_recorded_unassigned")
        self.assertFalse(payload["clinician_assigned"])
        self.assertFalse(payload["clinician_reviewed"])
        self.assertEqual(connection.statements[0][1], ("synthetic-1", USER["id"]))
        self.assertEqual(connection.committed[0][0], "clinical_review_requests")
        self.assertEqual(connection.committed[0][1][0], USER["id"])
        self.assertIn("No clinician", payload["notice"])


if __name__ == "__main__":
    unittest.main()
