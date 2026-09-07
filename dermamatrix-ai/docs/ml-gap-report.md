# ML/data gap report

Audit date: 2026-09-06. This report describes the repository state; it does not claim clinical validation.

| Feature | Status | Evidence / action |
| --- | --- | --- |
| Skin model | Partial | Optional HAM10000 ResNet-34 dermoscopic research adapter exists. This workstation has a Git-ignored local research weight file; source control does not distribute weights. It remains limited to attested dermoscopic single-lesion inputs and has lineage/calibration gates. |
| Hair model | Missing | No governed dataset, weights, evaluation, or inference model. Kept unavailable. |
| Nail model | Partial, rejected | A governed Figshare onychomycosis feasibility pipeline and a measured ResNet-18 experiment now exist. Its 0.592593 internal and 0.513777 locked-external balanced accuracies miss the predeclared promotion thresholds, so nail inference remains unavailable in the app. |
| Sweat model | Partial | Transparent questionnaire rules exist; no supervised tabular model. Kept rule-based. |
| Dataset pipeline | Partial | The SCIN adapter remains available. A separate governed Figshare nail preparation script now extracts source contact-sheet tiles into deterministic contact-sheet-grouped internal splits plus a locked external cohort. Raw data and artifacts remain out of Git and out of app inference. |
| Image quality | Exists | Resolution, exposure, and edge-variance gate exists; output now has `GOOD`/`ACCEPTABLE`/`LOW_QUALITY` status. |
| Image relevance | Partial | The Health Area Router validates the user-declared body-area context, rejects cross-area inputs, and requires dermoscopic capture attestation before the scoped skin-research route. No trained anatomy/relevance model exists, so declared context is never presented as automatic anatomical verification. |
| Probability calibration | Partial | The runtime has a strict version-matched temperature-scaling artifact loader; no accepted artifact is supplied to the app. The rejected nail experiment fitted temperature scaling on an independent validation split only, but it is not exposed at runtime. |
| Risk score | Exists, prototype | Reported-concern priority is separate from likelihood and is now versioned/factorized. It is not clinical disease risk. |
| PIRS | Exists, prototype | Preserved and versioned; transparent and not clinically validated. |
| Grad-CAM | Partial | Real Grad-CAM runs only with the optional dermoscopic weight and targets the selected model class. |
| SHAP | Missing by design | No compatible fitted sweat model exists. The rule contribution summary remains explicitly non-SHAP. |
| Model evaluation | Partial | The SCIN feasibility run was rejected at 0.520243 balanced accuracy on 32 test images. A nail ResNet-18 run was rejected at 0.592593 internal / 0.513777 locked-external balanced accuracy. The tooling remains available for future governed runs. |
| Dataset evaluation | Partial | The SCIN manifest is strict-label and case-grouped. The nail data are contact-sheet grouped internally and have a locked B1/B2/C/D external evaluation, but neither provides patient-level identifiers and the external nail cohort lacks a normal class. |
| Uncertainty handling | Partial | Existing confidence guard was crude. Added calibrated entropy/margin contract; OOD stays `OOD_NOT_EVALUATED` without an actual detector. |
| OOD handling | Missing | No fitted reference distribution/detector is bundled; the app cannot call an image in-domain or OOD. |
| Model versioning | Partial | Skin model version existed; all actual adapters now expose model/dataset/pipeline/calibration lineage in saved metadata. |
| ML metadata | Partial | Added a source-controlled runtime registry without claiming unavailable models are ready. |
| Normalized result contract | Exists | `assessment-result-v1` now persists one patient-safe result object for the UI, saved history, and PDFs. It separates calibrated condition likelihood (only when an artifact exists), self-reported symptom severity, reported-concern care priority, urgency routing, and unavailable disease risk. |

## Decision

Two governed feasibility experiments were executed and deliberately rejected
for application inference: SCIN clinical photos and the Han (2017) Figshare
nail-photo release. No raw dataset, checkpoint, calibration artifact, new
clinical-photo classifier, hair model, accepted nail model, segmentation
model, XGBoost model, or evaluation artifact is added to the application
repository. Promoting either run without acceptable measured performance,
patient-level splits, complete external validation, normal/OOD handling, and
clinical governance would be misleading.

## Current capability boundary

The running application does not convert a general face, skin, hair, or nail
photo into a disease classification. It preserves input-quality/context support
and general next steps for those routes. The bundled research adapter can run
only for an explicitly attested dermatoscopic single-lesion image, and it still
remains research-only. Sweat concerns remain questionnaire-only. A disease-risk
score remains unavailable until a validated, governed risk model is integrated;
reported concern priority is retained separately for care-routing purposes.
