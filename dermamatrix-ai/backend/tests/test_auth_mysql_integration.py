"""Opt-in, real-MySQL checks for registered-account ownership and sessions.

Run with DERMAMATRIX_RUN_MYSQL_INTEGRATION_TESTS=1 after the local MySQL stack
is running. The test creates uniquely named records and removes only those
records in tearDown.
"""

from __future__ import annotations

import os
import sys
import unittest
import uuid

from werkzeug.security import check_password_hash


BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import app, database  # noqa: E402


@unittest.skipUnless(
    os.getenv("DERMAMATRIX_RUN_MYSQL_INTEGRATION_TESTS") == "1",
    "Set DERMAMATRIX_RUN_MYSQL_INTEGRATION_TESTS=1 to run against local MySQL.",
)
class AccountMySQLIntegrationTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client_a = app.test_client()
        self.client_b = app.test_client()
        self.user_ids: list[int] = []
        self.tag = uuid.uuid4().hex[:12]
        self.password = "demonstration-password-123"

    def tearDown(self):
        if not self.user_ids:
            return
        placeholders = ", ".join(["%s"] * len(self.user_ids))
        connection = database()
        try:
            with connection.cursor() as cursor:
                # Child rows must be removed first. These IDs originate only
                # from this test's unique registration responses.
                for table in (
                    "reports",
                    "clinical_review_requests",
                    "progress_checkins",
                    "care_routines",
                    "analysis_records",
                    "assessments",
                    "medical_histories",
                    "consent_records",
                    "user_preferences",
                    "auth_accounts",
                ):
                    cursor.execute(f"DELETE FROM {table} WHERE user_id IN ({placeholders})", self.user_ids)
                cursor.execute(f"DELETE FROM users WHERE id IN ({placeholders})", self.user_ids)
            connection.commit()
        finally:
            connection.close()

    def register(self, client, name: str, email: str) -> dict:
        response = client.post(
            "/api/auth/register",
            json={
                "full_name": name,
                "email_address": email,
                "password": self.password,
                "confirm_password": self.password,
                "account_consent": True,
            },
        )
        self.assertEqual(response.status_code, 201, response.get_json())
        payload = response.get_json()
        self.user_ids.append(payload["user"]["id"])
        return payload

    def test_registered_session_profile_preferences_and_account_isolation(self):
        account_a = self.register(self.client_a, "Account A", f"account-a-{self.tag}@example.test")
        account_b = self.register(self.client_b, "Account B", f"account-b-{self.tag}@example.test")

        connection = database()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT password_hash FROM auth_accounts WHERE user_id=%s",
                    (account_a["user"]["id"],),
                )
                stored_hash = cursor.fetchone()["password_hash"]
        finally:
            connection.close()
        self.assertNotEqual(stored_hash, self.password)
        self.assertTrue(check_password_hash(stored_hash, self.password))

        current = self.client_a.get("/api/auth/me")
        self.assertEqual(current.status_code, 200)
        self.assertEqual(current.get_json()["user"]["id"], account_a["user"]["id"])

        profile = self.client_a.patch(
            "/api/profile",
            json={
                "full_name": "Account A Updated",
                "phone_number": "",
                "email_address": account_a["user"]["email_address"],
                "past_history": "No known allergy reported.",
                "current_history": "Tracking a clinician-confirmed concern.",
                "health_data_consent": True,
            },
        )
        self.assertEqual(profile.status_code, 200, profile.get_json())
        self.assertEqual(profile.get_json()["profile"]["full_name"], "Account A Updated")

        preferences = self.client_a.put(
            "/api/preferences",
            json={"theme": "dark", "notifications_enabled": False, "reduced_motion": True},
        )
        self.assertEqual(preferences.status_code, 200, preferences.get_json())
        self.assertEqual(preferences.get_json()["preferences"]["theme"], "dark")

        routine = self.client_a.post(
            "/api/routines",
            # A forged identifier is intentionally ignored; session ownership wins.
            json={"patient_id": account_b["user"]["patient_id"], "condition_label": "Clinician-confirmed concern", "routine_name": "Gentle routine", "start_date": "2026-09-07", "notes": "Test record"},
        )
        self.assertEqual(routine.status_code, 201, routine.get_json())
        routine_id = routine.get_json()["routine_id"]

        self.assertEqual(len(self.client_a.get("/api/routines").get_json()["routines"]), 1)
        self.assertEqual(self.client_b.get("/api/routines").get_json()["routines"], [])
        self.assertEqual(self.client_b.delete(f"/api/routines/{routine_id}").status_code, 404)
        self.assertEqual(self.client_b.get(f"/api/profiles/{account_a['user']['patient_id']}").status_code, 404)

        saved_sweat = self.client_a.post(
            "/api/sweat-assessments",
            json={
                "patient_id": account_b["user"]["patient_id"],
                "questionnaire_consent": True,
                "pattern": "usual",
                "frequency": "occasional",
                "duration": "less_than_week",
                "body_location": "underarms",
                "stress": "low",
                "heat": "low",
                "medication_change": False,
                "daily_impact": False,
                "urgent_concern": False,
            },
        )
        self.assertEqual(saved_sweat.status_code, 200, saved_sweat.get_json())
        self.assertEqual(saved_sweat.get_json()["persistence"], "mysql")
        self.assertEqual(len(self.client_a.get("/api/analysis-history").get_json()["analyses"]), 1)
        self.assertEqual(self.client_b.get("/api/analysis-history").get_json()["analyses"], [])

        self.assertEqual(self.client_a.post("/api/auth/logout").status_code, 200)
        self.assertEqual(self.client_a.get("/api/auth/me").status_code, 401)
        self.assertEqual(self.client_a.get("/api/routines").status_code, 401)


if __name__ == "__main__":
    unittest.main()
