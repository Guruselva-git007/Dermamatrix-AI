"""Versioned condition-knowledge boundary for the assessment result.

This module is intentionally separate from image inference.  It maps only the
HAM10000 research labels that the local dermatoscopic adapter can emit.  It
does not turn a research ranking into a diagnosis, estimate a cause, prescribe
a treatment, or claim support for hair, nail, ordinary clinical-photo, or
sweat-gland conditions that do not have a configured validated model.
"""

from __future__ import annotations

from clinical_intelligence_service import AREA_SYMPTOMS


KNOWLEDGE_VERSION = "dermamatrix-condition-knowledge-v1"
LAST_REVIEWED = "2026-09-06"

SOURCE_CATALOG = {
    "ham10000": {
        "title": "HAM10000 dataset label taxonomy",
        "url": "https://doi.org/10.1038/sdata.2018.161",
        "evidence_type": "Research dataset / model-label provenance",
    },
    "actinic_keratosis": {
        "title": "MedlinePlus: Actinic keratosis",
        "url": "https://www.medlineplus.gov/ency/article/000827.htm",
        "evidence_type": "NIH patient education",
    },
    "skin_cancer": {
        "title": "NCI: Skin cancer treatment (PDQ®)",
        "url": "https://www.cancer.gov/types/skin/patient/skin-treatment-pdq",
        "evidence_type": "NCI patient information",
    },
    "melanoma": {
        "title": "NCI: Melanoma treatment (PDQ®)",
        "url": "https://www.cancer.gov/types/skin/patient/melanoma-treatment-pdq",
        "evidence_type": "NCI patient information",
    },
    "moles": {
        "title": "MedlinePlus: Moles (nevus)",
        "url": "https://medlineplus.gov/moles.html",
        "evidence_type": "NIH patient education",
    },
}


def _research_label(*, code: str, name: str, aliases: tuple[str, ...], source_keys: tuple[str, ...]) -> dict:
    """Build conservative metadata for a class emitted by the research model."""
    return {
        "id": f"ham10000-{code}",
        "name": name,
        "health_area": "Skin",
        "aliases": list(aliases),
        "description": "A HAM10000 dermatoscopic research label. It is available only after the explicitly scoped research model runs and never confirms a diagnosis.",
        "common_symptoms": [],
        "visual_features": ["The only visual evidence exposed by this prototype is the model-derived research ranking and, when available, its Grad-CAM attention map."],
        "possible_causes": [],
        "risk_factors": [],
        "severity_indicators": [],
        "red_flags": [],
        "doctor_specialty": "Dermatologist",
        "self_care_guidance": "No condition-specific self-care or medicine is selected from this research label.",
        "routine_guidance": "Use the existing general routine only after considering personal tolerances and professional advice; it is not a treatment plan for this label.",
        "diet_lifestyle_guidance": "No condition-specific diet, supplement, recovery rate, or cure claim is generated from this label.",
        "treatment_categories": ["Professional evaluation", "Clinician-led treatment discussion if independently diagnosed"],
        "follow_up_guidance": "Timing depends on clinical examination, diagnosis, and change over time; this model does not predict recovery.",
        "prognosis_information": "Not determined by a research image-model label.",
        "product_categories": [],
        "monitoring_guidance": "Save a new assessment or self-reported check-in when a meaningful change occurs. The app does not passively monitor or compare retained images.",
        "urgency_level": "CONTEXT_DEPENDENT",
        "evidence_references": [SOURCE_CATALOG[key] for key in source_keys],
        "version": KNOWLEDGE_VERSION,
        "last_reviewed": LAST_REVIEWED,
        "status": "RESEARCH_LABEL_REFERENCE_ONLY",
    }


CONDITION_ONTOLOGY = {
    "akiec": _research_label(
        code="akiec", name="Actinic keratoses / intraepithelial carcinoma", aliases=("AKIEC",), source_keys=("ham10000", "actinic_keratosis"),
    ),
    "bcc": _research_label(
        code="bcc", name="Basal cell carcinoma", aliases=("BCC",), source_keys=("ham10000", "skin_cancer"),
    ),
    "bkl": _research_label(
        code="bkl", name="Benign keratosis-like lesion", aliases=("BKL",), source_keys=("ham10000",),
    ),
    "df": _research_label(
        code="df", name="Dermatofibroma", aliases=("DF",), source_keys=("ham10000",),
    ),
    "mel": _research_label(
        code="mel", name="Melanoma", aliases=("MEL",), source_keys=("ham10000", "melanoma"),
    ),
    "nv": _research_label(
        code="nv", name="Melanocytic nevus", aliases=("NV", "mole"), source_keys=("ham10000", "moles"),
    ),
    "vasc": _research_label(
        code="vasc", name="Vascular lesion", aliases=("VASC",), source_keys=("ham10000",),
    ),
}


def model_capability_matrix() -> list[dict]:
    """Expose the evidence boundary used by UI, API, and future integrations."""
    return [
        {
            "health_area": "Skin",
            "input": "Attested dermatoscopic single-lesion image",
            "model_supported_conditions": [entry["name"] for entry in CONDITION_ONTOLOGY.values()],
            "knowledge_conditions": [entry["name"] for entry in CONDITION_ONTOLOGY.values()],
            "likelihood": "Only with a version-matched independent-validation calibration artifact",
            "xai": "Grad-CAM only when the configured research model runs",
            "specialty": "Dermatologist",
            "monitoring": "Assessment metadata and self-reported check-ins; no stored-image comparison",
            "status": "RESEARCH_ONLY",
        },
        {
            "health_area": "Hair",
            "input": "Declared scalp or hair image",
            "model_supported_conditions": [],
            "knowledge_conditions": [],
            "likelihood": "Unavailable: no configured validated hair/scalp classifier",
            "xai": "Unavailable without a compatible classifier",
            "specialty": "Dermatologist",
            "monitoring": "Assessment metadata and self-reported check-ins",
            "status": "MODEL_NOT_CONFIGURED",
        },
        {
            "health_area": "Nails",
            "input": "Declared fingernail, toenail, or nail close-up",
            "model_supported_conditions": [],
            "knowledge_conditions": [],
            "likelihood": "Unavailable: no configured validated nail classifier",
            "xai": "Unavailable without a compatible classifier",
            "specialty": "Dermatologist",
            "monitoring": "Assessment metadata and self-reported check-ins",
            "status": "MODEL_NOT_CONFIGURED",
        },
        {
            "health_area": "Sweat",
            "input": "Questionnaire only",
            "model_supported_conditions": [],
            "knowledge_conditions": [],
            "likelihood": "Unavailable: transparent questionnaire prioritisation is not a validated condition model",
            "xai": "Questionnaire contribution summary; not SHAP",
            "specialty": "Qualified clinician determines the appropriate specialty",
            "monitoring": "Questionnaire assessment metadata and self-reported check-ins",
            "status": "RULE_BASED_PROTOTYPE",
        },
    ]


def _model_label_code(classifier: dict) -> str | None:
    predictions = classifier.get("top_predictions") or []
    if predictions and predictions[0].get("code") in CONDITION_ONTOLOGY:
        return predictions[0]["code"]
    code = (classifier.get("explainability") or {}).get("target_class")
    return code if code in CONDITION_ONTOLOGY else None


def _reported_context_factors(area: str, context: dict) -> list[dict]:
    labels = dict(AREA_SYMPTOMS.get(area, ()))
    factors = [
        {
            "type": "reported_symptom",
            "label": labels[symptom],
            "interpretation": "User-reported context for a clinician discussion; the app does not determine its cause.",
        }
        for symptom in context.get("relevant_symptoms", [])
        if symptom in labels
    ]
    if context.get("previous_care_reported"):
        factors.append({"type": "reported_prior_care", "label": "Previous care or treatment was reported", "interpretation": "Context only; it is not used to alter the image-model output."})
    if context.get("past_history_available") or context.get("current_history_available"):
        factors.append({"type": "saved_history_available", "label": "Saved health history is available", "interpretation": "A clinician can consider this context; free-text history is not used as an image-model feature or diagnostic fact."})
    if context.get("previous_assessment_count"):
        factors.append({"type": "prior_assessment_metadata", "label": f"{context['previous_assessment_count']} earlier saved assessment(s)", "interpretation": "Use comparable metadata for discussion only; differing model versions are not treated as progression."})
    return factors


def _follow_up_questions(area: str, context: dict) -> list[str]:
    labels = [label for symptom, label in AREA_SYMPTOMS.get(area, ()) if symptom not in set(context.get("relevant_symptoms", []))]
    if not labels:
        return ["Record a new check-in if the concern changes, persists, becomes painful, or worries you."]
    return [f"For a fuller discussion, record any relevant symptoms you have not yet selected: {', '.join(labels[:3])}."]


def _care_pathway(cdss: dict) -> dict:
    state = cdss.get("status", "UNCERTAIN")
    category = {
        "URGENT_EVALUATION_RECOMMENDED": "PROMPT PROFESSIONAL EVALUATION",
        "PROFESSIONAL_EVALUATION_RECOMMENDED": "PROFESSIONAL EVALUATION",
        "UNCERTAIN": "RETAKE / PROFESSIONAL DISCUSSION",
        "VALID_ASSESSMENT": "GENERAL SELF-CARE AND MONITORING",
    }.get(state, "PROFESSIONAL DISCUSSION")
    return {
        "category": category,
        "next_step": cdss.get("next_step", "Discuss ongoing concerns with a qualified clinician."),
        "prescription_status": "No independent prescription, dosage, diagnosis-specific treatment, or recovery promise is generated by this app.",
    }


def build_assessment_intelligence(*, area: str, classifier: dict, priority: dict, severity: dict, input_validation: dict, context: dict, cdss: dict, recommendations: dict) -> dict:
    """Compose model scope, knowledge metadata, declared context, and next steps.

    The returned object is persisted with an assessment, so every report can
    explain whether a conclusion came from a model, the knowledge registry, or
    user-provided context.  It must remain useful when no image model exists.
    """
    code = _model_label_code(classifier) if classifier.get("available") else None
    knowledge = CONDITION_ONTOLOGY.get(code) if code else None
    likelihood = classifier.get("condition_likelihood") or {}
    if knowledge and likelihood.get("available"):
        finding = {
            "status": "MODEL_SUPPORTED_CALIBRATED_RESEARCH_LABEL",
            "name": knowledge["name"],
            "condition_id": knowledge["id"],
            "model_class": code,
            "estimated_likelihood": likelihood.get("estimated_likelihood"),
            "label": "Calibrated research-model likelihood; not a diagnosis.",
            "notice": "The result remains research-only and requires independent clinical assessment.",
        }
    elif knowledge:
        top_prediction = classifier.get("top_prediction") or {}
        finding = {
            "status": "MODEL_SUPPORTED_RESEARCH_RANKING_ONLY",
            "name": knowledge["name"],
            "condition_id": knowledge["id"],
            "model_class": code,
            "estimated_likelihood": None,
            "relative_score": top_prediction.get("relative_score"),
            "label": "Highest-ranked research label; raw model ranking is not a real-world likelihood or diagnosis.",
            "notice": likelihood.get("notice") or "No calibrated condition likelihood is available.",
        }
    else:
        finding = {
            "status": "NO_MODEL_SUPPORTED_FINDING",
            "name": None,
            "condition_id": None,
            "estimated_likelihood": None,
            "label": "No model-supported condition finding is available for this assessment.",
            "notice": "The app preserves quality, reported symptoms, and next-step guidance without assigning an unsupported condition.",
        }

    doctor_specialty = knowledge["doctor_specialty"] if knowledge else ("Dermatologist" if area in {"Skin", "Hair", "Nails"} else "Qualified clinician")
    product_categories = [item.get("category") for item in recommendations.get("products", []) if item.get("category")]
    return {
        "knowledge_version": KNOWLEDGE_VERSION,
        "last_reviewed": LAST_REVIEWED,
        "finding": finding,
        "model_scope": {
            "input_validation": input_validation.get("status"),
            "model_available": bool(classifier.get("available")),
            "uncertainty": (classifier.get("uncertainty") or {}).get("status", "NOT_AVAILABLE"),
            "explanation": "Grad-CAM is included only when generated by the compatible research image model. It highlights model attention and is not lesion segmentation or proof of disease.",
        },
        "reported_context_factors": _reported_context_factors(area, context),
        "symptom_follow_up": _follow_up_questions(area, context),
        "reported_symptom_severity": {
            "level": severity.get("level"),
            "label": severity.get("label"),
            "validation_status": severity.get("validation_status"),
        },
        "reported_concern_priority": {
            "score": priority.get("score"),
            "level": priority.get("level"),
            "label": priority.get("label"),
            "validation_status": priority.get("validation_status"),
        },
        "care_pathway": _care_pathway(cdss),
        "follow_up": {
            "guidance": knowledge["follow_up_guidance"] if knowledge else cdss.get("monitoring"),
            "timeline": "No recovery timeline is predicted by this prototype.",
            "monitoring": cdss.get("monitoring"),
        },
        "doctor": {
            "recommended": bool(cdss.get("professional_evaluation_recommended")),
            "urgent": bool(cdss.get("urgent_evaluation_recommended")),
            "specialty": doctor_specialty,
            "directory": "Use the existing location-based directory handoff for current listing, rating, contact, and clinic booking details.",
            "appointment": "Appointment availability and confirmation remain with the clinic or external booking provider; no appointment is created by this app.",
        },
        "commerce": {
            "product_categories": product_categories,
            "eligible": recommendations.get("product_guidance") == "GENERAL_SELF_CARE_ONLY",
            "independence": "Products are selected downstream from existing care categories. Affiliate links never alter model output, likelihood, symptom severity, priority, CDSS, or doctor guidance.",
        },
        "knowledge": {
            "condition_available": bool(knowledge),
            "status": knowledge.get("status") if knowledge else "NO_MODEL_SUPPORTED_CONDITION",
            "references": knowledge.get("evidence_references", []) if knowledge else [],
            "condition_version": knowledge.get("version") if knowledge else None,
        },
    }
