"""Patient-safe, versioned result contract for completed assessments.

The application has several internal services (quality, classifier, reported
symptom severity, questionnaire, CDSS and recommendations). This module is
the single boundary that turns their actual outputs into a stable result for
the client, saved history and PDF export. It intentionally does not invent a
condition, calibrated probability, disease-risk score, segmentation result or
explainability artifact when an underlying service did not produce one.
"""

from __future__ import annotations


ASSESSMENT_RESULT_VERSION = "assessment-result-v1"


def _urgency(cdss: dict, urgent_notice: str | None) -> dict:
    """Keep care routing distinct from a disease-risk model."""
    state = cdss.get("status", "UNCERTAIN")
    if urgent_notice or state == "URGENT_EVALUATION_RECOMMENDED":
        return {
            "level": "PROMPT_EVALUATION_RECOMMENDED",
            "available": True,
            "source": "User-selected prompt-care concern and CDSS routing",
            "notice": cdss.get("next_step") or urgent_notice,
        }
    if state == "PROFESSIONAL_EVALUATION_RECOMMENDED":
        return {
            "level": "PROFESSIONAL_EVALUATION_RECOMMENDED",
            "available": True,
            "source": "Reported-concern priority and CDSS routing",
            "notice": cdss.get("next_step"),
        }
    return {
        "level": "ROUTINE_MONITORING",
        "available": True,
        "source": "CDSS routing",
        "notice": cdss.get("next_step"),
    }


def _condition(classifier: dict, intelligence: dict) -> dict:
    """Expose a condition only when the scoped classifier actually ran."""
    finding = intelligence.get("finding") or {}
    likelihood = classifier.get("condition_likelihood") or {}
    top_prediction = classifier.get("top_prediction") or {}
    available = bool(classifier.get("available") and finding.get("name"))
    calibrated = bool(available and likelihood.get("available") and likelihood.get("estimated_likelihood") is not None)
    if not available:
        return {
            "available": False,
            "status": finding.get("status", "NO_MODEL_SUPPORTED_FINDING"),
            "name": None,
            "estimated_likelihood": None,
            "relative_model_score": None,
            "certainty": "NOT_AVAILABLE",
            "notice": finding.get("notice") or classifier.get("reason") or "No compatible condition classifier ran for this assessment.",
        }
    return {
        "available": True,
        "status": finding.get("status", "MODEL_SUPPORTED_RESEARCH_RANKING_ONLY"),
        "name": finding.get("name"),
        "estimated_likelihood": likelihood.get("estimated_likelihood") if calibrated else None,
        "relative_model_score": top_prediction.get("relative_score"),
        "certainty": (classifier.get("uncertainty") or {}).get("certainty", "NOT_AVAILABLE"),
        "notice": finding.get("notice") or classifier.get("notice") or "Research-only model output; not a diagnosis.",
        "calibration": {
            "available": calibrated,
            "version": (classifier.get("calibration") or {}).get("calibration_version"),
            "notice": likelihood.get("notice"),
        },
    }


def build_assessment_result(response: dict) -> dict:
    """Create the normalized, persisted result without changing legacy fields.

    ``care_priority`` is the existing transparent reported-concern priority.
    It is intentionally separate from ``disease_risk`` because no validated
    disease-risk model is configured in this deployment.
    """
    classifier = response.get("research_classifier") or {}
    intelligence = response.get("condition_intelligence") or {}
    severity = response.get("severity") or {}
    quality = response.get("quality") or {}
    validation = response.get("input_validation") or {}
    priority = response.get("risk") or {}
    cdss = response.get("clinical_decision_support") or {}
    segmentation = response.get("segmentation") or {}
    candidate = response.get("candidate_region") or {}
    questionnaire = response.get("input_type") == "questionnaire"
    condition = _condition(classifier, intelligence)
    attention = classifier.get("attention_map") or classifier.get("explainability") or {}
    recommendations = response.get("recommendations") or {}

    return {
        "contract_version": ASSESSMENT_RESULT_VERSION,
        "area": response.get("area"),
        "input": {
            "type": response.get("input_type", "image"),
            "quality": {
                "status": quality.get("status") or validation.get("status"),
                "label": quality.get("label", "Questionnaire complete" if questionnaire else "Not assessed"),
                "score": quality.get("score"),
                "issues": quality.get("issues") or [],
            },
            "validation": {
                "status": validation.get("status"),
                "relevance_status": validation.get("relevance_status"),
                "classification_status": validation.get("classification_status"),
                "notice": validation.get("notice"),
            },
        },
        "condition": condition,
        "severity": {
            "available": severity.get("level") is not None,
            "level": severity.get("level", "NOT_ASSESSED"),
            "score": severity.get("score"),
            "source": "Self-reported symptoms",
            "notice": severity.get("label") or "This is not disease severity.",
            "validation_status": severity.get("validation_status"),
        },
        "disease_risk": {
            "available": False,
            "score": None,
            "level": "NOT_AVAILABLE",
            "source": None,
            "notice": "No validated disease-risk model is configured for this assessment.",
        },
        "care_priority": {
            "available": priority.get("score") is not None,
            "score": priority.get("score"),
            "level": priority.get("level") or priority.get("severity"),
            "source": "Reported concern details",
            "notice": priority.get("label") or "Reported concern priority is not disease risk or condition likelihood.",
            "version": priority.get("version"),
        },
        "urgency": _urgency(cdss, response.get("urgent_notice")),
        "explainability": {
            "available": bool(classifier.get("available") and attention.get("image")),
            "method": (classifier.get("explainability") or {}).get("method") if classifier.get("available") else "NOT_AVAILABLE",
            "notice": (classifier.get("explainability") or {}).get("explanation_text") if classifier.get("available") else "No compatible image classifier produced an explainability artifact.",
        },
        "segmentation": {
            "available": bool(segmentation.get("available")),
            "status": segmentation.get("status", "NOT_RUN"),
            "notice": segmentation.get("notice") or segmentation.get("message"),
            "candidate_region_available": bool(candidate.get("available") and candidate.get("reliable")),
        },
        "evidence": {
            "reported_context_factors": intelligence.get("reported_context_factors") or [],
            "questionnaire_features": (response.get("explainability") or {}).get("features") if questionnaire else [],
            "model_scope": intelligence.get("model_scope") or {},
        },
        "guidance": {
            "next_step": cdss.get("next_step") or (response.get("care_plan") or {}).get("next_step"),
            "care_pathway": intelligence.get("care_pathway") or {},
            "follow_up": intelligence.get("follow_up") or {},
            "doctor": intelligence.get("doctor") or {},
            "recommendations": recommendations,
            "care_plan": response.get("care_plan") or {},
            "medication_information": recommendations.get("medication_information") or {},
            "routine": recommendations.get("routine") or {},
            "diet": recommendations.get("diet") or [],
            "lifestyle": recommendations.get("lifestyle") or [],
            "products": recommendations.get("products") or [],
        },
        "lineage": {
            "model_id": classifier.get("model_id") or (response.get("model_metadata") or {}).get("model_id"),
            "model_version": classifier.get("model_version") or (response.get("model_metadata") or {}).get("model_version"),
            "dataset_version": classifier.get("dataset_version") or (response.get("model_metadata") or {}).get("dataset_version"),
            "pipeline_version": classifier.get("pipeline_version") or (response.get("model_metadata") or {}).get("pipeline_version"),
            "calibration_version": (classifier.get("calibration") or {}).get("calibration_version"),
        },
        "medical_disclaimer": response.get("medical_disclaimer") or "Educational prototype only. This response is not a diagnosis or medical advice.",
    }
