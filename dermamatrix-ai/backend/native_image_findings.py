"""Fast, deterministic image findings for ordinary Skin, Hair, and Nail photos.

All measurements describe the submitted frame or its central crop. They are
not anatomical segmentation, density estimates, disease signs, or diagnoses.
"""

from __future__ import annotations

import io

from PIL import Image, ImageOps


VERSION = "native-image-findings-v1"
TILE_NAMES = (
    ("upper left", "upper center", "upper right"),
    ("middle left", "center", "middle right"),
    ("lower left", "lower center", "lower right"),
)

LIMITATIONS = {
    "Skin": "These frame measurements do not identify acne, scars, pigmentation disorders, or a skin condition.",
    "Hair": "Hair and scalp have not been segmented. Frame contrast cannot establish hair density, scalp exposure, hair loss, or its cause.",
    "Nails": "Nail plates have not been segmented. Frame color and texture cannot establish nail discoloration, a nail disorder, or its cause.",
}


def _finding(name: str, region: str, evidence: str, metric: str) -> dict:
    return {
        "finding": name,
        "area": region,
        "visible_evidence": evidence,
        "certainty": "measured",
        "provenance": "local_pixel_analysis",
        "metric": metric,
    }


def analyze_native_image(image_bytes: bytes, *, area: str, quality_status: str) -> dict:
    """Measure the actual image after bounded decoding and orientation repair."""
    import numpy as np

    if area not in LIMITATIONS:
        raise ValueError("Unsupported image-finding area")

    with Image.open(io.BytesIO(image_bytes)) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGB")
        original_size = image.size
        image.thumbnail((768, 768), Image.Resampling.LANCZOS)
        pixels = np.asarray(image, dtype=np.float32)

    height, width = pixels.shape[:2]
    if min(width, height) < 10:
        return {
            "available": False, "status": "insufficient_pixels", "assessment_mode": "IMAGE_FINDINGS",
            "method_version": VERSION, "source": "local_pixel_analysis", "summary": "The image is too small for local image measurements.",
            "observations": [], "measurements": {"original_width": original_size[0], "original_height": original_size[1]},
            "not_assessable": [LIMITATIONS[area]], "photo_limitations": ["Retake the photo at a higher resolution."],
            "notice": "No image features were inferred from this very small photo.",
        }
    y0, y1 = int(height * 0.1), int(height * 0.9)
    x0, x1 = int(width * 0.1), int(width * 0.9)
    region = pixels[y0:y1, x0:x1]
    luminance = region @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    p10, p50, p90 = (float(value) for value in np.percentile(luminance, [10, 50, 90]))
    tonal_span = p90 - p10
    rgb_median = np.median(region.reshape(-1, 3), axis=0)
    color_deviation = float(np.mean(np.linalg.norm(region - rgb_median, axis=2)))
    horizontal_change = float(np.mean(np.abs(np.diff(luminance, axis=1))))
    vertical_change = float(np.mean(np.abs(np.diff(luminance, axis=0))))
    detail = (horizontal_change + vertical_change) / 2
    tile_values = []
    for row in range(3):
        for column in range(3):
            tile = luminance[
                row * luminance.shape[0] // 3:(row + 1) * luminance.shape[0] // 3,
                column * luminance.shape[1] // 3:(column + 1) * luminance.shape[1] // 3,
            ]
            tile_values.append((TILE_NAMES[row][column], float(np.median(tile))))
    darkest = min(tile_values, key=lambda item: item[1])
    brightest = max(tile_values, key=lambda item: item[1])
    tile_span = brightest[1] - darkest[1]
    dark_fraction = float(np.mean(luminance < 75)) * 100

    measurements = {
        "source": "local_pixel_analysis",
        "original_width": original_size[0],
        "original_height": original_size[1],
        "analyzed_width": width,
        "analyzed_height": height,
        "crop": "central 80% of frame",
        "luminance_p10": round(p10, 1),
        "luminance_median": round(p50, 1),
        "luminance_p90": round(p90, 1),
        "tonal_span": round(tonal_span, 1),
        "color_deviation": round(color_deviation, 1),
        "adjacent_pixel_change": round(detail, 1),
        "dark_pixel_fraction_percent": round(dark_fraction, 1),
        "darkest_tile": darkest[0],
        "brightest_tile": brightest[0],
        "tile_median_span": round(tile_span, 1),
    }

    if area == "Hair":
        observations = [
            _finding("Light and dark areas", "central 80% of photo", f"Brightness spans {p10:.0f}–{p90:.0f} on a 0–255 scale; {dark_fraction:.1f}% of sampled pixels are below 75/255 brightness. This includes any background or skin in the crop.", "luminance_p10_p90_and_dark_fraction"),
            _finding("Fine image detail", "central 80% of photo", f"Adjacent-pixel brightness change averages {detail:.1f}/255. Hair strands, skin, clothing, and background can all contribute.", "adjacent_pixel_change"),
            _finding("Where contrast falls", "nine photo regions", f"The {darkest[0]} tile is darkest and the {brightest[0]} tile is brightest; their median brightness differs by {tile_span:.1f}/255.", "tile_median_span"),
        ]
        summary = f"The photo submitted for a hair/scalp check has a {tonal_span:.0f}-point central light-dark range, with the darkest measured region at the {darkest[0]} of the frame."
    elif area == "Nails":
        observations = [
            _finding("Color variation", "central 80% of photo", f"Mean RGB color distance from the crop's median color is {color_deviation:.1f}, calculated from three 0–255 color channels. Surrounding fingers and background also contribute.", "color_deviation"),
            _finding("Lightness variation", "central 80% of photo", f"Brightness spans {p10:.0f}–{p90:.0f} on a 0–255 scale, a {tonal_span:.1f}-point spread.", "luminance_p10_p90"),
            _finding("Local surface detail", "central 80% of photo", f"Adjacent-pixel brightness change averages {detail:.1f}/255. This describes image detail, not nail ridges or pits specifically.", "adjacent_pixel_change"),
            _finding("Distribution in the frame", "nine photo regions", f"The {darkest[0]} tile is darkest and the {brightest[0]} tile is brightest; their median brightness differs by {tile_span:.1f}/255.", "tile_median_span"),
        ]
        summary = f"The photo submitted for a nail check has a {tonal_span:.0f}-point central lightness range and {color_deviation:.1f} mean RGB color distance from its median color."
    else:
        observations = [
            _finding("Tone variation", "central 80% of photo", f"Brightness spans {p10:.0f}–{p90:.0f} on a 0–255 scale, a {tonal_span:.1f}-point spread.", "luminance_p10_p90"),
            _finding("Color variation", "central 80% of photo", f"Mean RGB color distance from the crop's median color is {color_deviation:.1f}, calculated from three 0–255 color channels.", "color_deviation"),
            _finding("Local detail", "central 80% of photo", f"Adjacent-pixel brightness change averages {detail:.1f}/255. This can reflect skin texture, hair, shadows, or background.", "adjacent_pixel_change"),
            _finding("Distribution in the frame", "nine photo regions", f"The {darkest[0]} tile is darkest and the {brightest[0]} tile is brightest; their median brightness differs by {tile_span:.1f}/255.", "tile_median_span"),
        ]
        summary = f"The photo submitted for a skin check has a {tonal_span:.0f}-point central lightness range, with the darkest measured region at the {darkest[0]} of the frame."

    return {
        "available": True,
        "status": "limited_quality" if quality_status == "LOW_QUALITY" else "measured",
        "assessment_mode": "IMAGE_FINDINGS",
        "method_version": VERSION,
        "source": "local_pixel_analysis",
        "summary": summary,
        "observations": observations,
        "measurements": measurements,
        "not_assessable": [LIMITATIONS[area]],
        "photo_limitations": ["The selected category is user-declared; no validated anatomy detector verified it."] + (["Lighting or focus limits interpretation; retake the photo for clearer detail."] if quality_status == "LOW_QUALITY" else []),
        "notice": "Image-specific measurements from this photo, not a condition classification or medical diagnosis.",
    }


def validate_assessment_completeness(result: dict) -> dict:
    """Check required evidence was retained; never synthesize a missing value."""
    canonical = result.get("canonical_evidence") or {}
    statuses = canonical.get("component_status") or {}
    checks = {
        "image_quality": bool((canonical.get("image_quality") or result.get("quality") or {}).get("status")),
        "local_image_findings": bool((canonical.get("image_findings") or result.get("image_findings") or {}).get("observations")),
        "reported_context": bool(canonical.get("reported_context")) or "manual_context" in result,
        "reported_severity": bool((canonical.get("severity") or result.get("severity") or {}).get("level")),
        "reported_priority": bool((canonical.get("reported_priority") or result.get("risk") or {}).get("level")),
        "pirs": statuses.get("pirs") == "succeeded" if canonical else bool(result.get("pirs", {}).get("score") is not None),
        "general_guidance": bool(result.get("recommendations")),
    }
    return {
        "status": "complete_available_evidence" if all(checks.values()) else "incomplete",
        "checks": checks,
        "missing": [name for name, available in checks.items() if not available],
    }
