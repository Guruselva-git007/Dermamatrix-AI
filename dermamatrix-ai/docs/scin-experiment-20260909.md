# SCIN clinical-photo reproducibility run — 2026-09-09

## Decision

**Rejected for application inference.** This is an offline reproducibility run
of a narrow research task, not a condition detector for the DermaMatrix app.
Its model, calibration artifact, source metadata, images, predictions, and
integrity report are held in external research storage and are not reachable by
the Flask application.

## Governed input and integrity audit

- Source: official [Skin Condition Image Network (SCIN)](https://github.com/google-research-datasets/scin) release, under the [SCIN Data Use License](https://github.com/google-research-datasets/scin/blob/main/LICENSE).
- Strict selection: a source condition label had to be gradable, have exactly
  one dermatologist weighted label at least `0.70`, and have an `image_1`.
  The selected taxonomy is only **Eczema (127)** and **Urticaria (85)**. The
  2,371 source differential/multilabel records were not forced into a class;
  1,924 ungradable records and 48 records without a weighted label were also
  excluded.
- Split: 148 train / 32 independent validation / 32 held-out test. It is
  grouped by SCIN case ID. SCIN public case IDs do **not** establish a
  patient-level split.
- Integrity: 212/212 selected images were verified; no download errors, exact
  cross-split duplicates, or dHash pairs at Hamming distance `<= 4` were found.
  Perceptual-hash review is an audit signal, not a label or clinical feature.
- Privacy: the research manifest omits demographic fields, questionnaire data,
  and source free text. They are not model features.

## Reproducible experiment

- Architecture: ImageNet-initialised ResNet-18 with frozen backbone and trained
  two-class head.
- Preprocessing: RGB, resize short edge 256, centre crop 224, ImageNet
  normalisation; training-only horizontal flip and ±5% brightness/contrast.
- Run: four epochs, batch size 16, AdamW `0.001`, fixed seed `20260906`, Apple
  MPS. The model version timestamp is `20260908T184548Z` in UTC.
- Calibration: temperature scaling on the independent validation split only
  (`T=0.925`). Validation log loss changed `0.644813 → 0.644549`, but ECE
  worsened `0.096573 → 0.103335`; calibration is not a deployment artifact.

## Locked held-out result

| Metric | Result |
| --- | ---: |
| Samples | 32 |
| Accuracy | 0.406250 |
| Balanced accuracy | 0.414980 |
| Macro F1 | 0.405670 |
| Macro AUROC (OvR) | 0.437247 |
| Macro AUPRC | 0.491965 |
| Temperature-scaled log loss | 0.850293 |
| Temperature-scaled ECE | 0.266993 |

The result is below the earlier near-chance feasibility run. It therefore
remains rejected. It does not support user-facing disease classification,
probability, medication, treatment, risk, or product advice. It also has no
normal/healthy class, segmentation, open-set/OOD path, patient IDs, external
validation, subgroup analysis, or clinical validation.

## Next valid research step

Use a larger, intended-use-matched clinical-photo dataset with a documented
ground-truth protocol and verified patient-level grouping; pre-specify a normal
or open-set strategy; audit duplicates before model fitting; then perform locked
external and adequately powered subgroup evaluation. Only an independent
governance and clinical review may consider runtime promotion.
