#!/usr/bin/env python3
"""Run a compact, leakage-aware three-class dermoscopy research experiment.

The source tree stays read-only. This runner keeps a path-based manifest in an
external output directory, groups identical-byte images before fitting, and
never imports Flask or alters runtime model routing. It is deliberately unable
to promote a checkpoint: source provenance, patient grouping, near-duplicate
control, and deployment licensing remain unavailable.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import random
import sys
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
from PIL import Image
from torch import nn
from torch.utils.data import DataLoader, Dataset
from torchvision import models, transforms


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from calibration_service import CALIBRATION_SCHEMA_VERSION  # noqa: E402
from ml_evaluation import fit_temperature, multiclass_metrics, softmax  # noqa: E402


MODEL_ID = "dermamatrix-three-class-dermoscopy-research"
DATASET_VERSION = "local-three-class-dermoscopy-archive1-v1"
PIPELINE_VERSION = "dermamatrix-three-class-dermoscopy-resnet18-v1"
SEED = 20260923
CLASSES = ("melanoma", "nevus", "seborrheic_keratosis")
SOURCE_SPLITS = {"train": "train", "validation": "validation", "test": "test"}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


@dataclass(frozen=True)
class SourceRecord:
    image_id: str
    source_path: str
    split: str
    label: str
    width: int
    height: int
    image_format: str


class DermoscopyDataset(Dataset):
    def __init__(self, rows: list[SourceRecord], root: Path, transform: transforms.Compose):
        self.rows, self.root, self.transform = rows, root, transform
        self.label_index = {label: index for index, label in enumerate(CLASSES)}

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int):
        row = self.rows[index]
        with Image.open(self.root / row.source_path) as image:
            tensor = self.transform(image.convert("RGB"))
        return tensor, self.label_index[row.label], row.image_id, row.source_path


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
        raise RuntimeError("MPS was requested but is not available.")
    return torch.device(name)


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit_source(source_dir: Path) -> tuple[list[SourceRecord], dict]:
    """Decode every candidate and remove all exact-hash cross-split groups."""
    groups: dict[str, list[dict]] = defaultdict(list)
    invalid: list[dict] = []
    dimensions: Counter[str] = Counter()
    source_counts: Counter[tuple[str, str]] = Counter()
    for source_split, target_split in SOURCE_SPLITS.items():
        split_dir = source_dir / source_split
        if not split_dir.is_dir():
            raise FileNotFoundError(f"Missing expected split directory: {split_dir}")
        for label_dir in sorted(path for path in split_dir.iterdir() if path.is_dir()):
            label = label_dir.name
            if label not in CLASSES:
                raise ValueError(f"Unsupported source label: {label}")
            for path in sorted(label_dir.rglob("*")):
                if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
                    continue
                try:
                    with Image.open(path) as image:
                        image.verify()
                    with Image.open(path) as image:
                        width, height = image.size
                        image_format = str(image.format or "UNKNOWN")
                except (OSError, ValueError) as error:
                    invalid.append({"path": path.relative_to(source_dir).as_posix(), "error": str(error)})
                    continue
                digest = file_hash(path)
                relative = path.relative_to(source_dir).as_posix()
                groups[digest].append({
                    "source_path": relative,
                    "split": target_split,
                    "label": label,
                    "width": width,
                    "height": height,
                    "image_format": image_format,
                })
                dimensions[f"{width}x{height}"] += 1
                source_counts[(target_split, label)] += 1

    records: list[SourceRecord] = []
    duplicate_groups = 0
    cross_split_groups: list[list[str]] = []
    conflicting_label_groups: list[list[str]] = []
    within_split_duplicates_removed = 0
    for digest, entries in sorted(groups.items()):
        labels = {entry["label"] for entry in entries}
        splits = {entry["split"] for entry in entries}
        if len(entries) > 1:
            duplicate_groups += 1
        if len(labels) > 1:
            conflicting_label_groups.append([entry["source_path"] for entry in entries])
            continue
        if len(splits) > 1:
            cross_split_groups.append([entry["source_path"] for entry in entries])
            continue
        canonical = min(entries, key=lambda entry: entry["source_path"])
        within_split_duplicates_removed += len(entries) - 1
        records.append(SourceRecord(
            image_id=digest,
            source_path=canonical["source_path"],
            split=canonical["split"],
            label=canonical["label"],
            width=canonical["width"],
            height=canonical["height"],
            image_format=canonical["image_format"],
        ))

    split_check = defaultdict(set)
    for record in records:
        split_check[record.image_id].add(record.split)
    if any(len(splits) != 1 for splits in split_check.values()):
        raise RuntimeError("Exact-hash leakage remains after exclusion.")
    prepared_counts = Counter((record.split, record.label) for record in records)
    audit = {
        "dataset_name": "Local three-class dermoscopy archive (canonical dataset tree only)",
        "dataset_version": DATASET_VERSION,
        "source_mutated": False,
        "source_path_recording": "Relative paths only; full source paths stay outside Git.",
        "source_records_by_split_and_class": {f"{split}/{label}": count for (split, label), count in sorted(source_counts.items())},
        "prepared_records_by_split_and_class": {f"{split}/{label}": count for (split, label), count in sorted(prepared_counts.items())},
        "valid_source_images": int(sum(source_counts.values())),
        "invalid_source_images": len(invalid),
        "invalid_examples": invalid[:20],
        "selected_records": len(records),
        "image_dimensions": dict(sorted(dimensions.items())),
        "exact_duplicate_groups": duplicate_groups,
        "cross_split_exact_duplicate_groups_excluded": len(cross_split_groups),
        "cross_split_exact_duplicate_examples": cross_split_groups[:20],
        "conflicting_label_hash_groups_excluded": len(conflicting_label_groups),
        "within_split_duplicate_members_removed": within_split_duplicates_removed,
        "exact_hash_split_check": "PASSED",
        "patient_or_case_split_check": "NOT_POSSIBLE_SOURCE_HAS_NO_PATIENT_OR_CASE_IDS",
        "near_duplicate_audit": "NOT_ESTABLISHED; exact-hash grouping is enforced but perceptual/patient-level control is unavailable.",
        "duplicate_tree_lineage": "A second identical directory tree exists beside this canonical tree and was excluded before auditing/training.",
        "limitations": [
            "Local source provenance and deployment licence are not established.",
            "No patient/case identifiers or external validation data are available.",
            "All source images are 224x224, limiting real-world image-quality and resolution evidence.",
        ],
    }
    return records, audit


def run_epoch(model: nn.Module, loader: DataLoader, device: torch.device, loss_function: nn.Module,
              optimizer: torch.optim.Optimizer | None = None):
    training = optimizer is not None
    model.train(training)
    losses, logits, labels, ids, paths = [], [], [], [], []
    context = torch.enable_grad() if training else torch.inference_mode()
    with context:
        for images, targets, identifiers, relative_paths in loader:
            images, targets = images.to(device), targets.to(device)
            if training:
                optimizer.zero_grad(set_to_none=True)
            output = model(images)
            loss = loss_function(output, targets)
            if training:
                loss.backward()
                optimizer.step()
            losses.append(float(loss.detach().cpu()) * len(targets))
            logits.append(output.detach().cpu().numpy())
            labels.append(targets.detach().cpu().numpy())
            ids.extend(identifiers)
            paths.extend(relative_paths)
    count = sum(len(batch) for batch in labels)
    return sum(losses) / max(count, 1), np.concatenate(logits), np.concatenate(labels), ids, paths


def build_model() -> nn.Module:
    model = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1)
    model.fc = nn.Sequential(nn.Dropout(0.20), nn.Linear(model.fc.in_features, len(CLASSES)))
    return model


def select_rows(rows: list[SourceRecord], maximum: int, seed: int) -> list[SourceRecord]:
    if not maximum:
        return rows
    selected: list[SourceRecord] = []
    for label in CLASSES:
        candidates = sorted((row for row in rows if row.label == label), key=lambda row: row.image_id)
        randomizer = random.Random(f"{seed}:{label}")
        randomizer.shuffle(candidates)
        selected.extend(candidates[:maximum])
    return sorted(selected, key=lambda row: row.image_id)


def save_predictions(output: Path, rows: list[SourceRecord], identifiers: list[str], paths: list[str], logits: np.ndarray,
                     labels: np.ndarray, temperature: float) -> tuple[dict, list[dict]]:
    probabilities = softmax(logits / temperature)
    metrics = multiclass_metrics(labels, probabilities, CLASSES)
    rows_by_id = {row.image_id: row for row in rows}
    predictions: list[dict] = []
    for identifier, path, target, score in zip(identifiers, paths, labels, probabilities):
        prediction = int(score.argmax())
        predictions.append({
            "image_id": identifier,
            "source_path": path,
            "actual": CLASSES[int(target)],
            "predicted": CLASSES[prediction],
            "confidence": round(float(score[prediction]), 6),
            "correct": bool(prediction == int(target)),
            **{f"probability_{label}": round(float(value), 6) for label, value in zip(CLASSES, score)},
        })
    if set(identifiers) != set(rows_by_id):
        raise RuntimeError("Prediction IDs do not match the locked test manifest.")
    with (output / "test_predictions.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(predictions[0]))
        writer.writeheader()
        writer.writerows(predictions)
    return metrics, predictions


def render_confusion_matrix(metrics: dict, path: Path) -> None:
    figure, axis = plt.subplots(figsize=(5, 4))
    image = axis.imshow(np.asarray(metrics["confusion_matrix"]), cmap="Blues")
    figure.colorbar(image, ax=axis)
    axis.set(xticks=range(len(CLASSES)), yticks=range(len(CLASSES)), xticklabels=CLASSES, yticklabels=CLASSES,
             xlabel="Predicted", ylabel="Actual", title="Locked test confusion matrix")
    for row, values in enumerate(metrics["confusion_matrix"]):
        for column, value in enumerate(values):
            axis.text(column, row, value, ha="center", va="center")
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)


def ood_probe(model: nn.Module, transform: transforms.Compose, device: torch.device, image_path: Path | None) -> dict:
    """Record confidence only; no threshold is fitted or treated as an OOD detector."""
    probes = {"flat_gray_synthetic": Image.new("RGB", (224, 224), color=(127, 127, 127))}
    if image_path and image_path.is_file():
        with Image.open(image_path) as image:
            probes["out_of_scope_local_image"] = image.convert("RGB").copy()
    result = {"status": "NOT_VALIDATED_OOD_DETECTOR", "notice": "Confidence probes are diagnostic only and do not establish OOD detection."}
    model.eval()
    with torch.inference_mode():
        for name, image in probes.items():
            probabilities = torch.softmax(model(transform(image).unsqueeze(0).to(device)), dim=1)[0].detach().cpu().numpy()
            index = int(probabilities.argmax())
            result[name] = {"top_class": CLASSES[index], "max_softmax": round(float(probabilities[index]), 6)}
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", required=True, type=Path, help="Canonical directory containing train/validation/test splits.")
    parser.add_argument("--output-dir", required=True, type=Path, help="Ignored external artifact directory.")
    parser.add_argument("--epochs", type=int, default=4)
    parser.add_argument("--freeze-epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--max-train-per-class", type=int, default=0, help="0 keeps all leakage-safe training records.")
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--device", choices=("auto", "mps", "cpu"), default="auto")
    parser.add_argument("--ood-image", type=Path, help="Optional out-of-scope image for a diagnostic confidence probe.")
    args = parser.parse_args()
    if args.epochs < 1 or args.freeze_epochs < 0 or args.batch_size < 1:
        raise ValueError("epochs, freeze-epochs, and batch-size must be valid positive values.")
    if args.freeze_epochs >= args.epochs:
        raise ValueError("freeze-epochs must leave at least one fine-tuning epoch.")
    source_dir, output = args.source_dir.resolve(), args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    seed_everything(SEED)
    device = device_for(args.device)
    records, audit = audit_source(source_dir)
    split_rows = {split: [row for row in records if row.split == split] for split in ("train", "validation", "test")}
    if any(not rows for rows in split_rows.values()):
        raise RuntimeError("A leakage-safe split is empty.")
    selected_train = select_rows(split_rows["train"], args.max_train_per_class, SEED)
    with (output / "manifest.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(SourceRecord.__dataclass_fields__))
        writer.writeheader()
        writer.writerows(asdict(row) for row in records)
    with (output / "dataset_audit.json").open("w", encoding="utf-8") as file:
        json.dump(audit, file, indent=2)

    train_transform = transforms.Compose([
        transforms.Resize((224, 224)), transforms.RandomHorizontalFlip(), transforms.RandomRotation(8),
        transforms.ColorJitter(brightness=0.08, contrast=0.08), transforms.ToTensor(),
        transforms.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225)),
    ])
    evaluation_transform = transforms.Compose([
        transforms.Resize((224, 224)), transforms.ToTensor(),
        transforms.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225)),
    ])
    loaders = {
        "train": DataLoader(DermoscopyDataset(selected_train, source_dir, train_transform), batch_size=args.batch_size, shuffle=True, num_workers=0),
        "validation": DataLoader(DermoscopyDataset(split_rows["validation"], source_dir, evaluation_transform), batch_size=args.batch_size, shuffle=False, num_workers=0),
        "test": DataLoader(DermoscopyDataset(split_rows["test"], source_dir, evaluation_transform), batch_size=args.batch_size, shuffle=False, num_workers=0),
    }

    smoke_model = build_model().to(device)
    for parameter in smoke_model.parameters():
        parameter.requires_grad = False
    for parameter in smoke_model.fc.parameters():
        parameter.requires_grad = True
    loss_function = nn.CrossEntropyLoss()
    smoke_optimizer = torch.optim.AdamW(smoke_model.fc.parameters(), lr=args.learning_rate, weight_decay=1e-4)
    smoke_images, smoke_targets, _, _ = next(iter(loaders["train"]))
    smoke_model.train(); smoke_optimizer.zero_grad(set_to_none=True)
    smoke_logits = smoke_model(smoke_images[: min(4, len(smoke_images))].to(device))
    smoke_loss = loss_function(smoke_logits, smoke_targets[: min(4, len(smoke_targets))].to(device))
    smoke_loss.backward(); smoke_optimizer.step()
    smoke_path = output / ".smoke-checkpoint.pt"
    torch.save({"state_dict": {key: value.detach().cpu() for key, value in smoke_model.state_dict().items()}}, smoke_path)
    torch.load(smoke_path, map_location="cpu", weights_only=True)
    smoke_path.unlink()
    smoke = {"status": "PASSED", "tensor_shape": list(smoke_images.shape), "forward_shape": list(smoke_logits.shape), "loss": round(float(smoke_loss.detach().cpu()), 6), "optimizer_step": "PASSED", "checkpoint_roundtrip": "PASSED", "device": str(device)}
    with (output / "smoke_check.json").open("w", encoding="utf-8") as file:
        json.dump(smoke, file, indent=2)

    model = build_model().to(device)
    for parameter in model.parameters():
        parameter.requires_grad = False
    for parameter in model.fc.parameters():
        parameter.requires_grad = True
    optimizer = torch.optim.AdamW(model.fc.parameters(), lr=args.learning_rate, weight_decay=1e-4)
    best = {"macro_f1": -1.0, "balanced_accuracy": -1.0, "epoch": None, "state_dict": None}
    history: list[dict] = []
    baseline: dict | None = None
    for epoch in range(1, args.epochs + 1):
        if epoch == args.freeze_epochs + 1:
            for parameter in model.parameters():
                parameter.requires_grad = True
            optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate / 8, weight_decay=1e-4)
        train_loss, *_ = run_epoch(model, loaders["train"], device, loss_function, optimizer)
        validation_loss, validation_logits, validation_labels, _, _ = run_epoch(model, loaders["validation"], device, loss_function)
        validation_metrics = multiclass_metrics(validation_labels, softmax(validation_logits), CLASSES)
        point = {"epoch": epoch, "phase": "head_only" if epoch <= args.freeze_epochs else "fine_tune", "train_loss": round(train_loss, 6), "validation_loss": round(validation_loss, 6), "validation_macro_f1": validation_metrics["macro_f1"], "validation_balanced_accuracy": validation_metrics["balanced_accuracy"]}
        history.append(point)
        if epoch == args.freeze_epochs:
            baseline = {**point, "metrics": validation_metrics}
        if (point["validation_macro_f1"], point["validation_balanced_accuracy"]) > (best["macro_f1"], best["balanced_accuracy"]):
            best = {"macro_f1": point["validation_macro_f1"], "balanced_accuracy": point["validation_balanced_accuracy"], "epoch": epoch, "state_dict": {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}}
        print(json.dumps(point), flush=True)
    if best["state_dict"] is None or baseline is None:
        raise RuntimeError("No validation-selected checkpoint was produced.")
    model.load_state_dict(best["state_dict"])
    validation_loss, validation_logits, validation_labels, _, _ = run_epoch(model, loaders["validation"], device, loss_function)
    temperature, calibration_metrics = fit_temperature(validation_logits, validation_labels)
    test_started = time.perf_counter()
    test_loss, test_logits, test_labels, test_ids, test_paths = run_epoch(model, loaders["test"], device, loss_function)
    test_seconds = time.perf_counter() - test_started
    test_metrics, predictions = save_predictions(output, split_rows["test"], test_ids, test_paths, test_logits, test_labels, temperature)
    render_confusion_matrix(test_metrics, output / "test_confusion_matrix.png")
    difficult = sorted((row for row in predictions if not row["correct"]), key=lambda row: row["confidence"], reverse=True)[:30]
    with (output / "difficult_predictions.json").open("w", encoding="utf-8") as file:
        json.dump(difficult, file, indent=2)
    ood = ood_probe(model, evaluation_transform, device, args.ood_image.resolve() if args.ood_image else None)
    version = "dermamatrix-three-class-dermoscopy-research-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    checkpoint = {"model_id": MODEL_ID, "model_version": version, "deployment_status": "REJECTED", "architecture": "ImageNet-initialised ResNet-18; head warm-up then full fine-tune", "classes": list(CLASSES), "input_size": [224, 224], "preprocessing": "RGB; resize 224x224; ImageNet normalization", "dataset_version": DATASET_VERSION, "pipeline_version": PIPELINE_VERSION, "best_validation_epoch": best["epoch"], "state_dict": {key: value.detach().cpu() for key, value in model.state_dict().items()}}
    torch.save(checkpoint, output / "model.pt")
    calibration = {"schema_version": CALIBRATION_SCHEMA_VERSION, "model_id": MODEL_ID, "model_version": version, "dataset_version": DATASET_VERSION, "calibration_version": version + "-temperature-validation", "validation_split": "official validation after exact-hash cross-split exclusion", "method": "temperature_scaling", "temperature": temperature, "class_order": list(CLASSES), "metrics": calibration_metrics, "status": "RESEARCH_ONLY"}
    with (output / "calibration.json").open("w", encoding="utf-8") as file:
        json.dump(calibration, file, indent=2)
    report = {
        "status": "REJECTED_FOR_APPLICATION_INFERENCE",
        "promotion_gate": {"decision": "REJECTED", "reason": "No deployment licence/provenance record, patient or case IDs, near-duplicate control, external validation, prospective validation, clinical validation, or parity with the current seven-class runtime contract."},
        "model": {key: checkpoint[key] for key in checkpoint if key != "state_dict"},
        "dataset_audit": audit,
        "environment": {"python": platform.python_version(), "torch": torch.__version__, "device": str(device), "seed": SEED},
        "smoke_check": smoke,
        "training": {"epochs_requested": args.epochs, "freeze_epochs": args.freeze_epochs, "batch_size": args.batch_size, "selected_training_count": len(selected_train), "baseline_head_only_validation": baseline, "history": history, "selected_by": "validation macro F1, then validation balanced accuracy", "selected_epoch": best["epoch"]},
        "calibration": calibration_metrics,
        "held_out_test": {"evaluated_once_after_selection": True, "loss": round(test_loss, 6), "metrics": test_metrics, "inference_seconds": round(test_seconds, 6), "mean_seconds_per_image": round(test_seconds / len(test_labels), 6)},
        "ood_probe": ood,
        "error_analysis": {"high_confidence_errors_recorded": len(difficult), "artifact": "difficult_predictions.json"},
        "storage": {"artifact_policy": "Only the validation-selected checkpoint and calibration file are retained in this ignored output directory."},
    }
    with (output / "evaluation_report.json").open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)
    print(json.dumps({"status": report["status"], "best_validation_epoch": best["epoch"], "test_balanced_accuracy": test_metrics["balanced_accuracy"], "test_macro_f1": test_metrics["macro_f1"], "output_dir": str(output)}, indent=2))


if __name__ == "__main__":
    main()
