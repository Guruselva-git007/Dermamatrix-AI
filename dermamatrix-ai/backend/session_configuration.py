"""Narrow, opt-in production session prerequisites; no hosting claims."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import timedelta
import os


def session_configuration(environment: Mapping[str, str]) -> dict:
    production = environment.get("DERMAMATRIX_ENV", "local").lower() == "production"
    secret = environment.get("FLASK_SECRET_KEY", "")
    secure = environment.get("FLASK_SESSION_SECURE", "false").lower() == "true"
    if production:
        if len(secret) < 32 or secret.lower().startswith(("replace-", "changeme", "example")):
            raise ValueError("Production mode requires a persistent FLASK_SECRET_KEY of at least 32 characters; use a securely generated secret.")
        if not secure:
            raise ValueError("Production mode requires FLASK_SESSION_SECURE=true and verified HTTPS termination.")
    try:
        days = max(1, min(int(environment.get("FLASK_SESSION_DAYS", "14")), 30))
    except ValueError:
        days = 14
    return {
        "SECRET_KEY": secret or os.urandom(32),
        "PERMANENT_SESSION_LIFETIME": timedelta(days=days),
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "SESSION_COOKIE_SECURE": secure,
    }
