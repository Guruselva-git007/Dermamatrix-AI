"""Conservative gate for condition compatibility from ordinary photographs.

Current frame statistics have no verified anatomical location or semantic
feature detector. They cannot satisfy a disease/condition profile. Preserve
the gate explicitly so a future measured feature must pass it before any
Possible Concern can be emitted.
"""

from __future__ import annotations


VERSION = "condition-evidence-gate-v1"


def assess_condition_evidence(*, category: str, image_findings: dict,
                              validation: dict) -> dict:
    if category not in {"Skin", "Hair", "Nails"}:
        raise ValueError("Unsupported image category")
    observations = image_findings.get("observations") or []
    # A frame-level metric can be useful image evidence but cannot certify an
    # anatomical or disease feature. Missing evidence is UNKNOWN, not ABSENT.
    localized_semantic = [item for item in observations if item.get("provenance") == "validated_anatomical_detector"]
    return {
        "status": "INSUFFICIENT_MEASURED_EVIDENCE",
        "possible_concerns": [],
        "evidence_strength": None,
        "version": VERSION,
        "reason": "No validated category-specific condition profile can be scored from the available anatomically localized features.",
        "source": "evidence_scope_gate",
        "feature_scope": "FRAME_ONLY" if observations and not localized_semantic else "NO_LOCALIZED_CONDITION_PROFILE",
        "missing_evidence_state": "NOT_MEASURED",
        "domain_verification": validation.get("relevance_status"),
    }
