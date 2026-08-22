from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from minit.state import load_manifest


PERSISTENT_RUN_THRESHOLD = 2
PERSISTENT_LIVE_SECONDS_THRESHOLD = 30 * 60


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def local_app_status(project_dir: Path | None = None) -> dict[str, Any] | None:
    """Return management status derived only from the local project manifest."""
    manifest = load_manifest(project_dir)
    if manifest is None:
        return None

    history = manifest.get("publish_history", {})
    return {
        "app_id": manifest["id"],
        "name": manifest["name"],
        "runtime": manifest.get("runtime", "local"),
        "provider": manifest.get("provider", "auto"),
        "successful_runs": int(history.get("successful_runs", 0)),
        "total_live_seconds": int(history.get("total_live_seconds", 0)),
        "first_started_at": history.get("first_started_at"),
        "last_started_at": history.get("last_started_at"),
        "last_stopped_at": history.get("last_stopped_at"),
        "source": "local-manifest",
    }


def should_suggest_persistent_local_service(project_dir: Path | None = None) -> bool:
    """Decide locally whether repeated usage indicates a persistent service may help.

    This function performs no network calls and sends no usage data anywhere.
    It intentionally does not print or trigger a product suggestion; the CLI can
    use it later when persistent local deployment is actually available.
    """
    status = local_app_status(project_dir)
    if status is None:
        return False

    if status["successful_runs"] >= PERSISTENT_RUN_THRESHOLD:
        return True

    if status["total_live_seconds"] >= PERSISTENT_LIVE_SECONDS_THRESHOLD:
        return True

    first = _parse_datetime(status["first_started_at"])
    last = _parse_datetime(status["last_started_at"])
    if first is not None and last is not None and first.date() != last.date():
        return True

    return False
