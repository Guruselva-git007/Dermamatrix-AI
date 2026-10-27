"""Server-owned, factual prototype notices and consent evidence identifiers.

These describe current technical behavior. They are not approved legal terms,
an operator privacy policy, or evidence of legal/clinical compliance. Historical
clients that omit a notice version retain their API contract, but never acquire
evidence of accepting a notice they were not known to have been shown.
"""

from __future__ import annotations

from copy import deepcopy
from collections.abc import Mapping


PROCESSING_NOTICES = {
    "account": {
        "version": "prototype-account-notice-v1",
        "legacy_version": "local-auth-v1",
        "title": "Local account and sign-in",
        "summary": "Create a local account using your name, email, optional phone number and a salted password hash.",
        "retained": "Account details, sign-in information, preferences and this acknowledgement are stored in MySQL.",
        "guest_behavior": "Guest access does not create an account.",
        "limitations": "Operator-approved terms, retention periods and a privacy assistance channel are not configured.",
        "record_purpose": "Local account authentication and secure session",
    },
    "health_history": {
        "version": "prototype-health-history-notice-v1",
        "legacy_version": "india-prototype-v1",
        "title": "Save health history",
        "summary": "Store the past and current health details you provide for context in signed-in assessments.",
        "retained": "Submitted history and acknowledgement are stored in MySQL. Updating history adds a record; earlier entries remain.",
        "guest_behavior": "Health-history storage requires a signed-in account.",
        "limitations": "A retention, withdrawal and erasure process has not been approved or implemented.",
        "record_purpose": "MySQL storage of profile and health-history data for screening support",
    },
    "image_assessment": {
        "version": "prototype-image-notice-v1",
        "legacy_version": "legacy-image-acknowledgement-v1",
        "title": "Process an image assessment",
        "summary": "Process the uploaded image in memory on this app's server, with your reported context, using available local research tools.",
        "retained": "Source photos and overlays are not saved. Signed-in assessments save derived health information, reported context, results and acknowledgement in MySQL.",
        "guest_behavior": "Guest assessment results are returned to the current screen without account history or a persisted acknowledgement.",
        "limitations": "Research and educational use only; not a diagnosis or clinical validation. Opt-in presentation matching adds exact-file teaching metadata.",
        "record_purpose": "Local image processing and storage of derived assessment information",
    },
    "questionnaire_assessment": {
        "version": "prototype-questionnaire-notice-v1",
        "legacy_version": "legacy-questionnaire-acknowledgement-v1",
        "title": "Process a sweat questionnaire",
        "summary": "Process your answers with the app's bounded questionnaire rules; no image classifier is used.",
        "retained": "Signed-in assessments save reported questionnaire context, derived health information, results and acknowledgement in MySQL.",
        "guest_behavior": "Guest questionnaire results are returned to the current screen without account history or a persisted acknowledgement.",
        "limitations": "Research and educational use only; questionnaire completion cannot establish a diagnosis.",
        "record_purpose": "Questionnaire processing and storage of derived assessment information",
    },
}


class UnsupportedConsentNotice(ValueError):
    def __init__(self, purpose: str):
        self.purpose = purpose
        self.current_version = PROCESSING_NOTICES[purpose]["version"]
        super().__init__("The processing notice has changed. Review the current notice and try again.")


def public_processing_notices() -> dict:
    notices = deepcopy(PROCESSING_NOTICES)
    for notice in notices.values():
        notice.pop("legacy_version")
        notice.pop("record_purpose")
    return {
        "notices": notices,
        "operator_review_required": True,
        "contact_available": False,
        "notice_kind": "factual_prototype_processing_information",
        "external_navigation": "Maps and shopping links open separate external services. Their privacy terms apply after navigation.",
    }


def consent_notice_version(purpose: str, payload: Mapping) -> str:
    """Resolve evidence only against trusted server versions, never client text."""
    notice = PROCESSING_NOTICES[purpose]
    if "consent_notice_version" not in payload:
        return notice["legacy_version"]
    if hasattr(payload, "getlist"):
        values = payload.getlist("consent_notice_version")
        if len(values) != 1:
            raise UnsupportedConsentNotice(purpose)
        value = values[0]
    else:
        value = payload["consent_notice_version"]
    if not isinstance(value, str) or value != notice["version"]:
        raise UnsupportedConsentNotice(purpose)
    return notice["version"]


def consent_record_purpose(purpose: str, *, assessment_id: str | None = None,
                           history_id: int | None = None) -> str:
    """Link an acceptance to its activity using the existing 255-char column."""
    text = f"{purpose}: {PROCESSING_NOTICES[purpose]['record_purpose']}"
    if assessment_id is not None:
        text += f"; assessment_id={assessment_id}"
    if history_id is not None:
        text += f"; history_id={history_id}"
    if len(text) > 255:
        raise ValueError("Consent activity reference is too long.")
    return text
