from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from minit.private_fs import atomic_write_json, ensure_private_file

MINIT_DIR = ".minit"
APP_FILE = "app.json"
SCHEMA_VERSION = 1
DEFAULT_RUNTIME = "local"
DEFAULT_PROVIDER = "auto"


def manifest_path(project_dir: Path | None = None) -> Path:
    root = project_dir or Path.cwd()
    return root / MINIT_DIR / APP_FILE


def _normalize_publish_history(history: dict[str, Any] | None) -> dict[str, Any]:
    normalized = dict(history or {})
    normalized.setdefault("successful_runs", 0)
    normalized.setdefault("first_started_at", None)
    normalized.setdefault("last_started_at", None)
    normalized.setdefault("last_stopped_at", None)
    normalized.setdefault("total_live_seconds", 0)
    return normalized


def _normalize_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """Return a backward-compatible manifest with current defaults applied."""
    normalized = dict(manifest)
    normalized.setdefault("schema_version", SCHEMA_VERSION)
    normalized.setdefault("runtime", DEFAULT_RUNTIME)
    normalized.setdefault("provider", DEFAULT_PROVIDER)
    normalized["publish_history"] = _normalize_publish_history(normalized.get("publish_history"))
    return normalized


def load_manifest(project_dir: Path | None = None) -> dict[str, Any] | None:
    path = manifest_path(project_dir)
    if not path.exists():
        return None
    ensure_private_file(path)
    with path.open("r", encoding="utf-8") as handle:
        return _normalize_manifest(json.load(handle))


def save_manifest(manifest: dict[str, Any], project_dir: Path | None = None) -> dict[str, Any]:
    """Persist a manifest while preserving forward-compatible lifecycle fields."""
    path = manifest_path(project_dir)
    normalized = _normalize_manifest(manifest)
    atomic_write_json(path, normalized)
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
        "publish_history": _normalize_publish_history(None),
    }
    return save_manifest(manifest, root)


def ensure_manifest(project_dir: Path | None = None) -> tuple[dict[str, Any], bool]:
    existing = load_manifest(project_dir)
    if existing is not None:
        return existing, False
    return create_manifest(project_dir), True


def record_publish_start(
    project_dir: Path | None = None,
    started_at: datetime | None = None,
) -> dict[str, Any]:
    """Record a successful local publish in the local project manifest only."""
    manifest, _ = ensure_manifest(project_dir)
    when = started_at or datetime.now(timezone.utc)
    history = _normalize_publish_history(manifest.get("publish_history"))
    history["successful_runs"] += 1
    history["first_started_at"] = history["first_started_at"] or when.isoformat()
    history["last_started_at"] = when.isoformat()
    manifest["publish_history"] = history
    return save_manifest(manifest, project_dir)


def record_publish_stop(
    started_at: datetime,
    project_dir: Path | None = None,
    stopped_at: datetime | None = None,
) -> dict[str, Any] | None:
    """Record local live duration. No publish history is sent off the machine."""
    manifest = load_manifest(project_dir)
    if manifest is None:
        return None

    when = stopped_at or datetime.now(timezone.utc)
    duration_seconds = max(0, int((when - started_at).total_seconds()))
    history = _normalize_publish_history(manifest.get("publish_history"))
    history["last_stopped_at"] = when.isoformat()
    history["total_live_seconds"] += duration_seconds
    manifest["publish_history"] = history
    return save_manifest(manifest, project_dir)
