# Offline ML preparation, calibration, and evaluation

These scripts are deliberately offline-only. They do not download data, train a model, or alter the web application's inference route.

1. `backend/scripts/prepare_dataset_manifest.py` validates a CSV manifest with `patient_id,image_id,split,modality,label`. It rejects a patient assigned to more than one split.
2. Train/export only in a clinician-governed research environment after licence, consent, de-identification, and modality review. No training or export script is bundled because no approved training dataset/model run exists in this repository.
3. `backend/scripts/calibrate_temperature.py` fits temperature scaling on a labelled **validation** CSV of logits, never the training or locked test split. It writes a version-matched calibration artifact.
4. Place an approved artifact outside Git and point `DERMAMATRIX_CALIBRATION_PATH` at it, or use the ignored `backend/models/<model-id>_calibration.json` path. The runtime rejects a wrong model version, class order, method, temperature, or missing dataset/validation provenance.
5. `backend/scripts/evaluate_classifier.py` evaluates a held-out prediction CSV and writes accuracy, balanced accuracy, precision, recall/sensitivity, specificity, F1, AUROC, AUPRC, confusion matrix, Brier score, log loss, and expected calibration error. It labels metrics `NOT_COMPUTABLE` when the held-out labels cannot support a metric.

The scripts cannot establish clinical validity. They create reproducible experiment evidence only after an approved dataset and locked split are supplied.
