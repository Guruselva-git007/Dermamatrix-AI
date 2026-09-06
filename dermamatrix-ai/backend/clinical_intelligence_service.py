"""Small, auditable context and CDSS layer for the existing assessment flow.

This module deliberately keeps the image model unimodal.  It normalises only
user-entered, area-relevant symptoms and uses profile history as clinician
discussion context, never as an unexplainable CNN feature.
"""

from __future__ import annotations


AREA_SYMPTOMS = {
    "Skin": (
        ("itching", "Itching"), ("pain", "Pain"), ("redness", "Redness"),
        ("swelling", "Swelling"), ("scaling", "Scaling"), ("bleeding", "Bleeding"),
        ("discharge", "Discharge"), ("spreading", "Spreading / enlarging"),
    ),
    "Hair": (
        ("hair_loss", "Hair loss / thinning"), ("sudden_onset", "Sudden onset"),
        ("scalp_itching", "Scalp itching"), ("scalp_scaling", "Scalp scaling"),
        ("scalp_pain", "Scalp pain"), ("recent_stress", "Recent illness or stress"),
        ("family_history", "Family history reported"),
    ),
    "Nails": (
        ("nail_change", "Colour or texture change"), ("thickening", "Thickening"),
        ("nail_pain", "Pain"), ("nail_separation", "Nail separation / lifting"),
        ("trauma", "Recent trauma"), ("previous_infection", "Previous infection reported"),
    ),
    "Sweat": (
        ("excessive_sweating", "More sweating than usual"), ("reduced_sweating", "Less sweating than usual"),
        ("night_symptoms", "Night symptoms"), ("daily_impact", "Daily-life impact"),
        ("medication_change", "Recent medicine or health change"),
    ),
}


def symptom_catalog(area: str) -> list[dict]:
    """Public, display-safe symptom options for one selected health area."""
    return [{"id": item_id, "label": label} for item_id, label in AREA_SYMPTOMS.get(area, ())]


def normalise_symptoms(area: str, values: list[object] | tuple[object, ...]) -> list[str]:
    """Keep only area-relevant symptom IDs, in their published UI order."""
    submitted = {str(value).strip() for value in values}
    return [item_id for item_id, _label in AREA_SYMPTOMS.get(area, ()) if item_id in submitted]


def reported_symptom_severity(*, discomfort: int, change: int, symptoms: list[str], urgent_selected: bool) -> dict:
    """Describe reported symptom intensity; it is explicitly not disease severity."""
    high_attention_symptoms = {"bleeding", "discharge", "spreading", "sudden_onset", "scalp_pain", "nail_separation", "night_symptoms"}
    score = max(0, min(100, int(discomfort) * 2 + int(change) * 2 + len(symptoms) * 3))
    if any(item in high_attention_symptoms for item in symptoms):
        score = min(100, score + 12)
    if urgent_selected:
        score = max(score, 70)
    label = "MILD" if score < 28 else "MODERATE" if score < 58 else "HIGH"
    return {
        "score": score,
        "level": label,
        "label": "Self-reported symptom severity, not disease severity.",
        "method": "transparent input aggregation",
        "validation_status": "not_clinically_validated",
        "factors": [{"name": "Reported discomfort", "value": str(discomfort)}, {"name": "Reported recent change", "value": str(change)}, {"name": "Relevant symptoms selected", "value": str(len(symptoms))}],
    }


def patient_context_snapshot(*, area: str, symptoms: list[str], previous_treatment: str, history: dict | None = None, previous_assessment_count: int = 0) -> dict:
    """Store a minimised, explainable context snapshot without duplicating history text."""
    history = history or {}
    has_past_history = bool(str(history.get("past_history", "")).strip())
    has_current_history = bool(str(history.get("current_history", "")).strip())
    sources = ["area-relevant symptom selections"]
    if previous_treatment:
        sources.append("user-reported prior care")
    if has_past_history or has_current_history:
        sources.append("saved health-history availability")
    if previous_assessment_count:
        sources.append("saved assessment metadata")
    return {
        "area": area,
        "relevant_symptoms": symptoms,
        "previous_care_reported": bool(previous_treatment),
        "past_history_available": has_past_history,
        "current_history_available": has_current_history,
        "previous_assessment_count": previous_assessment_count,
        "context_sources": sources,
        "image_model_context": "No profile or history field is passed to the image classifier; the image model remains unimodal.",
        "cdss_context": "The CDSS uses area-relevant symptoms, reported prior care, and the availability of history for a clinician discussion. It does not infer diagnoses from free-text history.",
        "data_minimisation": "Age, sex, medications, allergies, and location are not collected as automated model features because this deployment has no governed, validated use for them.",
    }


def clinical_decision_support(*, area: str, risk: dict, severity: dict, input_validation: dict, classifier: dict, context: dict, urgent_selected: bool) -> dict:
    """Route the existing recommendation and referral modules without prescribing."""
    validation_status = input_validation.get("status", "UNCERTAIN")
    uncertainty = (classifier.get("uncertainty") or {}).get("status")
    risk_severity = risk.get("severity", "UNCERTAIN")
    if urgent_selected or risk_severity == "URGENT":
        state = "URGENT_EVALUATION_RECOMMENDED"
        title = "Seek timely professional evaluation"
        next_step = "You selected a prompt-care concern. Do not rely on app guidance alone; contact an appropriate clinician or urgent service now if you feel severely unwell."
    elif validation_status == "LOW_QUALITY" or uncertainty == "UNCERTAIN":
        state = "UNCERTAIN"
        title = "Retake or discuss this assessment"
        next_step = "The available input cannot support a confident condition assessment. Retake a clear, relevant image or discuss the concern with a qualified clinician."
    elif risk_severity in {"HIGH", "MODERATE"}:
        state = "PROFESSIONAL_EVALUATION_RECOMMENDED"
        title = "Professional evaluation is recommended"
        next_step = "Track the reported concern and arrange professional advice before changing care because symptoms are persistent, changing, or impactful."
    else:
        state = "VALID_ASSESSMENT"
        title = "General self-care and monitoring"
        next_step = "Use gentle general care, track meaningful changes, and seek professional advice if the concern persists, changes, or worries you."

    product_guidance = "GENERAL_SELF_CARE_ONLY" if state == "VALID_ASSESSMENT" else "DEFER_PRODUCT_DECISIONS"
    return {
        "status": state,
        "title": title,
        "next_step": next_step,
        "professional_evaluation_recommended": state in {"PROFESSIONAL_EVALUATION_RECOMMENDED", "URGENT_EVALUATION_RECOMMENDED"},
        "urgent_evaluation_recommended": state == "URGENT_EVALUATION_RECOMMENDED",
        "product_guidance": product_guidance,
        "monitoring": "Save this assessment as an ongoing query and submit a future check-in or assessment when a meaningful change occurs. No passive monitoring or cure claim is made.",
        "inputs_considered": ["reported-concern priority", "self-reported symptom severity", "input validation", "model uncertainty", "area-relevant context"],
        "context_scope": context["cdss_context"],
        "notice": "This CDSS layer provides structured educational guidance. It does not diagnose disease, prescribe treatment, or turn a research model label into a prescription.",
    }
