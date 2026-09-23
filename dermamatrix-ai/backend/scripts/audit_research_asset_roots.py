#!/usr/bin/env python3
"""Create a read-only inventory of external research-asset roots.

This utility deliberately does not extract archives, decode images, build a
manifest, or train a model.  It makes the distinction between raw research
sources, derived training artifacts, recovery copies, and reference documents
explicit before a future experiment is proposed.  A file inventory is never a
training-eligibility or application-inference decision.
"""

from __future__ import annotations

import argparse
import json
import os
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


IMAGE_SUFFIXES = {".avif", ".bmp", ".gif", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}
DOCUMENT_SUFFIXES = {".csv", ".doc", ".docx", ".ipynb", ".json", ".md", ".pdf", ".tsv", ".txt", ".xlsx"}


def inventory_directory(root: Path) -> dict:
    """Count files by coarse type without opening their contents."""
    counts = Counter()
    bytes_total = 0
    for directory, _, filenames in os.walk(root):
        for name in filenames:
            path = Path(directory) / name
            try:
                size = path.stat().st_size
            except OSError:
                counts["unreadable_files"] += 1
                continue
            bytes_total += size
            suffix = path.suffix.casefold()
            counts["files"] += 1
            if suffix in IMAGE_SUFFIXES:
                counts["image_files"] += 1
            elif suffix == ".zip":
                counts["zip_files"] += 1
            elif suffix in DOCUMENT_SUFFIXES:
                counts["document_or_metadata_files"] += 1
            else:
                counts["other_files"] += 1
    return {"exists": True, "bytes": bytes_total, **dict(sorted(counts.items()))}


def inspect_zip(path: Path) -> dict:
    """Read only the ZIP central directory; do not extract or CRC-scan it."""
    result = {"path": str(path), "bytes": path.stat().st_size}
    try:
        with zipfile.ZipFile(path) as archive:
            members = [member for member in archive.infolist() if not member.is_dir()]
    except (OSError, zipfile.BadZipFile) as error:
        return {**result, "status": "UNREADABLE_ZIP", "error": str(error)}
    suffixes = Counter(Path(member.filename).suffix.casefold() for member in members)
    result.update({
        "status": "CENTRAL_DIRECTORY_READABLE",
        "member_files": len(members),
        "image_members": sum(count for suffix, count in suffixes.items() if suffix in IMAGE_SUFFIXES),
        "top_level_entries": sorted({Path(member.filename).parts[0] for member in members if Path(member.filename).parts})[:30],
    })
    return result


def inventory_root(name: str, root: Path, role: str) -> dict:
    if not root.is_dir():
        return {"name": name, "path": str(root), "role": role, "exists": False}
    children = []
    for child in sorted(root.iterdir(), key=lambda item: item.name.casefold()):
        if child.is_dir():
            children.append({"name": child.name, "kind": "directory", **inventory_directory(child)})
        elif child.is_file() and child.suffix.casefold() == ".zip":
            children.append({"name": child.name, "kind": "zip", **inspect_zip(child)})
        elif child.is_file():
            children.append({"name": child.name, "kind": "file", "bytes": child.stat().st_size})
    zip_archives = [inspect_zip(path) for path in sorted(root.rglob("*.zip"), key=lambda item: str(item).casefold())]
    return {
        "name": name,
        "path": str(root),
        "role": role,
        "training_eligibility": "NOT_DETERMINED_BY_INVENTORY",
        "application_inference_eligibility": "NEVER_DETERMINED_BY_INVENTORY",
        "summary": inventory_directory(root),
        "zip_archives": zip_archives,
        "children": children,
    }


def parse_root(value: str) -> tuple[str, Path, str]:
    try:
        name, role, raw_path = value.split("=", 2)
    except ValueError as error:
        raise argparse.ArgumentTypeError("--root must be NAME=ROLE=ABSOLUTE_PATH") from error
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        raise argparse.ArgumentTypeError("research-asset roots must be absolute paths")
    return name, path, role


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", action="append", type=parse_root, required=True,
        help="Repeat NAME=ROLE=ABSOLUTE_PATH for each external asset root.",
    )
    parser.add_argument("--output-json", required=True, type=Path, help="Derived report destination outside Git.")
    args = parser.parse_args()

    output = args.output_json.expanduser().resolve()
    report = {
        "schema_version": "dermamatrix-research-asset-inventory-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "read_only": True,
        "guarantees": [
            "No archive was extracted or CRC-scanned.",
            "No image was decoded, hashed, copied, renamed, or modified.",
            "The inventory does not approve training, model promotion, or application inference.",
        ],
        "roots": [inventory_root(name, path, role) for name, path, role in args.root],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)
        file.write("\n")
    print(json.dumps({"output": str(output), "roots": len(report["roots"]), "read_only": True}))


if __name__ == "__main__":
    main()
