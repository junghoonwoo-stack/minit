from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from minit.private_fs import atomic_write_json, ensure_private_dir, ensure_private_file
from minit.service import load_service_spec
from minit.state import load_manifest

REGISTRY_SCHEMA_VERSION = 1
REGISTRY_FILE = "registry.json"


class RegistryError(RuntimeError):
    pass


def minit_home() -> Path:
    configured = os.environ.get("MINIT_HOME")
    root = Path(configured).expanduser() if configured else Path.home() / ".minit"
    return root.resolve()


def registry_path() -> Path:
    return minit_home() / REGISTRY_FILE


def _empty_registry() -> dict[str, Any]:
    return {"schema_version": REGISTRY_SCHEMA_VERSION, "apps": {}}


def load_registry() -> dict[str, Any]:
    path = registry_path()
    if not path.exists():
        return _empty_registry()
    ensure_private_file(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RegistryError("Minit global registry is unreadable or invalid.") from exc
    if payload.get("schema_version") != REGISTRY_SCHEMA_VERSION or not isinstance(payload.get("apps"), dict):
        raise RegistryError("Minit global registry has an unsupported format.")
    return payload


def save_registry(payload: dict[str, Any]) -> dict[str, Any]:
    ensure_private_dir(minit_home())
    atomic_write_json(registry_path(), payload, sort_keys=True)
    return payload


def register_project(project_dir: Path | None = None) -> dict[str, Any]:
    root = (project_dir or Path.cwd()).resolve()
    manifest = load_manifest(root)
    spec = load_service_spec(root)
    if manifest is None or spec is None:
        raise RegistryError("Only configured Minit local services can be registered.")

    registry = load_registry()
    apps = registry["apps"]
    app_id = manifest["id"]
    now = datetime.now(timezone.utc).isoformat()
    previous = apps.get(app_id) or {}
    entry = {
        "app_id": app_id,
        "name": manifest["name"],
        "project_dir": str(root),
        "port": int(spec["port"]),
        "registered_at": previous.get("registered_at") or now,
        "updated_at": now,
    }
    apps[app_id] = entry
    save_registry(registry)
    return entry


def list_registered_apps() -> list[dict[str, Any]]:
    registry = load_registry()
    return sorted(
        (dict(entry) for entry in registry["apps"].values()),
        key=lambda item: (str(item.get("name", "")).lower(), str(item.get("app_id", ""))),
    )


def resolve_registered_project(target: str) -> Path:
    target = target.strip()
    if not target:
        raise RegistryError("app target cannot be empty")

    entries = list_registered_apps()
    exact = [
        entry
        for entry in entries
        if entry.get("app_id") == target or entry.get("name") == target
    ]
    matches = exact or [
        entry for entry in entries if str(entry.get("app_id", "")).startswith(target)
    ]
    if not matches:
        raise RegistryError(f"No registered Minit app matches `{target}`. Run `minit ls`.")
    if len(matches) > 1:
        raise RegistryError(f"App target `{target}` is ambiguous. Use a longer app ID from `minit ls`.")

    root = Path(matches[0]["project_dir"]).expanduser()
    if not root.exists():
        raise RegistryError(
            f"Registered project directory is unavailable: {root}. The app may have been moved or the drive may be offline."
        )
    return root.resolve()
