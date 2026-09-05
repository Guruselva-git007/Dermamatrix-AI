"""Offline-only evaluation helpers for governed classifier experiments.

These helpers are not imported by the web application. They make a future
research run reproducible without implying that the bundled research adapter
has been evaluated, calibrated, or clinically validated.
"""

from __future__ import annotations

import math
from typing import Sequence

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_recall_fscore_support,
    roc_auc_score,
)


def softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - logits.max(axis=1, keepdims=True)
    values = np.exp(shifted)
    return values / values.sum(axis=1, keepdims=True)


def validate_patient_level_splits(rows: Sequence[dict]) -> list[str]:
    """Return leakage errors when a patient appears in more than one split."""
    locations: dict[str, set[str]] = {}
    for row in rows:
        patient_id = str(row.get("patient_id", "")).strip()
        split = str(row.get("split", "")).strip().lower()
        if not patient_id or not split:
            continue
        locations.setdefault(patient_id, set()).add(split)
    return [f"Patient {patient_id} appears in multiple splits: {', '.join(sorted(splits))}" for patient_id, splits in locations.items() if len(splits) > 1]


def expected_calibration_error(probabilities: np.ndarray, labels: np.ndarray, bins: int = 15) -> float:
    confidences = probabilities.max(axis=1)
    predictions = probabilities.argmax(axis=1)
    correct = predictions == labels
    ece = 0.0
    for start in np.linspace(0, 1, bins, endpoint=False):
        end = start + (1 / bins)
        in_bin = (confidences >= start) & (confidences < end if end < 1 else confidences <= end)
        if not np.any(in_bin):
            continue
        ece += float(np.mean(in_bin)) * abs(float(np.mean(correct[in_bin])) - float(np.mean(confidences[in_bin])))
    return ece


def multiclass_metrics(labels: Sequence[int], probabilities: Sequence[Sequence[float]], class_names: Sequence[str]) -> dict:
    """Compute classification and calibration metrics from held-out predictions."""
    y_true = np.asarray(labels, dtype=int)
    y_score = np.asarray(probabilities, dtype=float)
    if y_score.ndim != 2 or y_score.shape[1] != len(class_names) or len(y_true) != len(y_score):
        raise ValueError("Prediction matrix dimensions do not match labels and class names.")
    if len(y_true) == 0:
        raise ValueError("At least one held-out prediction is required.")
    if np.any(y_score < 0) or not np.allclose(y_score.sum(axis=1), 1.0, atol=1e-5):
        raise ValueError("Scores must be non-negative probabilities summing to one per row.")
    y_pred = y_score.argmax(axis=1)
    labels_range = list(range(len(class_names)))
    precision, recall, f1, support = precision_recall_fscore_support(y_true, y_pred, labels=labels_range, zero_division=0)
    matrix = confusion_matrix(y_true, y_pred, labels=labels_range)
    per_class = {}
    total = int(matrix.sum())
    for index, class_name in enumerate(class_names):
        true_positive = int(matrix[index, index])
        false_negative = int(matrix[index, :].sum() - true_positive)
        false_positive = int(matrix[:, index].sum() - true_positive)
        true_negative = total - true_positive - false_negative - false_positive
        specificity = true_negative / (true_negative + false_positive) if true_negative + false_positive else None
        per_class[class_name] = {
            "precision": round(float(precision[index]), 6),
            "recall_sensitivity": round(float(recall[index]), 6),
            "specificity": round(float(specificity), 6) if specificity is not None else "NOT_COMPUTABLE",
            "f1": round(float(f1[index]), 6),
            "support": int(support[index]),
        }
    one_hot = np.eye(len(class_names))[y_true]
    try:
        auroc = float(roc_auc_score(one_hot, y_score, multi_class="ovr", average="macro"))
    except ValueError:
        auroc = None
    try:
        auprc = float(average_precision_score(one_hot, y_score, average="macro"))
    except ValueError:
        auprc = None
    brier = float(np.mean(np.sum((one_hot - y_score) ** 2, axis=1)))
    return {
        "sample_count": int(len(y_true)),
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 6),
        "balanced_accuracy": round(float(balanced_accuracy_score(y_true, y_pred)), 6),
        "macro_precision": round(float(np.mean(precision)), 6),
        "macro_recall_sensitivity": round(float(np.mean(recall)), 6),
        "macro_f1": round(float(f1_score(y_true, y_pred, average="macro", zero_division=0)), 6),
        "auroc_ovr_macro": round(auroc, 6) if auroc is not None else "NOT_COMPUTABLE",
        "auprc_macro": round(auprc, 6) if auprc is not None else "NOT_COMPUTABLE",
        "log_loss": round(float(log_loss(y_true, y_score, labels=labels_range)), 6),
        "multiclass_brier_score": round(brier, 6),
        "expected_calibration_error": round(expected_calibration_error(y_score, y_true), 6),
        "confusion_matrix": matrix.tolist(),
        "per_class": per_class,
    }


def fit_temperature(logits: Sequence[Sequence[float]], labels: Sequence[int]) -> tuple[float, dict]:
    """Fit temperature scaling by validation-set log loss, without test leakage."""
    raw_logits = np.asarray(logits, dtype=float)
    y_true = np.asarray(labels, dtype=int)
    if raw_logits.ndim != 2 or len(raw_logits) != len(y_true) or len(y_true) < 2:
        raise ValueError("A labelled, independent validation set of logits is required.")
    if np.any(y_true < 0) or np.any(y_true >= raw_logits.shape[1]):
        raise ValueError("Labels do not match the logit class dimension.")
    candidates = np.linspace(0.25, 5.0, 191)
    losses = [log_loss(y_true, softmax(raw_logits / temperature), labels=list(range(raw_logits.shape[1]))) for temperature in candidates]
    best_index = int(np.argmin(losses))
    temperature = float(candidates[best_index])
    before = softmax(raw_logits)
    after = softmax(raw_logits / temperature)
    return temperature, {
        "validation_sample_count": int(len(y_true)),
        "log_loss_before": round(float(log_loss(y_true, before, labels=list(range(raw_logits.shape[1])))), 6),
        "log_loss_after": round(float(log_loss(y_true, after, labels=list(range(raw_logits.shape[1])))), 6),
        "brier_before": round(float(np.mean(np.sum((np.eye(raw_logits.shape[1])[y_true] - before) ** 2, axis=1))), 6),
        "brier_after": round(float(np.mean(np.sum((np.eye(raw_logits.shape[1])[y_true] - after) ** 2, axis=1))), 6),
        "ece_before": round(expected_calibration_error(before, y_true), 6),
        "ece_after": round(expected_calibration_error(after, y_true), 6),
        "temperature": round(temperature, 6),
    }
