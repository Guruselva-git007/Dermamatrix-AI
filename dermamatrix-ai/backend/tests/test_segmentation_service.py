"""Tests for compact, non-diagnostic visual-evidence artifacts."""

from __future__ import annotations

import io
import os
import sys
import unittest

from PIL import Image, ImageDraw


BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from segmentation_service import extract_visual_candidate_region


class VisualCandidateRegionTests(unittest.TestCase):
    def test_display_overlay_is_compact_webp_and_mask_stays_lossless_png(self):
        image = Image.new("RGB", (900, 700), color=(225, 220, 215))
        ImageDraw.Draw(image).ellipse((250, 170, 550, 470), fill=(75, 55, 50))
        payload = io.BytesIO()
        image.save(payload, format="PNG")

        result = extract_visual_candidate_region(payload.getvalue())

        self.assertTrue(result["available"])
        self.assertTrue(result["overlay"].startswith("data:image/webp;base64,"))
        self.assertTrue(result["mask"].startswith("data:image/png;base64,"))
        self.assertIn("not lesion segmentation", result["notice"].lower())


if __name__ == "__main__":
    unittest.main()
