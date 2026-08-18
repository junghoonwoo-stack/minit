from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MINIT_DIR = ".minit"
APP_FILE = "app.json"
SCHEMA_VERSION = 1
DEFAULT_RUNTIME = "local"
DEFAULT_PROVIDER = "auto"


def manifest_path(project_dir: Path | None = None) -> Path:
    root = project_dir or Path.cwd()
    return root / MINIT_DIR / APP_FILE


def _normalize_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """Return a backward-compatible manifest with current defaults applied."""
    normalized = dict(manifest)
    normalized.setdefault("schema_version", SCHEMA_VERSION)
    normalized.setdefault("runtime", DEFAULT_RUNTIME)
    normalized.setdefault("provider", DEFAULT_PROVIDER)
    return normalized


def load_manifest(project_dir: Path | None = None) -> dict[str, Any] | None:
    path = manifest_path(project_dir)
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        return _normalize_manifest(json.load(handle))


def save_manifest(manifest: dict[str, Any], project_dir: Path | None = None) -> dict[str, Any]:
    """Persist a manifest while preserving forward-compatible lifecycle fields."""
    path = manifest_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = _normalize_manifest(manifest)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(normalized, handle, indent=2)
        handle.write("\n")
    return normalized


def create_manifest(project_dir: Path | None = None, name: str | None = None) -> dict[str, Any]:
    root = project_dir or Path.cwd()
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "id": str(uuid.uuid4()),
        "name": name or root.name,
        "runtime": DEFAULT_RUNTIME,
        "provider": DEFAULT_PROVIDER,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return save_manifest(manifest, root)


def ensure_manifest(project_dir: Path | None = None) -> tuple[dict[str, Any], bool]:
    existing = load_manifest(project_dir)
    if existing is not None:
        return existing, False
    return create_manifest(project_dir), True
