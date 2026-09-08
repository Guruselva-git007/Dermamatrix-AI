"""SCIN manifest preparation primitives for offline research experiments.

The SCIN public release contains contribution/case identifiers, not verified
patient identifiers. This module therefore makes a deterministic *case*
grouped split and records that limitation in every output. It is intentionally
not imported by the Flask inference path.
"""

from __future__ import annotations

import ast
import csv
import hashlib
from collections import Counter
from pathlib import Path
from typing import Iterable

from sklearn.model_selection import train_test_split


IMAGE_BASE_URL = "https://storage.googleapis.com/dx-scin-public-data/"
SCIN_DATASET_VERSION = "SCIN-public-1.0.0-metadata-2024-03-05"
GRADABLE_VALUES = frozenset({"YES", "DEFAULT_YES_IMAGE_QUALITY_SUFFICIENT"})
DEFAULT_CLASSES = ("Eczema", "Urticaria")


def stable_image_id(case_id: str, image_path: str) -> str:
    """Return a reproducible non-source identifier for an image record."""
    return hashlib.sha256(f"{case_id}|{image_path}".encode("utf-8")).hexdigest()[:24]


def parse_weighted_label(value: str) -> dict[str, float]:
    """Safely parse SCIN's documented Python-dict-like weighted label field."""
    try:
        parsed = ast.literal_eval(value or "{}")
    except (SyntaxError, ValueError):
        return {}
    if not isinstance(parsed, dict):
        return {}
    clean: dict[str, float] = {}
    for label, weight in parsed.items():
        if isinstance(label, str) and isinstance(weight, (int, float)):
            clean[label] = float(weight)
    return clean


def is_condition_gradable(label_row: dict[str, str]) -> bool:
    """Accept only source values denoting sufficient condition-label quality."""
    values = (
        str(value).strip().upper()
        for key, value in label_row.items()
        if key.startswith("dermatologist_gradable_for_skin_condition_")
    )
    return any(value in GRADABLE_VALUES for value in values)


def _source_image_paths(case: dict[str, str], image_slots: Iterable[str]) -> list[tuple[str, str]]:
    return [(slot, path) for slot in image_slots if (path := str(case.get(f"{slot}_path", "")).strip())]


def _split_cases(cases: list[dict], seed: int) -> dict[str, list[dict]]:
    """Create 70/15/15 stratified splits before expanding a case's images."""
    train_cases, held_cases = train_test_split(cases, test_size=0.30, random_state=seed, stratify=[row["label"] for row in cases])
    validation_cases, test_cases = train_test_split(held_cases, test_size=0.50, random_state=seed, stratify=[row["label"] for row in held_cases])
    return {"train": train_cases, "validation": validation_cases, "test": test_cases}


def build_strict_manifest(
    cases_csv: str | Path,
    labels_csv: str | Path,
    classes: Iterable[str] = DEFAULT_CLASSES,
    *,
    seed: int = 20260906,
    minimum_class_cases: int = 20,
    minimum_label_weight: float = 0.70,
    image_slots: Iterable[str] = ("image_1",),
    taxonomy: dict[str, dict[str, str]] | None = None,
    taxonomy_version: str = "source-labels-unmapped",
) -> tuple[list[dict[str, str]], dict]:
    """Build a strict, case-grouped offline SCIN manifest.

    Differential/multilabel cases are counted in the audit but never coerced
    into a multiclass target. The manifest excludes source demographics and
    free text, which must not silently become model features.
    """
    requested_classes = tuple(dict.fromkeys(value.strip() for value in classes if value.strip()))
    slots = tuple(dict.fromkeys(value.strip() for value in image_slots if value.strip()))
    if len(requested_classes) < 2:
        raise ValueError("Choose at least two classes for a multiclass experiment.")
    if not slots or any(slot not in {"image_1", "image_2", "image_3"} for slot in slots):
        raise ValueError("image_slots must use one or more of image_1, image_2, image_3.")
    if not 0 < minimum_label_weight <= 1:
        raise ValueError("minimum_label_weight must be in (0, 1].")

    with Path(cases_csv).open(encoding="utf-8", newline="") as file:
        cases_by_id = {row["case_id"]: row for row in csv.DictReader(file) if row.get("case_id")}

    audit: Counter[str] = Counter()
    selected_cases: list[dict] = []
    seen_paths: set[str] = set()
    with Path(labels_csv).open(encoding="utf-8", newline="") as file:
        for label_row in csv.DictReader(file):
            audit["label_rows"] += 1
            case_id = str(label_row.get("case_id", "")).strip()
            case = cases_by_id.get(case_id)
            if not case:
                audit["missing_case"] += 1; continue
            if not is_condition_gradable(label_row):
                audit["ungradable"] += 1; continue
            weights = parse_weighted_label(label_row.get("weighted_skin_condition_label", ""))
            if not weights:
                audit["missing_weighted_label"] += 1; continue
            if len(weights) != 1:
                audit["differential_or_multilabel"] += 1; continue
            label, weight = next(iter(weights.items()))
            if label not in requested_classes:
                audit["outside_requested_taxonomy"] += 1; continue
            mapping = (taxonomy or {}).get(label, {})
            if taxonomy is not None and not mapping:
                audit["missing_canonical_mapping"] += 1; continue
            canonical_label = str(mapping.get("canonical_label", label)).strip()
            category = str(mapping.get("category", "skin")).strip().lower()
            if not canonical_label or category != "skin":
                audit["invalid_canonical_mapping"] += 1; continue
            if weight < minimum_label_weight:
                audit["below_label_weight_threshold"] += 1; continue
            image_paths = _source_image_paths(case, slots)
            if not image_paths:
                audit["missing_requested_image"] += 1; continue
            if any(path in seen_paths for _, path in image_paths):
                audit["duplicate_source_path"] += 1; continue
            seen_paths.update(path for _, path in image_paths)
            selected_cases.append({"case_id": case_id, "source_label": label, "label": canonical_label, "category": category, "label_weight": f"{weight:.4f}", "images": image_paths})
            audit["selected_cases"] += 1

    selected_counts = Counter(row["label"] for row in selected_cases)
    insufficient = [label for label in requested_classes if selected_counts[label] < minimum_class_cases]
    if insufficient:
        raise ValueError(f"Insufficient strict, gradable case count for: {', '.join(insufficient)}. Counts: {dict(selected_counts)}")

    split_cases = _split_cases(selected_cases, seed)
    rows: list[dict[str, str]] = []
    for split, case_rows in split_cases.items():
        for case in case_rows:
            for slot, path in case["images"]:
                rows.append({
                    "image_id": stable_image_id(case["case_id"], path),
                    "group_id": case["case_id"],
                    "group_id_type": "SCIN_CASE_ID_NOT_VERIFIED_PATIENT_ID",
                    "source_label": case["source_label"],
                    "canonical_label": case["label"],
                    "label": case["label"],
                    "category": case["category"],
                    "label_weight": case["label_weight"],
                    "source_dataset": SCIN_DATASET_VERSION,
                    "modality": "CLINICAL_PHOTO",
                    "source_image_slot": slot,
                    "image_url": IMAGE_BASE_URL + path,
                    "annotation": "single dermatologist weighted condition label at or above configured threshold",
                    "split": split,
                })
    rows.sort(key=lambda item: (item["split"], item["label"], item["image_id"]))
    summary = {
        "dataset": SCIN_DATASET_VERSION,
        "task": "Experimental clinical-photo skin-condition classification",
        "status": "EXPERIMENTAL_MANIFEST_ONLY_NOT_FOR_APPLICATION_INFERENCE",
        "classes": list(requested_classes),
        "canonical_classes": sorted(selected_counts),
        "taxonomy_version": taxonomy_version,
        "minimum_label_weight": minimum_label_weight,
        "image_slots": list(slots),
        "case_count": len(selected_cases),
        "image_count": len(rows),
        "case_label_counts": dict(sorted(selected_counts.items())),
        "split_case_counts": {name: len(items) for name, items in split_cases.items()},
        "split_image_counts": {name: sum(row["split"] == name for row in rows) for name in split_cases},
        "split_label_counts": {name: dict(sorted(Counter(row["label"] for row in rows if row["split"] == name).items())) for name in split_cases},
        "grouping": "SCIN case ID. The public release does not establish a verified patient ID; this is not a patient-level split claim.",
        "selection": "Gradable source condition label; exactly one weighted dermatologist label; configured label weight threshold; selected image slots only.",
        "privacy": "Manifest intentionally excludes demographic, questionnaire, and clinical free-text source fields.",
        "audit": dict(sorted(audit.items())),
    }
    return rows, summary
