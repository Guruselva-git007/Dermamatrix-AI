"""Isolated retry-lock cleanup tests: no app startup or database access."""

import unittest

from flask import Flask
import pymysql

from assessment_submission import guard_assessment_submission


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self.statement = ""

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, statement, _args=()):
        self.statement = statement
        self.connection.statements.append(statement)
        if "RELEASE_LOCK" in statement and self.connection.release_error is not None:
            raise self.connection.release_error

    def fetchone(self):
        return {"acquired": 1} if "GET_LOCK" in self.statement else None


class FakeConnection:
    def __init__(self, release_error=None):
        self.release_error = release_error
        self.statements = []
        self.close_calls = 0

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        pass

    def close(self):
        self.close_calls += 1


class SubmissionCleanupTests(unittest.TestCase):
    def setUp(self):
        self.connection = FakeConnection()
        self.view_error = None
        self.view_calls = 0
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True, SECRET_KEY="synthetic-cleanup-only")

        @self.app.post("/assessment")
        @guard_assessment_submission(
            database=lambda: self.connection,
            current_user=lambda _connection: {"id": 7},
            purpose="questionnaire_assessment",
        )
        def assessment():
            self.view_calls += 1
            if self.view_error is not None:
                raise self.view_error
            return {"status": "completed", "evidence": {"recorded": True}}

        self.client = self.app.test_client()
        with self.client.session_transaction() as session:
            session["user_id"] = 7

    def submit(self):
        return self.client.post(
            "/assessment",
            json={"questionnaire_consent": True, "body_location": "private-input-marker"},
            headers={"Idempotency-Key": "private-retry-key-12345"},
        )

    def test_successful_cleanup_releases_and_closes_once(self):
        response = self.submit()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["evidence"], {"recorded": True})
        self.assertEqual(self.view_calls, 1)
        self.assertTrue(any("RELEASE_LOCK" in statement for statement in self.connection.statements))
        self.assertEqual(self.connection.close_calls, 1)

    def test_release_mysql_failure_preserves_success_and_logs_no_private_details(self):
        self.connection.release_error = pymysql.OperationalError(2013, "private-error-marker")
        with self.assertLogs(self.app.logger, level="WARNING") as captured:
            response = self.submit()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "completed", "evidence": {"recorded": True}})
        self.assertEqual(self.view_calls, 1)
        self.assertEqual(self.connection.close_calls, 1)
        self.assertEqual(len(captured.records), 1)
        self.assertIn("lock cleanup could not be confirmed", captured.output[0])
        for private_value in ("private-error-marker", "private-input-marker", "private-retry-key-12345"):
            self.assertNotIn(private_value, captured.output[0])

    def test_release_mysql_failure_preserves_original_view_exception(self):
        original = RuntimeError("synthetic original processing error")
        self.view_error = original
        self.connection.release_error = pymysql.OperationalError(2013, "synthetic cleanup error")
        with self.assertLogs(self.app.logger, level="WARNING"):
            with self.assertRaises(RuntimeError) as raised:
                self.submit()
        self.assertIs(raised.exception, original)
        self.assertEqual(self.view_calls, 1)
        self.assertEqual(self.connection.close_calls, 1)

    def test_unexpected_cleanup_exception_still_closes_connection(self):
        self.connection.release_error = ValueError("synthetic programming error")
        with self.assertRaisesRegex(ValueError, "synthetic programming error"):
            self.submit()
        self.assertEqual(self.connection.close_calls, 1)


if __name__ == "__main__":
    unittest.main()
