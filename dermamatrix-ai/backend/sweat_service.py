"""Transparent sweat-questionnaire prioritisation for the local prototype.

This is deliberately not an XGBoost model and does not diagnose a sweat-gland
condition. It keeps the tabular module separate from image models and makes
each contribution visible until a validated tabular model is configured.
"""

from __future__ import annotations


FREQUENCY_LABELS = {
    0: "Occasional", 1: "A few times a week", 2: "Most days", 3: "Multiple times daily", 4: "Persistent / disruptive",
}


def _bounded_int(value: object, minimum: int, maximum: int) -> int:
    try:
        return max(minimum, min(maximum, int(value)))
    except (TypeError, ValueError):
        return minimum


def sweat_questionnaire_result(payload: dict) -> dict:
    """Calculate an explainable reported-concern priority from questionnaire data."""
    frequency = _bounded_int(payload.get("frequency"), 0, 4)
    duration = _bounded_int(payload.get("duration"), 0, 3)
    stress = _bounded_int(payload.get("stress"), 0, 3)
    heat = _bounded_int(payload.get("heat"), 0, 3)
    pattern = str(payload.get("pattern", "usual")).strip().lower()
    medication_change = bool(payload.get("medication_change"))
    daily_impact = bool(payload.get("daily_impact"))

    contributions = [
        {"feature": "Sweating frequency", "value": FREQUENCY_LABELS[frequency], "points": frequency * 8},
        {"feature": "Duration", "value": ("Less than a week", "1–4 weeks", "1–3 months", "More than 3 months")[duration], "points": duration * 5},
        {"feature": "Stress level", "value": ("Not reported", "Mild", "Moderate", "High")[stress], "points": stress * 3},
        {"feature": "Heat / humidity exposure", "value": ("Not reported", "Some", "Frequent", "High")[heat], "points": heat * 2},
        {"feature": "Recent medicine or health change", "value": "Reported" if medication_change else "Not reported", "points": 9 if medication_change else 0},
        {"feature": "Daily-life impact", "value": "Reported" if daily_impact else "Not reported", "points": 13 if daily_impact else 0},
    ]
    pattern_points = 8 if pattern in {"excessive", "reduced"} else 0
    contributions.insert(1, {"feature": "Reported pattern", "value": pattern.title() if pattern else "Usual", "points": pattern_points})
    score = min(92, max(18, 18 + sum(item["points"] for item in contributions)))
    level = "TRACK AND REVISIT" if score < 40 else "SCREENING SNAPSHOT" if score < 65 else "PROMPT-CARE FLAG"
    summary = (
        "This questionnaire suggests a lower-priority pattern to track."
        if score < 40
        else "This questionnaire suggests discussing persistent or changing sweating patterns with a clinician."
        if score < 65
        else "The reported pattern may warrant timely professional care. Do not rely on this app alone."
    )
    return {
        "risk_score": score,
        "risk_level": level,
        "summary": summary,
        "engine": {
            "name": "Sweat questionnaire prioritisation engine",
            "version": "questionnaire-v1",
            "status": "rule_based_prototype",
            "intended_use": "Educational reported-concern prioritisation only; not a diagnosis, prognosis, or validated XGBoost model.",
            "confidence": None,
        },
        "explainability": {
            "method": "Questionnaire input-contribution summary",
            "status": "available",
            "notice": "This is a transparent rule contribution summary, not SHAP values or clinical evidence.",
            "features": contributions,
        },
    }
