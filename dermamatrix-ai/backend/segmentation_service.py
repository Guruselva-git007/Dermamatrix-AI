"""Lesion segmentation provider and a clearly separated visual-region baseline.

The repository does not include trained segmentation weights.  The TorchScript
provider below is the real inference path for a compatible binary lesion model
when ``SEGMENTATION_MODEL_PATH`` is configured.  Until then, the API returns an
honest ``model_not_configured`` state.  The Otsu helper is retained only as a
visual candidate-region extraction step; it is never represented as model
segmentation.
"""

from __future__ import annotations

import base64
import io
import os
from functools import lru_cache

from PIL import Image, ImageFilter


NOTICE = "A trained lesion-segmentation model is required before a mask can be presented as model segmentation."
CANDIDATE_NOTICE = "Visual candidate-region extraction only; it is not lesion segmentation or a medical finding."


def _otsu_threshold(values: np.ndarray) -> int:
    import numpy as np

    histogram = np.bincount(values.ravel(), minlength=256).astype(float)
    total = values.size
    weighted_total = np.dot(np.arange(256), histogram)
    weight_background = sum_background = 0.0
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


def _data_url(image: Image.Image, *, image_format: str = "PNG") -> str:
    """Encode visual artifacts compactly without changing their pixel source.

    The browser only displays overlays; sending them as WebP avoids inflating
    each JSON assessment response with a large Base64 PNG. Binary masks stay
    lossless PNG so a configured segmentation provider never receives a
    lossy mask artifact.
    """
    buffer = io.BytesIO()
    if image_format == "WEBP":
        image.convert("RGB").save(buffer, format="WEBP", quality=82, method=4)
        mime_type = "image/webp"
    else:
        image.save(buffer, format="PNG")
        mime_type = "image/png"
    return f"data:{mime_type};base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


@lru_cache(maxsize=1)
def _load_segmentation_model():
    """Load a compatible TorchScript binary-segmentation model once."""
    model_path = os.getenv("SEGMENTATION_MODEL_PATH", "").strip()
    if not model_path or not os.path.isfile(model_path):
        return None, None
    import torch

    try:
        model = torch.jit.load(model_path, map_location="cpu")
        model.eval()
        return model, None
    except (RuntimeError, ValueError) as error:
        return None, str(error)


def _normalised_tensor(image: Image.Image) -> torch.Tensor:
    import numpy as np
    import torch

    resized = image.resize((256, 256), Image.Resampling.BILINEAR)
    values = np.asarray(resized, dtype=np.float32).transpose(2, 0, 1) / 255.0
    return torch.from_numpy((values - 0.5) / 0.5).unsqueeze(0)


def _probability_mask(logits: torch.Tensor, target_size: tuple[int, int]) -> np.ndarray:
    """Accept one-logit binary or two-channel logits from the configured model."""
    import torch
    import torch.nn.functional as functional

    if logits.ndim != 4 or logits.shape[0] != 1:
        raise ValueError("Segmentation model must return [1, C, H, W] logits.")
    if logits.shape[1] == 1:
        probabilities = torch.sigmoid(logits)
    elif logits.shape[1] == 2:
        probabilities = torch.softmax(logits, dim=1)[:, 1:2]
    else:
        raise ValueError("Segmentation model must return one or two channels.")
    probabilities = functional.interpolate(probabilities, size=target_size, mode="bilinear", align_corners=False)
    return probabilities[0, 0].detach().cpu().numpy()


def _overlay(image: Image.Image, mask: np.ndarray) -> Image.Image:
    import numpy as np

    rgba = np.zeros((*mask.shape, 4), dtype=np.uint8)
    rgba[mask] = (79, 163, 247, 122)
    # Pillow infers RGBA from the uint8 four-channel array. Supplying ``mode``
    # is deprecated and will stop working in a future Pillow release.
    return Image.alpha_composite(image.convert("RGBA"), Image.fromarray(rgba))


def segment_dermoscopic_lesion(image_bytes: bytes) -> dict:
    """Run configured trained segmentation weights, or report the truthful gap."""
    model, load_error = _load_segmentation_model()
    if load_error:
        return {
            "available": False,
            "status": "model_unavailable",
            "model": None,
            "affected_area_percent": None,
            "segmentation_confidence": None,
            "overlay": None,
            "mask": None,
            "notice": NOTICE,
            "message": "Configured segmentation weights could not be loaded. Check the TorchScript model path and output format.",
        }
    if model is None:
        return {
            "available": False,
            "status": "model_not_configured",
            "model": None,
            "affected_area_percent": None,
            "segmentation_confidence": None,
            "overlay": None,
            "mask": None,
            "notice": NOTICE,
            "message": "No trained lesion-segmentation weights are configured for this deployment.",
        }
    import torch

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    try:
        with torch.inference_mode():
            probabilities = _probability_mask(model(_normalised_tensor(image)), (image.height, image.width))
    except (RuntimeError, ValueError) as error:
        return {
            "available": False,
            "status": "model_error",
            "model": "TorchScript binary lesion segmentation model",
            "affected_area_percent": None,
            "segmentation_confidence": None,
            "overlay": None,
            "mask": None,
            "notice": NOTICE,
            "message": f"Segmentation model could not process this image: {error}",
        }
    mask = probabilities >= 0.5
    coverage = float(mask.mean() * 100)
    foreground = probabilities[mask]
    confidence = float(foreground.mean()) if foreground.size else 0.0
    return {
        "available": True,
        "status": "completed",
        "model": "Configured TorchScript binary lesion segmentation model",
        "affected_area_percent": round(coverage, 1),
        "segmentation_confidence": round(confidence, 4),
        "overlay": _data_url(_overlay(image, mask), image_format="WEBP"),
        # A two-dimensional uint8 array is inferred as an L-mode mask.
        "mask": _data_url(Image.fromarray((mask * 255).astype("uint8"))),
        "notice": "Segmentation confidence is the model's mean foreground output, not medical certainty.",
        "message": "Trained model segmentation completed.",
    }


def extract_visual_candidate_region(image_bytes: bytes) -> dict:
    """Extract a contrast-based visual candidate region, not model segmentation."""
    import numpy as np

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image.thumbnail((600, 600))
    gray = np.asarray(image.convert("L").filter(ImageFilter.MedianFilter(size=3)), dtype=np.uint8)
    threshold = _otsu_threshold(gray)
    mask = gray < threshold
    coverage = float(mask.mean() * 100)
    inside, outside = gray[mask], gray[~mask]
    contrast = float(abs(inside.mean() - outside.mean())) if inside.size and outside.size else 0.0
    plausible = 0.4 <= coverage <= 65 and contrast >= 9
    return {
        "available": True,
        "method": "Otsu contrast candidate-region extraction",
        "reliable": plausible,
        "affected_area_percent": round(coverage, 1) if plausible else None,
        "contrast_signal": round(contrast, 1),
        "overlay": _data_url(_overlay(image, mask), image_format="WEBP"),
        # A two-dimensional uint8 array is inferred as an L-mode mask.
        "mask": _data_url(Image.fromarray((mask * 255).astype("uint8"))),
        "notice": CANDIDATE_NOTICE,
        "message": "Visual candidate region extracted." if plausible else "Visual candidate region is unreliable; retake a centred, evenly lit dermatoscopic image.",
    }


def unavailable_candidate_region(reason: str) -> dict:
    return {"available": False, "reliable": False, "affected_area_percent": None, "notice": CANDIDATE_NOTICE, "message": reason}
