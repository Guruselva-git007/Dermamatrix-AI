"""Version-aware comparison of saved assessment metadata.

The result is a record of compatible measurement changes, not a clinical
statement about healing, cure, or disease progression.
"""

from __future__ import annotations


def _classification(snapshot: dict) -> dict:
    return snapshot.get("classification") or snapshot.get("research_classifier") or {}


def _likelihood(snapshot: dict) -> float | None:
    classifier = _classification(snapshot)
    likelihood = classifier.get("condition_likelihood") or {}
    value = likelihood.get("estimated_likelihood")
    return float(value) if likelihood.get("available") and isinstance(value, (int, float)) else None


def _model_signature(snapshot: dict) -> tuple[object, ...]:
    classifier = _classification(snapshot)
    calibration = classifier.get("calibration") or {}
    pipeline = snapshot.get("model_pipeline") or {}
    return (
        classifier.get("model_id"), classifier.get("model_version"),
        calibration.get("calibration_version"), classifier.get("pipeline_version") or (pipeline.get("model_lineage") or {}).get("pipeline_version"),
    )


def build_progress_comparison(*, user_id: int | None, area: str, current: dict, historical: list[dict]) -> dict:
    """Return one ongoing-query baseline/follow-up record from account-scoped data."""
    if not user_id:
        return {"status": "NOT_SAVED", "summary": "Guest results are not stored. Create an account before starting an ongoing query.", "journey": None}

    journey_id = f"ongoing-query-{user_id}-{area.lower().replace(' ', '-') }"
    if not historical:
        return {
            "status": "BASELINE_CREATED",
            "summary": "This saved assessment is the baseline for an ongoing query. A future compatible assessment can report measurement changes, but the app does not infer healing or cure.",
            "journey": {"journey_id": journey_id, "type": "ONGOING_QUERY", "area": area, "baseline_date": current.get("created_at"), "baseline_assessment_id": current.get("assessment_id"), "follow_up_count": 0},
            "comparison": {"risk": "No earlier saved priority record.", "likelihood": "No earlier compatible calibrated likelihood.", "images": "Source images are not retained for before/after comparison."},
        }

    baseline = historical[0]
    previous = historical[-1]
    previous_summary = previous.get("summary") or {}
    prior_risk = (previous_summary.get("risk") or {})
    current_risk = current.get("risk") or {}
    risk_compatible = current_risk.get("version") and current_risk.get("version") == prior_risk.get("version")
    risk_change = None
    if risk_compatible and isinstance(current_risk.get("score"), (int, float)) and isinstance(prior_risk.get("score"), (int, float)):
        risk_change = int(current_risk["score"] - prior_risk["score"])

    previous_likelihood = _likelihood(previous_summary)
    current_likelihood = _likelihood(current)
    likelihood_compatible = current_likelihood is not None and previous_likelihood is not None and _model_signature(current) == _model_signature(previous_summary)
    likelihood_change = round(current_likelihood - previous_likelihood, 4) if likelihood_compatible else None
    compatibility = "COMPATIBLE" if risk_compatible and (current_likelihood is None or likelihood_compatible) else "LIMITED"
    risk_note = f"Reported-concern priority changed by {risk_change:+d} points since the previous saved assessment." if risk_change is not None else "Reported-concern priority is not compared because the engine version differs or a score is unavailable."
    likelihood_note = f"Calibrated model-estimated likelihood changed by {likelihood_change:+.1%}; this is not evidence of disease progression or cure." if likelihood_change is not None else "Condition likelihood is not compared because calibration or model lineage is unavailable/incompatible."
    return {
        "status": "FOLLOW_UP_COMPARABLE" if compatibility == "COMPATIBLE" else "FOLLOW_UP_LIMITED",
        "summary": f"Follow-up saved. {risk_note} {likelihood_note}",
        "journey": {"journey_id": journey_id, "type": "ONGOING_QUERY", "area": area, "baseline_date": baseline.get("created_at"), "baseline_assessment_id": baseline.get("assessment_id"), "follow_up_count": len(historical), "comparison_compatibility": compatibility},
        "comparison": {"risk_change": risk_change, "likelihood_change": likelihood_change, "risk_engine_compatible": risk_compatible, "model_lineage_compatible": likelihood_compatible, "previous_assessment": previous.get("created_at"), "images": "Source images are not retained for before/after comparison."},
    }
