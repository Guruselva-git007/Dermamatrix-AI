#!/usr/bin/env python3
"""Train one explicitly experimental SCIN clinical-photo skin classifier offline.

This script is intentionally disconnected from the Flask inference API.  It
cannot make a production model: it produces a checkpoint, validation-fitted
temperature artifact, held-out test report, and experiment manifest for
research review.  SCIN case IDs are grouped, but are not claimed to be patient
identifiers.  The resulting small-data model must not be used for diagnosis.
"""

from __future__ import annotations

import argparse
import csv
import json
import platform
import random
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torch import nn
from torch.utils.data import DataLoader, Dataset
from torchvision import models, transforms


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
from calibration_service import CALIBRATION_SCHEMA_VERSION  # noqa: E402
from ml_evaluation import fit_temperature, multiclass_metrics, softmax, validate_grouped_splits  # noqa: E402


PREPROCESSING_VERSION = "scin-clinical-resnet18-v1"


class ManifestDataset(Dataset):
    def __init__(self, rows: list[dict], labels: list[str], transform: transforms.Compose):
        self.rows, self.labels, self.transform = rows, labels, transform
        self.label_index = {label: index for index, label in enumerate(labels)}

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int):
        row = self.rows[index]
        with Image.open(row["image_path"]) as image:
            tensor = self.transform(image.convert("RGB"))
        return tensor, self.label_index[row["label"]], row["image_id"]


def seed_everything(seed: int) -> None:
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    if torch.backends.mps.is_available():
        torch.mps.manual_seed(seed)


def choose_device(preference: str) -> torch.device:
    if preference == "mps" and torch.backends.mps.is_available():
        return torch.device("mps")
    if preference == "cuda" and torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def run_epoch(model: nn.Module, loader: DataLoader, device: torch.device, optimizer: torch.optim.Optimizer | None, loss_fn: nn.Module) -> tuple[float, np.ndarray, np.ndarray, list[str]]:
    training = optimizer is not None
    model.train(training)
    losses, logits_all, labels_all, ids_all = [], [], [], []
    with torch.set_grad_enabled(training):
        for images, labels, image_ids in loader:
            images, labels = images.to(device), labels.to(device)
            logits = model(images)
            loss = loss_fn(logits, labels)
            if training:
                optimizer.zero_grad(); loss.backward(); optimizer.step()
            losses.append(float(loss.detach().cpu()))
            logits_all.append(logits.detach().cpu().numpy())
            labels_all.append(labels.detach().cpu().numpy())
            ids_all.extend(image_ids)
    return float(np.mean(losses)), np.concatenate(logits_all), np.concatenate(labels_all), ids_all


def probabilities(logits: np.ndarray, temperature: float = 1.0) -> np.ndarray:
    return softmax(np.asarray(logits, dtype=float) / temperature)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest-csv", required=True, help="Local SCIN manifest from acquire_scin_images.py")
    parser.add_argument("--output-dir", required=True, help="External experiment directory; never a Git-tracked directory")
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--seed", type=int, default=20260906)
    parser.add_argument("--device", choices=("mps", "cuda", "cpu"), default="mps")
    parser.add_argument("--no-pretrained", action="store_true")
    args = parser.parse_args()
    if args.epochs < 1 or args.batch_size < 1:
        raise SystemExit("epochs and batch-size must be positive")
    seed_everything(args.seed)
    with open(args.manifest_csv, encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    required = {"image_id", "group_id", "label", "split", "image_path"}
    if not rows or required - set(rows[0]):
        raise SystemExit("Manifest must be a local manifest containing image_id, group_id, label, split, and image_path.")
    leakage = validate_grouped_splits(rows, "group_id")
    if leakage:
        raise SystemExit("SCIN case-group split leakage detected: " + "; ".join(leakage[:5]))
    missing_images = [row["image_path"] for row in rows if not Path(row["image_path"]).is_file()]
    if missing_images:
        raise SystemExit(f"{len(missing_images)} local image paths are missing; acquire images before training.")

    labels = sorted({row["label"] for row in rows})
    splits = {name: [row for row in rows if row["split"] == name] for name in ("train", "validation", "test")}
    if any(not splits[name] for name in splits):
        raise SystemExit("Manifest needs non-empty train, validation, and test splits.")
    device = choose_device(args.device)
    train_transform = transforms.Compose([
        transforms.Resize(256), transforms.CenterCrop(224), transforms.RandomHorizontalFlip(p=0.5),
        transforms.ColorJitter(brightness=0.05, contrast=0.05), transforms.ToTensor(),
        transforms.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
    ])
    eval_transform = transforms.Compose([
        transforms.Resize(256), transforms.CenterCrop(224), transforms.ToTensor(),
        transforms.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
    ])
    loaders = {
        "train": DataLoader(ManifestDataset(splits["train"], labels, train_transform), batch_size=args.batch_size, shuffle=True, num_workers=0),
        "validation": DataLoader(ManifestDataset(splits["validation"], labels, eval_transform), batch_size=args.batch_size, shuffle=False, num_workers=0),
        "test": DataLoader(ManifestDataset(splits["test"], labels, eval_transform), batch_size=args.batch_size, shuffle=False, num_workers=0),
    }
    weights = None if args.no_pretrained else models.ResNet18_Weights.IMAGENET1K_V1
    model = models.resnet18(weights=weights)
    for parameter in model.parameters():
        parameter.requires_grad = False
    model.fc = nn.Linear(model.fc.in_features, len(labels))
    model.to(device)
    class_counts = Counter(row["label"] for row in splits["train"])
    class_weight = torch.tensor([len(splits["train"]) / (len(labels) * class_counts[label]) for label in labels], dtype=torch.float32, device=device)
    loss_fn = nn.CrossEntropyLoss(weight=class_weight)
    optimizer = torch.optim.AdamW(model.fc.parameters(), lr=args.learning_rate, weight_decay=1e-4)
    history, best_state, best_loss = [], None, float("inf")
    for epoch in range(1, args.epochs + 1):
        train_loss, _, _, _ = run_epoch(model, loaders["train"], device, optimizer, loss_fn)
        validation_loss, _, _, _ = run_epoch(model, loaders["validation"], device, None, loss_fn)
        history.append({"epoch": epoch, "train_loss": round(train_loss, 6), "validation_loss": round(validation_loss, 6)})
        if validation_loss < best_loss:
            best_loss = validation_loss
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
    if best_state is None:
        raise RuntimeError("Training did not produce a checkpoint.")
    model.load_state_dict(best_state)
    validation_loss, validation_logits, validation_labels, _ = run_epoch(model, loaders["validation"], device, None, loss_fn)
    temperature, calibration_metrics = fit_temperature(validation_logits, validation_labels)
    test_loss, test_logits, test_labels, test_ids = run_epoch(model, loaders["test"], device, None, loss_fn)
    raw_test = probabilities(test_logits)
    calibrated_test = probabilities(test_logits, temperature)
    output = Path(args.output_dir); output.mkdir(parents=True, exist_ok=True)
    version = "scin-clinical-resnet18-experiment-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    checkpoint = {
        "model_id": "scin-clinical-resnet18-experiment",
        "model_version": version,
        "status": "EXPERIMENTAL_NOT_DEPLOYABLE",
        "architecture": "ResNet-18 frozen ImageNet backbone with trained classification head",
        "classes": labels,
        "preprocessing_version": PREPROCESSING_VERSION,
        "state_dict": model.state_dict(),
    }
    torch.save(checkpoint, output / "model.pt")
    calibration = {
        "schema_version": CALIBRATION_SCHEMA_VERSION,
        "model_id": checkpoint["model_id"],
        "model_version": version,
        "dataset_version": "SCIN-public-1.0.0-strict-single-label",
        "calibration_version": version + "-temperature-validation",
        "validation_split": "validation",
        "method": "temperature_scaling",
        "temperature": temperature,
        "class_order": labels,
        "metrics": calibration_metrics,
        "status": "EXPERIMENTAL_VALIDATION_ONLY_NOT_FOR_DEPLOYMENT",
    }
    with (output / "calibration.json").open("w", encoding="utf-8") as file:
        json.dump(calibration, file, indent=2)
    predictions = []
    for image_id, true_label, raw, calibrated in zip(test_ids, test_labels, raw_test, calibrated_test):
        predictions.append({"image_id": image_id, "true_label": labels[int(true_label)], "raw_probabilities": raw.tolist(), "calibrated_probabilities": calibrated.tolist()})
    with (output / "test_predictions.json").open("w", encoding="utf-8") as file:
        json.dump(predictions, file, indent=2)
    report = {
        "status": "EXPERIMENTAL_NOT_DEPLOYABLE",
        "prohibition": "This experiment is not clinically validated and must not be wired into the DermaMatrix inference API or described as diagnostic.",
        "model": {key: checkpoint[key] for key in ("model_id", "model_version", "architecture", "classes", "preprocessing_version")},
        "dataset": {"name": "SCIN", "selection": "strict single weighted label >= 0.7; one first image per SCIN case", "grouping": "SCIN case ID, not verified patient ID", "split_counts": {key: len(value) for key, value in splits.items()}},
        "environment": {"python": platform.python_version(), "torch": torch.__version__, "device": str(device), "seed": args.seed},
        "training": {"epochs": args.epochs, "batch_size": args.batch_size, "learning_rate": args.learning_rate, "class_weights": class_weight.detach().cpu().tolist(), "augmentation": "horizontal flip plus brightness/contrast jitter ±5%", "history": history, "best_validation_loss": round(best_loss, 6)},
        "validation_calibration": calibration_metrics,
        "held_out_test": {"loss": round(test_loss, 6), "raw": multiclass_metrics(test_labels, raw_test, labels), "temperature_scaled": multiclass_metrics(test_labels, calibrated_test, labels)},
        "external_validation": "NOT_PERFORMED",
        "subgroup_evaluation": "NOT_PERFORMED; do not infer fairness from this small subset.",
        "limitations": ["Small selected dataset; performance estimates are unstable.", "SCIN case IDs are not verified patient IDs.", "Classes are dermatologist weighted labels, not a confirmed diagnosis for every image.", "No normal/healthy class, segmentation model, OOD detector, hair model, nail model, or clinical validation is supplied by this experiment."],
    }
    with (output / "evaluation_report.json").open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)
    print(json.dumps({"model_version": version, "status": report["status"], "output_dir": str(output), "held_out_test": report["held_out_test"]["temperature_scaled"]}, indent=2))


if __name__ == "__main__":
    main()
