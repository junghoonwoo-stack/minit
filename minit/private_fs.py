from __future__ import annotations

import json
import os
import secrets
from pathlib import Path
from typing import Any

PRIVATE_DIR_MODE = 0o700
PRIVATE_FILE_MODE = 0o600


def _chmod_if_posix(path: Path, mode: int) -> None:
    if os.name != "nt":
        path.chmod(mode)


def ensure_private_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    _chmod_if_posix(path, PRIVATE_DIR_MODE)
    return path


def ensure_private_file(path: Path) -> Path:
    if path.exists():
        _chmod_if_posix(path, PRIVATE_FILE_MODE)
    return path


def _temporary_path(path: Path) -> Path:
    return path.with_name(f".{path.name}.{os.getpid()}.{secrets.token_hex(4)}.tmp")


def atomic_write_bytes(path: Path, data: bytes) -> None:
    ensure_private_dir(path.parent)
    tmp = _temporary_path(path)
    try:
        with tmp.open("wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        _chmod_if_posix(tmp, PRIVATE_FILE_MODE)
        tmp.replace(path)
        _chmod_if_posix(path, PRIVATE_FILE_MODE)
    finally:
        tmp.unlink(missing_ok=True)


def atomic_write_text(path: Path, text: str) -> None:
    atomic_write_bytes(path, text.encode("utf-8"))


def atomic_write_json(path: Path, payload: Any, *, sort_keys: bool = False) -> None:
    text = json.dumps(payload, indent=2, sort_keys=sort_keys) + "\n"
    atomic_write_text(path, text)


def harden_private_tree(root: Path) -> None:
    """Best-effort owner-only permissions for Minit-managed local state.

    Windows ACLs are not modified here; Windows security remains delegated to
    the user's profile/credential store until an explicit ACL implementation is
    added and tested.
    """
    if not root.exists():
        return
    ensure_private_dir(root)
    if os.name == "nt":
        return
    for path in root.rglob("*"):
        try:
            if path.is_dir():
                path.chmod(PRIVATE_DIR_MODE)
            elif path.is_file():
                path.chmod(PRIVATE_FILE_MODE)
        except OSError:
            # Hardening is best-effort for existing trees; individual secure
            # write helpers still enforce permissions for new Minit state.
            continue
