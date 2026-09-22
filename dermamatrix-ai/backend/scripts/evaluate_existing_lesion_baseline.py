#!/usr/bin/env python3
"""Evaluate the existing ResNet-34 adapter on the reconstructed held-out split.

This is a comparison baseline for ``run_skin_lesion_experiment.py``.  It uses
the same exact-hash grouped manifest and cache as the candidate experiment,
but preserves the currently deployed adapter's architecture and preprocessing.
The result is a research comparison, not clinical validation.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader
from torchvision import models, transforms


BACKEND_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = BACKEND_DIR / "scripts"
for directory in (BACKEND_DIR, SCRIPTS_DIR):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from ml_evaluation import multiclass_metrics  # noqa: E402
from run_skin_lesion_experiment import (  # noqa: E402
    CLASSES,
    SkinLesionDataset,
    device_for,
    prepare_records,
    render_confusion_matrix,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-zip", required=True, type=Path)
    parser.add_argument("--cache-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--checkpoint", default=BACKEND_DIR / "models" / "ham10000_resnet34_research.ptw", type=Path)
    parser.add_argument("--batch-size", default=48, type=int)
    parser.add_argument("--device", default="auto", choices=("auto", "mps", "cpu"))
    args = parser.parse_args()
    output = args.output_dir.resolve()
    records, audit = prepare_records(args.source_zip.resolve(), args.cache_dir.resolve(), output)
    test_rows = [record for record in records if record.split == "test"]
    device = device_for(args.device)
    model = models.resnet34(weights=None)
    model.fc = torch.nn.Linear(model.fc.in_features, len(CLASSES))
    model.load_state_dict(torch.load(args.checkpoint.resolve(), map_location="cpu", weights_only=True))
    model.eval().to(device)
    # This intentionally matches the deployed ``lesion_classifier`` adapter.
    deployed_transform = transforms.Compose([transforms.Resize(280), transforms.CenterCrop(224), transforms.ToTensor()])
    loader = DataLoader(SkinLesionDataset(test_rows, args.cache_dir.resolve(), deployed_transform), batch_size=args.batch_size, shuffle=False, num_workers=0)
    logits_batches, label_batches, ids = [], [], []
    started = time.perf_counter()
    with torch.inference_mode():
        for tensors, labels, image_ids in loader:
            logits_batches.append(model(tensors.to(device)).cpu().numpy())
            label_batches.append(labels.numpy())
            ids.extend(image_ids)
    elapsed = time.perf_counter() - started
    logits = np.concatenate(logits_batches)
    labels = np.concatenate(label_batches)
    probabilities = torch.softmax(torch.tensor(logits), dim=1).numpy()
    metrics = multiclass_metrics(labels, probabilities, CLASSES)
    by_id = {record.image_id: record for record in test_rows}
    rows = []
    for index, (image_id, true_index, scores) in enumerate(zip(ids, labels, probabilities, strict=True)):
        prediction = int(np.argmax(scores))
        rows.append({
            "image_id": image_id,
            "true_label": CLASSES[int(true_index)],
            "predicted_label": CLASSES[prediction],
            "relative_score": round(float(scores[prediction]), 6),
            "correct": bool(prediction == int(true_index)),
            "source_members": by_id[image_id].source_members,
            **{f"score_{label}": round(float(scores[class_index]), 6) for class_index, label in enumerate(CLASSES)},
        })
    with (output / "existing_resnet34_baseline_predictions.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    render_confusion_matrix(metrics, output / "existing_resnet34_baseline_confusion_matrix.png")
    report = {
        "model": "ham10000_resnet34_research.ptw",
        "architecture": "ResNet-34",
        "checkpoint": "Local runtime artifact backend/models/ham10000_resnet34_research.ptw (not committed)",
        "evaluation": "Exact-hash-grouped held-out source split reconstructed by the shared experiment runner.",
        "preprocessing": "Matches the deployed adapter: RGB conversion; resize short edge 280; centre crop 224; tensor conversion.",
        "calibration": "NOT_CONFIGURED; metrics use raw softmax rankings and do not establish condition likelihoods.",
        "metrics": metrics,
        "timing": {"total_seconds": round(elapsed, 4), "mean_seconds_per_image": round(elapsed / len(labels), 6)},
        "dataset_audit": audit,
        "limitations": [
            "No patient IDs, near-duplicate guarantee, external validation, or clinical validation are available.",
            "This comparison does not make the existing model calibrated or clinically validated.",
        ],
    }
    with (output / "existing_resnet34_baseline.json").open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)
    print(json.dumps({"accuracy": metrics["accuracy"], "balanced_accuracy": metrics["balanced_accuracy"], "macro_f1": metrics["macro_f1"], "mean_seconds_per_image": report["timing"]["mean_seconds_per_image"]}, indent=2))


if __name__ == "__main__":
    main()
