"""Scoped lesion-region extraction for dermatoscopic research images.

This is a deterministic image-processing baseline, not a trained U-Net and not
validated clinical lesion segmentation. It is deliberately unavailable for
selfies, hair/scalp, nails, sweat concerns, and ordinary camera photos.
"""

from __future__ import annotations

import base64
import io

import numpy as np
from PIL import Image, ImageFilter


NOTICE = "Research image-region extraction only; it is not validated lesion segmentation or a medical finding."


def _otsu_threshold(values: np.ndarray) -> int:
    histogram = np.bincount(values.ravel(), minlength=256).astype(float)
    total = values.size
    weighted_total = np.dot(np.arange(256), histogram)
    weight_background = 0.0
    sum_background = 0.0
    best_threshold, best_variance = 0, -1.0
    for threshold in range(256):
        weight_background += histogram[threshold]
        if weight_background == 0:
            continue
        weight_foreground = total - weight_background
        if weight_foreground == 0:
            break
        sum_background += threshold * histogram[threshold]
        mean_background = sum_background / weight_background
        mean_foreground = (weighted_total - sum_background) / weight_foreground
        variance = weight_background * weight_foreground * (mean_background - mean_foreground) ** 2
        if variance > best_variance:
            best_threshold, best_variance = threshold, variance
    return best_threshold


def _data_url(image: Image.Image) -> str:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def extract_dermoscopic_region(image_bytes: bytes) -> dict:
    """Extract a candidate darker region and return a transparent overlay.

    The coverage and contrast checks are quality signals only. They are not a
    segmentation-model confidence score.
    """
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image.thumbnail((600, 600))
    base = np.asarray(image, dtype=np.uint8)
    gray = np.asarray(image.convert("L").filter(ImageFilter.MedianFilter(size=3)), dtype=np.uint8)
    threshold = _otsu_threshold(gray)
    mask = gray < threshold
    coverage = float(mask.mean() * 100)
    inside = gray[mask]
    outside = gray[~mask]
    contrast = float(abs(inside.mean() - outside.mean())) if inside.size and outside.size else 0.0
    plausible = 0.4 <= coverage <= 65 and contrast >= 9
    rgba = np.zeros((*mask.shape, 4), dtype=np.uint8)
    rgba[mask] = (12, 187, 157, 120)
    overlay = Image.alpha_composite(image.convert("RGBA"), Image.fromarray(rgba, mode="RGBA"))
    message = "Candidate region extracted for research review." if plausible else "Candidate region is unreliable; retake a centred, evenly lit dermatoscopic image."
    return {
        "available": True,
        "method": "Otsu contrast baseline",
        "validated": False,
        "reliable": plausible,
        "affected_area_percent": round(coverage, 1) if plausible else None,
        "contrast_signal": round(contrast, 1),
        "overlay": _data_url(overlay),
        "mask": _data_url(Image.fromarray((mask * 255).astype("uint8"), mode="L")),
        "notice": NOTICE,
        "message": message,
    }


def unavailable_region(reason: str) -> dict:
    return {"available": False, "reliable": False, "affected_area_percent": None, "notice": NOTICE, "message": reason}
