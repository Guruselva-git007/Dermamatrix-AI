"""Install the pinned public Nail checkpoint for fully offline local inference.

Run once during setup. Assessment requests never call the network.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
import urllib.request
from pathlib import Path


REVISION = "661603d35bab2904055d4d4a943bf305b03a59f9"
SOURCE = f"https://huggingface.co/shibarashii/nail-disease-detection/resolve/{REVISION}/best_models/convnexttiny/best_model.pth"
EXPECTED_SHA256 = "6c58cd98c9368268115d00f6acd6d1f03dba73132eaacd15cbfa9cf9dfb5bf19"
DESTINATION = Path(__file__).resolve().parents[1] / "models" / "nail_convnexttiny_research.pth"


def sha256(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def main() -> None:
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    if DESTINATION.is_file() and sha256(DESTINATION) == EXPECTED_SHA256:
        print(f"Verified local Nail checkpoint: {DESTINATION}")
        return
    fd, temporary_name = tempfile.mkstemp(prefix="nail-checkpoint-", dir=DESTINATION.parent)
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        with urllib.request.urlopen(SOURCE, timeout=60) as response, temporary.open("wb") as target:
            while chunk := response.read(1024 * 1024):
                target.write(chunk)
        if sha256(temporary) != EXPECTED_SHA256:
            raise ValueError("Downloaded checkpoint checksum does not match the pinned source")
        temporary.replace(DESTINATION)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"Installed local Nail checkpoint: {DESTINATION}")


if __name__ == "__main__":
    main()
