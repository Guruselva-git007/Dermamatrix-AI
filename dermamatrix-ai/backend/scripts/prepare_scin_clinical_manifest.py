#!/usr/bin/env python3
"""Write a governed, strict SCIN manifest for an offline experiment.

This script only prepares a manifest. It never downloads data, trains a
model, or enables application inference.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
from scin_pipeline import DEFAULT_CLASSES, build_strict_manifest  # noqa: E402


def load_taxonomy(path: str | None) -> tuple[dict[str, dict[str, str]] | None, str]:
    if not path:
        return None, "source-labels-unmapped"
    with Path(path).open(encoding="utf-8") as file:
        document = json.load(file)
    mappings = document.get("mappings") if isinstance(document, dict) else None
    if not isinstance(mappings, list):
        raise ValueError("Taxonomy JSON must contain a mappings array.")
    result: dict[str, dict[str, str]] = {}
    for mapping in mappings:
        if not isinstance(mapping, dict):
            continue
        source_label = str(mapping.get("source_label", "")).strip()
        if source_label:
            result[source_label] = mapping
    return result, str(document.get("taxonomy_version", "unversioned-taxonomy"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases-csv", required=True)
    parser.add_argument("--labels-csv", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--summary-json", required=True)
    parser.add_argument("--classes", default=",".join(DEFAULT_CLASSES), help="Exact SCIN labels for one scoped experiment.")
    parser.add_argument("--image-slots", default="image_1", help="Comma-separated subset of image_1,image_2,image_3. Case grouping is preserved.")
    parser.add_argument("--seed", type=int, default=20260906)
    parser.add_argument("--minimum-class-cases", type=int, default=20)
    parser.add_argument("--minimum-label-weight", type=float, default=0.70)
    parser.add_argument("--taxonomy-json", help="Optional explicit SCIN-source to DermaMatrix canonical mapping.")
    args = parser.parse_args()
    try:
        taxonomy, taxonomy_version = load_taxonomy(args.taxonomy_json)
        rows, summary = build_strict_manifest(
            args.cases_csv,
            args.labels_csv,
            (value.strip() for value in args.classes.split(",")),
            seed=args.seed,
            minimum_class_cases=args.minimum_class_cases,
            minimum_label_weight=args.minimum_label_weight,
            image_slots=(value.strip() for value in args.image_slots.split(",")),
            taxonomy=taxonomy,
            taxonomy_version=taxonomy_version,
        )
    except ValueError as error:
        raise SystemExit(str(error)) from error

    output = Path(args.output_csv); output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    summary_path = Path(args.summary_json); summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
