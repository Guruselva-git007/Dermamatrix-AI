# Nail research experiment — 2026-09-07

**Decision:** `REJECTED_FOR_APPLICATION_INFERENCE`

This is a reproducible offline feasibility experiment, not a deployed medical
feature. It must not be used to classify user images in DermaMatrix.

## Dataset and governance

- **Source:** Han SS (2017), *Model Onychomycosis Training Datasets (JPG
  thumbnails) and Validation Datasets*, [Figshare v2](https://doi.org/10.6084/m9.figshare.5398573.v2).
- **Licence:** CC BY 4.0.
- **Task:** normal-appearing nail vs nail dystrophy vs onychomycosis, from
  clinical nail-photo thumbnails.
- **Prepared internal data:** 8,904 crops from the A1 source contact sheets:
  6,300 training, 1,254 independent validation, 1,350 internal test.
- **Locked external data:** B1/B2/C/D, 1,358 crops: 578 nail dystrophy and 780
  onychomycosis. No normal-appearing external cohort is provided.
- **Split constraint:** Patient IDs are absent. Internal splitting is grouped
  by source contact sheet to prevent tile leakage; it is not patient-level.
- **Source labels:** A1 image-finding/chart-review labels; validation ground
  truth uses methods documented by the author that vary by cohort (culture,
  KOH, and clinical response among them).
- **Demographics and skin tone:** Not available for this run, so subgroup
  analysis is `INSUFFICIENT_METADATA`.

Raw archives, extracted crops, model weights, calibration artifacts, and
prediction records are stored outside source control.

## Fixed experiment

- **Architecture:** ImageNet-initialised ResNet-18, frozen feature extractor,
  three-class trained head.
- **Input:** RGB 160×160; ImageNet normalization.
- **Run:** 3 epochs, batch size 64, capped 2,000 training images per class,
  fixed seed 20260907.
- **Calibration:** validation-only temperature scaling, `T = 1.375`.
- **OOD research artifact:** nearest-class-centroid cosine distance in the
  penultimate feature space, fitted from the independent validation split.
- **Promotion rule set before measurement:** internal balanced accuracy ≥ 0.70
  **and** locked-external balanced accuracy ≥ 0.65.

## Measured outcome

| Evaluation | Sample count | Balanced accuracy | Macro-F1 | Other |
| --- | ---: | ---: | ---: | --- |
| Internal test | 1,350 | 0.592593 | 0.586892 | AUROC (macro OVR) 0.798295; Brier 0.506715 |
| Locked external test | 1,358 | 0.513777 | 0.344603 | log loss 0.973170; Brier 0.594511 |

Calibration-set log loss moved from 0.915950 to 0.898392 and Brier score from
0.560132 to 0.549389. Calibration improves the scoring representation; it
does not repair insufficient discrimination. Both predeclared promotion
thresholds failed. The external cohort was held out for evaluation and was not
used to tune the model.

## Consequence

The Flask app retains its existing nail-image boundary: no disease label,
likelihood, risk score, medication, or product selection is created from an
ordinary nail image. A future candidate would require a better governed
development dataset with patient-level splits, a complete normal external
cohort, performance that passes a predeclared threshold, calibration and OOD
testing, subgroup evaluation where metadata permits, and clinical governance.
