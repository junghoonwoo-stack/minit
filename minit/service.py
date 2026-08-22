from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from minit.private_fs import atomic_write_json, ensure_private_file
from minit.state import MINIT_DIR, ensure_manifest

SERVICE_FILE = "service.json"
SERVICE_SCHEMA_VERSION = 1
RESTART_POLICIES = {"never", "on-failure", "always"}
ENVIRONMENT_POLICY = "minimal"

SENSITIVE_ARGUMENT_NAMES = {
    "--api-key",
    "--apikey",
    "--password",
    "--passwd",
    "--secret",
    "--token",
    "--access-token",
    "--private-key",
}


def service_spec_path(project_dir: Path | None = None) -> Path:
    root = (project_dir or Path.cwd()).resolve()
    return root / MINIT_DIR / SERVICE_FILE


def _contains_sensitive_command_argument(command: list[str]) -> bool:
    for part in command:
        lowered = part.lower()
        if lowered in SENSITIVE_ARGUMENT_NAMES:
            return True
        if any(lowered.startswith(f"{name}=") for name in SENSITIVE_ARGUMENT_NAMES):
            return True
    return False


def build_service_spec(
    command: list[str],
    port: int,
    project_dir: Path | None = None,
    restart_policy: str = "on-failure",
) -> dict[str, Any]:
    """Build a local service specification without starting a process.

    Commands are stored as an argv list rather than a shell command. Plaintext
    secret values and inherited environment-variable values do not belong in
    this file.
    """
    if not command or not all(isinstance(part, str) and part for part in command):
        raise ValueError("command must contain at least one non-empty argument")
    if _contains_sensitive_command_argument(command):
        raise ValueError(
            "command appears to contain a secret argument; keep secrets out of service.json"
        )
    if not 1 <= port <= 65535:
        raise ValueError("port must be between 1 and 65535")
    if restart_policy not in RESTART_POLICIES:
        raise ValueError(f"unsupported restart policy: {restart_policy}")

    root = (project_dir or Path.cwd()).resolve()
    manifest, _ = ensure_manifest(root)

    return {
        "schema_version": SERVICE_SCHEMA_VERSION,
        "app_id": manifest["id"],
        "command": list(command),
        "working_dir": str(root),
        "port": port,
        "restart_policy": restart_policy,
        "environment_policy": ENVIRONMENT_POLICY,
        "autostart": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def save_service_spec(spec: dict[str, Any], project_dir: Path | None = None) -> dict[str, Any]:
    atomic_write_json(service_spec_path(project_dir), spec)
    return spec


def configure_local_service(
    command: list[str],
    port: int,
    project_dir: Path | None = None,
    restart_policy: str = "on-failure",
) -> dict[str, Any]:
    spec = build_service_spec(command, port, project_dir, restart_policy)
    return save_service_spec(spec, project_dir)


def load_service_spec(project_dir: Path | None = None) -> dict[str, Any] | None:
    path = service_spec_path(project_dir)
    if not path.exists():
        return None
    ensure_private_file(path)
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)
