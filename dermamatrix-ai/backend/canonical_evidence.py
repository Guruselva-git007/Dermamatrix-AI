"""One provenance-preserving record for a single uploaded image assessment."""

from __future__ import annotations


def component_status(value: dict | None, *, attempted: bool, failed: bool = False) -> str:
    if failed:
        return "failed"
    if not attempted:
        return "not_run"
    return "succeeded" if value and value.get("available", True) else "unavailable"


def build_image_evidence(*, area: str, quality: dict, validation: dict,
                         findings: dict, candidate: dict, segmentation: dict,
                         classifier: dict, reported_context: dict, severity: dict,
                         pirs: dict, assessment_risk: dict, priority: dict,
                         attempted: dict, failed: dict) -> dict:
    """Record only outputs actually produced; unavailable components stay empty."""
    prediction = classifier.get("top_prediction") or {}
    likelihood = classifier.get("condition_likelihood") or {}
    classification_available = bool(classifier.get("available") and prediction.get("condition"))
    ranked_predictions = classifier.get("top_predictions") or [] if classification_available else []
    # Retain reproducible metadata, never overlays or pixel masks in history.
    candidate_metadata = {key: value for key, value in candidate.items() if key not in {"overlay", "mask"}}
    segmentation_metadata = {key: value for key, value in segmentation.items() if key not in {"overlay", "mask"}}
    statuses = {
        "classification": component_status(classifier, attempted=attempted.get("classification", False), failed=failed.get("classification", False)),
        "segmentation": component_status(segmentation, attempted=attempted.get("segmentation", False), failed=failed.get("segmentation", False)),
        "image_processing": component_status(findings, attempted=True, failed=failed.get("image_processing", False)),
        "candidate_region": component_status(candidate, attempted=attempted.get("candidate_region", False), failed=failed.get("candidate_region", False)),
        "severity": component_status(severity, attempted=True, failed=failed.get("severity", False)),
        "pirs": component_status(pirs, attempted=attempted.get("pirs", False), failed=failed.get("pirs", False)),
        "assessment_risk": component_status(assessment_risk, attempted=True, failed=failed.get("assessment_risk", False)),
        "reported_priority": component_status(priority, attempted=True, failed=failed.get("reported_priority", False)),
    }
    if attempted.get("classification") and not failed.get("classification") and not classification_available:
        statuses["classification"] = "unavailable"
    if attempted.get("segmentation") and not failed.get("segmentation") and not segmentation.get("available"):
        statuses["segmentation"] = "unavailable"
    return {
        "version": "image-evidence-v1",
        "category": area,
        "image_quality": quality,
        "validation": validation,
        "classification": {
            "status": statuses["classification"],
            "condition": prediction.get("condition") if classification_available else None,
            "confidence": likelihood.get("estimated_likelihood") if classification_available and likelihood.get("available") else None,
            "probabilities": classifier.get("probabilities") or {} if classification_available else {},
            "ranked_predictions": ranked_predictions,
            "score_kind": "calibrated_likelihood" if likelihood.get("available") else "relative_model_score" if classification_available else None,
            "model_id": classifier.get("model_id") if classification_available else None,
        },
        "visible_findings": findings.get("observations") or [],
        "image_findings": findings,
        "measurements": findings.get("measurements") or {},
        "candidate_region": candidate_metadata,
        "segmentation": segmentation_metadata,
        "reported_context": reported_context,
        "severity": severity,
        "pirs": pirs,
        "assessment_risk": assessment_risk,
        "reported_priority": priority,
        "component_status": statuses,
        "evidence_sources": {
            "image_findings": findings.get("source") if findings.get("available") else None,
            "classification": classifier.get("model_id") if classification_available else None,
            "severity": severity.get("method") if severity.get("level") else None,
            "pirs": pirs.get("version") if pirs.get("score") is not None else None,
        },
        "assessment_type": "RESEARCH_CLASSIFICATION" if classification_available else "IMAGE_FINDINGS" if findings.get("available") else "LIMITED_EVIDENCE",
    }
