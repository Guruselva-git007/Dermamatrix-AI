#!/usr/bin/env python3
"""Create a deterministic, case-grouped SCIN clinical-photo experiment manifest.

It uses a strict single-label subset only.  SCIN exposes contribution/case
identifiers rather than verified longitudinal patient identifiers, so the
result is case-grouped—not claimed as patient-level splitting.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

from sklearn.model_selection import train_test_split


DEFAULT_CLASSES = ("Eczema", "Urticaria")
IMAGE_BASE_URL = "https://storage.googleapis.com/dx-scin-public-data/"


def stable_id(case_id: str, path: str) -> str:
    return hashlib.sha256(f"{case_id}|{path}".encode("utf-8")).hexdigest()[:24]


def parse_weighted_label(value: str) -> dict:
    try:
        parsed = ast.literal_eval(value or "{}")
    except (ValueError, SyntaxError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases-csv", required=True)
    parser.add_argument("--labels-csv", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--summary-json", required=True)
    parser.add_argument("--classes", default=",".join(DEFAULT_CLASSES), help="Strict, exact SCIN weighted labels.")
    parser.add_argument("--seed", type=int, default=20260906)
    parser.add_argument("--minimum-class-cases", type=int, default=20)
    args = parser.parse_args()
    classes = tuple(value.strip() for value in args.classes.split(",") if value.strip())
    if len(classes) < 2:
        raise SystemExit("Choose at least two classes for a multiclass experiment.")

    with open(args.cases_csv, encoding="utf-8", newline="") as file:
        cases = {row["case_id"]: row for row in csv.DictReader(file)}
    selected = []
    with open(args.labels_csv, encoding="utf-8", newline="") as file:
        for label_row in csv.DictReader(file):
            case = cases.get(label_row.get("case_id", ""))
            weights = parse_weighted_label(label_row.get("weighted_skin_condition_label", ""))
            if not case or len(weights) != 1:
                continue
            label, confidence = next(iter(weights.items()))
            image_path = str(case.get("image_1_path", "")).strip()
            if label not in classes or not image_path or not isinstance(confidence, (int, float)) or confidence < 0.7:
                continue
            selected.append({
                "image_id": stable_id(label_row["case_id"], image_path),
                "group_id": label_row["case_id"],
                "group_id_type": "SCIN_CASE_ID_NOT_VERIFIED_PATIENT_ID",
                "label": label,
                "source_dataset": "SCIN-public-1.0.0",
                "modality": "CLINICAL_PHOTO",
                "image_url": IMAGE_BASE_URL + image_path,
                "body_site": "self-reported source metadata retained outside manifest",
                "annotation": "single weighted dermatologist label >= 0.7",
            })
    counts = Counter(row["label"] for row in selected)
    insufficient = [label for label in classes if counts[label] < args.minimum_class_cases]
    if insufficient:
        raise SystemExit(f"Insufficient strict single-label cases for: {', '.join(insufficient)}. Counts: {dict(counts)}")

    labels = [row["label"] for row in selected]
    train_rows, held_rows = train_test_split(selected, test_size=0.30, random_state=args.seed, stratify=labels)
    held_labels = [row["label"] for row in held_rows]
    validation_rows, test_rows = train_test_split(held_rows, test_size=0.50, random_state=args.seed, stratify=held_labels)
    for split, rows in (("train", train_rows), ("validation", validation_rows), ("test", test_rows)):
        for row in rows:
            row["split"] = split
    rows = sorted(train_rows + validation_rows + test_rows, key=lambda item: (item["split"], item["label"], item["image_id"]))
    output_path = Path(args.output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    summary = {
        "dataset": "SCIN-public-1.0.0",
        "task": "Experimental clinical-photo skin classification",
        "classes": list(classes),
        "case_count": len(rows),
        "split_counts": {split: sum(row["split"] == split for row in rows) for split in ("train", "validation", "test")},
        "label_counts": dict(Counter(row["label"] for row in rows)),
        "split_label_counts": {split: dict(Counter(row["label"] for row in rows if row["split"] == split)) for split in ("train", "validation", "test")},
        "grouping": "SCIN case ID. SCIN does not expose verified patient IDs in this manifest; no patient-level leakage claim is made.",
        "selection": "One image_1 per case; exactly one weighted dermatologist label; weight >= 0.7; no multilabel/differential cases.",
        "status": "EXPERIMENTAL_MANIFEST_ONLY",
    }
    with open(args.summary_json, "w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
