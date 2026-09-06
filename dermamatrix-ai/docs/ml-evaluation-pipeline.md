# Offline ML preparation, calibration, and evaluation

These scripts are deliberately offline-only. They never alter the web
application's inference route or promote an output to the app.

1. `backend/scripts/prepare_dataset_manifest.py` validates a CSV manifest with `patient_id,image_id,split,modality,label`. It rejects a patient assigned to more than one split.
2. `backend/scripts/prepare_scin_clinical_manifest.py` is the governed SCIN adapter. It keeps only a strict single-label subset, uses one image per SCIN case, writes deterministic case-grouped splits, and explicitly labels those IDs as **not verified patient IDs**.
3. `backend/scripts/acquire_scin_images.py` downloads only manifest-selected images after an explicit `--accept-scin-license` acknowledgement. Its target must be outside Git.
4. `backend/scripts/train_scin_clinical_experiment.py` trains an offline, checkpoint-only ResNet-18 experiment, fits temperature scaling on validation logits, and produces a held-out report. It writes `EXPERIMENTAL_NOT_DEPLOYABLE` artifacts and has no Flask import path.
5. `backend/scripts/calibrate_temperature.py` fits temperature scaling on a labelled **validation** CSV of logits, never the training or locked test split. It writes a version-matched calibration artifact.
6. Place an approved artifact outside Git and point `DERMAMATRIX_CALIBRATION_PATH` at it, or use the ignored `backend/models/<model-id>_calibration.json` path. The runtime rejects a wrong model version, class order, method, temperature, or missing dataset/validation provenance.
7. `backend/scripts/evaluate_classifier.py` evaluates a held-out prediction CSV and writes accuracy, balanced accuracy, precision, recall/sensitivity, specificity, F1, AUROC, AUPRC, confusion matrix, Brier score, log loss, and expected calibration error. It labels metrics `NOT_COMPUTABLE` when the held-out labels cannot support a metric.

The scripts cannot establish clinical validity. They create reproducible experiment evidence only after an approved dataset and locked split are supplied.
