# ML/data gap report

Audit date: 2026-09-06. This report describes the repository state; it does not claim clinical validation.

| Feature | Status | Evidence / action |
| --- | --- | --- |
| Skin model | Partial | Optional HAM10000 ResNet-34 dermoscopic research adapter exists; weights are not committed or installed. Retained and given lineage/calibration gates. |
| Hair model | Missing | No governed dataset, weights, evaluation, or inference model. Kept unavailable. |
| Nail model | Missing | No governed dataset, weights, evaluation, or inference model. Kept unavailable. |
| Sweat model | Partial | Transparent questionnaire rules exist; no supervised tabular model. Kept rule-based. |
| Dataset pipeline | Missing | Added manifest validation only; no data download or training run. |
| Image quality | Exists | Resolution, exposure, and edge-variance gate exists; output now has `GOOD`/`ACCEPTABLE`/`LOW_QUALITY` status. |
| Image relevance | Partial | Dermoscopic skin route requires explicit capture attestation; no trained anatomy/relevance model exists. Hair/nail relevance remains unavailable. |
| Probability calibration | Missing | Added strict temperature-scaling artifact loader; no artifact is supplied, so no condition likelihood is shown. |
| Risk score | Exists, prototype | Reported-concern priority is separate from likelihood and is now versioned/factorized. It is not clinical disease risk. |
| PIRS | Exists, prototype | Preserved and versioned; transparent and not clinically validated. |
| Grad-CAM | Partial | Real Grad-CAM runs only with the optional dermoscopic weight and targets the selected model class. |
| SHAP | Missing by design | No compatible fitted sweat model exists. The rule contribution summary remains explicitly non-SHAP. |
| Model evaluation | Missing | Added offline held-out evaluation tooling; no metrics are claimed until governed experiment data are provided. |
| Dataset evaluation | Missing | Added patient-level manifest/split validation; no dataset evaluation has been run. |
| Uncertainty handling | Partial | Existing confidence guard was crude. Added calibrated entropy/margin contract; OOD stays `OOD_NOT_EVALUATED` without an actual detector. |
| OOD handling | Missing | No fitted reference distribution/detector is bundled; the app cannot call an image in-domain or OOD. |
| Model versioning | Partial | Skin model version existed; all actual adapters now expose model/dataset/pipeline/calibration lineage in saved metadata. |
| ML metadata | Partial | Added a source-controlled runtime registry without claiming unavailable models are ready. |

## Decision

No raw dataset, new clinical-photo classifier, hair model, nail model, segmentation model, XGBoost model, calibration artifact, or evaluation result is added in this repository update. Doing so without provenance, licence review, patient-level splits, held-out evaluation, calibration, and intended-use governance would create a misleading medical claim.
