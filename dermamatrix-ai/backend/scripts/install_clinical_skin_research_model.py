"""Install the pinned clinical Skin checkpoint for offline DermaMatrix inference."""

from __future__ import annotations

import hashlib
import os
import tempfile
import urllib.request
from pathlib import Path


REVISION = "a614ae0c12e8590f06d4f25b529b6b568a517903"
SOURCE = f"https://huggingface.co/RevelaCap/clinical-skin-condition-v1/resolve/{REVISION}/best_model.pth"
EXPECTED_SHA256 = "eba9a581505c60cee98152c790c4113a1549c691248d518cc5d1e7097feb20bc"
DESTINATION = Path(__file__).resolve().parents[1] / "models" / "clinical_skin_best_model.pth"


def sha256(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def main() -> None:
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    if DESTINATION.is_file() and sha256(DESTINATION) == EXPECTED_SHA256:
        print(f"Verified local clinical Skin checkpoint: {DESTINATION}")
        return
    fd, temporary_name = tempfile.mkstemp(prefix="clinical-skin-checkpoint-", dir=DESTINATION.parent)
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
    print(f"Installed local clinical Skin checkpoint: {DESTINATION}")


if __name__ == "__main__":
    main()
