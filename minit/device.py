from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

from minit.private_fs import atomic_write_json, ensure_private_file

DEVICE_FILE = "device.json"
DEVICE_SCHEMA_VERSION = 1


def minit_home() -> Path:
    return Path(os.environ.get("MINIT_HOME", Path.home() / ".minit")).expanduser().resolve()


def device_path() -> Path:
    return minit_home() / DEVICE_FILE


def get_or_create_device_id() -> str:
    path = device_path()
    if path.exists():
        ensure_private_file(path)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError("Local Minit device identity is damaged.") from exc
        device_id = payload.get("device_id")
        if payload.get("schema_version") != DEVICE_SCHEMA_VERSION or not isinstance(device_id, str):
            raise RuntimeError("Local Minit device identity is invalid.")
        return device_id

    device_id = str(uuid.uuid4())
    atomic_write_json(
        path,
        {
            "schema_version": DEVICE_SCHEMA_VERSION,
            "device_id": device_id,
        },
    )
    return device_id
