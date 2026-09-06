#!/usr/bin/env python3
"""Acquire only manifest-selected SCIN images outside the repository.

The caller must explicitly acknowledge the SCIN licence.  Files are verified
as images and the generated local manifest contains no source demographics.
"""

from __future__ import annotations

import argparse
import csv
import shutil
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from PIL import Image


def fetch(row: dict, image_dir: Path, timeout: int) -> tuple[str, str]:
    suffix = Path(row["image_url"]).suffix.lower() or ".png"
    destination = image_dir / f"{row['image_id']}{suffix}"
    if destination.is_file():
        return row["image_id"], str(destination)
    request = urllib.request.Request(row["image_url"], headers={"User-Agent": "DermaMatrixResearchDatasetAcquirer/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response, destination.open("wb") as file:
            shutil.copyfileobj(response, file)
        with Image.open(destination) as image:
            image.verify()
        return row["image_id"], str(destination)
    except Exception:
        destination.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest-csv", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--accept-scin-license", action="store_true")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()
    if not args.accept_scin_license:
        raise SystemExit("Refusing acquisition: pass --accept-scin-license only after reviewing the SCIN Data Use License.")
    with open(args.manifest_csv, encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    if not rows:
        raise SystemExit("Manifest is empty.")
    root = Path(args.output_root); image_dir = root / "images"; image_dir.mkdir(parents=True, exist_ok=True)
    completed, errors = {}, []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(fetch, row, image_dir, args.timeout): row for row in rows}
        for future in as_completed(futures):
            row = futures[future]
            try:
                image_id, image_path = future.result(); completed[image_id] = image_path
            except Exception as error:
                errors.append({"image_id": row["image_id"], "url": row["image_url"], "error": str(error)})
    local_rows = [{**row, "image_path": completed[row["image_id"]]} for row in rows if row["image_id"] in completed]
    with (root / "manifest_local.csv").open("w", encoding="utf-8", newline="") as file:
        fieldnames = list(local_rows[0]) if local_rows else [*rows[0], "image_path"]
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader(); writer.writerows(local_rows)
    with (root / "download_errors.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=("image_id", "url", "error")); writer.writeheader(); writer.writerows(errors)
    print(f"Downloaded/verified {len(local_rows)}/{len(rows)} SCIN images; errors: {len(errors)}")
    if errors:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
