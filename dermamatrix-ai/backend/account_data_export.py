"""Read-only copy of known local account tables, with no PDF row limits.

This is a technical account-data download, not a complete legal access-request
service, retention policy, withdrawal mechanism or deletion procedure. Explicit
columns keep password hashes and future authentication secrets out of queries.
No source-image files, logs, backups or server configuration are read.
"""

from __future__ import annotations

import base64
from datetime import date, datetime, time, timezone
from decimal import Decimal
from flask import current_app, has_app_context
import json


FORMAT_VERSION = "dermamatrix-local-account-data-v1"

# All account-owned tables and columns in the current schema, including the
# existing additive risk columns. Keep this allowlist aligned with schema work.
# Do not use SELECT *: auth_accounts also contains the salted password hash.
ACCOUNT_COLUMNS = {
    "users": ("id", "patient_id", "full_name", "phone_number", "email_address", "created_at", "updated_at", "last_login_at", "is_active"),
    "auth_accounts": ("id", "user_id", "email_address", "created_at"),
    "medical_histories": ("id", "user_id", "past_history", "current_history", "updated_at"),
    "consent_records": ("id", "user_id", "consent_version", "purpose", "accepted_at"),
    "assessments": ("id", "assessment_id", "user_id", "area", "risk_score", "quality_score", "clinical_status", "created_at",
                    "assessment_risk_score", "assessment_risk_level", "urgency_level", "risk_factors_json", "risk_explanation",
                    "risk_methodology_version", "risk_inputs_json", "risk_calculated_at"),
    "analysis_records": ("id", "assessment_id", "user_id", "area", "result_json", "image_stored", "created_at"),
    "clinical_review_requests": ("id", "user_id", "assessment_id", "status", "requested_at"),
    "care_routines": ("id", "routine_id", "user_id", "condition_label", "routine_name", "start_date", "notes", "created_at", "updated_at"),
    "progress_checkins": ("id", "checkin_id", "user_id", "routine_id", "checkin_date", "reported_trend", "discomfort_score", "change_score",
                          "priority_score", "note", "image_stored", "created_at"),
    "reports": ("id", "report_id", "assessment_id", "user_id", "report_type", "generated_at"),
    "user_preferences": ("id", "user_id", "theme", "notifications_enabled", "reduced_motion", "updated_at"),
}


class AccountDataExportError(ValueError):
    """An export cannot be safely completed; never include private row values."""


def begin_account_data_snapshot(connection) -> None:
    """Start a single MySQL/InnoDB snapshot before account authentication reads."""
    with connection.cursor() as cursor:
        cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        cursor.execute("START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY")


def _reject_nonstandard_json_constant(_value):
    raise ValueError("Not a JSON constant")


def _json_field_status(value) -> str:
    if value is None:
        return "null_preserved"
    try:
        json.loads(value, parse_constant=_reject_nonstandard_json_constant)
    except (TypeError, ValueError, UnicodeDecodeError, RecursionError):
        return "malformed_preserved"
    return "valid_json_preserved"


def collect_account_data(connection, user_id: int) -> dict:
    """Collect every owned row without joins, truncation or version conversion."""
    records = {}
    with connection.cursor() as cursor:
        for table, columns in ACCOUNT_COLUMNS.items():
            owner_column = "id" if table == "users" else "user_id"
            cursor.execute(
                f"SELECT {', '.join(columns)} FROM {table} WHERE {owner_column}=%s ORDER BY id ASC",
                (user_id,),
            )
            rows = []
            for source in cursor.fetchall():
                # Restrict even a fake/changed database adapter to the declared
                # public columns. Missing columns fail rather than drop data.
                if any(column not in source for column in columns):
                    raise AccountDataExportError("The local account schema is not supported by this export.")
                row = {column: source[column] for column in columns}
                json_fields = {column: _json_field_status(row[column]) for column in columns if column.endswith("_json")}
                if json_fields:
                    row["json_field_status"] = json_fields
                rows.append(row)
            records[table] = rows
    if has_app_context() and current_app.config.get("CONSUMER_ENABLED"):
        extra_columns = {
            "account_mail_jobs": ("job_id", "user_id", "purpose", "target_email", "state", "created_at", "updated_at"),
            "account_security": ("user_id", "email_verified_at", "processing_paused", "updated_at"),
            "account_sessions": ("user_id", "device_label", "created_at", "expires_at", "revoked"),
            "consumer_records": ("record_id", "user_id", "kind", "subject_id", "data_json", "created_at", "updated_at"),
            "reminder_jobs": ("job_id", "user_id", "routine_id", "due_at", "state", "attempts", "available_at", "provider_reference", "created_at", "updated_at"),
            "account_tokens": ("user_id", "purpose", "target_email", "expires_at", "consumed", "created_at"),
        }
        with connection.cursor() as cursor:
            for table, columns in extra_columns.items():
                cursor.execute(f"SELECT {', '.join(columns)} FROM {table} WHERE user_id=%s ORDER BY user_id, created_at" if "created_at" in columns else f"SELECT {', '.join(columns)} FROM {table} WHERE user_id=%s", (user_id,))
                records[table] = [{column: source[column] for column in columns} for source in cursor.fetchall()]
    effective_views = {}
    if has_app_context() and current_app.config.get('CONSUMER_ENABLED'):
        from consumer_continuity import effective_checkins, effective_events
        effective_views['checkins'] = effective_checkins(connection, user_id, records['progress_checkins'])
        event_rows = [dict(id=r['record_id'], routine_id=r['subject_id'], **json.loads(r['data_json']), created_at=r['created_at']) for r in records['consumer_records'] if r['kind'] == 'routine_event']
        effective_views['routine_actions'] = effective_events(connection, user_id, event_rows)
        effective_views['meaning'] = 'Current projections use immutable correction records. Original rows and all revisions remain in records.'
    return {
        'effective_views': effective_views,
        "format_version": FORMAT_VERSION + ("-consumer" if len(records) > len(ACCOUNT_COLUMNS) else ""),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": {
            "description": "All rows owned by this signed-in account in the known account tables listed in records, including enabled consumer tables; no 50/50/100 PDF limits.",
            "legal_request_status": "Technical local account-data copy; not a complete legal access-request service or evidence that all applicable data-rights obligations are satisfied.",
            "exclusions": ["Password hashes, session secrets and credentials", "Other accounts' records and unowned guest results",
                           "Source-image files and overlays (not stored by the current assessment pipeline)",
                           "Server configuration, system logs, backups and schema-migration records"],
            "changes_to_data": "None. This read-only download does not withdraw consent, change retention, erase records or reinterpret historical notice acceptance.",
        },
        "snapshot": {"isolation": "REPEATABLE READ", "read_only": True, "consistent_snapshot": True},
        "encoding": {
            "dates_and_times": "ISO 8601; database values retain their stored timezone/naive representation. generated_at is UTC.",
            "json_fields": "Original *_json content is preserved exactly. json_field_status identifies malformed or null content; no historical result details are silently replaced.",
            "non_json_scalars": "Unexpected bytes use a typed base64 object; Decimal values use a typed exact-decimal string object.",
        },
        "counts": {table: len(rows) for table, rows in records.items()},
        "records": records,
    }


def _json_scalar(value):
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return {"$type": "decimal", "value": str(value)}
    if isinstance(value, (bytes, bytearray, memoryview)):
        return {"$type": "bytes", "encoding": "base64", "value": base64.b64encode(bytes(value)).decode("ascii")}
    raise AccountDataExportError("A stored value cannot be safely represented in this export.")


def encode_account_data(payload: dict) -> bytes:
    try:
        return (json.dumps(payload, ensure_ascii=False, allow_nan=False, indent=2, default=_json_scalar) + "\n").encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError) as error:
        raise AccountDataExportError("The local account data could not be fully represented.") from error
