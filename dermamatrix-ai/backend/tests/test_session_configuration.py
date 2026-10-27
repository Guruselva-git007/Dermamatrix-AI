"""Pure configuration checks; no local secrets, app import, server or MySQL."""

from datetime import timedelta
import unittest

from session_configuration import session_configuration


class SessionConfigurationTests(unittest.TestCase):
    def test_local_defaults_remain_http_compatible(self):
        config = session_configuration({})
        self.assertEqual(len(config["SECRET_KEY"]), 32)
        self.assertTrue(config["SESSION_COOKIE_HTTPONLY"])
        self.assertEqual(config["SESSION_COOKIE_SAMESITE"], "Lax")
        self.assertFalse(config["SESSION_COOKIE_SECURE"])
        self.assertEqual(config["PERMANENT_SESSION_LIFETIME"], timedelta(days=14))

    def test_existing_local_secret_and_duration_contract_are_preserved(self):
        for supplied, days in (("invalid", 14), ("0", 1), ("7", 7), ("60", 30)):
            with self.subTest(duration=supplied):
                config = session_configuration({"FLASK_SECRET_KEY": "synthetic-local", "FLASK_SESSION_DAYS": supplied})
                self.assertEqual(config["SECRET_KEY"], "synthetic-local")
                self.assertEqual(config["PERMANENT_SESSION_LIFETIME"], timedelta(days=days))

    def test_production_rejects_missing_short_or_obvious_placeholder_secret(self):
        for secret in ("", "short", "replace-with-a-long-random-local-secret", "changeme" + "-" * 40, "example" + "-" * 40):
            with self.subTest(secret_kind=len(secret)), self.assertRaises(ValueError):
                session_configuration({"DERMAMATRIX_ENV": "production", "FLASK_SESSION_SECURE": "true", "FLASK_SECRET_KEY": secret})

    def test_production_requires_secure_cookie_explicitly(self):
        for secure in ("", "false", "1", "yes"):
            with self.subTest(secure=secure), self.assertRaises(ValueError):
                session_configuration({"DERMAMATRIX_ENV": "production", "FLASK_SECRET_KEY": "synthetic-only-" * 4, "FLASK_SESSION_SECURE": secure})

    def test_valid_opt_in_production_config_is_stable(self):
        environment = {"DERMAMATRIX_ENV": "production", "FLASK_SECRET_KEY": "synthetic-only-" * 4, "FLASK_SESSION_SECURE": "true"}
        first, second = session_configuration(environment), session_configuration(environment)
        self.assertEqual(first["SECRET_KEY"], second["SECRET_KEY"])
        self.assertTrue(first["SESSION_COOKIE_SECURE"])
        self.assertTrue(first["SESSION_COOKIE_HTTPONLY"])


if __name__ == "__main__":
    unittest.main()
