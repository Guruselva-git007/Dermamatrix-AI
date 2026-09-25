"""Read-only check of local viva files without copying or publishing images."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import sys

from PIL import Image


BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(BACKEND_DIR))

from presentation_case_service import PRESENTATION_CASES, presentation_case_for_digest  # noqa: E402


def main() -> int:
    folder = Path(os.getenv("DERMAMATRIX_PRESENTATION_ASSETS_DIR") or REPO_ROOT / "DERMA PRESENTATION")
    if not folder.is_dir():
        print(f"Presentation assets are missing: {folder}", file=sys.stderr)
        return 1

    supported = {".png", ".jpg", ".jpeg", ".webp", ".avif"}
    matched: set[str] = set()
    ordinary = 0
    for path in sorted(folder.iterdir()):
        if not path.is_file() or path.suffix.lower() not in supported:
            continue
        try:
            with Image.open(path) as image:
                image.verify()
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except (OSError, ValueError) as error:
            print(f"Presentation image cannot be decoded: {path.name} ({error})", file=sys.stderr)
            return 1
        case = PRESENTATION_CASES.get(digest)
        if case is None:
            ordinary += 1
            continue
        presentation_case_for_digest(digest, case["area"])
        matched.add(digest)

    missing = set(PRESENTATION_CASES) - matched
    if missing:
        case_ids = ", ".join(sorted(PRESENTATION_CASES[digest]["case_id"] for digest in missing))
        print(f"Missing {len(missing)} exact teaching files: {case_ids}", file=sys.stderr)
        return 1

    print(f"Presentation assets ready: {len(matched)} exact teaching files; {ordinary} ordinary photos have no teaching label.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
