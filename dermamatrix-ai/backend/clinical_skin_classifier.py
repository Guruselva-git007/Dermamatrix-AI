"""Local, research-only five-class classifier for ordinary clinical skin photos."""

from __future__ import annotations

import hashlib
import io
import os
from functools import lru_cache

from PIL import Image, ImageOps

from calibration_service import prediction_uncertainty
from model_metadata import CLINICAL_SKIN_MODEL_ID, CLINICAL_SKIN_MODEL_VERSION, CLINICAL_SKIN_DATASET_VERSION, CLINICAL_SKIN_PIPELINE_VERSION


WEIGHTS_PATH = os.path.join(os.path.dirname(__file__), "models", "clinical_skin_best_model.pth")
WEIGHTS_SHA256 = "eba9a581505c60cee98152c790c4113a1549c691248d518cc5d1e7097feb20bc"
CLASSES = (
    "Eczema / dermatitis", "Urticaria / allergic reaction", "Folliculitis / acne-like",
    "Psoriasis / papulosquamous", "Lesion — dermoscopic review recommended",
)
PREPROCESSING = "EXIF transpose; RGB; resize to 224x224; ImageNet mean/std normalization"


def weights_available() -> bool:
    return os.path.isfile(WEIGHTS_PATH)


@lru_cache(maxsize=1)
def load_model():
    if not weights_available():
        return None
    with open(WEIGHTS_PATH, "rb") as checkpoint_file:
        checksum = hashlib.file_digest(checkpoint_file, "sha256").hexdigest()
    if checksum != WEIGHTS_SHA256:
        raise ValueError("Clinical skin checkpoint checksum mismatch")
    import torch
    from torchvision import models

    model = models.efficientnet_b0(weights=None)
    model.classifier[1] = torch.nn.Linear(model.classifier[1].in_features, len(CLASSES))
    checkpoint = torch.load(WEIGHTS_PATH, map_location="cpu", weights_only=True)
    expected_mapping = {label: index for index, label in enumerate(CLASSES)}
    if checkpoint.get("class_to_idx") != expected_mapping:
        raise ValueError("Clinical skin checkpoint class order differs from the verified mapping")
    model.load_state_dict(checkpoint["model_state_dict"], strict=True)
    model.eval()
    return model


def classify_clinical_skin_photo(image_bytes: bytes) -> dict:
    model = load_model()
    if model is None:
        return {"available": False, "reason": "Local clinical-skin research weights are not installed."}
    import torch
    from torchvision import transforms

    image = ImageOps.exif_transpose(Image.open(io.BytesIO(image_bytes))).convert("RGB")
    tensor = transforms.Compose([
        transforms.Resize((224, 224)), transforms.ToTensor(),
        transforms.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
    ])(image).unsqueeze(0)
    with torch.inference_mode():
        logits = model(tensor)[0]
        probabilities = torch.softmax(logits, dim=0).tolist()
    ranked = sorted(enumerate(probabilities), key=lambda item: item[1], reverse=True)
    predictions = [
        {"code": CLASSES[index], "label": CLASSES[index], "relative_score": round(float(score), 4),
         "calibrated_probability": None}
        for index, score in ranked
    ]
    top_index, top_score = ranked[0]
    uncertainty = prediction_uncertainty(probabilities, score_kind="raw_softmax")
    return {
        "available": True, "model": "clinical Skin EfficientNet research adapter",
        "model_id": CLINICAL_SKIN_MODEL_ID, "model_version": CLINICAL_SKIN_MODEL_VERSION,
        "dataset_version": CLINICAL_SKIN_DATASET_VERSION, "pipeline_version": CLINICAL_SKIN_PIPELINE_VERSION,
        "image_requirement": "Ordinary skin close-up or body/face skin photo; not dermoscopy. Anatomy is user-declared, not automatically verified.",
        "top_predictions": predictions, "raw_logits": [round(float(value), 6) for value in logits.tolist()],
        "class_order": list(CLASSES), "preprocessing": PREPROCESSING, "input_shape": [1, 3, 224, 224],
        "top_prediction": {"condition": CLASSES[top_index], "relative_score": round(float(top_score), 4),
                           "calibrated_probability": None, "target_class_index": top_index},
        "alternatives": [{"condition": item["label"], "relative_score": item["relative_score"],
                          "calibrated_probability": None} for item in predictions[1:]],
        "condition_likelihood": {"available": False, "status": "NOT_AVAILABLE", "estimated_likelihood": None,
                                 "notice": "No version-matched independent-validation calibration is installed."},
        "calibration": {"available": False, "status": "NOT_CONFIGURED", "calibration_version": None},
        "uncertainty": uncertainty,
        "normal_appearance": {"available": False, "status": "NO_HEALTHY_CLASS", "is_normal": None,
                              "validated": False, "confidence": None, "minimum_confidence": None,
                              "condition_signal": "NOT_EVALUATED", "notice": "This five-class model cannot assess normal appearance."},
        "model_confidence": round(float(top_score), 4), "model_confidence_kind": "raw_softmax",
        "non_condition_top_class": top_index == 4,
        "raw_top_score": round(float(top_score), 4), "low_confidence": uncertainty["certainty"] == "LOW",
        "below_confidence_threshold": uncertainty["certainty"] == "LOW", "confidence_threshold": 0.5,
        "confidence_notice": "Raw softmax compares the five trained labels only, not disease likelihood.",
        "explainability": {"method": "not_available", "explanation_text": "No validated visual attribution is available for this adapter."},
        "notice": "Research-only local model ranking. The upstream publisher reports lower performance on smartphone SCIN images and no clinical validation. The lesion class is a review prompt, not a cancer result. No OOD detector or calibrated likelihood is configured; this is not a diagnosis.",
    }
