from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from minit.backups import latest_backup_summary
from minit.device import get_or_create_device_id
from minit.runtime import load_runtime_state, runtime_is_running
from minit.service import load_service_spec
from minit.state import ensure_manifest

CLOUD_STATUS_SCHEMA_VERSION = 1

# This is intentionally narrow. Adding a field to this schema is a privacy
# decision, not a convenience refactor.
_ALLOWED_SCHEMA: dict[str, Any] = {
    "schema_version": int,
    "app_id": str,
    "device_id": str,
    "observed_at": str,
    "service": {
        "configured": bool,
        "running": bool,
        "status": str,
        "health": str,
        "restart_count": int,
        "autostart": bool,
    },
    "resources": {
        "available": bool,
        "cpu_percent": (int, float, type(None)),
        "rss_bytes": (int, type(None)),
        "child_processes": (int, type(None)),
    },
    "history": {
        "successful_runs": int,
        "total_live_seconds": int,
    },
    "backup": {
        "available": bool,
        "backup_id": (str, type(None)),
        "created_at": (str, type(None)),
        "ciphertext_bytes": (int, type(None)),
    },
}

_FORBIDDEN_KEY_FRAGMENTS = {
    "name",
    "command",
    "path",
    "directory",
    "cwd",
    "log",
    "secret",
    "token",
    "password",
    "key",
    "prompt",
    "input",
    "output",
    "content",
    "filename",
    "url",
}


def _validate_shape(value: Any, schema: Any, path: str = "payload") -> None:
    if isinstance(schema, dict):
        if not isinstance(value, dict):
            raise ValueError(f"{path} must be an object")
        unknown = set(value) - set(schema)
        missing = set(schema) - set(value)
        if unknown:
            raise ValueError(f"{path} contains non-allowlisted fields: {sorted(unknown)}")
        if missing:
            raise ValueError(f"{path} is missing required fields: {sorted(missing)}")
        for key, child_schema in schema.items():
            lowered = key.lower()
            if any(fragment in lowered for fragment in _FORBIDDEN_KEY_FRAGMENTS):
                raise ValueError(f"Cloud schema itself contains forbidden field name: {path}.{key}")
            _validate_shape(value[key], child_schema, f"{path}.{key}")
        return

    if not isinstance(value, schema):
        raise ValueError(f"{path} has invalid type: {type(value).__name__}")


def validate_cloud_status_payload(payload: dict[str, Any]) -> dict[str, Any]:
    _validate_shape(payload, _ALLOWED_SCHEMA)
    if payload["schema_version"] != CLOUD_STATUS_SCHEMA_VERSION:
        raise ValueError("Unsupported cloud status schema version")
    return payload


def build_cloud_status_payload(project_dir: Path | None = None) -> dict[str, Any]:
    root = (project_dir or Path.cwd()).resolve()
    manifest, _ = ensure_manifest(root)
    history = manifest.get("publish_history", {})
    spec = load_service_spec(root)
    runtime = load_runtime_state(root)
    running = runtime_is_running(root) if runtime is not None else False
    metrics = runtime.get("metrics", {}) if runtime else {}
    latest_backup = latest_backup_summary(root)

    payload: dict[str, Any] = {
        "schema_version": CLOUD_STATUS_SCHEMA_VERSION,
        "app_id": manifest["id"],
        "device_id": get_or_create_device_id(),
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "service": {
            "configured": spec is not None,
            "running": running,
            "status": str(runtime.get("status", "not-configured" if spec is None else "stopped")) if runtime else ("not-configured" if spec is None else "stopped"),
            "health": str(runtime.get("health", "unknown")) if runtime else "unknown",
            "restart_count": int(runtime.get("restart_count", 0)) if runtime else 0,
            "autostart": bool(spec.get("autostart", False)) if spec else False,
        },
        "resources": {
            "available": bool(metrics.get("available", False)) if running else False,
            "cpu_percent": metrics.get("cpu_percent") if running and metrics.get("available") else None,
            "rss_bytes": int(metrics["rss_bytes"]) if running and metrics.get("available") and isinstance(metrics.get("rss_bytes"), (int, float)) else None,
            "child_processes": int(metrics["child_processes"]) if running and metrics.get("available") and isinstance(metrics.get("child_processes"), (int, float)) else None,
        },
        "history": {
            "successful_runs": int(history.get("successful_runs", 0)),
            "total_live_seconds": int(history.get("total_live_seconds", 0)),
        },
        "backup": {
            "available": latest_backup is not None,
            "backup_id": latest_backup["backup_id"] if latest_backup else None,
            "created_at": latest_backup["created_at"] if latest_backup else None,
            "ciphertext_bytes": latest_backup["ciphertext_bytes"] if latest_backup else None,
        },
    }
    return validate_cloud_status_payload(payload)


def cloud_cleartext_policy() -> tuple[str, ...]:
    return (
        "opaque app/device identifiers",
        "service health/status and restart count",
        "CPU/RAM/process-count operational metrics",
        "aggregate run count and live duration",
        "autostart state",
        "latest encrypted-backup ID/time/ciphertext size",
    )
