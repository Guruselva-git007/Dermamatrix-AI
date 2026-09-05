"""Strict calibration and uncertainty boundary for compatible classifiers.

No artifact is shipped with the project. Therefore raw softmax outputs are
never presented as calibrated condition likelihoods. A caller can opt in only
by supplying a version-matched temperature-scaling artifact fitted on an
independent validation split.
"""

from __future__ import annotations

import json
import math
import os
from functools import lru_cache
from typing import Sequence


CALIBRATION_SCHEMA_VERSION = "dermamatrix-calibration-v1"


def _softmax(values: Sequence[float]) -> list[float]:
    maximum = max(values)
    exponentials = [math.exp(value - maximum) for value in values]
    denominator = sum(exponentials)
    return [value / denominator for value in exponentials]


def calibration_path(model_id: str) -> str:
    configured = os.getenv("DERMAMATRIX_CALIBRATION_PATH", "").strip()
    if configured:
        return configured
    return os.path.join(os.path.dirname(__file__), "models", f"{model_id}_calibration.json")


@lru_cache(maxsize=8)
def load_temperature_calibration(model_id: str, model_version: str, class_order: tuple[str, ...]) -> dict:
    """Load only a complete, version-matched calibration artifact."""
    path = calibration_path(model_id)
    unavailable = {
        "available": False,
        "status": "NOT_CONFIGURED",
        "calibration_version": None,
        "method": None,
        "notice": "No compatible calibration artifact is configured; raw model scores are not shown as condition likelihoods.",
    }
    if not os.path.isfile(path):
        return unavailable
    try:
        with open(path, encoding="utf-8") as file:
            artifact = json.load(file)
        if artifact.get("schema_version") != CALIBRATION_SCHEMA_VERSION:
            raise ValueError("unsupported schema version")
        if artifact.get("model_id") != model_id or artifact.get("model_version") != model_version:
            raise ValueError("model lineage does not match")
        if tuple(artifact.get("class_order") or ()) != class_order:
            raise ValueError("class order does not match")
        if artifact.get("method") != "temperature_scaling":
            raise ValueError("only temperature scaling is supported by this runtime")
        temperature = float(artifact.get("temperature"))
        if not 0.05 <= temperature <= 10:
            raise ValueError("temperature is outside the accepted range")
        if not artifact.get("calibration_version") or not artifact.get("dataset_version") or not artifact.get("validation_split"):
            raise ValueError("artifact is missing independent-validation provenance")
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        return {
            "available": False,
            "status": "INVALID_ARTIFACT",
            "calibration_version": None,
            "method": None,
            "notice": f"Calibration artifact is not usable: {error}. Raw model scores are not shown as condition likelihoods.",
        }
    return {
        "available": True,
        "status": "AVAILABLE",
        "calibration_version": artifact["calibration_version"],
        "dataset_version": artifact["dataset_version"],
        "validation_split": artifact["validation_split"],
        "method": artifact["method"],
        "temperature": temperature,
        "metrics": artifact.get("metrics", {}),
        "notice": "Temperature scaling was loaded from a version-matched independent-validation artifact.",
    }


def calibrated_probabilities(logits: Sequence[float], calibration: dict) -> list[float] | None:
    """Return calibrated probabilities only when a valid artifact is loaded."""
    if not calibration.get("available"):
        return None
    temperature = float(calibration["temperature"])
    return _softmax([float(value) / temperature for value in logits])


def prediction_uncertainty(probabilities: Sequence[float] | None) -> dict:
    """Describe uncertainty without pretending an OOD detector exists."""
    if not probabilities:
        return {
            "status": "UNCERTAIN",
            "certainty": "NOT_AVAILABLE",
            "entropy": None,
            "margin": None,
            "ood_status": "OOD_NOT_EVALUATED",
            "notice": "Calibrated probabilities and a fitted OOD detector are unavailable, so no condition likelihood or in-domain claim is made.",
        }
    ranked = sorted((float(value) for value in probabilities), reverse=True)
    class_count = len(ranked)
    entropy = -sum(value * math.log(value + 1e-12) for value in ranked) / math.log(class_count)
    margin = ranked[0] - ranked[1] if class_count > 1 else ranked[0]
    certainty = "LOW" if ranked[0] < 0.5 or margin < 0.1 or entropy > 0.8 else "MODERATE" if ranked[0] < 0.75 or margin < 0.25 else "HIGH"
    return {
        "status": "LOW_CONFIDENCE" if certainty == "LOW" else "CALIBRATED_OUTPUT",
        "certainty": certainty,
        "entropy": round(entropy, 4),
        "margin": round(margin, 4),
        "ood_status": "OOD_NOT_EVALUATED",
        "notice": "Certainty is derived from calibrated class distribution entropy and margin. This deployment has no fitted OOD detector, so it does not label an image in-domain or out-of-distribution.",
    }
