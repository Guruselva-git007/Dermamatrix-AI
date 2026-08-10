"""Runnable, non-clinical screening-triage model for the college prototype.

The coefficients below are deliberately conservative demonstration parameters;
they are not trained on patient data and must not be used for diagnosis.
"""

from __future__ import annotations

from math import exp


MODEL_VERSION = "screening-triage-v1-demo"


def sigmoid(value: float) -> float:
    return 1 / (1 + exp(-value))


def run_screening_model(duration: int, discomfort: int, change: int, quality: int, image_features: dict) -> dict:
    """Combine non-diagnostic symptom signals with image quality into a triage score."""
    symptom_load = min(1.0, (max(0, duration) + max(0, discomfort) + max(0, change)) / 61)
    image_reliability = max(0.0, min(1.0, quality / 100))
    # Quality reduces model confidence, not a patient's risk.
    probability = sigmoid(-1.15 + 2.25 * symptom_load + 0.25 * (1 - image_reliability))
    risk_score = min(92, max(28, round(28 + probability * 64)))
    return {
        "name": "Screening-triage engine", "version": MODEL_VERSION, "risk_score": risk_score,
        "confidence": round(0.45 + image_reliability * 0.42, 2), "intended_use": "Educational triage support only; not a diagnosis model.",
        "inputs_used": {"symptom_duration": duration, "discomfort": discomfort, "recent_change": change, "image_quality": quality, "image_resolution": f"{image_features['width']}×{image_features['height']}"},
    }
