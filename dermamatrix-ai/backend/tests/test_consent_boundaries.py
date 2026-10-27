"""Consent API regressions using synthetic images and transactional fake storage.

Run with PYTHONPATH=backend:backend/tests .venv/bin/python -m unittest
test_consent_boundaries -v. The real app startup is never imported; route
definitions are loaded by isolated_application without local settings/schema
initialization. These tests prove route control flow and simulated atomic
writes, not actual MySQL durability or real model classification.
"""

from __future__ import annotations

from contextlib import ExitStack
import hashlib
from io import BytesIO
import json
import unittest
from unittest.mock import patch

from flask import Request
from PIL import Image, ImageDraw
import pymysql
from werkzeug.datastructures import MultiDict

from isolated_application import load_isolated_application
import presentation_case_service


MISSING = object()
INVALID_JSON_CONSENT = (MISSING, False, None, "true", "false", 1, 0, [], [True], {}, {"accepted": True}, "yes")
USER = {"id": 7, "patient_id": "DMX-SYNTHETIC", "full_name": "Synthetic Test",
        "phone_number": "", "email_address": "synthetic@example.test", "created_at": "2026-10-22 00:00:00",
        "updated_at": "2026-10-22 00:00:00", "last_login_at": "2026-10-22 00:00:00"}


class TransactionalFake:
    """Minimal transaction ledger; never connects or models a SQL engine."""

    def __init__(self, fail_table=None):
        self.pending = []
        self.committed = []
        self.statements = []
        self.commits = self.rollbacks = self.closes = 0
        self.fail_table = fail_table
        self.existing_account = False

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        if self.fail_table == "commit":
            raise pymysql.OperationalError(1234, "Synthetic commit failure")
        self.committed.extend(self.pending)
        if any(row[0] == "auth_accounts" for row in self.pending):
            self.existing_account = True
        self.pending.clear()
        self.commits += 1

    def rollback(self):
        self.pending.clear()
        self.rollbacks += 1

    def close(self):
        self.closes += 1


class FakeCursor:
    lastrowid = USER["id"]

    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, sql, args=()):
        statement = " ".join(sql.split())
        self.statement = statement
        self.connection.statements.append((statement, args))
        words = statement.split()
        if words[0] in {"INSERT", "UPDATE"}:
            table = words[2] if words[0] == "INSERT" else words[1]
            if table == self.connection.fail_table:
                raise pymysql.OperationalError(1234, "Synthetic transaction failure")
            self.connection.pending.append((table, tuple(args)))

    def fetchone(self):
        if self.statement.startswith("SELECT COUNT"):
            return {"count": 0}
        return {"id": USER["id"]} if self.connection.existing_account else None


class ReadProbe(BytesIO):
    def __init__(self):
        super().__init__()
        self.read_calls = 0

    def read(self, *args):
        self.read_calls += 1
        return super().read(*args)


def synthetic_photo():
    image = Image.new("RGB", (620, 620), "#9e725f")
    draw = ImageDraw.Draw(image)
    for x in range(0, 620, 13):
        draw.line((x, 0, x, 619), fill="#43332e", width=3)
    output = BytesIO()
    image.save(output, "PNG")
    return output.getvalue()


class ConsentBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_isolated_application()
        cls.photo = synthetic_photo()

    def setUp(self):
        self.client = self.module.app.test_client()

    def sign_in(self):
        with self.client.session_transaction() as session:
            session.update(user_id=USER["id"], patient_id=USER["patient_id"])

    def persistence(self, connection):
        stack = ExitStack()
        stack.enter_context(patch.object(self.module, "database", return_value=connection))
        stack.enter_context(patch.object(self.module, "current_user", return_value=USER.copy()))
        stack.enter_context(patch.object(self.module, "account_history", return_value={"past_history": "Synthetic past", "current_history": "Synthetic current"}))
        stack.enter_context(patch.object(self.module, "authenticated_response", return_value={"user": USER.copy()}))
        return stack

    def test_rejected_image_consent_precedes_every_protected_operation(self):
        invalid = (MISSING, "", "false", "True", "TRUE", "1", "0", "null", "[]", "{}", " true", "true ", ["true", "false"], ["true", "true"])
        protected = ("_opened_image", "_image_quality_from_decoded", "presentation_case_for_image",
                     "run_screening_model", "classify_dermoscopic_lesion", "classify_clinical_skin_photo",
                     "classify_nail_photo", "build_image_evidence", "database")
        for signed_in in (False, True):
            for presentation in ("false", "true"):
                for value in invalid:
                    with self.subTest(signed_in=signed_in, presentation=presentation, consent=value):
                        self.client = self.module.app.test_client()
                        if signed_in:
                            self.sign_in()
                        streams = []
                        def file_stream(*_args, **_kwargs):
                            stream = ReadProbe(); streams.append(stream); return stream
                        fields = MultiDict([("image", (BytesIO(b"synthetic-invalid-image"), "synthetic.png")),
                                            ("presentation_case_enabled", presentation)])
                        if value is not MISSING:
                            for entry in value if isinstance(value, list) else [value]:
                                fields.add("image_consent", entry)
                        with ExitStack() as stack:
                            stack.enter_context(patch.object(Request, "_get_file_stream", side_effect=file_stream))
                            probes = [stack.enter_context(patch.object(self.module, name, side_effect=AssertionError(name))) for name in protected]
                            with self.assertNoLogs(self.module.app.logger, level="WARNING"):
                                response = self.client.post("/api/assessments", data=fields, content_type="multipart/form-data")
                            self.assertEqual(response.status_code, 400)
                            self.assertIn("consent", response.get_json()["error"])
                            self.assertTrue(streams, "Exercise a received multipart image")
                            self.assertTrue(all(stream.read_calls == 0 for stream in streams))
                            for probe in probes:
                                probe.assert_not_called()

    def test_valid_image_consent_keeps_real_decode_and_shared_guest_path(self):
        digest = hashlib.sha256(self.photo).hexdigest()
        synthetic_case = {"case_id": "synthetic-hair-teaching", "area": "Hair", "topic_id": "seborrheic-dermatitis",
                          "teaching_label": "Synthetic teaching fixture", "teaching_summary": "Test-only exact-file teaching metadata."}
        for presentation in (False, True):
            with self.subTest(presentation=presentation), ExitStack() as stack:
                stack.enter_context(patch.dict(presentation_case_service.PRESENTATION_CASES, {digest: synthetic_case}))
                database = stack.enter_context(patch.object(self.module, "database", side_effect=AssertionError("Guest must not persist")))
                decode = stack.enter_context(patch.object(self.module, "_opened_image", wraps=self.module._opened_image))
                quality = stack.enter_context(patch.object(self.module, "_image_quality_from_decoded", wraps=self.module._image_quality_from_decoded))
                matching = stack.enter_context(patch.object(self.module, "presentation_case_for_image", wraps=self.module.presentation_case_for_image))
                priority = stack.enter_context(patch.object(self.module, "run_screening_model", wraps=self.module.run_screening_model))
                response = self.client.post("/api/assessments", data={
                    "image": (BytesIO(self.photo), "synthetic.png"), "area": "Hair", "image_context": "scalp",
                    "image_consent": "true", "presentation_case_enabled": str(presentation).lower(),
                }, content_type="multipart/form-data")
                self.assertEqual(response.status_code, 200, response.get_json())
                result = response.get_json()
                self.assertEqual(result["persistence"], "not-persisted-guest")
                self.assertTrue(result["canonical_evidence"]["visible_findings"])
                self.assertEqual(result["assessment_result"]["content_quality"]["status"], "complete")
                if presentation:
                    self.assertTrue(result["presentation_case"]["matched"])
                    self.assertEqual(result["presentation_case"]["case_id"], synthetic_case["case_id"])
                else:
                    self.assertNotIn("presentation_case", result)
                for probe in (decode, quality, matching, priority):
                    probe.assert_called_once()
                database.assert_not_called()

    def registration_payload(self, consent=True):
        payload = {"full_name": USER["full_name"], "email_address": USER["email_address"],
                   "password": "synthetic-password", "confirm_password": "synthetic-password"}
        if consent is not MISSING:
            payload["account_consent"] = consent
        return payload

    def test_registration_requires_literal_json_true_before_storage(self):
        for value in INVALID_JSON_CONSENT:
            with self.subTest(consent=value), patch.object(self.module, "database") as database:
                response = self.client.post("/api/auth/register", json=self.registration_payload(value))
                self.assertEqual(response.status_code, 400)
                database.assert_not_called()

    def test_valid_registration_is_atomic_and_retry_does_not_duplicate_consent(self):
        connection = TransactionalFake()
        with self.persistence(connection):
            response = self.client.post("/api/auth/register", json=self.registration_payload())
            self.assertEqual(response.status_code, 201)
            self.assertEqual(connection.commits, 1)
            self.assertEqual([table for table, _ in connection.committed],
                             ["users", "auth_accounts", "medical_histories", "consent_records", "user_preferences"])
            consent = next(args for table, args in connection.committed if table == "consent_records")
            self.assertEqual(consent[0], USER["id"])
            self.assertEqual(consent[1], "local-auth-v1")
            self.assertTrue(consent[2]); self.assertTrue(consent[3])
            retry = self.client.post("/api/auth/register", json=self.registration_payload())
            self.assertEqual(retry.status_code, 409)
            self.assertEqual(connection.commits, 1)
            self.assertEqual(sum(table == "consent_records" for table, _ in connection.committed), 1)

    def test_registration_write_failures_rollback_and_leave_no_session(self):
        for table in ("users", "auth_accounts", "medical_histories", "consent_records", "user_preferences", "commit"):
            with self.subTest(failed_table=table):
                self.client = self.module.app.test_client()
                connection = TransactionalFake(fail_table=table)
                with self.persistence(connection):
                    response = self.client.post("/api/auth/register", json=self.registration_payload())
                self.assertEqual(response.status_code, 503)
                self.assertEqual(connection.commits, 0)
                self.assertEqual(connection.rollbacks, 1)
                self.assertEqual(connection.committed, [])
                self.assertEqual(connection.pending, [])
                self.assertEqual(connection.closes, 1)
                with self.client.session_transaction() as session:
                    self.assertNotIn("user_id", session)

    def profile_request(self, path, payload):
        return self.client.open(path, method="PATCH" if path == "/api/profile" else "POST", json=payload)

    def test_profile_routes_reject_malformed_consent_without_any_write(self):
        for path in ("/api/profile", "/api/profiles"):
            for value in INVALID_JSON_CONSENT:
                with self.subTest(path=path, consent=value):
                    connection = TransactionalFake()
                    payload = {"full_name": "Must not update", "past_history": "Synthetic past", "current_history": "Synthetic current"}
                    if value is not MISSING:
                        payload["health_data_consent"] = value
                    with self.persistence(connection):
                        response = self.profile_request(path, payload)
                    self.assertEqual(response.status_code, 400)
                    self.assertEqual(connection.statements, [])
                    self.assertEqual(connection.commits, 0)
                    self.assertEqual(connection.pending, [])
                    self.assertEqual(connection.committed, [])

    def test_valid_health_history_and_consent_share_the_session_owner_and_commit(self):
        for path in ("/api/profile", "/api/profiles"):
            with self.subTest(path=path):
                connection = TransactionalFake()
                payload = {"past_history": "Synthetic past", "current_history": "Synthetic current",
                           "health_data_consent": True, "user_id": 999, "patient_id": "DMX-OTHER"}
                with self.persistence(connection):
                    response = self.profile_request(path, payload)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(connection.commits, 1)
                self.assertEqual([table for table, _ in connection.committed], ["users", "medical_histories", "consent_records"])
                update, history, consent = [args for _, args in connection.committed]
                self.assertEqual(update[-1], USER["id"])
                self.assertEqual(history[0], USER["id"])
                self.assertEqual(consent[0], USER["id"])
                self.assertEqual(history[1:3], ("Synthetic past", "Synthetic current"))
                self.assertEqual(consent[1], "india-prototype-v1")
                self.assertEqual(history[-1], consent[-1])

    def test_health_history_write_failures_roll_back_both_profile_routes(self):
        for path in ("/api/profile", "/api/profiles"):
            for table in ("users", "medical_histories", "consent_records", "commit"):
                with self.subTest(path=path, failed_table=table):
                    connection = TransactionalFake(fail_table=table)
                    with self.persistence(connection):
                        response = self.profile_request(path, {"past_history": "Synthetic past", "current_history": "Synthetic current", "health_data_consent": True})
                    self.assertEqual(response.status_code, 503)
                    self.assertEqual(connection.rollbacks, 1)
                    self.assertEqual(connection.commits, 0)
                    self.assertEqual(connection.pending, [])
                    self.assertEqual(connection.committed, [])
                    self.assertEqual(connection.closes, 1)

    def test_nonhealth_profile_update_does_not_create_health_consent(self):
        connection = TransactionalFake()
        with self.persistence(connection):
            response = self.profile_request("/api/profile", {"full_name": "Synthetic Updated"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([table for table, _ in connection.committed], ["users"])

    def test_valid_authenticated_image_keeps_owner_scoped_result_persistence(self):
        self.sign_in()
        connection = TransactionalFake()
        with self.persistence(connection), patch.object(self.module, "versioned_progress_summary", return_value={"journey": None}):
            response = self.client.post("/api/assessments", data={
                "image": (BytesIO(self.photo), "synthetic.png"), "area": "Hair", "image_context": "scalp",
                "image_consent": "true", "patient_id": "DMX-OTHER",
            }, content_type="multipart/form-data")
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(response.get_json()["persistence"], "mysql")
        self.assertEqual([table for table, _ in connection.committed], ["assessments", "analysis_records", "consent_records"])
        self.assertEqual(connection.commits, 1)
        self.assertTrue(all(args[1] == USER["id"] for _, args in connection.committed[:2]))
        self.assertEqual(connection.committed[-1][1][0], USER["id"])
        summary = json.loads(connection.committed[1][1][3])
        self.assertEqual(summary["assessment_result"], response.get_json()["assessment_result"])

    def test_nonobject_json_is_rejected_without_writes(self):
        for path in ("/api/auth/register", "/api/profile", "/api/profiles"):
            for payload in ([], [True], "true", True, False, 1, 0, None):
                with self.subTest(path=path, payload=payload):
                    connection = TransactionalFake()
                    with self.persistence(connection):
                        method = "PATCH" if path == "/api/profile" else "POST"
                        # json=None means no JSON in Flask's client; include a
                        # literal null to exercise the malformed-body contract.
                        response = self.client.open(path, method=method, data=json.dumps(payload), content_type="application/json")
                    self.assertEqual(response.status_code, 400)
                    self.assertEqual(connection.statements, [])
                    self.assertEqual(connection.commits, 0)


if __name__ == "__main__":
    unittest.main()
