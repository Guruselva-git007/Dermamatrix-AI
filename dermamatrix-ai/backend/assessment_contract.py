"""Patient-safe, versioned result contract for completed assessments.

The application has several internal services (quality, classifier, reported
symptom severity, questionnaire, CDSS and recommendations). This module is
the single boundary that turns their actual outputs into a stable result for
the client, saved history and PDF export. It intentionally does not invent a
condition, calibrated probability, disease-risk score, segmentation result or
explainability artifact when an underlying service did not produce one.
"""

from __future__ import annotations


ASSESSMENT_RESULT_VERSION = "assessment-result-v1.3"


def _urgency(cdss: dict, urgent_notice: str | None, assessment_risk: dict) -> dict:
    """Keep care routing distinct from a disease-risk model."""
    calculated = assessment_risk.get("urgency")
    if calculated:
        return {
            "level": calculated,
            "available": True,
            "source": "Assessment concern indicator and CDSS routing",
            "notice": cdss.get("next_step") or assessment_risk.get("urgency_label"),
        }
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


def _assessment_status(response: dict, classifier: dict, validation: dict) -> dict:
    """Describe what the completed pathway could actually establish.

    This is deliberately separate from a possible model label, condition
    likelihood, reported severity, and the project-defined concern indicator.
    It gives clients one stable, non-clinical outcome code without converting
    an unavailable or research-only component into a medical conclusion.
    """
    input_type = response.get("input_type", "image")
    quality = response.get("quality") or {}
    validation_status = validation.get("status")
    uncertainty = classifier.get("uncertainty") or {}
    uncertainty_status = uncertainty.get("status")
    ood_status = uncertainty.get("ood_status")

    if input_type == "questionnaire":
        return {
            "code": "QUESTIONNAIRE_ASSESSMENT",
            "label": "Questionnaire assessment completed",
            "notice": "This transparent questionnaire pathway does not run an image classifier or validated condition model.",
        }
    if quality.get("status") == "LOW_QUALITY" or validation_status in {"LOW_QUALITY", "INVALID_INPUT", "UNSUPPORTED"}:
        return {
            "code": "INPUT_UNSUITABLE",
            "label": "Input unsuitable for a condition assessment",
            "notice": validation.get("notice") or "Retake a clear, relevant image before relying on this screening summary.",
        }
    if ood_status == "OUT_OF_DISTRIBUTION":
        return {
            "code": "OUT_OF_DISTRIBUTION",
            "label": "Image is outside the configured model scope",
            "notice": uncertainty.get("notice") or "No condition result is shown for an image outside the configured model scope.",
        }
    if classifier.get("available"):
        if uncertainty_status == "LOW_CONFIDENCE":
            return {
                "code": "UNCERTAIN",
                "label": "Research-model output is uncertain",
                "notice": uncertainty.get("notice") or "The model output did not meet the configured certainty threshold.",
            }
        return {
            "code": "RESEARCH_ONLY",
            "label": "Research-only model output",
            "notice": classifier.get("notice") or "This research result is not a diagnosis or a clinically validated decision.",
        }
    if uncertainty_status in {"UNCERTAIN", "LOW_CONFIDENCE"} and validation_status not in {"VALID", "VALID_RELEVANT"}:
        return {
            "code": "UNCERTAIN",
            "label": "Assessment is uncertain",
            "notice": uncertainty.get("notice") or validation.get("notice") or "The available input cannot support a confident condition assessment.",
        }
    return {
        "code": "MODEL_UNAVAILABLE",
        "label": "No compatible condition model is available",
        "notice": classifier.get("reason") or validation.get("notice") or "This assessment preserves quality and reported concerns without assigning an unsupported condition.",
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
    assessment_risk = response.get("assessment_risk") or {}
    cdss = response.get("clinical_decision_support") or {}
    segmentation = response.get("segmentation") or {}
    candidate = response.get("candidate_region") or {}
    visual_evidence = response.get("visual_evidence") or {}
    presentation_case = response.get("presentation_case") or {}
    questionnaire = response.get("input_type") == "questionnaire"
    condition = _condition(classifier, intelligence)
    assessment_status = _assessment_status(response, classifier, validation)
    attention = classifier.get("attention_map") or classifier.get("explainability") or {}
    recommendations = response.get("recommendations") or {}

    return {
        "contract_version": ASSESSMENT_RESULT_VERSION,
        "area": response.get("area"),
        "status": assessment_status,
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
        "visual_evidence": {
            "available": bool(visual_evidence.get("available")),
            "affected_area_percent": visual_evidence.get("affected_area_percent"),
            "source": visual_evidence.get("source"),
            "notice": visual_evidence.get("notice") or candidate.get("notice") or candidate.get("message"),
            "scope": "Contrast-based candidate-region evidence only; it is not disease severity, anatomy detection, or segmentation.",
        },
        "disease_risk": {
            "available": False,
            "score": None,
            "level": "NOT_AVAILABLE",
            "source": None,
            "notice": "No validated disease-risk model is configured for this assessment.",
        },
        "assessment_risk": {
            "available": bool(assessment_risk.get("available") and assessment_risk.get("score") is not None),
            "score": assessment_risk.get("score"),
            "level": assessment_risk.get("level") or "NOT_ASSESSED",
            "urgency": assessment_risk.get("urgency"),
            "urgency_label": assessment_risk.get("urgency_label"),
            "factors": assessment_risk.get("factors") or [],
            "factor_labels": assessment_risk.get("factor_labels") or [],
            "explanation": assessment_risk.get("explanation"),
            "methodology": assessment_risk.get("methodology"),
            "methodology_version": assessment_risk.get("methodology_version"),
            "validation_status": assessment_risk.get("validation_status"),
            "notice": assessment_risk.get("label") or "Assessment concern indicator is not a disease probability or diagnosis.",
        },
        "care_priority": {
            "available": priority.get("score") is not None,
            "score": priority.get("score"),
            "level": priority.get("level") or priority.get("severity"),
            "source": "Reported concern details",
            "notice": priority.get("label") or "Reported concern priority is not disease risk or condition likelihood.",
            "version": priority.get("version"),
        },
        "urgency": _urgency(cdss, response.get("urgent_notice"), assessment_risk),
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
        "presentation": {
            "is_reference_case": bool(presentation_case.get("matched")),
            "reference_case_id": presentation_case.get("case_id"),
            "label": presentation_case.get("teaching_label"),
            "matching_method": presentation_case.get("matching_method"),
            "notice": presentation_case.get("notice"),
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
