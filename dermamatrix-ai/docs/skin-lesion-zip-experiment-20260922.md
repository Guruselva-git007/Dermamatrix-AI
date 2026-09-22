# Local skin-lesion archive audit and retained-model comparison — 2026-09-22

## Scope and source handling

This is an offline research experiment over the user-provided local image
source. The source was read-only throughout: no supplied image, archive, or
CSV was renamed, overwritten, or placed in Git. Derived RGB image caches and
candidate checkpoints are external, non-Git research artifacts. The committed
records contain only aggregate metrics, hashes, file-independent manifest
metadata, and visual evaluation artifacts.

## Dataset inventory and decisions

| Local source | Inventory | Decision |
| --- | ---: | --- |
| `kaggle/` image folders | 38,760 images, six broad labels | Not used. Exact-duplicate analysis found 2,761 duplicate groups crossing the supplied train/validation/test structure (5,855 files); its split is not credible for model evaluation. |
| `archive.zip` | 36,656 images, 14 labels | Used for a strictly limited seven-label dermoscopic-style research comparison only. The source had 319 exact-duplicate groups crossing splits (641 files) and one conflicting-label hash group, so exact-hash grouping and collision exclusions were applied before fitting/evaluation. |
| `archive (2)/SkinDisease/` | 828 images, 10-class test partition only | Not trainable as supplied: no training/validation partition or usable provenance record. |
| `skin_defects.csv` | 30 tabular rows referencing unavailable acne images | Not usable for image training. |
| `dermatology_database_1.csv` and duplicate | 366 tabular rows each | Supporting tabular material only, not image-classification training data. |

The selected archive mapping is intentionally only `akiec`, `bcc`, `bkl`,
`df`, `mel`, `nv`, and `vasc`, matching the existing HAM10000 adapter. The
seven non-dermoscopic or out-of-scope source labels were excluded. The
prepared collection contains 24,651 source records after exact-hash grouping;
the test set has 2,475 images and validation has 2,466. Two conflicting-label
hash groups were excluded. Exact hash isolation passed, but the source has no
patient/case identifiers and no near-duplicate guarantee, so this is not a
patient-level split or a clinical-validation claim.

The archive README cites component datasets but this local copy does not
provide a deployable ML licence record. That, the missing case IDs,
near-duplicate uncertainty, lack of external/prospective validation, and lack
of clinical validation are hard promotion blockers.

## Reproducible evaluation

`backend/scripts/run_skin_lesion_experiment.py` reconstructs the prepared
collection deterministically (seed `20260922`), validates exact-hash split
isolation, caches only derived images outside Git, trains an optional
ImageNet-initialised ResNet-18 research candidate, fits temperature scaling on
validation only, and writes predictions, metrics, plots, difficult cases, and
a promotion decision. It cannot modify Flask routing or promote a checkpoint.

`backend/scripts/evaluate_existing_lesion_baseline.py` evaluates the active
runtime ResNet-34 with the same RGB / resize-short-edge-280 / centre-crop-224
preprocessing used by the app. Both reports are linked below.

| Model | Held-out accuracy | Balanced accuracy | Macro F1 | Calibration | Decision |
| --- | ---: | ---: | ---: | --- | --- |
| Active HAM10000 ResNet-34 research runtime | 0.691313 | 0.560303 | 0.506399 | Not configured; raw ranking only | Retained as the existing runtime research model; not clinically validated. |
| ResNet-18 archive candidate (2 epochs; balanced cap 800/class) | 0.560000 | 0.546283 | 0.441332 | Temperature 0.9 fitted on validation; held-out ECE 0.039306 | `RESEARCH_ONLY_CANDIDATE_NOT_AUTO_PROMOTED`; it underperformed the retained model on Macro F1 and balanced accuracy. |

The ResNet-18 candidate checkpoint and calibration JSON remain outside the
repository and are not referenced by Flask. No application inference model was
replaced. The active ResNet-34 scores must continue to be presented as an
uncalibrated research ranking, never as diagnostic probability.

## Segmentation and explainability

No dataset supplied masks or annotations suitable for lesion segmentation, and
no segmentation model was trained or integrated. The app's Grad-CAM is an
attention visualisation. Its candidate-region display is explicitly visual-only
and reports `model_not_configured` for segmentation; it is not a lesion mask,
area measurement, or medical finding.

## Artifacts and presentation

- [Dataset audit](../results/skin-lesion-zip-v1/dataset_audit.json), [candidate held-out report](../results/skin-lesion-zip-v1/evaluation_report.json), and [retained-model baseline](../results/skin-lesion-zip-v1/existing_resnet34_baseline.json) are the authoritative metric records.
- [Candidate confusion matrix](../results/skin-lesion-zip-v1/test_confusion_matrix.png), [retained-model confusion matrix](../results/skin-lesion-zip-v1/existing_resnet34_baseline_confusion_matrix.png), and [training curves](../results/skin-lesion-zip-v1/training_curves.png) are generated from the actual runs.
- Start the app with `bash backend/scripts/run_app.sh`. For a safe demonstration of the model route, select **Skin**, choose **dermoscopic lesion**, upload one full-resolution dermoscopic lesion image, and complete the dermoscopy attestation. A normal clinical photo, hair/scalp, nail, or sweat flow must not receive a lesion label.

This experiment is a reproducible negative promotion decision, not a medical
device performance claim.
