"""Shared reported-concern priority normalisation.

The local prototype has no validated disease-risk model.  This service gives
every modality one vocabulary for *reported-concern priority* while preserving
that limitation for the API and UI.
"""

from __future__ import annotations


RISK_LEVELS = ("LOW", "MODERATE", "HIGH", "URGENT", "UNCERTAIN")
RISK_ENGINE_VERSION = "reported-concern-priority-v1.2"
RISK_THRESHOLDS = {"LOW_MAX_EXCLUSIVE": 40, "MODERATE_MAX_EXCLUSIVE": 65, "HIGH_MIN": 65}


def _result(*, score: int | None, severity: str, level: str, title: str, summary: str, professional_evaluation_recommended: bool, urgent_attention_recommended: bool, factors: list[dict]) -> dict:
    """Build one versioned, explicitly non-clinical priority record."""
    return {
        "score": score,
        "severity": severity,
        "level": level,
        "title": title,
        "summary": summary,
        "professional_evaluation_recommended": professional_evaluation_recommended,
        "urgent_attention_recommended": urgent_attention_recommended,
        "version": RISK_ENGINE_VERSION,
        "method": "configurable reported-concern threshold normalisation",
        "thresholds": RISK_THRESHOLDS,
        "validation_status": "not_clinically_validated",
        "factors": factors,
        "label": "Reported-concern priority, not condition likelihood or disease risk.",
    }


def normalise_reported_priority(score: int | float | None, urgent_selected: bool = False) -> dict:
    """Map a bounded prototype score to a consistent, non-diagnostic domain result."""
    try:
        bounded_score = max(0, min(100, int(round(float(score)))))
    except (TypeError, ValueError):
        return _result(score=None, severity="UNCERTAIN", level="UNCERTAIN", title="Unable to prepare a screening summary", summary="The reported details could not be normalised. Try again or discuss the concern with a clinician.", professional_evaluation_recommended=True, urgent_attention_recommended=False, factors=[{"name": "Input score", "value": "Invalid or unavailable"}])

    if urgent_selected:
        return _result(score=max(65, bounded_score), severity="URGENT", level="PROMPT-CARE FLAG", title="Do not rely on the app alone", summary="You selected rapid worsening or severe symptoms. Contact a registered medical practitioner or local urgent service now if you feel severely unwell.", professional_evaluation_recommended=True, urgent_attention_recommended=True, factors=[{"name": "Normalised input score", "value": f"{bounded_score}/100"}, {"name": "Prompt-care concern", "value": "Selected by user"}])
    if bounded_score < 40:
        return _result(score=bounded_score, severity="LOW", level="TRACK AND REVISIT", title="A lower-priority screening snapshot", summary="Your reported concern can be tracked over time. Seek professional advice if it changes, becomes painful, persists, or worries you.", professional_evaluation_recommended=False, urgent_attention_recommended=False, factors=[{"name": "Normalised input score", "value": f"{bounded_score}/100"}])
    if bounded_score < 65:
        return _result(score=bounded_score, severity="MODERATE", level="SCREENING SNAPSHOT", title="Keep an eye on reported changes", summary="Your reported details are worth tracking and discussing with a clinician if new, changing, persistent, or concerning.", professional_evaluation_recommended=True, urgent_attention_recommended=False, factors=[{"name": "Normalised input score", "value": f"{bounded_score}/100"}])
    return _result(score=bounded_score, severity="HIGH", level="PROMPT-CARE FLAG", title="Do not rely on the app alone", summary="Your selected symptom details suggest seeking timely professional care. This tool cannot determine a diagnosis or urgency on its own.", professional_evaluation_recommended=True, urgent_attention_recommended=False, factors=[{"name": "Normalised input score", "value": f"{bounded_score}/100"}])
