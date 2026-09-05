"""Shared reported-concern priority normalisation.

The local prototype has no validated disease-risk model.  This service gives
every modality one vocabulary for *reported-concern priority* while preserving
that limitation for the API and UI.
"""

from __future__ import annotations


RISK_LEVELS = ("LOW", "MODERATE", "HIGH", "URGENT", "UNCERTAIN")


def normalise_reported_priority(score: int | float | None, urgent_selected: bool = False) -> dict:
    """Map a bounded prototype score to a consistent, non-diagnostic domain result."""
    try:
        bounded_score = max(0, min(100, int(round(float(score)))))
    except (TypeError, ValueError):
        return {
            "score": None,
            "severity": "UNCERTAIN",
            "level": "UNCERTAIN",
            "title": "Unable to prepare a screening summary",
            "summary": "The reported details could not be normalised. Try again or discuss the concern with a clinician.",
            "professional_evaluation_recommended": True,
            "urgent_attention_recommended": False,
        }

    if urgent_selected:
        return {
            "score": max(65, bounded_score),
            "severity": "URGENT",
            "level": "PROMPT-CARE FLAG",
            "title": "Do not rely on the app alone",
            "summary": "You selected rapid worsening or severe symptoms. Contact a registered medical practitioner or local urgent service now if you feel severely unwell.",
            "professional_evaluation_recommended": True,
            "urgent_attention_recommended": True,
        }
    if bounded_score < 40:
        return {
            "score": bounded_score,
            "severity": "LOW",
            "level": "TRACK AND REVISIT",
            "title": "A lower-priority screening snapshot",
            "summary": "Your reported concern can be tracked over time. Seek professional advice if it changes, becomes painful, persists, or worries you.",
            "professional_evaluation_recommended": False,
            "urgent_attention_recommended": False,
        }
    if bounded_score < 65:
        return {
            "score": bounded_score,
            "severity": "MODERATE",
            "level": "SCREENING SNAPSHOT",
            "title": "Keep an eye on reported changes",
            "summary": "Your reported details are worth tracking and discussing with a clinician if new, changing, persistent, or concerning.",
            "professional_evaluation_recommended": True,
            "urgent_attention_recommended": False,
        }
    return {
        "score": bounded_score,
        "severity": "HIGH",
        "level": "PROMPT-CARE FLAG",
        "title": "Do not rely on the app alone",
        "summary": "Your selected symptom details suggest seeking timely professional care. This tool cannot determine a diagnosis or urgency on its own.",
        "professional_evaluation_recommended": True,
        "urgent_attention_recommended": False,
    }
