"""Research-only HAM10000 dermatoscopic lesion classifier.

Weights: Tschandl et al.'s ResNet-34 research model, distributed under MIT.
This module is intentionally limited to dermatoscopic single-lesion images. It
is not validated for face photos, selfies, hair, nails, sweat-gland concerns,
or clinical decision-making.
"""

from __future__ import annotations

import io
import os
from functools import lru_cache

import torch
import torch.nn.functional as functional
from PIL import Image
from torchvision import models, transforms


WEIGHTS_PATH = os.path.join(os.path.dirname(__file__), "models", "ham10000_resnet34_research.ptw")
CLASSES = ("akiec", "bcc", "bkl", "df", "mel", "nv", "vasc")
LABELS = {
    "akiec": "Actinic keratoses / intraepithelial carcinoma", "bcc": "Basal cell carcinoma", "bkl": "Benign keratosis-like lesion",
    "df": "Dermatofibroma", "mel": "Melanoma", "nv": "Melanocytic nevus", "vasc": "Vascular lesion",
}
RESEARCH_NOTICE = "Research-only model output. It is not a diagnosis, medical advice, or a replacement for RMP assessment."


@lru_cache(maxsize=1)
def load_model():
    if not os.path.exists(WEIGHTS_PATH):
        return None
    model = models.resnet34(weights=None)
    model.fc = torch.nn.Linear(model.fc.in_features, len(CLASSES))
    state = torch.load(WEIGHTS_PATH, map_location="cpu", weights_only=True)
    model.load_state_dict(state)
    model.eval()
    return model


def classify_dermoscopic_lesion(image_bytes: bytes) -> dict:
    """Return top research labels for a dermatoscopic lesion image."""
    model = load_model()
    if model is None:
        return {"available": False, "reason": "Research weights are not installed.", "notice": RESEARCH_NOTICE}
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    tensor = transforms.Compose([transforms.Resize(280), transforms.CenterCrop(224), transforms.ToTensor()])(image).unsqueeze(0)
    with torch.inference_mode():
        probabilities = functional.softmax(model(tensor), dim=1)[0].tolist()
    ranked = sorted(zip(CLASSES, probabilities), key=lambda value: value[1], reverse=True)
    return {
        "available": True,
        "model": "HAM10000 ResNet-34 research model", "model_version": "Tschandl-2020-resnet34", "image_requirement": "Single, in-focus dermatoscopic lesion image only—not a face photo or selfie.",
        "top_predictions": [{"code": code, "label": LABELS[code], "probability": round(probability, 4)} for code, probability in ranked[:3]],
        "notice": RESEARCH_NOTICE,
    }
