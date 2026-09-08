# DermaMatrix research datasets

This file records governed research sources. It does not make a source a
runtime model, clinical validation, or a user-data source.

## SCIN — Skin Condition Image Network

- **Official source:** [Google Research SCIN repository](https://github.com/google-research-datasets/scin)
- **Schema:** [official dataset schema](https://github.com/google-research-datasets/scin/blob/main/dataset_schema.md)
- **License:** [SCIN Data Use License](https://github.com/google-research-datasets/scin/blob/main/LICENSE), reviewed for the September 2026 governed run. Follow the current source terms and retain any required attribution before each access.
- **Local handling:** raw images, metadata, manifests with source paths,
  checkpoints, calibration artifacts, predictions, and integrity reports stay
  outside Git. Never attempt to identify, re-identify, or re-link contributors.
- **Scoped run:** 212 gradable clinical photographs from 212 SCIN cases, one
  `image_1` per case. It includes only strict single-label Eczema (127) and
  Urticaria (85) records with a weighted dermatologist label of at least 0.70.
  The run excludes 1,924 ungradable and 2,371 differential/multilabel records
  from its hard-label objective; 48 records without a weighted label are also
  excluded. These exclusions do not make any case healthy or normal.
- **Split:** deterministic 148 train / 32 validation / 32 held-out test,
  grouped by SCIN case ID. Public SCIN case IDs are not verified patient IDs.
- **Integrity:** exact SHA-256 and dHash are computed after acquisition. Exact
  and thresholded near-duplicate matches across splits block training; the
  audit must complete before a run can start.
- **Outcome:** the latest ResNet-18 feasibility run is rejected from the app:
  held-out balanced accuracy 0.414980, macro F1 0.405670, and AUROC 0.437247
  on 32 test images. See [the run report](docs/scin-experiment-20260909.md).

SCIN is currently the only declared clinical-photo skin research source in the
external pipeline. It does not supply a deployed Hair, Nail, Sweat, normal,
severity, or disease-risk model for DermaMatrix.

## Other sources

The source-by-source status, restrictions, and task mapping are maintained in
[docs/dataset-registry.md](docs/dataset-registry.md). The tracked
[`dataset_registry.json`](dataset_registry.json) is a compact, machine-readable
layout declaration. It must agree with the backend governance registry before a
new source is prepared.
