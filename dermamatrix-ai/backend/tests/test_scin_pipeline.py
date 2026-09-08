import csv
import tempfile
import unittest
from pathlib import Path

from scin_pipeline import build_strict_manifest, is_condition_gradable


class ScinManifestPipelineTests(unittest.TestCase):
    def _metadata(self, root: Path) -> tuple[Path, Path]:
        cases_path, labels_path = root / "cases.csv", root / "labels.csv"
        cases, labels = [], []
        for label, prefix in (("Eczema", "eczema"), ("Urticaria", "urticaria")):
            for number in range(10):
                case_id = f"{prefix}-{number}"
                cases.append({"case_id": case_id, "image_1_path": f"dataset/{case_id}.png", "image_2_path": "", "image_3_path": ""})
                labels.append({
                    "case_id": case_id,
                    "dermatologist_gradable_for_skin_condition_1": "DEFAULT_YES_IMAGE_QUALITY_SUFFICIENT",
                    "dermatologist_gradable_for_skin_condition_2": "",
                    "weighted_skin_condition_label": repr({label: 1.0}),
                })
        labels.extend([
            {"case_id": "eczema-0", "dermatologist_gradable_for_skin_condition_1": "NO", "dermatologist_gradable_for_skin_condition_2": "", "weighted_skin_condition_label": "{'Eczema': 1.0}"},
            {"case_id": "urticaria-0", "dermatologist_gradable_for_skin_condition_1": "YES", "dermatologist_gradable_for_skin_condition_2": "", "weighted_skin_condition_label": "{'Urticaria': 0.6, 'Eczema': 0.4}"},
        ])
        with cases_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=cases[0].keys()); writer.writeheader(); writer.writerows(cases)
        with labels_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=labels[0].keys()); writer.writeheader(); writer.writerows(labels)
        return cases_path, labels_path

    def test_source_gradability_values_are_handled_explicitly(self):
        self.assertTrue(is_condition_gradable({"dermatologist_gradable_for_skin_condition_1": "YES"}))
        self.assertTrue(is_condition_gradable({"dermatologist_gradable_for_skin_condition_1": "DEFAULT_YES_IMAGE_QUALITY_SUFFICIENT"}))
        self.assertFalse(is_condition_gradable({"dermatologist_gradable_for_skin_condition_1": "NO"}))

    def test_manifest_is_case_grouped_and_excludes_source_sensitive_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            cases, labels = self._metadata(Path(directory))
            rows, summary = build_strict_manifest(cases, labels, minimum_class_cases=10)
        self.assertEqual(len(rows), 20)
        split_by_case = {}
        for row in rows:
            self.assertNotIn("demographic", row)
            self.assertNotIn("questionnaire", row)
            split_by_case.setdefault(row["group_id"], set()).add(row["split"])
        self.assertTrue(all(len(splits) == 1 for splits in split_by_case.values()))
        self.assertEqual(summary["audit"]["differential_or_multilabel"], 1)
        self.assertEqual(summary["audit"]["selected_cases"], 20)
        self.assertIn("not a patient-level split claim", summary["grouping"])

    def test_insufficient_taxonomy_is_rejected_instead_of_silently_relabelled(self):
        with tempfile.TemporaryDirectory() as directory:
            cases, labels = self._metadata(Path(directory))
            with self.assertRaisesRegex(ValueError, "Insufficient strict, gradable case count"):
                build_strict_manifest(cases, labels, classes=("Eczema", "Psoriasis"), minimum_class_cases=2)


if __name__ == "__main__":
    unittest.main()
