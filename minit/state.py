from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MINIT_DIR = ".minit"
APP_FILE = "app.json"


def manifest_path(project_dir: Path | None = None) -> Path:
    root = project_dir or Path.cwd()
    return root / MINIT_DIR / APP_FILE


def load_manifest(project_dir: Path | None = None) -> dict[str, Any] | None:
    path = manifest_path(project_dir)
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def create_manifest(project_dir: Path | None = None, name: str | None = None) -> dict[str, Any]:
    root = project_dir or Path.cwd()
    path = manifest_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)

    manifest = {
        "id": str(uuid.uuid4()),
        "name": name or root.name,
        "runtime": "local",
        "provider": "auto",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    with path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
        handle.write("\n")
    return manifest


def ensure_manifest(project_dir: Path | None = None) -> tuple[dict[str, Any], bool]:
    existing = load_manifest(project_dir)
    if existing is not None:
        return existing, False
    return create_manifest(project_dir), True
