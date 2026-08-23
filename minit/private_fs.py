from __future__ import annotations

import csv
import json
import os
import secrets
import subprocess
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


def _windows_user_sid() -> str:
    result = subprocess.run(
        ["whoami", "/user", "/fo", "csv", "/nh"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise OSError(f"Could not determine Windows user SID: {result.stderr.strip()}")
    row = next(csv.reader([result.stdout.strip()]), None)
    if not row or len(row) < 2 or not row[1].startswith("S-"):
        raise OSError("Could not parse Windows user SID.")
    return row[1]


def _run_icacls(args: list[str]) -> None:
    result = subprocess.run(
        ["icacls", *args],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise OSError(f"Windows ACL hardening failed: {result.stderr.strip() or 'icacls error'}")


def _harden_windows_tree(root: Path) -> None:
    user_sid = f"*{_windows_user_sid()}"
    system_sid = "*S-1-5-18"
    _run_icacls([str(root), "/inheritance:r", "/T", "/C"])
    _run_icacls(
        [
            str(root),
            "/grant:r",
            f"{user_sid}:(OI)(CI)F",
            f"{system_sid}:(OI)(CI)F",
            "/T",
            "/C",
        ]
    )
    for broad_sid in ("*S-1-1-0", "*S-1-5-11", "*S-1-5-32-545"):
        _run_icacls([str(root), "/remove:g", broad_sid, "/T", "/C"])


def harden_private_tree(root: Path) -> None:
    """Enforce private permissions for Minit-managed local state.

    POSIX uses owner-only mode bits. Windows removes inherited/broad group
    grants from the Minit tree and grants Full Control to the current user and
    SYSTEM. Administrators can still exercise normal OS-level administrative
    authority; this boundary is intended to protect against ordinary sibling
    processes/users, not a compromised administrator/kernel.
    """
    if not root.exists():
        return
    ensure_private_dir(root)
    if os.name == "nt":
        _harden_windows_tree(root)
        return
    for path in root.rglob("*"):
        try:
            if path.is_dir():
                path.chmod(PRIVATE_DIR_MODE)
            elif path.is_file():
                path.chmod(PRIVATE_FILE_MODE)
        except OSError:
            # Existing trees may contain transient files. New Minit writes still
            # go through owner-only atomic helpers.
            continue
