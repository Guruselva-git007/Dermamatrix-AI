# ML/data gap report

Audit date: 2026-09-06. This report describes the repository state; it does not claim clinical validation.

| Feature | Status | Evidence / action |
| --- | --- | --- |
| Skin model | Partial | Optional HAM10000 ResNet-34 dermoscopic research adapter exists. This workstation has a Git-ignored local research weight file; source control does not distribute weights. It remains limited to attested dermoscopic single-lesion inputs and has lineage/calibration gates. |
| Hair model | Missing | No governed dataset, weights, evaluation, or inference model. Kept unavailable. |
| Nail model | Missing | No governed dataset, weights, evaluation, or inference model. Kept unavailable. |
| Sweat model | Partial | Transparent questionnaire rules exist; no supervised tabular model. Kept rule-based. |
| Dataset pipeline | Partial | Added a governed SCIN manifest adapter, explicit licence acknowledgement, manifest-bound acquisition, case-group leakage check, and external offline training script. Raw data and artifacts remain out of Git and out of app inference. |
| Image quality | Exists | Resolution, exposure, and edge-variance gate exists; output now has `GOOD`/`ACCEPTABLE`/`LOW_QUALITY` status. |
| Image relevance | Partial | The Health Area Router validates the user-declared body-area context, rejects cross-area inputs, and requires dermoscopic capture attestation before the scoped skin-research route. No trained anatomy/relevance model exists, so declared context is never presented as automatic anatomical verification. |
| Probability calibration | Missing | Added strict temperature-scaling artifact loader; no artifact is supplied, so no condition likelihood is shown. |
| Risk score | Exists, prototype | Reported-concern priority is separate from likelihood and is now versioned/factorized. It is not clinical disease risk. |
| PIRS | Exists, prototype | Preserved and versioned; transparent and not clinically validated. |
| Grad-CAM | Partial | Real Grad-CAM runs only with the optional dermoscopic weight and targets the selected model class. |
| SHAP | Missing by design | No compatible fitted sweat model exists. The rule contribution summary remains explicitly non-SHAP. |
| Model evaluation | Partial | A SCIN feasibility run has a real held-out report but its 0.520243 balanced accuracy on 32 test images causes rejection from app inference. The tooling remains available for future governed runs. |
| Dataset evaluation | Partial | The SCIN manifest is strict-label, case-grouped, and has a locked held-out split. It is not a patient-level or external validation study. |
| Uncertainty handling | Partial | Existing confidence guard was crude. Added calibrated entropy/margin contract; OOD stays `OOD_NOT_EVALUATED` without an actual detector. |
| OOD handling | Missing | No fitted reference distribution/detector is bundled; the app cannot call an image in-domain or OOD. |
| Model versioning | Partial | Skin model version existed; all actual adapters now expose model/dataset/pipeline/calibration lineage in saved metadata. |
| ML metadata | Partial | Added a source-controlled runtime registry without claiming unavailable models are ready. |

## Decision

A governed external SCIN feasibility experiment was executed and deliberately
rejected for application inference. No raw dataset, checkpoint, calibration
artifact, new clinical-photo classifier, hair model, nail model, segmentation
model, XGBoost model, or evaluation artifact is added to the application
repository. Promoting the run without patient-level splits, external
validation, normal/OOD handling, and clinical governance would be misleading.
