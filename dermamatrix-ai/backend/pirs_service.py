"""Personalised Individual Risk Score (PIRS) boundary for the prototype.

PIRS is intentionally a transparent aggregation wrapper around the already
normalised reported-concern priority.  It is configurable and explicitly not a
clinically validated formula, prediction, prognosis, or diagnosis.
"""

from __future__ import annotations


def calculate_pirs(
    *,
    area: str,
    priority: dict,
    model_confidence: float | None = None,
    image_quality: int | None = None,
    reported_factors: list[str] | None = None,
) -> dict:
    """Return a reproducible PIRS record from normalised, not raw UI, inputs."""
    score = priority.get("score")
    factors = [
        {"name": "Normalised reported-concern priority", "value": f"{score}/100" if score is not None else "Unavailable"},
        {"name": "Assessment area", "value": area},
        {"name": "Priority severity", "value": priority.get("severity", "UNCERTAIN")},
    ]
    if image_quality is not None:
        factors.append({"name": "Image readiness", "value": f"{image_quality}/100 (reliability context only)"})
    if model_confidence is not None:
        factors.append({"name": "Model output confidence", "value": f"{round(model_confidence * 100)}% (not medical certainty)"})
    for factor in reported_factors or []:
        if factor:
            factors.append({"name": "Reported factor", "value": factor})
    return {
        "score": score,
        "band": priority.get("severity", "UNCERTAIN"),
        "factors": factors,
        "confidence": None,
        "method": "transparent-prototype-aggregation-v1",
        "validation_status": "not_clinically_validated",
        "label": "Personalised reported-concern priority for tracking only; not a clinical prediction.",
        "explanation": "PIRS reuses the normalised prototype priority and records the inputs considered. It does not claim an established medical scoring formula.",
    }
