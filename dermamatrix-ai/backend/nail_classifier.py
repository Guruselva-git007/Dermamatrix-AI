"""Local research ranking for declared nail close-up photographs.

The upstream MIT checkpoint has a class list and internal test metrics, but no
published inference transform or external clinical validation.  This adapter
uses the conventional ImageNet ConvNeXt transform and states that assumption
in every result.  It never interprets softmax as disease probability.
"""

from __future__ import annotations

import hashlib
import io
import os
from functools import lru_cache

from PIL import Image, ImageOps

from calibration_service import prediction_uncertainty
from model_metadata import NAIL_MODEL_ID, NAIL_MODEL_VERSION, NAIL_DATASET_VERSION, NAIL_PIPELINE_VERSION


WEIGHTS_PATH = os.path.join(os.path.dirname(__file__), "models", "nail_convnexttiny_research.pth")
WEIGHTS_SHA256 = "6c58cd98c9368268115d00f6acd6d1f03dba73132eaacd15cbfa9cf9dfb5bf19"
CLASSES = (
    "Melanonychia", "Beau's Lines", "Blue Nail", "Clubbing", "Healthy Nail",
    "Koilonychia", "Muehrcke's Lines", "Onychogryphosis", "Pitting", "Terry's Nails",
)
PREPROCESSING = "EXIF transpose; RGB; resize short edge to 236; center crop 224; ImageNet mean/std normalization (assumed; upstream transform unpublished)"


def weights_available() -> bool:
    return os.path.isfile(WEIGHTS_PATH)


@lru_cache(maxsize=1)
def load_model():
    if not weights_available():
        return None
    with open(WEIGHTS_PATH, "rb") as checkpoint:
        checksum = hashlib.file_digest(checkpoint, "sha256").hexdigest()
    if checksum != WEIGHTS_SHA256:
        raise ValueError("Nail checkpoint checksum mismatch")
    import torch
    from torchvision import models

    model = models.convnext_tiny(weights=None)
    model.classifier[2] = torch.nn.Linear(model.classifier[2].in_features, len(CLASSES))
    state = torch.load(WEIGHTS_PATH, map_location="cpu", weights_only=True)
    model.load_state_dict(state, strict=True)
    model.eval()
    return model


def classify_nail_photo(image_bytes: bytes) -> dict:
    model = load_model()
    if model is None:
        return {"available": False, "reason": "Local nail research weights are not installed."}
    import torch
    from torchvision import transforms

    image = ImageOps.exif_transpose(Image.open(io.BytesIO(image_bytes))).convert("RGB")
    transform = transforms.Compose([
        transforms.Resize(236), transforms.CenterCrop(224), transforms.ToTensor(),
        transforms.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
    ])
    tensor = transform(image).unsqueeze(0)
    with torch.inference_mode():
        logits = model(tensor)[0]
        probabilities = torch.softmax(logits, dim=0).tolist()
    ranked = sorted(enumerate(probabilities), key=lambda value: value[1], reverse=True)
    predictions = [
        {"code": CLASSES[index], "label": CLASSES[index], "calibrated_probability": None,
         "relative_score": round(float(score), 4)}
        for index, score in ranked[:5]
    ]
    top_index, top_score = ranked[0]
    uncertainty = prediction_uncertainty(probabilities, score_kind="raw_softmax")
    return {
        "available": True,
        "model": "Nail ConvNeXt research adapter",
        "model_id": NAIL_MODEL_ID, "model_version": NAIL_MODEL_VERSION,
        "dataset_version": NAIL_DATASET_VERSION, "pipeline_version": NAIL_PIPELINE_VERSION,
        "image_requirement": "Declared in-focus nail close-up. The app does not automatically verify anatomy.",
        "top_predictions": predictions,
        "raw_logits": [round(float(value), 6) for value in logits.tolist()],
        "class_order": list(CLASSES), "preprocessing": PREPROCESSING, "input_shape": [1, 3, 224, 224],
        "top_prediction": {"condition": CLASSES[top_index], "calibrated_probability": None,
                           "relative_score": round(float(top_score), 4), "target_class_index": top_index},
        "alternatives": [{"condition": item["label"], "calibrated_probability": None,
                          "relative_score": item["relative_score"]} for item in predictions[1:]],
        "condition_likelihood": {"available": False, "status": "NOT_AVAILABLE", "estimated_likelihood": None,
                                 "notice": "No version-matched calibration or external nail-photo validation is available."},
        "calibration": {"available": False, "status": "NOT_CONFIGURED", "calibration_version": None},
        "uncertainty": uncertainty,
        "normal_appearance": {"available": False, "status": "UNVALIDATED_HEALTHY_CLASS", "is_normal": None,
                              "validated": False, "confidence": None, "minimum_confidence": None,
                              "condition_signal": "NOT_EVALUATED",
                              "notice": "The Healthy Nail class is unvalidated for ruling out nail conditions."},
        "model_confidence": round(float(top_score), 4), "model_confidence_kind": "raw_softmax",
        "non_condition_top_class": CLASSES[top_index] == "Healthy Nail",
        "raw_top_score": round(float(top_score), 4), "low_confidence": uncertainty["certainty"] == "LOW",
        "below_confidence_threshold": uncertainty["certainty"] == "LOW", "confidence_threshold": 0.5,
        "confidence_notice": "Raw softmax compares this model's ten labels only; it is not a disease probability.",
        "explainability": {"method": "not_available", "explanation_text": "No validated nail attention or segmentation map is available."},
        "notice": "Research-only local model ranking. Upstream inference transform is undocumented; ImageNet preprocessing is assumed. No external clinical validation, calibrated likelihood, or OOD detector is available. This is not a diagnosis.",
    }
