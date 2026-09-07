"""Deterministic, explainable assessment-concern indicator.

This is a project-defined weighted evidence model for an educational prototype.
It is deliberately *not* a disease probability, prognosis, diagnosis, or
clinically validated medical risk score.  Its only job is to turn the same
bounded assessment inputs shown to the user into a reproducible 0–100 concern
indicator and a separate care-urgency suggestion.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


RISK_ENGINE_VERSION = "dermamatrix-assessment-risk-v1.0"
RISK_METHOD = "Explainable weighted assessment-evidence model"
RISK_THRESHOLDS = (
    (20, "LOW"),
    (40, "MILD"),
    (60, "MODERATE"),
    (80, "HIGH"),
    (101, "VERY_HIGH"),
)


@dataclass(frozen=True)
class ConditionRiskProfile:
    key: str
    aliases: tuple[str, ...]
    baseline: int
    severity_weight: float = 0.34
    progression_weight: int = 12
    symptom_weights: tuple[tuple[str, int], ...] = ()
    urgency_floor: str = "SELF_CARE_MONITOR"


# This is structured configuration, not a diagnostic ontology. A profile is
# only selected when a scoped condition label exists; otherwise the area-level
# undifferentiated profile is used. Values are transparent project parameters,
# not clinical thresholds or prevalence estimates.
CONDITION_PROFILES = (
    ConditionRiskProfile("undifferentiated-skin", (), 7, symptom_weights=(("itching", 2), ("pain", 5), ("redness", 2), ("swelling", 5), ("scaling", 2), ("bleeding", 16), ("discharge", 16), ("spreading", 11))),
    ConditionRiskProfile("undifferentiated-hair", (), 6, symptom_weights=(("hair_loss", 2), ("sudden_onset", 10), ("scalp_itching", 2), ("scalp_scaling", 2), ("scalp_pain", 9))),
    ConditionRiskProfile("undifferentiated-nails", (), 8, symptom_weights=(("nail_change", 3), ("thickening", 3), ("nail_pain", 8), ("nail_separation", 11))),
    ConditionRiskProfile("undifferentiated-sweat", (), 7, severity_weight=0.25, progression_weight=6, symptom_weights=(("excessive_sweating", 4), ("reduced_sweating", 4), ("night_symptoms", 8), ("daily_impact", 8), ("medication_change", 5))),
    ConditionRiskProfile("acne", ("acne", "acne vulgaris", "blackheads", "whiteheads", "comedones"), 8, symptom_weights=(("pain", 6), ("swelling", 5), ("discharge", 10), ("spreading", 5))),
    ConditionRiskProfile("folliculitis", ("folliculitis",), 12, symptom_weights=(("pain", 7), ("discharge", 14), ("spreading", 9))),
    ConditionRiskProfile("eczema", ("eczema", "atopic dermatitis", "contact dermatitis"), 10, symptom_weights=(("itching", 4), ("pain", 6), ("discharge", 14), ("spreading", 8))),
    ConditionRiskProfile("psoriasis", ("psoriasis",), 13, symptom_weights=(("scaling", 4), ("pain", 7), ("spreading", 7))),
    ConditionRiskProfile("seborrheic-dermatitis", ("seborrheic dermatitis", "dandruff"), 8, symptom_weights=(("scalp_itching", 4), ("scalp_scaling", 3), ("scalp_pain", 8))),
    ConditionRiskProfile("rosacea", ("rosacea",), 10, symptom_weights=(("redness", 4), ("pain", 6), ("swelling", 6))),
    ConditionRiskProfile("tinea", ("fungal rash", "tinea", "tinea corporis", "ringworm", "tinea pedis", "athlete's foot"), 15, symptom_weights=(("itching", 4), ("scaling", 3), ("spreading", 12), ("discharge", 15))),
    ConditionRiskProfile("hyperpigmentation", ("hyperpigmentation", "melasma", "post-inflammatory hyperpigmentation", "oily skin", "excess sebum"), 5, symptom_weights=(("spreading", 4),)),
    ConditionRiskProfile("alopecia", ("alopecia areata", "androgenetic alopecia", "pattern hair loss", "telogen effluvium", "hair thinning", "hair shedding"), 8, symptom_weights=(("hair_loss", 4), ("sudden_onset", 10), ("scalp_pain", 8))),
    ConditionRiskProfile("onychomycosis", ("onychomycosis", "nail fungus", "nail dystrophy", "nail pitting", "nail ridging"), 12, symptom_weights=(("thickening", 4), ("nail_change", 4), ("nail_pain", 8), ("nail_separation", 10))),
    ConditionRiskProfile("nail-psoriasis", ("nail psoriasis",), 12, symptom_weights=(("nail_change", 4), ("nail_pain", 8), ("nail_separation", 10))),
    ConditionRiskProfile("blue-nail", ("blue nail", "blue-grey nail", "nail discoloration"), 16, urgency_floor="ROUTINE_MEDICAL_REVIEW", symptom_weights=(("nail_pain", 8), ("nail_separation", 8))),
    ConditionRiskProfile("suspicious-lesion", ("melanoma", "basal cell carcinoma", "actinic keratoses", "intraepithelial carcinoma", "suspicious pigmented lesion"), 26, severity_weight=0.38, progression_weight=22, urgency_floor="MEDICAL_REVIEW_RECOMMENDED", symptom_weights=(("bleeding", 25), ("pain", 7), ("spreading", 10))),
)

AREA_DEFAULT_PROFILE = {
    "Skin": "undifferentiated-skin",
    "Hair": "undifferentiated-hair",
    "Nails": "undifferentiated-nails",
    "Sweat": "undifferentiated-sweat",
}
URGENCY_ORDER = {
    "SELF_CARE_MONITOR": 0,
    "ROUTINE_MEDICAL_REVIEW": 1,
    "MEDICAL_REVIEW_RECOMMENDED": 2,
    "PROMPT_MEDICAL_EVALUATION": 3,
    "URGENT_EVALUATION": 4,
}
URGENCY_LABELS = {
    "SELF_CARE_MONITOR": "Self-care / monitor",
    "ROUTINE_MEDICAL_REVIEW": "Routine medical review",
    "MEDICAL_REVIEW_RECOMMENDED": "Medical review recommended",
    "PROMPT_MEDICAL_EVALUATION": "Prompt medical evaluation",
    "URGENT_EVALUATION": "Urgent evaluation",
}


def _bounded(value: Any, lower: int = 0, upper: int = 100) -> int:
    try:
        return max(lower, min(upper, int(round(float(value)))))
    except (TypeError, ValueError):
        return lower


def _profile_for(area: str, condition_name: str | None) -> ConditionRiskProfile:
    needle = str(condition_name or "").casefold()
    if needle:
        for profile in CONDITION_PROFILES:
            if any(alias in needle for alias in profile.aliases):
                return profile
    default_key = AREA_DEFAULT_PROFILE.get(area, "undifferentiated-skin")
    return next(profile for profile in CONDITION_PROFILES if profile.key == default_key)


def _risk_level(score: int) -> str:
    for limit, level in RISK_THRESHOLDS:
        if score < limit:
            return level
    return "VERY_HIGH"


def _as_factor(key: str, label: str, points: int, source: str) -> dict:
    return {"key": key, "label": label, "points": int(points), "source": source}


def _higher_urgency(first: str, second: str) -> str:
    return first if URGENCY_ORDER[first] >= URGENCY_ORDER[second] else second


def _urgency(*, score: int, profile: ConditionRiskProfile, urgent_selected: bool, symptoms: list[str], recent_change: int, discomfort: int) -> str:
    urgency = profile.urgency_floor
    if urgent_selected:
        return "URGENT_EVALUATION"
    if "bleeding" in symptoms and profile.key == "suspicious-lesion" and recent_change >= 18:
        return "PROMPT_MEDICAL_EVALUATION"
    if score >= 80:
        urgency = _higher_urgency(urgency, "PROMPT_MEDICAL_EVALUATION")
    elif score >= 60:
        urgency = _higher_urgency(urgency, "MEDICAL_REVIEW_RECOMMENDED")
    elif score >= 40 or "discharge" in symptoms or "spreading" in symptoms:
        urgency = _higher_urgency(urgency, "ROUTINE_MEDICAL_REVIEW")
    if discomfort >= 25 and score >= 60:
        urgency = _higher_urgency(urgency, "PROMPT_MEDICAL_EVALUATION")
    return urgency


def calculate_assessment_risk(
    *,
    area: str,
    condition_name: str | None,
    condition_source: str | None,
    model_confidence: float | None,
    severity: dict | None,
    duration: int | None,
    discomfort: int | None,
    recent_change: int | None,
    symptoms: list[str] | None,
    urgent_selected: bool,
    image_quality: int | None = None,
    quality_status: str | None = None,
    uncertainty_status: str | None = None,
    input_validation_status: str | None = None,
    affected_area_percent: float | None = None,
    questionnaire: dict | None = None,
) -> dict:
    """Calculate one reproducible assessment-level concern indicator.

    A condition label is optional and only adjusts the profile when it came
    from a scoped model. Low model confidence and poor image quality are
    reliability context, not automatic risk escalators.
    """
    severity = severity or {}
    questionnaire = questionnaire or {}
    selected_symptoms = list(dict.fromkeys(str(item) for item in (symptoms or []) if item))
    profile = _profile_for(area, condition_name)
    factors: list[dict] = []
    missing_inputs: list[str] = []
    inputs_used: list[str] = []
    total = profile.baseline
    factors.append(_as_factor("profile_baseline", "Assessment profile baseline", profile.baseline, profile.key))
    inputs_used.append("assessment area and condition profile")

    severity_score = severity.get("score")
    if isinstance(severity_score, (int, float)):
        severity_points = round(_bounded(severity_score) * profile.severity_weight)
        total += severity_points
        factors.append(_as_factor("reported_severity", f"Reported symptom severity: {_bounded(severity_score)}/100", severity_points, "reported severity"))
        inputs_used.append("reported symptom severity")
    else:
        missing_inputs.append("reported symptom severity")

    duration_value = _bounded(duration, 0, 24)
    duration_points = 0 if duration_value <= 0 else 3 if duration_value <= 4 else 6 if duration_value <= 10 else 9
    if duration is None:
        missing_inputs.append("symptom duration")
    else:
        total += duration_points
        inputs_used.append("duration")
        if duration_points:
            factors.append(_as_factor("duration", "Symptoms reported for longer than one week", duration_points, "reported duration"))

    change_value = _bounded(recent_change, 0, 30)
    progression_points = 0 if change_value <= 0 else max(3, round(profile.progression_weight * min(change_value / 18, 1)))
    if recent_change is None:
        missing_inputs.append("recent change")
    else:
        total += progression_points
        inputs_used.append("reported recent change")
        if progression_points:
            factors.append(_as_factor("progression", "A recent change was reported", progression_points, "reported change"))

    discomfort_value = _bounded(discomfort, 0, 30)
    if discomfort is None:
        missing_inputs.append("reported discomfort")
    elif discomfort_value >= 25:
        total += 10
        factors.append(_as_factor("severe_discomfort", "Severe or worsening discomfort was reported", 10, "reported discomfort"))
        inputs_used.append("reported discomfort")
    elif discomfort_value > 0:
        inputs_used.append("reported discomfort")

    profile_symptom_weights = dict(profile.symptom_weights)
    generic_symptom_weights = {"bleeding": 12, "discharge": 12, "spreading": 9, "pain": 4, "swelling": 4, "night_symptoms": 6}
    for symptom in selected_symptoms:
        points = profile_symptom_weights.get(symptom, generic_symptom_weights.get(symptom, 0))
        if points:
            total += points
            factors.append(_as_factor(f"symptom_{symptom}", symptom.replace("_", " ").capitalize() + " was reported", points, "selected symptom"))
    if selected_symptoms:
        inputs_used.append("area-relevant symptoms")
    else:
        missing_inputs.append("optional area-relevant symptoms")

    if isinstance(affected_area_percent, (int, float)):
        extent = max(0.0, min(100.0, float(affected_area_percent)))
        extent_points = 0 if extent < 5 else 3 if extent < 20 else 7 if extent < 45 else 11
        total += extent_points
        inputs_used.append("model-reported visual extent")
        if extent_points:
            factors.append(_as_factor("visual_extent", f"Model-reported candidate region: {round(extent)}% of frame", extent_points, "visual extent"))
    else:
        missing_inputs.append("model-reported visual extent")

    if area == "Sweat":
        pattern = str(questionnaire.get("pattern", "usual")).lower()
        frequency = _bounded(questionnaire.get("frequency"), 0, 4)
        questionnaire_duration = _bounded(questionnaire.get("duration"), 0, 3)
        questionnaire_points = (4 if pattern in {"excessive", "reduced"} else 0) + frequency * 2 + questionnaire_duration * 2
        if questionnaire.get("daily_impact"):
            questionnaire_points += 8
        if questionnaire.get("medication_change"):
            questionnaire_points += 5
        total += questionnaire_points
        inputs_used.append("sweat questionnaire responses")
        if questionnaire_points:
            factors.append(_as_factor("questionnaire", "Sweat-pattern questionnaire contribution", questionnaire_points, "questionnaire"))

    if urgent_selected:
        total += 30
        factors.append(_as_factor("prompt_care_selected", "Prompt-care concern selected", 30, "user-selected escalation"))
        inputs_used.append("prompt-care selection")

    # Quality, confidence, and uncertainty never raise the score. They clarify
    # reliability and prevent a project score from being misread as certainty.
    reliability = {
        "condition_source": condition_source or "No condition label used",
        "model_confidence": model_confidence if isinstance(model_confidence, (int, float)) else None,
        "image_quality": image_quality,
        "quality_status": quality_status or "NOT_APPLICABLE",
        "uncertainty_status": uncertainty_status or "NOT_AVAILABLE",
        "input_validation_status": input_validation_status or "NOT_AVAILABLE",
    }
    if model_confidence is None:
        missing_inputs.append("calibrated model likelihood")
    if image_quality is None:
        missing_inputs.append("image-quality score")
    if uncertainty_status and uncertainty_status not in {"CALIBRATED_OUTPUT", "NOT_APPLICABLE_NO_CLASSIFIER", "NOT_AVAILABLE_NO_VALIDATED_TABULAR_MODEL"}:
        factors.append(_as_factor("uncertainty", "Input/model uncertainty limits interpretation", 0, "reliability context"))

    score = _bounded(total)
    level = _risk_level(score)
    urgency = _urgency(score=score, profile=profile, urgent_selected=urgent_selected, symptoms=selected_symptoms, recent_change=change_value, discomfort=discomfort_value)
    factor_labels = [factor["label"] for factor in factors if factor["points"] > 0]
    if not factor_labels:
        factor_labels = ["Low reported symptom burden in the available assessment"]
    explanation = (
        f"This {level.lower().replace('_', ' ')} assessment concern indicator uses the reported symptoms, severity, timing, "
        f"change, and relevant modality-specific indicators available in this assessment. "
        "It is not a disease probability, diagnosis, or clinically validated medical risk score."
    )
    return {
        "available": True,
        "score": score,
        "level": level,
        "urgency": urgency,
        "urgency_label": URGENCY_LABELS[urgency],
        "factors": factors,
        "factor_labels": factor_labels,
        "explanation": explanation,
        "calculation_inputs": {"used": inputs_used, "missing_optional": missing_inputs, "reliability": reliability},
        "condition_profile": {"key": profile.key, "condition_name": condition_name, "condition_source": condition_source or "No condition label used"},
        "methodology": RISK_METHOD,
        "methodology_version": RISK_ENGINE_VERSION,
        "validation_status": "not_clinically_validated",
        "label": "Explainable AI-assisted assessment concern indicator; not disease probability or diagnosis.",
        "calculated_at": datetime.now(timezone.utc).isoformat(),
    }
