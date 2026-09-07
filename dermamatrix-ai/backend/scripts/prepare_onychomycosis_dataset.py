#!/usr/bin/env python3
"""Prepare a governed nail-image research dataset outside the source repo.

The Figshare release by Han (2017), DOI 10.6084/m9.figshare.5398573.v2,
stores A1 training thumbnails as labelled contact sheets.  This utility splits
those sheets into their original tiles, creates deterministic *sheet-grouped*
internal splits, and separately extracts the B1/B2/C/D validation cohorts.

It deliberately does not claim patient-level splitting: the release does not
provide patient identifiers.  Raw images, crops, manifests and experiments
must remain in a research-data directory that is not committed to Git.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import shutil
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image


DATASET_ID = "han-onychomycosis-figshare-5398573-v2"
DATASET_DOI = "https://doi.org/10.6084/m9.figshare.5398573.v2"
DATASET_LICENSE = "CC BY 4.0"
CLASSES = ("normal_appearing_nail", "nail_dystrophy", "onychomycosis")
SHEET_LABELS = {
    "normalnail": "normal_appearing_nail",
    "naildystrophy": "nail_dystrophy",
    "onychomycosis": "onychomycosis",
}


def stable_id(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", "replace")).hexdigest()[:24]


def sheet_label(name: str) -> str | None:
    lowered = name.casefold().replace("_", "")
    matched = [label for token, label in SHEET_LABELS.items() if token in lowered]
    return matched[0] if len(set(matched)) == 1 else None


def white_runs(values: np.ndarray, minimum: float = 0.96) -> list[tuple[int, int]]:
    """Find continuous near-white separator bands in a montage axis."""
    selected = values >= minimum
    runs: list[tuple[int, int]] = []
    start: int | None = None
    for index, is_selected in enumerate(selected):
        if is_selected and start is None:
            start = index
        elif not is_selected and start is not None:
            runs.append((start, index - 1)); start = None
    if start is not None:
        runs.append((start, len(selected) - 1))
    return runs


def tile_intervals(image: Image.Image) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    """Recover contact-sheet tile bounds from its intentional white gutters."""
    array = np.asarray(image.convert("RGB"))
    near_white = array.min(axis=2) >= 245
    vertical = white_runs(near_white.mean(axis=0))
    horizontal = white_runs(near_white.mean(axis=1))

    def intervals(runs: list[tuple[int, int]], length: int) -> list[tuple[int, int]]:
        output: list[tuple[int, int]] = []
        previous_end = -1
        for start, end in runs:
            if start - previous_end > 20:
                output.append((previous_end + 1, start))
            previous_end = end
        if length - previous_end > 20:
            output.append((previous_end + 1, length))
        return [(start, end) for start, end in output if end - start >= 48]

    columns, rows = intervals(vertical, image.width), intervals(horizontal, image.height)
    if len(columns) < 2 or len(rows) < 2:
        raise ValueError("Unable to recover a contact-sheet grid from this source image.")
    return columns, rows


def safe_save(image: Image.Image, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").resize((128, 128), Image.Resampling.LANCZOS).save(destination, format="JPEG", quality=94)


def extract_training_sheets(a1_zip: Path, output: Path, max_per_class: int) -> list[dict]:
    records: list[dict] = []
    per_class_split = Counter()
    split_order = ("train", "validation", "internal_test")
    quotas = {
        "train": max(1, round(max_per_class * 0.70)),
        "validation": max(1, round(max_per_class * 0.15)),
        "internal_test": max(1, max_per_class - round(max_per_class * 0.70) - round(max_per_class * 0.15)),
    }
    with zipfile.ZipFile(a1_zip) as archive:
        by_label: dict[str, list[zipfile.ZipInfo]] = defaultdict(list)
        for info in archive.infolist():
            label = sheet_label(info.filename) if not info.is_dir() and Path(info.filename).suffix.casefold() == ".png" else None
            if label:
                by_label[label].append(info)
        assigned: list[tuple[zipfile.ZipInfo, str, str]] = []
        for label in CLASSES:
            sheets = sorted(by_label[label], key=lambda item: item.filename)
            # Assign entire source sheets to one split.  This prevents tiles
            # from the same montage from leaking into validation or test.
            sheets.sort(key=lambda item: stable_id("split:" + item.filename))
            if len(sheets) < 3:
                raise ValueError(f"Need at least three source sheets for {label}; found {len(sheets)}.")
            train_end = max(1, round(len(sheets) * 0.70))
            validation_end = min(len(sheets) - 1, max(train_end + 1, round(len(sheets) * 0.85)))
            for index, info in enumerate(sheets):
                split = "train" if index < train_end else "validation" if index < validation_end else "internal_test"
                assigned.append((info, label, split))
        for info, label, split in assigned:
            if per_class_split[(label, split)] >= quotas[split]:
                continue
            group_id = stable_id("sheet:" + info.filename)
            try:
                with Image.open(io.BytesIO(archive.read(info))) as sheet:
                    columns, rows = tile_intervals(sheet)
                    for row_index, (top, bottom) in enumerate(rows):
                        for column_index, (left, right) in enumerate(columns):
                            if per_class_split[(label, split)] >= quotas[split]:
                                break
                            tile = sheet.crop((left, top, right, bottom))
                            # Empty grid cells are white.  Do not make them examples.
                            if np.asarray(tile.convert("L")).std() < 3:
                                continue
                            image_id = stable_id(f"{info.filename}:{row_index}:{column_index}")
                            relative = Path("crops") / "internal" / label / f"{image_id}.jpg"
                            safe_save(tile, output / relative)
                            records.append({
                                "image_id": image_id, "image_path": str(relative), "label": label,
                                "split": split, "source_partition": "A1_training_contact_sheet",
                                "group_id": group_id, "group_id_type": "SOURCE_CONTACT_SHEET_NOT_PATIENT_ID",
                                "source_reference": info.filename, "modality": "CLINICAL_NAIL_PHOTO",
                            })
                            per_class_split[(label, split)] += 1
                        if per_class_split[(label, split)] >= quotas[split]:
                            break
            except (OSError, ValueError) as error:
                print(f"Skipping unreadable sheet {info.filename!r}: {error}")
    return records


def external_label(path: str) -> str | None:
    parts = [part.casefold() for part in Path(path).parts]
    if "onychomycosis" in parts:
        return "onychomycosis"
    if "naildystrophy" in parts:
        return "nail_dystrophy"
    return None


def extract_external_validation(external_zip: Path, output: Path) -> list[dict]:
    records: list[dict] = []
    with zipfile.ZipFile(external_zip) as archive:
        for info in sorted(archive.infolist(), key=lambda item: item.filename):
            label = external_label(info.filename)
            if info.is_dir() or not label or Path(info.filename).suffix.casefold() not in {".jpg", ".jpeg"}:
                continue
            image_id = stable_id("external:" + info.filename)
            relative = Path("crops") / "external" / label / f"{image_id}.jpg"
            try:
                with Image.open(io.BytesIO(archive.read(info))) as source:
                    safe_save(source, output / relative)
            except OSError as error:
                print(f"Skipping unreadable external image {info.filename!r}: {error}")
                continue
            cohort = next((part for part in Path(info.filename).parts if re.fullmatch(r"[BCD][12]?", part)), "external")
            records.append({
                "image_id": image_id, "image_path": str(relative), "label": label,
                "split": "external_test", "source_partition": f"{cohort}_external_validation",
                "group_id": image_id, "group_id_type": "PATIENT_ID_NOT_AVAILABLE",
                "source_reference": info.filename, "modality": "CLINICAL_NAIL_PHOTO",
            })
    return records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--a1-zip", required=True, type=Path)
    parser.add_argument("--external-zip", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--max-per-class", type=int, default=6000, help="Balanced cap; must be positive.")
    args = parser.parse_args()
    if args.max_per_class < 100:
        raise SystemExit("--max-per-class must be at least 100 for a meaningful split.")
    if not args.a1_zip.is_file() or not args.external_zip.is_file():
        raise SystemExit("Both source archives must exist and have passed their source integrity checks.")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("Output directory must be empty to keep the preparation run reproducible.")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    internal = extract_training_sheets(args.a1_zip, args.output_dir, args.max_per_class)
    external = extract_external_validation(args.external_zip, args.output_dir)
    if not internal or not external:
        raise SystemExit("No usable records were prepared; inspect source archive layouts.")
    labels = Counter(row["label"] for row in internal)
    split_labels = {split: Counter(row["label"] for row in internal if row["split"] == split) for split in ("train", "validation", "internal_test")}
    if any(labels[name] < 100 for name in CLASSES) or any(split_labels[split][label] < 20 for split in split_labels for label in CLASSES):
        raise SystemExit(f"Not enough balanced records for every class and internal split: { {split: dict(values) for split, values in split_labels.items()} }")
    rows = internal + external
    with (args.output_dir / "manifest.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    summary = {
        "dataset_id": DATASET_ID, "source": DATASET_DOI, "license": DATASET_LICENSE,
        "task": "Research-only clinical nail-photo classification: normal-appearing nail, nail dystrophy, or onychomycosis.",
        "classes": list(CLASSES), "internal_record_count": len(internal), "external_record_count": len(external),
        "counts_by_label_and_split": {split: dict(Counter(row["label"] for row in rows if row["split"] == split)) for split in ("train", "validation", "internal_test", "external_test")},
        "grouping": "Training/validation/internal-test assignment is contact-sheet grouped, not patient grouped. External source patient IDs are unavailable.",
        "ground_truth": "A1 labels are source image finding and/or chart-review labels. B1/B2/C/D validation cohorts are documented by the dataset author as culture/KOH/clinical-response-backed methods; exact method varies by cohort.",
        "limitations": ["Source population and capture conditions may not generalise to this app's users.", "No patient identifiers are provided, so no patient-level leakage claim is made.", "Normal-appearing nail has no external test cohort in this release.", "This preparation does not create a clinical diagnostic model."],
        "status": "PREPARED_FOR_OFFLINE_RESEARCH_TRAINING_ONLY",
    }
    with (args.output_dir / "dataset_summary.json").open("w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
