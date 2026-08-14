"""Research-only HAM10000 dermatoscopic lesion classifier.

Weights: Tschandl et al.'s ResNet-34 research model, distributed under MIT.
This module is intentionally limited to dermatoscopic single-lesion images. It
is not validated for face photos, selfies, hair, nails, sweat-gland concerns,
or clinical decision-making.
"""

from __future__ import annotations

import io
import os
import base64
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
LOW_CONFIDENCE_THRESHOLD = 0.50


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
    """Return research labels plus a Grad-CAM attention map for dermoscopy only."""
    model = load_model()
    if model is None:
        return {"available": False, "reason": "Research weights are not installed.", "notice": RESEARCH_NOTICE}
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    tensor = transforms.Compose([transforms.Resize(280), transforms.CenterCrop(224), transforms.ToTensor()])(image).unsqueeze(0)
    activations = []
    hook = model.layer4.register_forward_hook(lambda _module, _inputs, output: activations.append(output))
    try:
        model.zero_grad(set_to_none=True)
        logits = model(tensor)
        predicted_index = int(logits.argmax(dim=1).item())
        activations[0].retain_grad()
        logits[0, predicted_index].backward()
        gradients = activations[0].grad[0]
        weights = gradients.mean(dim=(1, 2), keepdim=True)
        attention = functional.relu((weights * activations[0][0]).sum(dim=0, keepdim=True))
        attention = functional.interpolate(attention.unsqueeze(0), size=(224, 224), mode="bilinear", align_corners=False)[0, 0]
        attention = attention - attention.min()
        attention = attention / (attention.max() + 1e-8)
        attention_image = Image.fromarray((attention.detach().cpu().numpy() * 255).astype("uint8"), mode="L")
        buffer = io.BytesIO()
        attention_image.save(buffer, format="PNG")
        attention_base64 = base64.b64encode(buffer.getvalue()).decode("ascii")
        probabilities = functional.softmax(logits, dim=1)[0].detach().cpu().tolist()
    finally:
        hook.remove()
    ranked = sorted(zip(CLASSES, probabilities), key=lambda value: value[1], reverse=True)
    top_probability = float(ranked[0][1])
    return {
        "available": True,
        "model": "HAM10000 ResNet-34 research model", "model_version": "Tschandl-2020-resnet34", "image_requirement": "Single, in-focus dermatoscopic lesion image only—not a face photo or selfie.",
        "top_predictions": [{"code": code, "label": LABELS[code], "probability": round(probability, 4)} for code, probability in ranked[:3]],
        "top_prediction": {"condition": LABELS[ranked[0][0]], "confidence": round(top_probability, 4)},
        "alternatives": [{"condition": LABELS[code], "confidence": round(probability, 4)} for code, probability in ranked[1:3]],
        "model_confidence": round(top_probability, 4), "uncertainty": round(1 - top_probability, 4), "low_confidence": top_probability < LOW_CONFIDENCE_THRESHOLD,
        "below_confidence_threshold": top_probability < LOW_CONFIDENCE_THRESHOLD, "confidence_threshold": LOW_CONFIDENCE_THRESHOLD,
        "confidence_notice": "AI model confidence reflects its relative output for this research image domain, not the chance that a patient has a condition.",
        "attention_map": {"image": f"data:image/png;base64,{attention_base64}", "label": "Grad-CAM research attention map — not a lesion segmentation or medical finding."},
        "explainability": {"method": "Grad-CAM", "heatmap": f"data:image/png;base64,{attention_base64}", "explanation_text": "Highlighted image regions contributed most to this research model output. They do not identify a diagnosis or lesion boundary."},
        "notice": RESEARCH_NOTICE,
    }
