#!/usr/bin/env python3
"""Fit a versioned temperature-scaling artifact from an independent validation CSV.

Required CSV columns: patient_id,split,true_label,logit_<class> for each class.
Never run this on the model's training data or a final untouched test set.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys


BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)
from calibration_service import CALIBRATION_SCHEMA_VERSION  # noqa: E402
from ml_evaluation import fit_temperature, validate_patient_level_splits  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validation-csv", required=True)
    parser.add_argument("--classes", required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--model-version", required=True)
    parser.add_argument("--dataset-version", required=True)
    parser.add_argument("--calibration-version", required=True)
    parser.add_argument("--validation-split", default="validation")
    parser.add_argument("--output-json", required=True)
    args = parser.parse_args()
    classes = [value.strip() for value in args.classes.split(",") if value.strip()]
    with open(args.validation_csv, newline="", encoding="utf-8") as file:
        all_rows = list(csv.DictReader(file))
    leakage = validate_patient_level_splits(all_rows)
    if leakage:
        raise SystemExit("Patient-level split leakage detected: " + " | ".join(leakage[:10]))
    rows = [row for row in all_rows if row.get("split", "").lower() == args.validation_split.lower()]
    if not rows:
        raise SystemExit("No validation rows matched the requested split.")
    labels = [classes.index(row["true_label"]) for row in rows]
    logits = [[float(row[f"logit_{class_name}"]) for class_name in classes] for row in rows]
    temperature, metrics = fit_temperature(logits, labels)
    artifact = {
        "schema_version": CALIBRATION_SCHEMA_VERSION,
        "model_id": args.model_id,
        "model_version": args.model_version,
        "dataset_version": args.dataset_version,
        "calibration_version": args.calibration_version,
        "validation_split": args.validation_split,
        "method": "temperature_scaling",
        "temperature": temperature,
        "class_order": classes,
        "metrics": metrics,
    }
    with open(args.output_json, "w", encoding="utf-8") as file:
        json.dump(artifact, file, indent=2)
    print(f"Wrote calibration artifact to {args.output_json}")


if __name__ == "__main__":
    main()
