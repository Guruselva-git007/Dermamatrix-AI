"""Account-scoped retry protection using existing saved assessment records.

No image cache, new table or process-local replay store. A MySQL advisory lock
serializes one key across workers; only a committed metadata record is replayed.
Legacy clients without a key retain their existing request contract.
"""
from functools import wraps
import hashlib
import hmac
import json
import re

import pymysql

from flask import current_app, g, jsonify, request, session

from processing_notices import UnsupportedConsentNotice, consent_notice_version


def submission_fingerprint() -> str:
    """Bind a retry to the same fields and bytes after explicit consent."""
    if request.is_json:
        content = json.dumps(request.get_json(), sort_keys=True, separators=(",", ":")).encode()
    else:
        fields = sorted((key, request.form.getlist(key)) for key in request.form)
        files = []
        for key, upload in request.files.items(multi=True):
            position = upload.stream.tell()
            digest = hashlib.sha256()
            try:
                for chunk in iter(lambda: upload.stream.read(65536), b""):
                    digest.update(chunk)
            finally:
                upload.stream.seek(position)
            files.append((key, upload.filename, digest.hexdigest()))
        content = json.dumps([fields, files], sort_keys=True).encode()
    # Do not retain a directly guessable hash of questionnaire answers.
    return hmac.new(str(current_app.secret_key).encode(), content, hashlib.sha256).hexdigest()


def guard_assessment_submission(*, database, current_user, purpose):
    def decorate(view):
        @wraps(view)
        def guarded(*args, **kwargs):
            key = request.headers.get("Idempotency-Key")
            if key is None:
                return view(*args, **kwargs)
            if not re.fullmatch(r"[A-Za-z0-9_-]{16,80}", key):
                return jsonify(error="Invalid assessment retry key."), 400
            payload = request.get_json(silent=True) if request.is_json else request.form
            accepted = (isinstance(payload, dict) and payload.get("questionnaire_consent") is True
                        if purpose == "questionnaire_assessment"
                        else request.form.getlist("image_consent") == ["true"])
            # The original endpoint owns consent validation and its exact errors.
            # Never read file streams or look up a prior result before consent.
            if not accepted:
                return view(*args, **kwargs)
            try:
                consent_notice_version(purpose, payload)
            except UnsupportedConsentNotice:
                return view(*args, **kwargs)
            if not session.get("user_id"):
                return view(*args, **kwargs)
            try:
                connection = database()
            except pymysql.MySQLError:
                # A storage outage must still allow honest local evidence.
                return view(*args, **kwargs)
            locked = False
            try:
                user = current_user(connection)
                if not user:
                    return jsonify(error="Your session ended. Sign in again before submitting."), 401
                token = hashlib.sha256(f"{user['id']}:{purpose}:{key}".encode()).hexdigest()
                assessment_id = "dmx-retry-" + token[:40]
                lock_name = "dmx:" + token[:60]
                # End the authentication read snapshot before waiting on a writer.
                connection.commit()
                with connection.cursor() as cursor:
                    cursor.execute("SELECT GET_LOCK(%s, 1) AS acquired", (lock_name,))
                    locked = cursor.fetchone()["acquired"] == 1
                    if not locked:
                        return jsonify(error="This assessment is still processing. Wait, then retry the same submission.", code="ASSESSMENT_IN_PROGRESS"), 409
                    fingerprint = submission_fingerprint()
                    cursor.execute("SELECT result_json FROM analysis_records WHERE assessment_id=%s AND user_id=%s", (assessment_id, user["id"]))
                    record = cursor.fetchone()
                if record:
                    try:
                        saved = json.loads(record["result_json"])
                    except (TypeError, ValueError):
                        return jsonify(error="The saved retry record is unreadable. Its original evidence has not been changed.", code="ASSESSMENT_RECORD_UNAVAILABLE"), 409
                    if not isinstance(saved, dict) or saved.get("submission_fingerprint") != fingerprint:
                        return jsonify(error="This retry key belongs to different inputs. Start a new assessment.", code="ASSESSMENT_INPUT_CHANGED"), 409
                    saved.pop("submission_fingerprint", None)
                    saved.update(assessment_id=assessment_id, persistence="mysql", replayed=True,
                                 research_classifier=saved.get("classification", {}))
                    return jsonify(saved)
                g.assessment_submission_id = assessment_id
                g.assessment_submission_fingerprint = fingerprint
                return view(*args, **kwargs)
            finally:
                try:
                    if locked:
                        try:
                            with connection.cursor() as cursor:
                                cursor.execute("SELECT RELEASE_LOCK(%s)", (lock_name,))
                        except pymysql.MySQLError:
                            # Cleanup must not replace completed evidence or the
                            # original processing error. Closing this dedicated
                            # connection is still required on every path.
                            current_app.logger.warning(
                                "Assessment retry lock cleanup could not be confirmed; closing its connection."
                            )
                finally:
                    connection.close()
        return guarded
    return decorate
