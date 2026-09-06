# SCIN clinical-photo feasibility experiment — 2026-09-06

## Decision

**Rejected for application inference.** This offline run exists to prove the
data, split, calibration, and evaluation workflow—not to add a condition
classifier to DermaMatrix AI.

## Governed input

- Dataset: Skin Condition Image Network (SCIN), using the official public
  metadata and image bucket under the [SCIN Data Use License](https://github.com/google-research-datasets/scin/blob/main/LICENSE).
- Selection: 212 images, one `image_1` per SCIN case, exactly one dermatologist
  weighted condition label of at least 0.7. Only Eczema (127) and Urticaria
  (85) were sufficiently represented under this rule.
- Split: 148 train, 32 validation, 32 held-out test. The split is deterministic
  and case-grouped. A SCIN case ID is **not** a verified patient identifier, so
  this must not be described as a patient-level split.
- Storage: images, manifests with paths, checkpoint, calibration artifact, and
  predictions live in an external research directory. None is tracked by Git
  or reachable from the Flask inference API.

## Experiment

- Architecture: ImageNet-initialised ResNet-18, frozen backbone, trained
  two-class head.
- Preprocessing: RGB, resize short edge 256, centre crop 224, ImageNet
  normalisation. Training-only augmentation: horizontal flip and ±5% brightness
  / contrast jitter.
- Run: 8 epochs, batch size 16, AdamW at 0.001, fixed seed 20260906, Apple MPS.
- Calibration: temperature scaling on the independent validation split only;
  temperature 0.625. Validation log loss changed from 0.579909 to 0.567127;
  validation ECE worsened from 0.160752 to 0.206031, another reason this
  artifact cannot be reused as a production calibration claim.

## Locked test outcome

| Metric | Result |
| --- | ---: |
| Samples | 32 |
| Accuracy | 0.531250 |
| Balanced accuracy | 0.520243 |
| Macro F1 | 0.519520 |
| Macro AUROC (OvR) | 0.477733 |
| Macro AUPRC | 0.531115 |
| Test log loss after temperature scaling | 0.890457 |
| Test ECE after temperature scaling | 0.305360 |

The small test set, near-chance discrimination, declining held-out calibration,
absence of normal/healthy and unknown classes, absence of segmentation, and no
external or clinical validation make the run unusable for user-facing
classification or treatment advice.

## Required before a future candidate model

1. A larger, clinician-governed, intended-use-matched clinical-photo dataset
   with patient-level IDs and consent/governance documentation.
2. Locked patient-level splits, duplicate/near-duplicate review, a normal/other
   or open-set strategy, relevance validation, and quality gates.
3. External and subgroup evaluation with adequate samples, then independent
   review of calibration and model failure modes.
4. A separate approval decision before any model is connected to the app.
