"""Governed dataset declarations for offline DermaMatrix ML experiments.

Raw datasets live outside the source repository.  A declaration is not an
endorsement for production inference: it records scope, licence and data
limitations so experiment code cannot silently promote a dataset to a clinical
model.
"""

from __future__ import annotations


SCIN_V1 = {
    "dataset_name": "Skin Condition Image Network (SCIN)",
    "dataset_version": "SCIN-public-1.0.0-metadata-2024-03-05",
    "source": "https://github.com/google-research-datasets/scin",
    "data_root": "https://storage.googleapis.com/dx-scin-public-data/dataset/",
    "license": "SCIN Data Use License",
    "license_url": "https://github.com/google-research-datasets/scin/blob/main/LICENSE",
    "task": "Research-only clinical-photo skin-condition classification experiment",
    "health_area": "Skin",
    "body_site": "Multiple self-reported body sites",
    "modality": "CLINICAL_PHOTO",
    "label_schema": "Dermatologist weighted differential labels; strict single-label filtering is required for multiclass experiments.",
    "annotation_type": "Dermatologist condition labels; participant-provided context and demographics; estimated skin tone fields.",
    "quality": "Contains gradability metadata and known duplicate/missing-image caveats documented by the source.",
    "demographics": "Self-reported demographic and history fields are available in source metadata; they must not become model features without a governed protocol.",
    "skin_tone_coverage": "Self-reported Fitzpatrick skin type, dermatologist-estimated Fitzpatrick type, and layperson-estimated Monk skin tone are documented by SCIN.",
    "splits": "No production split is assumed. DermaMatrix creates deterministic case-grouped train/validation/test splits for offline research.",
    "intended_use": "Research and education only. No model trained from this declaration may be promoted automatically to the application inference API.",
    "restrictions": "Retain attribution and licence terms; never attempt re-identification or re-linking; do not commit images or source metadata to Git.",
}


ONYCHOMYCOSIS_FIGSHARE_V2 = {
    "dataset_name": "Model Onychomycosis Training Datasets (JPG thumbnails) and Validation Datasets",
    "dataset_version": "han-onychomycosis-figshare-5398573-v2",
    "source": "https://doi.org/10.6084/m9.figshare.5398573.v2",
    "citation": "Han SS (2017), Figshare dataset 5398573, version 2.",
    "license": "CC BY 4.0",
    "license_url": "https://creativecommons.org/licenses/by/4.0/",
    "task": "Offline research-only clinical nail-photo classification: normal-appearing nail, nail dystrophy, or onychomycosis.",
    "health_area": "Nails",
    "modality": "CLINICAL_NAIL_PHOTO",
    "source_contents": "A1 has 49,567 labelled thumbnail images; A2 has 3,741 labelled thumbnail images; B1/B2/C/D external validation cohorts total 1,358 images. The DermaMatrix run used a capped A1 subset and B1/B2/C/D only.",
    "label_schema": "A1 classes: NormalNail, NailDystrophy, Onychomycosis. The external release contains NailDystrophy and Onychomycosis only; it has no normal-appearing external cohort.",
    "ground_truth": "A1 labels are source image-finding and/or chart-review labels. The author documents culture, KOH, and clinical-response-backed methods across validation cohorts; exact method varies by cohort.",
    "demographics": "Not supplied in the downloaded publication metadata for the prepared run; no demographic or skin-tone performance claim is made.",
    "patient_ids": "Not supplied. Internal records are grouped by source contact sheet to avoid tile leakage, but this is not a patient-level split.",
    "prepared_run": "2026-09-07: 8,904 internal crops (6,300 train / 1,254 validation / 1,350 test) and 1,358 locked external crops. Raw archives, crops, manifests, checkpoints and reports remain outside Git.",
    "intended_use": "Dataset governance and offline feasibility evaluation only. A prepared dataset or experiment cannot promote itself to the application inference API.",
    "limitations": "Contact-sheet thumbnails and unavailable patient IDs constrain generalisation and leakage analysis. It is not a face, hair, skin-lesion, sweat, severity, treatment, or segmentation dataset.",
}


EXCLUDED_DATASETS = {
    "HAM10000": {
        "reason": "Harvard Dataverse terms report CC BY-NC 4.0. It is incompatible with an app that contains affiliate/commerce functionality unless a separate non-commercial research boundary and legal review are established.",
        "source": "https://doi.org/10.7910/DVN/DBW86T",
    },
    "DDI-2": {
        "reason": "Stanford's research-use agreement is non-commercial and requires individual registration; it is not silently acquired or used by the automation.",
        "source": "https://daneshjoulab.github.io/ddi2-dataset/index.html",
    },
    "hair": {
        "reason": "No public, task-matched, governed hair/scalp dataset with sufficient labels and an evaluated model has been selected in this repository. Hair image inference remains unavailable rather than fabricated.",
    },
}


DATASET_REGISTRY = {
    "scin_v1": SCIN_V1,
    "onychomycosis_figshare_v2": ONYCHOMYCOSIS_FIGSHARE_V2,
    "excluded": EXCLUDED_DATASETS,
}


# This record deliberately retains a negative outcome.  It lets future work
# trace the selected source and experiment without making the checkpoint an app
# asset or accidentally treating it as a clinically usable model.
EXPERIMENTS = {
    "scin_clinical_resnet18_20260906": {
        "experiment_id": "scin-clinical-resnet18-experiment-20260906T003738Z",
        "dataset_key": "scin_v1",
        "dataset_selection": "212 clinical photos; one image per SCIN case; strict single weighted dermatologist label >= 0.7; Eczema versus Urticaria only.",
        "split": "148 train / 32 independent validation / 32 held-out test; case-grouped, not claimed patient-grouped.",
        "architecture": "ImageNet-initialised ResNet-18 with a frozen backbone and trained two-class head.",
        "calibration": "Temperature scaling fitted only on the 32-image validation split (T=0.625).",
        "held_out_evaluation": {
            "balanced_accuracy": 0.520243,
            "macro_f1": 0.51952,
            "auroc_ovr_macro": 0.477733,
            "sample_count": 32,
        },
        "decision": "REJECTED_FOR_APPLICATION_INFERENCE",
        "reason": "Small, unstable experiment with near-chance held-out performance; no healthy/normal class, OOD detector, segmentation, external validation, or clinical validation.",
        "artifact_storage": "External research directory only; images, checkpoint, predictions, and calibration artifact are intentionally excluded from Git and from the Flask inference API.",
    },
    "nail_onychomycosis_resnet18_20260907": {
        "experiment_id": "onychomycosis-resnet18-research-20260907T023133Z",
        "dataset_key": "onychomycosis_figshare_v2",
        "dataset_selection": "Capped, contact-sheet-grouped A1 subset: 2,100 train / 450 validation / 450 internal-test per class except validation onychomycosis 354; locked B1/B2/C/D external cohort: 578 nail dystrophy / 780 onychomycosis.",
        "split": "6,300 train / 1,254 independent validation / 1,350 internal test / 1,358 locked external test. Patient IDs unavailable; source-contact-sheet grouping is not a patient-level split.",
        "architecture": "ImageNet-initialised ResNet-18 with a frozen backbone and trained three-class classification head.",
        "calibration": "Temperature scaling fitted only on the independent validation set (T=1.375). Validation log loss improved from 0.915950 to 0.898392; calibration remains research-only.",
        "internal_test": {
            "balanced_accuracy": 0.592593,
            "macro_f1": 0.586892,
            "auroc_ovr_macro": 0.798295,
            "brier_score": 0.506715,
            "sample_count": 1350,
        },
        "external_test": {
            "balanced_accuracy": 0.513777,
            "macro_f1": 0.344603,
            "log_loss": 0.97317,
            "brier_score": 0.594511,
            "sample_count": 1358,
            "normal_class_status": "NOT_AVAILABLE_IN_EXTERNAL_COHORT",
        },
        "promotion_thresholds": "Internal balanced accuracy >= 0.70 and external balanced accuracy >= 0.65, set before the run. The locked external cohort was not used for tuning.",
        "decision": "REJECTED_FOR_APPLICATION_INFERENCE",
        "reason": "Both predefined balanced-accuracy thresholds failed. This prevents a misleading nail-disease or normal-image claim; the model is not loaded by the Flask API.",
        "artifact_storage": "External research directory only; raw data, crops, checkpoint, calibration artifact, OOD reference and evaluation report are intentionally excluded from Git and from live inference.",
    }
}


DATASET_REGISTRY["experiments"] = EXPERIMENTS
