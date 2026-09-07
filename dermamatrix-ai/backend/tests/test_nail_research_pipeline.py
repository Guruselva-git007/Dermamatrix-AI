"""Regression coverage for the offline governed nail-data pipeline.

These tests exercise metadata and source-layout helpers only. They never load
research images or a rejected checkpoint into the application runtime.
"""

from __future__ import annotations

import os
import sys
import unittest

from PIL import Image, ImageDraw


BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BACKEND_DIR, "scripts")
for directory in (BACKEND_DIR, SCRIPTS_DIR):
    if directory not in sys.path:
        sys.path.insert(0, directory)

from dataset_registry import DATASET_REGISTRY
from model_metadata import model_metadata
from prepare_onychomycosis_dataset import external_label, sheet_label, tile_intervals


class NailResearchPipelineTests(unittest.TestCase):
    def test_source_labels_are_explicit_and_do_not_guess_unlabelled_files(self):
        self.assertEqual(sheet_label("A1/NormalNail_001.png"), "normal_appearing_nail")
        self.assertEqual(sheet_label("A1/NailDystrophy_001.png"), "nail_dystrophy")
        self.assertEqual(sheet_label("A1/Onychomycosis_001.png"), "onychomycosis")
        self.assertIsNone(sheet_label("A1/unknown-condition.png"))
        self.assertEqual(external_label("B1/Onychomycosis/example.jpg"), "onychomycosis")
        self.assertEqual(external_label("C/NailDystrophy/example.jpg"), "nail_dystrophy")
        self.assertIsNone(external_label("C/NormalNail/example.jpg"))

    def test_contact_sheet_splitter_recovers_only_a_guttered_grid(self):
        image = Image.new("RGB", (220, 220), "white")
        draw = ImageDraw.Draw(image)
        for left in (10, 120):
            for top in (10, 120):
                draw.rectangle((left, top, left + 80, top + 80), fill=(100, 80, 70))
        columns, rows = tile_intervals(image)
        self.assertEqual(len(columns), 2)
        self.assertEqual(len(rows), 2)
        with self.assertRaises(ValueError):
            tile_intervals(Image.new("RGB", (220, 220), (80, 80, 80)))

    def test_rejected_nail_experiment_stays_out_of_runtime_inference(self):
        dataset = DATASET_REGISTRY["onychomycosis_figshare_v2"]
        experiment = DATASET_REGISTRY["experiments"]["nail_onychomycosis_resnet18_20260907"]
        metadata = model_metadata("onychomycosis-resnet18-research")
        self.assertEqual(dataset["license"], "CC BY 4.0")
        self.assertEqual(experiment["decision"], "REJECTED_FOR_APPLICATION_INFERENCE")
        self.assertEqual(metadata["status"], "REJECTED_FOR_APPLICATION_INFERENCE")
        self.assertLess(experiment["external_test"]["balanced_accuracy"], 0.65)
        self.assertIn("not loaded", metadata["limitations"])


if __name__ == "__main__":
    unittest.main()
