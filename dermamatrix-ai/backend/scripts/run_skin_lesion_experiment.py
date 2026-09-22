#!/usr/bin/env python3
"""Run a reproducible, leakage-aware dermatoscopy research experiment.

The source archive is deliberately read-only.  This script copies only
deduplicated records into an external cache, never into the repository, and
does not make a clinical-validation claim.  It maps only the seven classes
that match the existing HAM10000 research adapter; unrelated clinical-photo
classes in the archive are excluded rather than silently merged.

The archive's published split contains exact duplicates.  Every identical-byte
group is assigned to one split (test takes precedence, then validation), so a
sample cannot appear in both training and evaluation.  Patient identifiers and
near-duplicate guarantees are not available in this source and are recorded as
limitations in the generated audit.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import platform
import random
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from zipfile import ZipFile

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
from PIL import Image
from torch import nn
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
from torchvision import models, transforms


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from calibration_service import CALIBRATION_SCHEMA_VERSION  # noqa: E402
from ml_evaluation import fit_temperature, multiclass_metrics, softmax  # noqa: E402


MODEL_ID = "dermamatrix-ham10000-resnet18-research"
DATASET_VERSION = "skin-ds-kaggle-local-archive-audit-20260922"
PIPELINE_VERSION = "dermamatrix-dermoscopy-resnet18-v1"
SEED = 20260922

# Do not fold squamous-cell carcinoma into AKIEC merely because the older
# HAM10000 abbreviation mentions intraepithelial carcinoma.  The source labels
# do not establish that equivalence.
SOURCE_TO_CLASS = {
    "Actinic keratoses": "akiec",
    "Basal cell carcinoma": "bcc",
    "Benign keratosis-like lesions": "bkl",
    "Dermatofibroma": "df",
    "Melanoma": "mel",
    "Melanocytic nevi": "nv",
    "Vascular lesions": "vasc",
}
CLASSES = tuple(SOURCE_TO_CLASS.values())
SPLIT_ORDER = {"train": 0, "val": 1, "test": 2}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


@dataclass(frozen=True)
class PreparedRecord:
    image_id: str
    image_path: str
    label: str
    split: str
    source_members: int
    width: int
    height: int
    image_format: str
    image_mode: str


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.backends.mps.is_available():
        torch.mps.manual_seed(seed)


def device_for(name: str) -> torch.device:
    if name == "auto":
        return torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    if name == "mps" and not torch.backends.mps.is_available():
        raise ValueError("MPS was requested but is not available.")
    return torch.device(name)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        while chunk := file.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _source_split(parts: tuple[str, ...]) -> str | None:
    if len(parts) < 3 or parts[0] not in SPLIT_ORDER:
        return None
    return parts[0]


def _selected_split(splits: set[str]) -> str:
    """Keep an already-held-out record held out when duplicates cross splits."""
    return max(splits, key=lambda value: SPLIT_ORDER[value])


def cache_preprocessed_image(path: Path, payload: bytes) -> None:
    """Persist a bounded RGB inference cache, never a second raw-data copy."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        return
    with Image.open(io.BytesIO(payload)) as source:
        image = source.convert("RGB")
        shortest = min(image.size)
        if shortest > 256:
            scale = 256 / shortest
            image = image.resize((round(image.width * scale), round(image.height * scale)), Image.Resampling.LANCZOS)
        temporary = path.with_suffix(path.suffix + ".partial")
        image.save(temporary, format="JPEG", quality=90, optimize=True)
    temporary.replace(path)


def prepare_records(source_zip: Path, cache_dir: Path, output_dir: Path) -> tuple[list[PreparedRecord], dict]:
    """Build a deduplicated cache and audit from a local ZIP without mutating it."""
    if not source_zip.is_file():
        raise FileNotFoundError(f"Source ZIP does not exist: {source_zip}")
    groups: dict[str, list[dict]] = defaultdict(list)
    source_counts = Counter()
    skipped = Counter()
    source_format = Counter()
    source_mode = Counter()
    below_quality_minimum = 0
    too_large = 0

    with ZipFile(source_zip) as archive:
        for member in archive.infolist():
            filename = member.filename
            parts = Path(filename).parts
            split = _source_split(parts)
            if split is None or len(parts) < 3 or Path(filename).suffix.lower() not in IMAGE_SUFFIXES:
                continue
            source_label = parts[1]
            target_label = SOURCE_TO_CLASS.get(source_label)
            if target_label is None:
                skipped[source_label] += 1
                continue
            raw = archive.read(member)
            digest = sha256_bytes(raw)
            try:
                with Image.open(io.BytesIO(raw)) as image:
                    width, height = image.size
                    image_format = str(image.format or "UNKNOWN")
                    image_mode = str(image.mode)
            except (OSError, ValueError) as error:
                skipped[f"unreadable:{source_label}"] += 1
                continue
            source_counts[(split, target_label)] += 1
            source_format[image_format] += 1
            source_mode[image_mode] += 1
            below_quality_minimum += int(min(width, height) < 450)
            too_large += int(width * height > 16_000_000)
            groups[digest].append({
                "split": split,
                "label": target_label,
                "source_member": filename,
                "payload": raw,
                "width": width,
                "height": height,
                "format": image_format,
                "mode": image_mode,
                "suffix": Path(filename).suffix.lower(),
            })

    records: list[PreparedRecord] = []
    cross_split_groups = 0
    duplicate_groups = 0
    conflicting_label_groups = 0
    cross_split_examples: list[list[str]] = []
    for digest, entries in sorted(groups.items()):
        labels = {entry["label"] for entry in entries}
        if len(labels) != 1:
            conflicting_label_groups += 1
            continue
        splits = {entry["split"] for entry in entries}
        if len(entries) > 1:
            duplicate_groups += 1
        if len(splits) > 1:
            cross_split_groups += 1
            if len(cross_split_examples) < 10:
                cross_split_examples.append([entry["source_member"] for entry in entries])
        selected = _selected_split(splits)
        canonical = sorted(entries, key=lambda entry: (SPLIT_ORDER[entry["split"]], entry["source_member"]))[0]
        relative_path = Path("images") / f"{digest}.jpg"
        cache_preprocessed_image(cache_dir / relative_path, canonical["payload"])
        records.append(PreparedRecord(
            image_id=digest,
            image_path=relative_path.as_posix(),
            label=canonical["label"],
            split=selected,
            source_members=len(entries),
            width=canonical["width"],
            height=canonical["height"],
            image_format=canonical["format"],
            image_mode=canonical["mode"],
        ))

    overlap = defaultdict(set)
    for record in records:
        overlap[record.image_id].add(record.split)
    if any(len(splits) != 1 for splits in overlap.values()):
        raise RuntimeError("Exact-hash leakage remains after split reconstruction.")
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.csv"
    with manifest_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(PreparedRecord.__dataclass_fields__))
        writer.writeheader()
        writer.writerows(record.__dict__ for record in records)
    prepared_counts = Counter((record.split, record.label) for record in records)
    audit = {
        "dataset_name": "Skin Lesions Dataset local archive",
        "dataset_version": DATASET_VERSION,
        "source_archive": "User-provided local archive.zip (not committed)",
        "source_archive_sha256": sha256_file(source_zip),
        "source_mutated": False,
        "processed_cache": "External processed cache (not committed)",
        "cache_preprocessing": "RGB conversion; resize shortest edge to 256 pixels when larger; JPEG quality 90. Original bytes remain only in the read-only source archive.",
        "scope": "Seven source-labelled dermatoscopic-style ISIC classes mapped to the existing HAM10000 research adapter.",
        "excluded_source_classes": dict(sorted(skipped.items())),
        "source_records_by_split_and_class": {f"{split}/{label}": count for (split, label), count in sorted(source_counts.items())},
        "prepared_records_by_split_and_class": {f"{split}/{label}": count for (split, label), count in sorted(prepared_counts.items())},
        "selected_records": len(records),
        "exact_duplicate_groups": duplicate_groups,
        "exact_duplicate_groups_crossing_source_splits": cross_split_groups,
        "exact_duplicate_cross_split_examples": cross_split_examples,
        "conflicting_label_hash_groups_excluded": conflicting_label_groups,
        "exact_hash_split_check": "PASSED",
        "patient_id_split_check": "NOT_POSSIBLE_SOURCE_HAS_NO_PATIENT_OR_CASE_IDS",
        "near_duplicate_audit": "NOT_ESTABLISHED; exact duplicate grouping is enforced but this source cannot support a patient-level or near-duplicate guarantee.",
        "image_formats": dict(sorted(source_format.items())),
        "image_modes": dict(sorted(source_mode.items())),
        "images_below_450px_short_edge": below_quality_minimum,
        "images_over_16_megapixels": too_large,
        "manifest": "results/skin-lesion-zip-v1/manifest.csv",
        "limitations": [
            "The archive README cites component datasets but does not provide a machine-learning deployment licence in this local copy.",
            "No patient or case IDs are supplied, so this is not a patient-level split or clinical validation.",
            "Exact duplicates are grouped before training; near-duplicate leakage remains a documented residual risk.",
            "This experiment is research-only and is not a diagnostic, triage, prognosis, or treatment-selection model.",
        ],
    }
    with (output_dir / "dataset_audit.json").open("w", encoding="utf-8") as file:
        json.dump(audit, file, indent=2)
    plot_class_distribution(prepared_counts, output_dir / "class_distribution.png")
    return records, audit


def plot_class_distribution(counts: Counter, output: Path) -> None:
    labels = list(CLASSES)
    positions = np.arange(len(labels))
    figure, axis = plt.subplots(figsize=(11, 5))
    width = 0.25
    for offset, split in enumerate(("train", "val", "test")):
        axis.bar(positions + (offset - 1) * width, [counts[(split, label)] for label in labels], width=width, label=split)
    axis.set_xticks(positions, labels)
    axis.set_ylabel("Exact-hash deduplicated images")
    axis.set_title("Prepared dermatoscopy research dataset distribution")
    axis.legend()
    figure.tight_layout()
    figure.savefig(output, dpi=160)
    plt.close(figure)


class SkinLesionDataset(Dataset):
    def __init__(self, rows: list[PreparedRecord], cache_dir: Path, transform: transforms.Compose):
        self.rows = rows
        self.cache_dir = cache_dir
        self.transform = transform

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, int, str]:
        row = self.rows[index]
        with Image.open(self.cache_dir / row.image_path) as image:
            tensor = self.transform(image.convert("RGB"))
        return tensor, CLASSES.index(row.label), row.image_id


def selected_training_rows(rows: Iterable[PreparedRecord], max_per_class: int, seed: int) -> list[PreparedRecord]:
    grouped: dict[str, list[PreparedRecord]] = defaultdict(list)
    for row in rows:
        grouped[row.label].append(row)
    selected: list[PreparedRecord] = []
    randomizer = random.Random(seed)
    for label in CLASSES:
        candidates = sorted(grouped[label], key=lambda row: row.image_id)
        randomizer.shuffle(candidates)
        selected.extend(candidates[:max_per_class] if max_per_class else candidates)
    return sorted(selected, key=lambda row: row.image_id)


def run_epoch(model: nn.Module, loader: DataLoader, device: torch.device, loss_function: nn.Module,
              optimizer: torch.optim.Optimizer | None = None) -> tuple[float, np.ndarray, np.ndarray, list[str]]:
    training = optimizer is not None
    model.train(training)
    loss_total, sample_count = 0.0, 0
    logits_batches, labels_batches, identifiers = [], [], []
    context = torch.enable_grad() if training else torch.inference_mode()
    with context:
        for tensors, labels, ids in loader:
            tensors, labels = tensors.to(device), labels.to(device)
            if training:
                optimizer.zero_grad(set_to_none=True)
            logits = model(tensors)
            loss = loss_function(logits, labels)
            if training:
                loss.backward()
                optimizer.step()
            loss_total += float(loss.detach().cpu()) * len(labels)
            sample_count += len(labels)
            logits_batches.append(logits.detach().cpu().numpy())
            labels_batches.append(labels.detach().cpu().numpy())
            identifiers.extend(ids)
    return loss_total / max(sample_count, 1), np.concatenate(logits_batches), np.concatenate(labels_batches), identifiers


def build_model() -> nn.Module:
    weights = models.ResNet18_Weights.IMAGENET1K_V1
    model = models.resnet18(weights=weights)
    model.fc = nn.Sequential(nn.Dropout(0.20), nn.Linear(model.fc.in_features, len(CLASSES)))
    return model


def render_training_curves(history: list[dict], output: Path) -> None:
    figure, axis = plt.subplots(1, 2, figsize=(11, 4))
    epochs = [row["epoch"] for row in history]
    axis[0].plot(epochs, [row["train_loss"] for row in history], marker="o", label="train")
    axis[0].plot(epochs, [row["validation_loss"] for row in history], marker="o", label="validation")
    axis[0].set_title("Cross-entropy loss"); axis[0].set_xlabel("epoch"); axis[0].legend()
    axis[1].plot(epochs, [row["validation_macro_f1"] for row in history], marker="o", label="validation macro F1")
    axis[1].plot(epochs, [row["validation_balanced_accuracy"] for row in history], marker="o", label="validation balanced accuracy")
    axis[1].set_ylim(0, 1); axis[1].set_title("Validation discrimination"); axis[1].set_xlabel("epoch"); axis[1].legend()
    figure.tight_layout(); figure.savefig(output, dpi=160); plt.close(figure)


def render_confusion_matrix(metrics: dict, output: Path) -> None:
    matrix = np.asarray(metrics["confusion_matrix"])
    figure, axis = plt.subplots(figsize=(8, 7))
    image = axis.imshow(matrix, cmap="Blues")
    figure.colorbar(image, ax=axis, fraction=0.046, pad=0.04)
    axis.set_xticks(range(len(CLASSES)), CLASSES, rotation=45, ha="right")
    axis.set_yticks(range(len(CLASSES)), CLASSES)
    axis.set_xlabel("Predicted"); axis.set_ylabel("Held-out true label"); axis.set_title("Held-out test confusion matrix")
    for row in range(len(CLASSES)):
        for column in range(len(CLASSES)):
            axis.text(column, row, str(matrix[row, column]), ha="center", va="center", color="white" if matrix[row, column] > matrix.max() / 2 else "black", fontsize=8)
    figure.tight_layout(); figure.savefig(output, dpi=180); plt.close(figure)


def write_predictions(output: Path, split: str, rows: list[PreparedRecord], identifiers: list[str], logits: np.ndarray,
                      labels: np.ndarray, temperature: float) -> tuple[dict, list[dict]]:
    probabilities = softmax(logits / temperature)
    metrics = multiclass_metrics(labels, probabilities, CLASSES)
    by_id = {row.image_id: row for row in rows}
    result_rows = []
    for image_id, label_index, scores in zip(identifiers, labels, probabilities, strict=True):
        row = by_id[image_id]
        ranked = np.argsort(scores)[::-1]
        result_rows.append({
            "image_id": image_id,
            "split": split,
            "true_label": CLASSES[int(label_index)],
            "predicted_label": CLASSES[int(ranked[0])],
            "confidence": round(float(scores[ranked[0]]), 6),
            "correct": bool(int(label_index) == int(ranked[0])),
            "source_members": row.source_members,
            **{f"score_{label}": round(float(scores[index]), 6) for index, label in enumerate(CLASSES)},
            **{f"logit_{label}": round(float(logits_row), 6) for label, logits_row in zip(CLASSES, logits[len(result_rows)])},
        })
    with (output / f"{split}_predictions.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(result_rows[0]))
        writer.writeheader(); writer.writerows(result_rows)
    return metrics, result_rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-zip", required=True, type=Path)
    parser.add_argument("--cache-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--model-output", required=True, type=Path, help="External artifact directory; never place binary weights in the repository.")
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--freeze-epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=48)
    parser.add_argument("--max-train-per-class", type=int, default=2200)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--device", default="auto", choices=("auto", "mps", "cpu"))
    parser.add_argument("--sanity", action="store_true", help="Run one tiny forward/backward/checkpoint test only.")
    args = parser.parse_args()
    if args.epochs < 1 or args.freeze_epochs < 0 or args.batch_size < 1:
        raise ValueError("epochs, freeze-epochs, and batch-size must be positive where applicable.")
    seed_everything(SEED)
    device = device_for(args.device)
    output = args.output_dir.resolve()
    records, audit = prepare_records(args.source_zip.resolve(), args.cache_dir.resolve(), output)
    split_rows = {split: [record for record in records if record.split == split] for split in ("train", "val", "test")}
    if any(not split_rows[split] for split in split_rows):
        raise RuntimeError("Prepared split is empty.")
    maximum = 8 if args.sanity else args.max_train_per_class
    train_rows = selected_training_rows(split_rows["train"], maximum, SEED)
    if args.sanity:
        split_rows["val"] = selected_training_rows(split_rows["val"], 4, SEED)
        split_rows["test"] = selected_training_rows(split_rows["test"], 4, SEED)
    train_transform = transforms.Compose([
        transforms.Resize(256), transforms.RandomResizedCrop(224, scale=(0.82, 1.0)), transforms.RandomHorizontalFlip(),
        transforms.ColorJitter(brightness=0.08, contrast=0.08, saturation=0.05), transforms.ToTensor(),
        transforms.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225)),
    ])
    evaluation_transform = transforms.Compose([
        transforms.Resize(256), transforms.CenterCrop(224), transforms.ToTensor(),
        transforms.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225)),
    ])
    train_dataset = SkinLesionDataset(train_rows, args.cache_dir.resolve(), train_transform)
    class_counts = Counter(row.label for row in train_rows)
    sample_weights = [1.0 / class_counts[row.label] for row in train_rows]
    sampler = WeightedRandomSampler(sample_weights, len(sample_weights), generator=torch.Generator().manual_seed(SEED))
    loaders = {
        "train": DataLoader(train_dataset, batch_size=args.batch_size, sampler=sampler, num_workers=0),
        "val": DataLoader(SkinLesionDataset(split_rows["val"], args.cache_dir.resolve(), evaluation_transform), batch_size=args.batch_size, shuffle=False, num_workers=0),
        "test": DataLoader(SkinLesionDataset(split_rows["test"], args.cache_dir.resolve(), evaluation_transform), batch_size=args.batch_size, shuffle=False, num_workers=0),
    }
    model = build_model().to(device)
    loss_function = nn.CrossEntropyLoss()
    for parameter in model.parameters():
        parameter.requires_grad = False
    for parameter in model.fc.parameters():
        parameter.requires_grad = True
    optimizer = torch.optim.AdamW((parameter for parameter in model.parameters() if parameter.requires_grad), lr=args.learning_rate, weight_decay=1e-4)
    best = {"validation_macro_f1": -1.0, "state_dict": None, "epoch": None}
    history = []
    for epoch in range(1, args.epochs + 1):
        if epoch == args.freeze_epochs + 1:
            for parameter in model.parameters():
                parameter.requires_grad = True
            optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate / 8, weight_decay=1e-4)
        train_loss, _, _, _ = run_epoch(model, loaders["train"], device, loss_function, optimizer)
        validation_loss, validation_logits, validation_labels, _ = run_epoch(model, loaders["val"], device, loss_function)
        validation_metrics = multiclass_metrics(validation_labels, softmax(validation_logits), CLASSES)
        point = {
            "epoch": epoch,
            "train_loss": round(train_loss, 6),
            "validation_loss": round(validation_loss, 6),
            "validation_macro_f1": validation_metrics["macro_f1"],
            "validation_balanced_accuracy": validation_metrics["balanced_accuracy"],
        }
        history.append(point)
        if point["validation_macro_f1"] > best["validation_macro_f1"]:
            best = {"validation_macro_f1": point["validation_macro_f1"], "state_dict": {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}, "epoch": epoch}
        print(json.dumps(point), flush=True)
    if best["state_dict"] is None:
        raise RuntimeError("No model checkpoint was selected.")
    model.load_state_dict(best["state_dict"])
    validation_loss, validation_logits, validation_labels, validation_ids = run_epoch(model, loaders["val"], device, loss_function)
    temperature, calibration_metrics = fit_temperature(validation_logits, validation_labels)
    test_started = time.perf_counter()
    test_loss, test_logits, test_labels, test_ids = run_epoch(model, loaders["test"], device, loss_function)
    test_elapsed = time.perf_counter() - test_started
    validation_metrics, _ = write_predictions(output, "validation", split_rows["val"], validation_ids, validation_logits, validation_labels, temperature)
    test_metrics, prediction_rows = write_predictions(output, "test", split_rows["test"], test_ids, test_logits, test_labels, temperature)
    render_training_curves(history, output / "training_curves.png")
    render_confusion_matrix(test_metrics, output / "test_confusion_matrix.png")
    difficult = sorted((row for row in prediction_rows if not row["correct"]), key=lambda row: row["confidence"], reverse=True)[:30]
    samples = sorted((row for row in prediction_rows if row["correct"]), key=lambda row: row["confidence"], reverse=True)[:30]
    with (output / "difficult_predictions.json").open("w", encoding="utf-8") as file:
        json.dump(difficult, file, indent=2)
    with (output / "sample_predictions.json").open("w", encoding="utf-8") as file:
        json.dump(samples, file, indent=2)
    version = "dermamatrix-ham10000-resnet18-research-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    checkpoint = {
        "model_id": MODEL_ID,
        "model_version": version,
        "deployment_status": "RESEARCH_ONLY_CANDIDATE",
        "architecture": "ImageNet-initialised ResNet-18 fine-tuned with a weighted sampler",
        "classes": list(CLASSES),
        "input_size": [224, 224],
        "preprocessing": "RGB; resize 256; centre crop 224 at evaluation; ImageNet normalization.",
        "dataset_version": DATASET_VERSION,
        "pipeline_version": PIPELINE_VERSION,
        "best_epoch": best["epoch"],
        "state_dict": best["state_dict"],
    }
    model_output = args.model_output.resolve()
    model_output.mkdir(parents=True, exist_ok=True)
    checkpoint_path = model_output / "model.pt"
    torch.save(checkpoint, checkpoint_path)
    calibration = {
        "schema_version": CALIBRATION_SCHEMA_VERSION,
        "model_id": MODEL_ID,
        "model_version": version,
        "dataset_version": DATASET_VERSION,
        "calibration_version": version + "-temperature-validation",
        "validation_split": "hash-grouped validation split; source patient IDs unavailable",
        "method": "temperature_scaling",
        "temperature": temperature,
        "class_order": list(CLASSES),
        "metrics": calibration_metrics,
    }
    calibration_path = model_output / "calibration.json"
    with calibration_path.open("w", encoding="utf-8") as file:
        json.dump(calibration, file, indent=2)
    report = {
        "status": "RESEARCH_ONLY_CANDIDATE_NOT_AUTO_PROMOTED",
        "model": {**{key: checkpoint[key] for key in ("model_id", "model_version", "deployment_status", "architecture", "classes", "input_size", "preprocessing", "dataset_version", "pipeline_version", "best_epoch")}, "checkpoint": "External research artifact (not committed): model.pt", "calibration": "External research artifact (not committed): calibration.json"},
        "dataset_audit": audit,
        "environment": {"python": platform.python_version(), "torch": torch.__version__, "device": str(device), "seed": SEED},
        "training": {"epochs_requested": args.epochs, "freeze_epochs": args.freeze_epochs, "batch_size": args.batch_size, "selected_training_count": len(train_rows), "class_counts": dict(sorted(class_counts.items())), "history": history},
        "calibration": calibration_metrics,
        "validation": {"loss": round(validation_loss, 6), "metrics": validation_metrics},
        "held_out_test": {"loss": round(test_loss, 6), "metrics": test_metrics, "inference_seconds": round(test_elapsed, 4), "mean_seconds_per_image": round(test_elapsed / len(test_labels), 6)},
        "promotion_gate": {
            "decision": "NOT_AUTO_PROMOTED",
            "reason": "The source lacks patient/case identifiers, a deployment licence record, a near-duplicate guarantee, external validation, prospective validation, and clinical validation. A good internal held-out result is not enough to replace the existing scoped adapter.",
        },
    }
    with (output / "evaluation_report.json").open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)
    print(json.dumps({"status": report["status"], "output_dir": str(output), "test_accuracy": test_metrics["accuracy"], "test_balanced_accuracy": test_metrics["balanced_accuracy"], "test_macro_f1": test_metrics["macro_f1"]}, indent=2))


if __name__ == "__main__":
    main()
