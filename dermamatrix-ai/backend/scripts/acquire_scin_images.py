#!/usr/bin/env python3
"""Acquire manifest-selected SCIN images into external research storage.

The caller must acknowledge the source licence. Raw images, source metadata,
and every generated research artifact remain outside Git and outside Flask.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import shutil
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from PIL import Image


def fetch(row: dict[str, str], image_dir: Path, timeout: int) -> tuple[str, Path]:
    suffix = Path(row["image_url"]).suffix.lower() or ".png"
    destination = image_dir / f"{row['image_id']}{suffix}"
    if not destination.is_file():
        request = urllib.request.Request(row["image_url"], headers={"User-Agent": "DermaMatrixResearchDatasetAcquirer/2.0"})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response, destination.open("wb") as file:
                shutil.copyfileobj(response, file)
        except Exception:
            destination.unlink(missing_ok=True)
            raise
    try:
        with Image.open(destination) as image:
            image.verify()
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return row["image_id"], destination


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def image_fingerprint(path: Path) -> dict[str, str | int]:
    """Return exact and perceptual fingerprints for audit, never for labels."""
    with Image.open(path) as image:
        width, height = image.size
        grayscale = image.convert("L").resize((9, 8), Image.Resampling.LANCZOS)
        pixels = list(grayscale.get_flattened_data())
    bits = "".join("1" if pixels[row * 9 + col] > pixels[row * 9 + col + 1] else "0" for row in range(8) for col in range(8))
    return {"image_sha256": sha256_file(path), "image_dhash": f"{int(bits, 2):016x}", "image_width": width, "image_height": height}


def near_duplicate_pairs(rows: list[dict[str, str]], threshold: int, max_pairs: int) -> tuple[list[dict[str, str | int]], bool]:
    """Audit perceptually similar images without silently removing any sample."""
    pairs: list[dict[str, str | int]] = []
    compared = 0
    for left, right in itertools.combinations(rows, 2):
        compared += 1
        if compared > max_pairs:
            return pairs, True
        distance = (int(left["image_dhash"], 16) ^ int(right["image_dhash"], 16)).bit_count()
        if distance <= threshold:
            pairs.append({
                "left_image_id": left["image_id"], "right_image_id": right["image_id"],
                "left_split": left["split"], "right_split": right["split"], "hamming_distance": distance,
            })
    return pairs, False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest-csv", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--accept-scin-license", action="store_true")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--near-duplicate-hamming-threshold", type=int, default=4)
    parser.add_argument("--near-duplicate-max-pairs", type=int, default=250000)
    args = parser.parse_args()
    if not args.accept_scin_license:
        raise SystemExit("Refusing acquisition: pass --accept-scin-license only after reviewing the SCIN Data Use License.")
    with Path(args.manifest_csv).open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    required = {"image_id", "group_id", "label", "split", "image_url"}
    if not rows or required - set(rows[0]):
        raise SystemExit("Manifest must include image_id, group_id, label, split, and image_url.")
    root = Path(args.output_root); image_dir = root / "images"; image_dir.mkdir(parents=True, exist_ok=True)
    completed: dict[str, Path] = {}; errors: list[dict[str, str]] = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(fetch, row, image_dir, args.timeout): row for row in rows}
        for future in as_completed(futures):
            row = futures[future]
            try:
                image_id, image_path = future.result(); completed[image_id] = image_path
            except Exception as error:
                errors.append({"image_id": row["image_id"], "error": str(error)})

    local_rows: list[dict[str, str]] = []
    for row in rows:
        path = completed.get(row["image_id"])
        if not path:
            continue
        fingerprints = image_fingerprint(path)
        local_rows.append({**row, "image_path": str(path), **{key: str(value) for key, value in fingerprints.items()}})

    by_hash: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in local_rows:
        by_hash[row["image_sha256"]].append(row)
    exact_duplicates = [
        {"image_ids": [item["image_id"] for item in items], "splits": sorted({item["split"] for item in items})}
        for items in by_hash.values() if len(items) > 1
    ]
    cross_split_exact = [item for item in exact_duplicates if len(item["splits"]) > 1]
    near_pairs, pair_limit_reached = near_duplicate_pairs(local_rows, max(0, args.near_duplicate_hamming_threshold), max(1, args.near_duplicate_max_pairs))
    cross_split_near = [item for item in near_pairs if item["left_split"] != item["right_split"]]
    integrity_status = (
        "FAILED_INCOMPLETE_NEAR_DUPLICATE_AUDIT" if pair_limit_reached
        else "FAILED_CROSS_SPLIT_EXACT_DUPLICATE" if cross_split_exact
        else "FAILED_CROSS_SPLIT_NEAR_DUPLICATE" if cross_split_near
        else "PASSED_DUPLICATE_AND_NEAR_DUPLICATE_AUDIT"
    )
    integrity = {
        "status": integrity_status,
        "image_count": len(local_rows),
        "download_error_count": len(errors),
        "exact_duplicate_groups": exact_duplicates,
        "cross_split_exact_duplicates": cross_split_exact,
        "near_duplicate_hamming_threshold": args.near_duplicate_hamming_threshold,
        "near_duplicate_pairs": near_pairs,
        "cross_split_near_duplicate_pairs": cross_split_near,
        "near_duplicate_pair_limit_reached": pair_limit_reached,
        "near_duplicate_note": "Potential near matches are retained in the report for review. Cross-split near matches block training until the researcher resolves the duplicate or re-splits by case.",
    }
    with (root / "manifest_local.csv").open("w", encoding="utf-8", newline="") as file:
        fields = list(local_rows[0]) if local_rows else [*rows[0], "image_path", "image_sha256", "image_dhash", "image_width", "image_height"]
        writer = csv.DictWriter(file, fieldnames=fields); writer.writeheader(); writer.writerows(local_rows)
    with (root / "download_errors.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=("image_id", "error")); writer.writeheader(); writer.writerows(errors)
    with (root / "integrity_report.json").open("w", encoding="utf-8") as file:
        json.dump(integrity, file, indent=2)
    print(json.dumps({"downloaded_verified": len(local_rows), "requested": len(rows), "download_errors": len(errors), "integrity_status": integrity["status"], "near_duplicate_review_count": len(cross_split_near)}, indent=2))
    if errors:
        raise SystemExit(2)
    if cross_split_exact or cross_split_near or pair_limit_reached:
        raise SystemExit(3)


if __name__ == "__main__":
    main()
