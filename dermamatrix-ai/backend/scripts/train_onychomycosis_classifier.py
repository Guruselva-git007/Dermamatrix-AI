#!/usr/bin/env python3
"""Train and evaluate the scoped nail research classifier offline.

The script is intentionally outside the Flask runtime.  It creates a versioned
checkpoint, temperature-calibration artifact, evaluation report and OOD
reference statistics.  Runtime inference will load the result only when the
recorded internal and external performance thresholds pass.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
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


MODEL_ID = "onychomycosis-resnet18-research"
DATASET_VERSION = "han-onychomycosis-figshare-5398573-v2"
PIPELINE_VERSION = "nail-research-resnet18-v1"
CLASSES = ("normal_appearing_nail", "nail_dystrophy", "onychomycosis")


class NailDataset(Dataset):
    def __init__(self, rows: list[dict], root: Path, transform):
        self.rows, self.root, self.transform = rows, root, transform
        self.index = {label: number for number, label in enumerate(CLASSES)}

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int):
        row = self.rows[index]
        with Image.open(self.root / row["image_path"]) as image:
            return self.transform(image.convert("RGB")), self.index[row["label"]], row["image_id"]


def seed_everything(seed: int) -> None:
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    if torch.backends.mps.is_available():
        torch.mps.manual_seed(seed)


def device_for(name: str) -> torch.device:
    if name == "mps" and torch.backends.mps.is_available(): return torch.device("mps")
    if name == "cuda" and torch.cuda.is_available(): return torch.device("cuda")
    return torch.device("cpu")


def run_epoch(model, loader, device, loss_fn, optimizer=None):
    training = optimizer is not None
    model.train(training)
    losses, logits, labels, identifiers = [], [], [], []
    with torch.set_grad_enabled(training):
        for images, targets, image_ids in loader:
            images, targets = images.to(device), targets.to(device)
            output = model(images); loss = loss_fn(output, targets)
            if training:
                optimizer.zero_grad(); loss.backward(); optimizer.step()
            losses.append(float(loss.detach().cpu())); logits.append(output.detach().cpu().numpy()); labels.append(targets.detach().cpu().numpy()); identifiers.extend(image_ids)
    return float(np.mean(losses)), np.concatenate(logits), np.concatenate(labels), identifiers


def feature_vectors(model, loader, device) -> tuple[np.ndarray, np.ndarray]:
    features, targets = [], []
    capture: list[torch.Tensor] = []
    hook = model.fc.register_forward_pre_hook(lambda _module, inputs: capture.append(inputs[0].detach()))
    model.eval()
    try:
        with torch.inference_mode():
            for images, labels, _ids in loader:
                capture.clear(); model(images.to(device))
                features.append(capture[0].cpu().numpy()); targets.append(labels.numpy())
    finally:
        hook.remove()
    return np.concatenate(features), np.concatenate(targets)


def capped_rows(rows: list[dict], cap: int, seed: int) -> list[dict]:
    selected = []
    for label in CLASSES:
        candidates = sorted((row for row in rows if row["label"] == label), key=lambda row: row["image_id"])
        rng = random.Random(f"{seed}:{label}"); rng.shuffle(candidates)
        selected.extend(candidates[:cap])
    return selected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--max-train-per-class", type=int, default=4000)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--seed", type=int, default=20260907)
    parser.add_argument("--device", choices=("mps", "cuda", "cpu"), default="mps")
    parser.add_argument("--minimum-internal-balanced-accuracy", type=float, default=0.70)
    parser.add_argument("--minimum-external-balanced-accuracy", type=float, default=0.65)
    args = parser.parse_args()
    if args.epochs < 1 or args.batch_size < 1 or args.max_train_per_class < 100:
        raise SystemExit("epochs, batch size and max train samples must be positive; max train samples must be at least 100.")
    manifest_path = args.dataset_dir / "manifest.csv"
    summary_path = args.dataset_dir / "dataset_summary.json"
    if not manifest_path.is_file() or not summary_path.is_file():
        raise SystemExit("Run prepare_onychomycosis_dataset.py first.")
    with manifest_path.open(encoding="utf-8", newline="") as file: rows = list(csv.DictReader(file))
    if not rows: raise SystemExit("Prepared manifest is empty.")
    split_rows = {name: [row for row in rows if row["split"] == name] for name in ("train", "validation", "internal_test", "external_test")}
    leakage = validate_grouped_splits([row for row in rows if row["split"] != "external_test"], "group_id")
    if leakage: raise SystemExit("Grouped split leakage: " + "; ".join(leakage[:5]))
    if any(not split_rows[name] for name in split_rows): raise SystemExit("Every internal and external split must contain records.")
    if any(not (args.dataset_dir / row["image_path"]).is_file() for row in rows): raise SystemExit("Prepared image crop is missing.")
    seed_everything(args.seed); device = device_for(args.device)
    selected_train = capped_rows(split_rows["train"], args.max_train_per_class, args.seed)
    train_tf = transforms.Compose([transforms.Resize((160, 160)), transforms.RandomHorizontalFlip(), transforms.RandomRotation(8), transforms.ColorJitter(brightness=0.08, contrast=0.08), transforms.ToTensor(), transforms.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225))])
    eval_tf = transforms.Compose([transforms.Resize((160, 160)), transforms.ToTensor(), transforms.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225))])
    loaders = {
        "train": DataLoader(NailDataset(selected_train, args.dataset_dir, train_tf), batch_size=args.batch_size, shuffle=True, num_workers=0),
        **{name: DataLoader(NailDataset(records, args.dataset_dir, eval_tf), batch_size=args.batch_size, shuffle=False, num_workers=0) for name, records in split_rows.items() if name != "train"},
    }
    model = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1)
    for parameter in model.parameters(): parameter.requires_grad = False
    model.fc = nn.Linear(model.fc.in_features, len(CLASSES)); model.to(device)
    loss_fn = nn.CrossEntropyLoss(); optimizer = torch.optim.AdamW(model.fc.parameters(), lr=args.learning_rate, weight_decay=1e-4)
    best_state, best_loss, history = None, float("inf"), []
    for epoch in range(1, args.epochs + 1):
        train_loss, _, _, _ = run_epoch(model, loaders["train"], device, loss_fn, optimizer)
        validation_loss, _, _, _ = run_epoch(model, loaders["validation"], device, loss_fn)
        history.append({"epoch": epoch, "train_loss": round(train_loss, 6), "validation_loss": round(validation_loss, 6)})
        if validation_loss < best_loss:
            best_loss = validation_loss; best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
    if best_state is None: raise RuntimeError("Training did not produce a model state.")
    model.load_state_dict(best_state)
    _vloss, validation_logits, validation_labels, _ = run_epoch(model, loaders["validation"], device, loss_fn)
    temperature, calibration_metrics = fit_temperature(validation_logits, validation_labels)
    internal_loss, internal_logits, internal_labels, _ = run_epoch(model, loaders["internal_test"], device, loss_fn)
    external_loss, external_logits, external_labels, external_ids = run_epoch(model, loaders["external_test"], device, loss_fn)
    internal_metrics = multiclass_metrics(internal_labels, softmax(internal_logits / temperature), CLASSES)
    external_metrics = multiclass_metrics(external_labels, softmax(external_logits / temperature), CLASSES)
    validation_features, validation_feature_labels = feature_vectors(model, loaders["validation"], device)
    train_features, train_feature_labels = feature_vectors(model, DataLoader(NailDataset(selected_train, args.dataset_dir, eval_tf), batch_size=args.batch_size, shuffle=False, num_workers=0), device)
    centroids = np.stack([train_features[train_feature_labels == index].mean(axis=0) for index in range(len(CLASSES))])
    centroids /= np.linalg.norm(centroids, axis=1, keepdims=True) + 1e-12
    normalised_validation = validation_features / (np.linalg.norm(validation_features, axis=1, keepdims=True) + 1e-12)
    distances = 1 - normalised_validation @ centroids.T
    ood_threshold = float(np.quantile(distances.min(axis=1), 0.98))
    version = "onychomycosis-resnet18-research-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    passes = internal_metrics["balanced_accuracy"] >= args.minimum_internal_balanced_accuracy and external_metrics["balanced_accuracy"] >= args.minimum_external_balanced_accuracy
    status = "RESEARCH_READY_FOR_SCOPED_SCREENING" if passes else "REJECTED_FOR_APPLICATION_INFERENCE"
    args.output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint = {
        "model_id": MODEL_ID, "model_version": version, "status": status, "architecture": "ImageNet-initialised ResNet-18 with trained classification head", "classes": list(CLASSES),
        "input_size": [160, 160], "preprocessing": "RGB; resize 160x160; ImageNet normalization", "dataset_version": DATASET_VERSION, "pipeline_version": PIPELINE_VERSION,
        "ood_reference": {"method": "nearest class-centroid cosine distance in penultimate ResNet feature space", "centroids": centroids.tolist(), "threshold": round(ood_threshold, 6), "threshold_quantile": 0.98, "fit_split": "independent validation split"},
        "state_dict": model.state_dict(),
    }
    torch.save(checkpoint, args.output_dir / "model.pt")
    calibration = {"schema_version": CALIBRATION_SCHEMA_VERSION, "model_id": MODEL_ID, "model_version": version, "dataset_version": DATASET_VERSION, "calibration_version": version + "-temperature-validation", "validation_split": "validation", "method": "temperature_scaling", "temperature": temperature, "class_order": list(CLASSES), "metrics": calibration_metrics, "status": "RESEARCH_CALIBRATION"}
    with (args.output_dir / "calibration.json").open("w", encoding="utf-8") as file: json.dump(calibration, file, indent=2)
    report = {
        "status": status, "promotion_thresholds": {"minimum_internal_balanced_accuracy": args.minimum_internal_balanced_accuracy, "minimum_external_balanced_accuracy": args.minimum_external_balanced_accuracy},
        "model": {key: checkpoint[key] for key in ("model_id", "model_version", "architecture", "classes", "input_size", "preprocessing", "dataset_version", "pipeline_version")},
        "dataset": json.load(summary_path.open(encoding="utf-8")), "environment": {"python": platform.python_version(), "torch": torch.__version__, "device": str(device), "seed": args.seed},
        "training": {"epochs": args.epochs, "batch_size": args.batch_size, "selected_training_count": len(selected_train), "history": history, "best_validation_loss": round(best_loss, 6)},
        "calibration": calibration_metrics, "internal_test": {"loss": round(internal_loss, 6), "metrics": internal_metrics},
        "external_test": {"loss": round(external_loss, 6), "metrics": external_metrics, "sample_count": len(external_ids), "normal_class_status": "NOT_AVAILABLE_IN_EXTERNAL_COHORT"},
        "ood": checkpoint["ood_reference"], "limitations": ["Research-only model; not clinical validation or a diagnostic device.", "Source patient IDs are unavailable, so internal splitting is contact-sheet grouped rather than patient-level.", "Normal-appearing nail is evaluated internally only; the external cohort has disease classes only.", "No lesion/nail segmentation, severity model, or treatment-selection model is included."],
    }
    with (args.output_dir / "evaluation_report.json").open("w", encoding="utf-8") as file: json.dump(report, file, indent=2)
    print(json.dumps({"status": status, "output_dir": str(args.output_dir), "internal_balanced_accuracy": internal_metrics["balanced_accuracy"], "external_balanced_accuracy": external_metrics["balanced_accuracy"]}, indent=2))


if __name__ == "__main__":
    main()
