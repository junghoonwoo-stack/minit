from __future__ import annotations

import os
from pathlib import Path


def ensure_private_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        path.chmod(0o700)
    return path


def ensure_private_file(path: Path) -> Path:
    ensure_private_dir(path.parent)
    path.touch(exist_ok=True)
    if os.name != "nt":
        path.chmod(0o600)
    return path


def harden_private_file(path: Path) -> None:
    if os.name != "nt" and path.exists():
        path.chmod(0o600)
