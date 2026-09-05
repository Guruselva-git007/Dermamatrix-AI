#!/usr/bin/env python3
"""Validate a governed dataset manifest before any offline ML experiment.

The input CSV must contain patient_id, image_id, split, modality, and label.
No image is copied, downloaded, or transformed by this script.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter


BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)
from ml_evaluation import validate_patient_level_splits  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest-csv", required=True)
    parser.add_argument("--dataset-name", required=True)
    parser.add_argument("--dataset-version", required=True)
    parser.add_argument("--output-json", required=True)
    args = parser.parse_args()
    with open(args.manifest_csv, newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    required = {"patient_id", "image_id", "split", "modality", "label"}
    missing = required - set(rows[0] if rows else {})
    if missing:
        raise SystemExit("Manifest is missing columns: " + ", ".join(sorted(missing)))
    leakage = validate_patient_level_splits(rows)
    if leakage:
        raise SystemExit("Patient-level split leakage detected: " + " | ".join(leakage[:10]))
    modalities = Counter(row["modality"] for row in rows)
    labels = Counter(row["label"] for row in rows)
    output = {
        "dataset_name": args.dataset_name,
        "dataset_version": args.dataset_version,
        "row_count": len(rows),
        "patient_count": len({row["patient_id"] for row in rows}),
        "modality_counts": modalities,
        "label_counts": labels,
        "patient_level_split_check": "PASSED",
        "notice": "This manifest validates experiment metadata only. It does not establish licence, consent, ground truth quality, clinical validation, or dataset suitability.",
    }
    with open(args.output_json, "w", encoding="utf-8") as file:
        json.dump(output, file, indent=2)
    print(f"Wrote manifest summary to {args.output_json}")


if __name__ == "__main__":
    main()
