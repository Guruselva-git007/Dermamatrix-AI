#!/usr/bin/env python3
"""Evaluate an offline classifier prediction CSV on a held-out split.

CSV columns: patient_id,split,modality,true_label,score_<class> for each class.
Scores must be probabilities, not logits. The script refuses patient leakage.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys


BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)
from ml_evaluation import multiclass_metrics, validate_patient_level_splits  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions-csv", required=True)
    parser.add_argument("--classes", required=True, help="Comma-separated class codes in score-column order")
    parser.add_argument("--held-out-split", default="test")
    parser.add_argument("--modality", required=True, choices=("DERMOSCOPIC", "CLINICAL_PHOTO", "UNKNOWN"))
    parser.add_argument("--output-json", required=True)
    args = parser.parse_args()
    classes = [value.strip() for value in args.classes.split(",") if value.strip()]
    with open(args.predictions_csv, newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    leakage = validate_patient_level_splits(rows)
    if leakage:
        raise SystemExit("Patient-level split leakage detected: " + " | ".join(leakage[:10]))
    held_out = [row for row in rows if row.get("split", "").lower() == args.held_out_split.lower() and row.get("modality") == args.modality]
    if not held_out:
        raise SystemExit("No held-out rows matched the requested split and modality.")
    labels = []
    probabilities = []
    for row in held_out:
        if row.get("true_label") not in classes:
            raise SystemExit(f"Unsupported label in held-out data: {row.get('true_label')}")
        labels.append(classes.index(row["true_label"]))
        probabilities.append([float(row[f"score_{class_name}"]) for class_name in classes])
    report = {
        "evaluation_status": "OFFLINE_HELD_OUT_EVALUATION",
        "modality": args.modality,
        "held_out_split": args.held_out_split,
        "classes": classes,
        "patient_level_split_check": "PASSED",
        "metrics": multiclass_metrics(labels, probabilities, classes),
        "external_validation": "EXTERNAL_VALIDATION_NOT_AVAILABLE unless this CSV is explicitly an untouched external dataset.",
    }
    with open(args.output_json, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)
    print(f"Wrote held-out evaluation to {args.output_json}")


if __name__ == "__main__":
    main()
