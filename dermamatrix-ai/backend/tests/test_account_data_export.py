"""Complete local account-copy contract using fake DB and actual Flask routes.

No application startup, local settings, real database, image or model is used.
Separate isolated-MySQL verification checks actual read-snapshot semantics.
"""

from __future__ import annotations

import copy
from datetime import date, datetime, timezone
from decimal import Decimal
import json
import re
import unittest
from unittest.mock import patch

import pymysql

from account_data_export import ACCOUNT_COLUMNS, FORMAT_VERSION, encode_account_data
from isolated_application import load_isolated_application


def account_rows():
    tables = {table: [] for table in ACCOUNT_COLUMNS}
    for owner in (7, 99):
        for table, columns in ACCOUNT_COLUMNS.items():
            count = {"medical_histories": 4, "consent_records": 57, "assessments": 53,
                     "analysis_records": 53, "care_routines": 52, "progress_checkins": 103,
                     "clinical_review_requests": 3, "reports": 2}.get(table, 1)
            for index in range(count):
                row = {column: None for column in columns}
                row["id"] = owner if table == "users" else owner * 1000 + index
                if "user_id" in row:
                    row["user_id"] = owner
                if "assessment_id" in row:
                    row["assessment_id"] = f"assessment-{owner}-{index}"
                if "created_at" in row:
                    row["created_at"] = datetime(2025, 9, 1, 12, 34, 56)
                if table == "users":
                    row.update(patient_id=f"DMX-{owner}", full_name=f"Synthetic {owner}",
                               phone_number="", email_address=f"synthetic-{owner}@example.test", is_active=True)
                if table == "auth_accounts":
                    # Even a changed fake driver returning unrequested columns
                    # must not expose the password hash or any future secret.
                    row.update(email_address=f"synthetic-{owner}@example.test", password_hash="must-never-export-secret-hash", reset_token="must-never-export-secret-token")
                if table == "analysis_records":
                    row["result_json"] = json.dumps({"assessment_result": {"contract_version": "historical-v0",
                        "consumer": {"cause_sections": [{"title": "Older complete details", "items": [f"owner-{owner}-detail-{index}"]}],
                                     "nutrition_sections": [{"items": ["preserve exact older content"]}]}}}, ensure_ascii=False)
                    row["image_stored"] = False
                if table == "medical_histories":
                    row.update(past_history=f"Older history {index}", current_history=f"Current history {index}")
                if table == "consent_records":
                    row.update(consent_version="historical-unknown-notice", purpose="Unchanged historical purpose", accepted_at=datetime(2025, 9, 1))
                if table == "care_routines":
                    row.update(routine_id=f"routine-{owner}-{index}", start_date=date(2025, 9, 1))
                if table == "progress_checkins":
                    row.update(checkin_id=f"checkin-{owner}-{index}", routine_id=f"routine-{owner}-0", checkin_date=date(2025, 9, 1))
                tables[table].append(row)
    return tables


class FakeReadConnection:
    def __init__(self, rows=None, fail_on=None):
        self.rows = rows if rows is not None else account_rows()
        self.fail_on = fail_on
        self.statements = []
        self.rollbacks = self.closes = self.commits = 0

    def cursor(self):
        return FakeReadCursor(self)

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closes += 1

    def commit(self):
        self.commits += 1
        raise AssertionError("Account data download must never commit business writes")


class FakeReadCursor:
    def __init__(self, connection):
        self.connection = connection
        self.result = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, sql, args=()):
        statement = " ".join(sql.split())
        self.connection.statements.append((statement, args))
        if self.connection.fail_on and self.connection.fail_on in statement:
            raise pymysql.OperationalError(1234, "Synthetic read failure")
        if not statement.startswith("SELECT "):
            if not statement.startswith(("SET TRANSACTION ", "START TRANSACTION ")):
                raise AssertionError("Unexpected write or non-read SQL")
            return
        table = re.search(r" FROM ([a-z_]+) ", statement).group(1)
        owner_column = "id" if table == "users" else "user_id"
        self.result = [copy.deepcopy(row) for row in self.connection.rows[table] if row[owner_column] == args[0]]
        if "is_active=TRUE" in statement:
            self.result = [row for row in self.result if row.get("is_active")]

    def fetchone(self):
        return self.result[0] if self.result else None

    def fetchall(self):
        return self.result


class AccountDataExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_isolated_application("_dermamatrix_export_test_app")

    def setUp(self):
        self.client = self.module.app.test_client()

    def sign_in(self, owner=7):
        with self.client.session_transaction() as session:
            session.update(user_id=owner, patient_id=f"DMX-{owner}")

    def test_guest_cannot_open_a_connection_or_choose_an_owner(self):
        with patch.object(self.module, "database") as database:
            response = self.client.get("/api/account-data/download?user_id=7&patient_id=DMX-7")
        self.assertEqual(response.status_code, 401)
        database.assert_not_called()

    def test_complete_owned_records_exceed_all_pdf_bounds_and_preserve_old_details(self):
        self.sign_in()
        connection = FakeReadConnection()
        before = copy.deepcopy(connection.rows)
        with patch.object(self.module, "database", return_value=connection):
            response = self.client.get("/api/account-data/download?user_id=99&patient_id=DMX-99")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["format_version"], FORMAT_VERSION)
        self.assertEqual(datetime.fromisoformat(payload["generated_at"]).utcoffset(), timezone.utc.utcoffset(None))
        self.assertEqual(set(payload["records"]), set(ACCOUNT_COLUMNS))
        self.assertEqual(payload["counts"]["analysis_records"], 53)
        self.assertEqual(payload["counts"]["assessments"], 53)
        self.assertEqual(payload["counts"]["care_routines"], 52)
        self.assertEqual(payload["counts"]["progress_checkins"], 103)
        self.assertEqual(payload["counts"]["medical_histories"], 4)
        self.assertEqual(payload["counts"]["consent_records"], 57)
        for table, rows in payload["records"].items():
            self.assertEqual(payload["counts"][table], len(rows))
            owner_key = "id" if table == "users" else "user_id"
            self.assertTrue(all(row[owner_key] == 7 for row in rows))
        result = payload["records"]["analysis_records"][-1]
        self.assertEqual(result["result_json"], before["analysis_records"][52]["result_json"])
        content = json.loads(result["result_json"])["assessment_result"]
        self.assertEqual(content["contract_version"], "historical-v0")
        self.assertEqual(content["consumer"]["cause_sections"][0]["items"], ["owner-7-detail-52"])
        self.assertEqual(result["json_field_status"]["result_json"], "valid_json_preserved")
        self.assertEqual(payload["records"]["medical_histories"][0]["past_history"], "Older history 0")
        self.assertEqual(payload["records"]["consent_records"][0]["consent_version"], "historical-unknown-notice")
        raw = response.data.decode("utf-8")
        for forbidden in ("password_hash", "reset_token", "must-never-export-secret", "owner-99-detail", "synthetic-99@example.test"):
            self.assertNotIn(forbidden, raw)
        self.assertEqual(connection.rows, before)
        self.assertEqual(connection.rollbacks, 1)
        self.assertEqual(connection.closes, 1)
        self.assertEqual(connection.commits, 0)
        self.assertTrue(connection.statements[0][0].startswith("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
        self.assertEqual(connection.statements[1][0], "START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY")
        for sql, args in connection.statements[2:]:
            self.assertEqual(args, (7,))
            self.assertNotIn("LIMIT", sql)
            self.assertNotIn("*", sql)
            self.assertNotIn("password_hash", sql)

    def test_attachment_is_private_same_origin_and_uncached(self):
        self.sign_in()
        with patch.object(self.module, "database", return_value=FakeReadConnection()):
            response = self.client.get("/api/account-data/download")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content_type.startswith("application/json"))
        self.assertIn("attachment;", response.headers["Content-Disposition"])
        self.assertIn("dermamatrix-local-account-data-", response.headers["Content-Disposition"])
        self.assertIn("private", response.headers["Cache-Control"])
        self.assertIn("no-store", response.headers["Cache-Control"])
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["Cross-Origin-Resource-Policy"], "same-origin")
        self.assertNotIn("Access-Control-Allow-Origin", response.headers)
        self.assertNotIn("ETag", response.headers)

    def test_malformed_and_null_stored_json_are_retained_without_invention(self):
        self.sign_in()
        connection = FakeReadConnection()
        malformed = '{"historical-detail": [not valid JSON — preserve exactly'
        connection.rows["analysis_records"][0]["result_json"] = malformed
        connection.rows["assessments"][0]["risk_inputs_json"] = "NaN"
        connection.rows["assessments"][0]["risk_factors_json"] = None
        with patch.object(self.module, "database", return_value=connection):
            response = self.client.get("/api/account-data/download")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        oldest = payload["records"]["analysis_records"][0]
        self.assertEqual(oldest["result_json"], malformed)
        self.assertEqual(oldest["json_field_status"]["result_json"], "malformed_preserved")
        assessment = payload["records"]["assessments"][0]
        self.assertEqual(assessment["risk_inputs_json"], "NaN")
        self.assertEqual(assessment["json_field_status"]["risk_inputs_json"], "malformed_preserved")
        self.assertIsNone(assessment["risk_factors_json"])
        self.assertEqual(assessment["json_field_status"]["risk_factors_json"], "null_preserved")

    def test_missing_optional_rows_are_empty_and_no_defaults_are_persisted(self):
        self.sign_in()
        connection = FakeReadConnection()
        for table in ACCOUNT_COLUMNS:
            if table != "users":
                connection.rows[table] = []
        with patch.object(self.module, "database", return_value=connection):
            response = self.client.get("/api/account-data/download")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["records"]["consent_records"], [])
        self.assertEqual(payload["records"]["user_preferences"], [])
        self.assertTrue(all(count == 0 for table, count in payload["counts"].items() if table != "users"))
        self.assertEqual(connection.commits, 0)

    def test_inactive_or_stale_session_is_rejected_and_snapshot_closed(self):
        self.sign_in(333)
        connection = FakeReadConnection()
        with patch.object(self.module, "database", return_value=connection):
            response = self.client.get("/api/account-data/download")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(len(connection.statements), 3)
        self.assertEqual(connection.rollbacks, 1)
        self.assertEqual(connection.closes, 1)

    def test_read_and_serialization_failures_never_return_partial_or_log_health_data(self):
        self.sign_in()
        for failure in ("START TRANSACTION", "FROM analysis_records", "serialization", "missing-column"):
            with self.subTest(failure=failure):
                connection = FakeReadConnection(fail_on=failure if failure.startswith(("START", "FROM")) else None)
                if failure == "serialization":
                    connection.rows["medical_histories"][0]["past_history"] = object()
                if failure == "missing-column":
                    del connection.rows["consent_records"][0]["consent_version"]
                with patch.object(self.module, "database", return_value=connection), self.assertNoLogs(self.module.app.logger, level="WARNING"):
                    response = self.client.get("/api/account-data/download")
                self.assertEqual(response.status_code, 503 if failure.startswith(("START", "FROM")) else 500)
                self.assertNotIn("records", response.get_json())
                self.assertNotIn("Older history", response.data.decode("utf-8"))
                self.assertEqual(connection.rollbacks, 1)
                self.assertEqual(connection.closes, 1)
                self.assertEqual(connection.commits, 0)

    def test_repeated_downloads_have_no_business_writes_or_changed_records(self):
        self.sign_in()
        connection = FakeReadConnection()
        before = copy.deepcopy(connection.rows)
        with patch.object(self.module, "database", return_value=connection):
            first = self.client.get("/api/account-data/download").get_json()
            second = self.client.get("/api/account-data/download").get_json()
        self.assertEqual(first["records"], second["records"])
        self.assertEqual(first["counts"], second["counts"])
        self.assertEqual(connection.rows, before)
        self.assertEqual(connection.rollbacks, 2)
        self.assertEqual(connection.closes, 2)
        self.assertEqual(connection.commits, 0)

    def test_scalar_encoding_is_explicit_and_lossless(self):
        payload = json.loads(encode_account_data({"date": date(2025, 9, 1), "moment": datetime(2025, 9, 1, tzinfo=timezone.utc),
                                                "decimal": Decimal("1.2300000000000000001"), "bytes": b"\x00\xff"}))
        self.assertEqual(payload["date"], "2025-09-01")
        self.assertEqual(payload["moment"], "2025-09-01T00:00:00+00:00")
        self.assertEqual(payload["decimal"], {"$type": "decimal", "value": "1.2300000000000000001"})
        self.assertEqual(payload["bytes"], {"$type": "bytes", "encoding": "base64", "value": "AP8="})


if __name__ == "__main__":
    unittest.main()
