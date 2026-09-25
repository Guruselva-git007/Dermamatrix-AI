"""Exercise the installed research weight with one local dermoscopic demo file."""

from __future__ import annotations

import hashlib
from pathlib import Path
import sys


BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
SAMPLE = REPO_ROOT / "research-assets/original-sources/DermamatrixResearchData/skin-lesion-zip-v1/presentation-samples/ISIC_0000035_downsampled.jpg"
SAMPLE_SHA256 = "f902094c9531e92431f56a6be58f8746e766f1e3e6c15d2068328a9beb65d488"
sys.path.insert(0, str(BACKEND_DIR))

from lesion_classifier import classify_dermoscopic_lesion  # noqa: E402


def main() -> int:
    if not SAMPLE.is_file():
        print(f"Dermoscopy presentation sample is missing: {SAMPLE}", file=sys.stderr)
        return 1
    image_bytes = SAMPLE.read_bytes()
    if hashlib.sha256(image_bytes).hexdigest() != SAMPLE_SHA256:
        print("Dermoscopy presentation sample differs from the verified local file.", file=sys.stderr)
        return 1
    result = classify_dermoscopic_lesion(image_bytes)
    if not result.get("available") or len(result.get("top_predictions") or []) != 3:
        print("Research classifier did not produce three rankings.", file=sys.stderr)
        return 1
    if not str(result.get("attention_map", {}).get("image", "")).startswith("data:image/png;base64,"):
        print("Research classifier did not produce a Grad-CAM map.", file=sys.stderr)
        return 1
    print(f"Research model ready: three rankings and Grad-CAM produced; calibration {result.get('calibration', {}).get('status', 'unknown')}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
