"""Versioned metadata for the ML components that actually exist in this repo.

This is intentionally descriptive, not a catalogue of aspirational models.
Unavailable modalities remain explicitly unavailable until a governed model,
its weights, calibration artifact, and evaluation record are supplied.
"""

from __future__ import annotations

import copy
import os


SKIN_MODEL_ID = "ham10000-resnet34-research"
SKIN_MODEL_VERSION = "Tschandl-2020-resnet34"
SKIN_DATASET_VERSION = "HAM10000-2018-upstream-weight-lineage"
PIPELINE_VERSION = "dermamatrix-inference-v1.2"


MODEL_METADATA = {
    SKIN_MODEL_ID: {
        "model_id": SKIN_MODEL_ID,
        "model_name": "HAM10000 ResNet-34 research adapter",
        "model_version": SKIN_MODEL_VERSION,
        "dataset_version": SKIN_DATASET_VERSION,
        "pipeline_version": PIPELINE_VERSION,
        "task": "multiclass classification",
        "architecture": "ResNet-34",
        "input_modality": "DERMOSCOPIC",
        "input_size": [224, 224],
        "classes": ["akiec", "bcc", "bkl", "df", "mel", "nv", "vasc"],
        "preprocessing": "RGB conversion; resize short edge to 280; centre crop to 224; tensor conversion.",
        "training_data": "Upstream HAM10000/dermatoscopy research weight. The exact training-run manifest is not bundled in this repository.",
        "evaluation": {
            "status": "NOT_AVAILABLE_IN_REPOSITORY",
            "internal_validation": "Not supplied with the upstream weight.",
            "external_validation": "EXTERNAL_VALIDATION_NOT_AVAILABLE",
            "subgroup_evaluation": "NOT_AVAILABLE_IN_REPOSITORY",
        },
        "calibration": {
            "status": "NOT_CONFIGURED",
            "accepted_method": "temperature_scaling",
            "artifact_requirement": "Independent validation-set artifact matching model version and class order.",
        },
        "ood": {
            "status": "NOT_CONFIGURED",
            "notice": "The research adapter has no fitted out-of-distribution detector in this deployment.",
        },
        "limitations": "Research-only dermatoscopic lesion adapter. Not for face/selfie, ordinary clinical photo, hair/scalp, nail, sweat, deficiency, diagnosis, prognosis, or treatment selection.",
    },
    "hair-model-adapter": {
        "model_id": "hair-model-adapter",
        "model_name": "Hair/scalp image-model adapter",
        "status": "NOT_CONFIGURED",
        "task": "not available",
        "limitations": "No governed training data, weights, calibration artifact, or evaluation report is bundled.",
    },
    "nail-model-adapter": {
        "model_id": "nail-model-adapter",
        "model_name": "Nail image-model adapter",
        "status": "NOT_CONFIGURED",
        "task": "not available",
        "limitations": "No governed training data, weights, calibration artifact, or evaluation report is bundled.",
    },
    "scin-clinical-resnet18-experiment": {
        "model_id": "scin-clinical-resnet18-experiment",
        "model_name": "SCIN clinical-photo ResNet-18 experiment",
        "model_version": "scin-clinical-resnet18-experiment-20260906T003738Z",
        "dataset_version": "SCIN-public-1.0.0-strict-single-label",
        "pipeline_version": "scin-clinical-resnet18-v1",
        "status": "REJECTED_FOR_APPLICATION_INFERENCE",
        "task": "two-class experimental clinical-photo classification (Eczema versus Urticaria)",
        "architecture": "ImageNet-initialised ResNet-18 with frozen backbone and trained head",
        "input_modality": "CLINICAL_PHOTO",
        "evaluation": {
            "held_out_sample_count": 32,
            "balanced_accuracy": 0.520243,
            "macro_f1": 0.51952,
            "auroc_ovr_macro": 0.477733,
            "external_validation": "NOT_PERFORMED",
        },
        "calibration": {
            "method": "temperature_scaling",
            "validation_split": "32-image independent validation split",
            "status": "EXPERIMENTAL_ONLY_NOT_RUNTIME_CONFIGURED",
        },
        "limitations": "Rejected from the app because held-out performance is near chance. No normal class, segmentation, OOD detection, patient-level identifier, external validation, or clinical validation. Checkpoint is external and deliberately not loaded by this runtime.",
    },
    "sweat-questionnaire-v1": {
        "model_id": "sweat-questionnaire-v1",
        "model_name": "Sweat questionnaire prioritisation engine",
        "model_version": "questionnaire-v1",
        "pipeline_version": PIPELINE_VERSION,
        "status": "RULE_BASED_PROTOTYPE",
        "task": "questionnaire-based reported-concern prioritisation",
        "calibration": {"status": "NOT_APPLICABLE_NO_SUPERVISED_MODEL"},
        "ood": {"status": "NOT_APPLICABLE_QUESTIONNAIRE"},
        "explainability": "Deterministic input-contribution summary; not SHAP values.",
        "limitations": "Not a validated tabular classifier, diagnosis, prognosis, or XGBoost model.",
    },
}


def model_metadata(model_id: str) -> dict:
    """Return a copy so request-specific readiness never mutates the registry."""
    metadata = copy.deepcopy(MODEL_METADATA[model_id])
    if model_id == SKIN_MODEL_ID:
        metadata["weights_available"] = os.path.isfile(
            os.path.join(os.path.dirname(__file__), "models", "ham10000_resnet34_research.ptw")
        )
    return metadata


def all_model_metadata() -> list[dict]:
    return [model_metadata(model_id) for model_id in MODEL_METADATA]
