# Research-asset roots audit — 2026-09-23

## Scope

This audit separates the four user-provided local roots by role. It does not
merge them, retrain a model, or change application inference. A folder with
images is not automatically a compatible or licensed training cohort.

| Root | Observed role | Training / application decision |
| --- | --- | --- |
| `dermamatrix-ai/` | Application source, tests, safety contract, and the existing narrowly scoped runtime adapter | Not a dataset. No raw images or new weights are added to Git. |
| `legacy-recovery/` | Recovery copies of code, environment state, and local database materials | Not a dataset; excluded from all data manifests and training. |
| `local-artifacts/` | PDF reference and presentation material | Not a dataset; excluded from all data manifests and training. |
| `research-assets/` | External raw sources, extracted datasets, and derived experiment artifacts | Read-only research storage. Each source needs its own licence, target, grouping, duplicate, split, evaluation, and promotion review. |

The repeatable, read-only inventory tool is
`backend/scripts/audit_research_asset_roots.py`. It counts files and reads ZIP
central directories only; it never extracts, decodes, copies, hashes, trains
on, or promotes source material. Its JSON output must remain outside Git.

## Evidence-based source decisions

| Source inside `research-assets` | Evidence | Decision |
| --- | --- | --- |
| `new datasets/archive (1)/dataset` | 1,403 three-class dermoscopy images. Exact SHA-256 split collisions were excluded and a ResNet-18 experiment was run with a locked 363-image test. | Candidate achieved 0.728377 macro F1 but is **rejected for app inference**: source licence/provenance, patient/case grouping, near-duplicate control, external validation, clinical validation, and compatibility with the live seven-class contract are absent. See [three-class record](three-class-dermoscopy-experiment-20260923.md). |
| `new datasets/` other extracted sources | 42 other extracted directories include mixed skin/hair/nail modalities, segmentation masks, broad labels, missing splits, unknown provenance, and known duplicate leakage. | Not combined or trained as one classifier. Detailed inventory is in [the local dataset audit](local-dataset-audit-20260923.md). |
| `original-sources/kaggle/` | 38,760 broad clinical-image records; 2,761 exact-duplicate groups cross its supplied train/validation/test partitions. | Excluded; its evaluation split is not credible. |
| `original-sources/archive.zip` | 36,656 images mixing dermoscopy and ordinary clinical infection images. A seven-class dermoscopic subset was exact-hash grouped for an earlier ResNet-18 comparison. | Candidate underperformed the retained ResNet-34 (0.546283 versus 0.560303 balanced accuracy) and lacks a deployable source licence / patient IDs. It remains rejected. See [archive record](skin-lesion-zip-experiment-20260922.md). |
| `original-sources/train_a1.zip`, `train_a2.zip`, `external_validation.zip` | Han Figshare nail source. The controlled three-class run used contact-sheet grouping and a locked 1,358-image external cohort. | Rejected: 0.592593 internal and 0.513777 external balanced accuracy, below predeclared thresholds. Nail inference stays unavailable. |
| `original-sources/DermamatrixResearchData/scin-v1` | Official SCIN two-class, case-grouped feasibility experiment with duplicate/near-duplicate audit. Held-out balanced accuracy was 0.414980 in the stricter repeat. | Rejected; no clinical-photo condition classifier is loaded. |
| `original-sources/archive (2)/SkinDisease/` and local CSV/notebook material | Test-only images or records without usable image/provenance/split information. | Not trainable as supplied. |
| `training-runs/` | Derived checkpoints, metrics, calibration, and manifests from experiments. | Never a source dataset and never a promotion signal by itself. |

## Current application state

The app has been tested without weakening its scope. The retained optional
HAM10000 ResNet-34 is still limited to an attested dermatoscopic single-lesion
research route; the prior held-out comparison recorded 0.560303 balanced
accuracy and 0.506399 macro F1, not clinical validation. Hair, nail, and
general clinical-photo image classifiers remain unavailable. The shared
upload-quality, reported-concern, guidance, history, and clinician-handoff
workflow remains available for every supported health area without pretending
that a rejected or incompatible model can classify it.

Before any new model can change the app, a source must pass documented
provenance/licence review, task and modality matching, patient/case grouping,
exact and near-duplicate controls, fixed validation/test protocol,
calibration, external evaluation, subgroup review, clinical review, and
runtime-contract compatibility. The registry's default policy blocks
undeclared datasets from manifest preparation.
