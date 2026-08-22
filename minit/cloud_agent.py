from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from minit.backups import create_backup
from minit.cloud_client import CloudClientError, sync_status, upload_backup
from minit.environment import supervisor_environment
from minit.private_fs import atomic_write_json, ensure_private_dir, ensure_private_file
from minit.state import MINIT_DIR

AGENT_CONFIG_FILE = "cloud-agent-config.json"
AGENT_STATE_FILE = "cloud-agent-state.json"
AGENT_LOG_DIR = "logs"
AGENT_LOG_FILE = "cloud-agent.log"
AGENT_SCHEMA_VERSION = 1
DEFAULT_STATUS_INTERVAL_SECONDS = 60
MIN_STATUS_INTERVAL_SECONDS = 30
MAX_BACKOFF_SECONDS = 15 * 60


class CloudAgentError(RuntimeError):
    pass


def _root(project_dir: Path | None = None) -> Path:
    return (project_dir or Path.cwd()).resolve()


def config_path(project_dir: Path | None = None) -> Path:
    return _root(project_dir) / MINIT_DIR / AGENT_CONFIG_FILE


def state_path(project_dir: Path | None = None) -> Path:
    return _root(project_dir) / MINIT_DIR / AGENT_STATE_FILE


def log_path(project_dir: Path | None = None) -> Path:
    return _root(project_dir) / MINIT_DIR / AGENT_LOG_DIR / AGENT_LOG_FILE


def build_config(
    *,
    status_interval_seconds: int = DEFAULT_STATUS_INTERVAL_SECONDS,
    backup_interval_seconds: int = 0,
) -> dict[str, Any]:
    if status_interval_seconds < MIN_STATUS_INTERVAL_SECONDS:
        raise CloudAgentError(
            f"status interval must be at least {MIN_STATUS_INTERVAL_SECONDS} seconds"
        )
    if backup_interval_seconds < 0:
        raise CloudAgentError("backup interval cannot be negative")
    if 0 < backup_interval_seconds < 60 * 60:
        raise CloudAgentError("automatic backup interval must be at least 1 hour")
    return {
        "schema_version": AGENT_SCHEMA_VERSION,
        "status_interval_seconds": int(status_interval_seconds),
        "backup_interval_seconds": int(backup_interval_seconds),
    }


def save_config(config: dict[str, Any], project_dir: Path | None = None) -> dict[str, Any]:
    validated = build_config(
        status_interval_seconds=int(config.get("status_interval_seconds", DEFAULT_STATUS_INTERVAL_SECONDS)),
        backup_interval_seconds=int(config.get("backup_interval_seconds", 0)),
    )
    atomic_write_json(config_path(project_dir), validated)
    return validated


def load_config(project_dir: Path | None = None) -> dict[str, Any]:
    path = config_path(project_dir)
    if not path.exists():
        return build_config()
    ensure_private_file(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CloudAgentError("Cloud agent configuration is damaged.") from exc
    if payload.get("schema_version") != AGENT_SCHEMA_VERSION:
        raise CloudAgentError("Unsupported cloud agent configuration version.")
    return build_config(
        status_interval_seconds=int(payload.get("status_interval_seconds", DEFAULT_STATUS_INTERVAL_SECONDS)),
        backup_interval_seconds=int(payload.get("backup_interval_seconds", 0)),
    )


def load_state(project_dir: Path | None = None) -> dict[str, Any] | None:
    path = state_path(project_dir)
    if not path.exists():
        return None
    ensure_private_file(path)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _save_state(state: dict[str, Any], project_dir: Path) -> None:
    atomic_write_json(state_path(project_dir), state)


def _pid_alive(pid: int | None) -> bool:
    if not pid or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def agent_is_running(project_dir: Path | None = None) -> bool:
    state = load_state(project_dir)
    return bool(state and _pid_alive(state.get("pid")))


def _log(message: str, project_dir: Path) -> None:
    path = log_path(project_dir)
    ensure_private_dir(path.parent)
    timestamp = datetime.now(timezone.utc).isoformat()
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{timestamp} {message}\n")
    ensure_private_file(path)


def run_agent(project_dir: Path) -> int:
    root = project_dir.resolve()
    config = load_config(root)
    stop_requested = False

    def request_stop(*_args: Any) -> None:
        nonlocal stop_requested
        stop_requested = True

    if os.name != "nt":
        signal.signal(signal.SIGTERM, request_stop)
        signal.signal(signal.SIGINT, request_stop)

    state: dict[str, Any] = {
        "schema_version": AGENT_SCHEMA_VERSION,
        "pid": os.getpid(),
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "last_status_sync_at": None,
        "last_status_sync_ok": None,
        "last_status_error": None,
        "last_backup_at": None,
        "last_backup_id": None,
        "last_backup_ok": None,
        "last_backup_error": None,
        "consecutive_status_failures": 0,
    }
    _save_state(state, root)
    _log("cloud agent started", root)

    status_interval = int(config["status_interval_seconds"])
    backup_interval = int(config["backup_interval_seconds"])
    next_status = time.monotonic()
    next_backup = time.monotonic() + backup_interval if backup_interval else None

    try:
        while not stop_requested:
            now = time.monotonic()
            if now >= next_status:
                try:
                    sync_status(root)
                    state["last_status_sync_at"] = datetime.now(timezone.utc).isoformat()
                    state["last_status_sync_ok"] = True
                    state["last_status_error"] = None
                    state["consecutive_status_failures"] = 0
                    next_status = now + status_interval
                    _log("status sync succeeded", root)
                except Exception as exc:
                    state["last_status_sync_at"] = datetime.now(timezone.utc).isoformat()
                    state["last_status_sync_ok"] = False
                    state["last_status_error"] = f"{type(exc).__name__}: {exc}"[:1000]
                    failures = int(state.get("consecutive_status_failures", 0)) + 1
                    state["consecutive_status_failures"] = failures
                    backoff = min(status_interval * (2 ** min(failures - 1, 5)), MAX_BACKOFF_SECONDS)
                    next_status = now + backoff
                    _log(f"status sync failed; retry in {backoff}s: {type(exc).__name__}", root)
                _save_state(state, root)

            if next_backup is not None and now >= next_backup:
                try:
                    created = create_backup(root)
                    upload_backup(created["backup_id"], root)
                    state["last_backup_at"] = datetime.now(timezone.utc).isoformat()
                    state["last_backup_id"] = created["backup_id"]
                    state["last_backup_ok"] = True
                    state["last_backup_error"] = None
                    _log(f"encrypted backup uploaded: {created['backup_id']}", root)
                except Exception as exc:
                    state["last_backup_at"] = datetime.now(timezone.utc).isoformat()
                    state["last_backup_ok"] = False
                    state["last_backup_error"] = f"{type(exc).__name__}: {exc}"[:1000]
                    _log(f"automatic backup failed: {type(exc).__name__}", root)
                next_backup = time.monotonic() + backup_interval
                _save_state(state, root)

            time.sleep(0.5)
    finally:
        state["status"] = "stopped"
        state["stopped_at"] = datetime.now(timezone.utc).isoformat()
        _save_state(state, root)
        _log("cloud agent stopped", root)
    return 0


def start_agent(
    project_dir: Path | None = None,
    *,
    status_interval_seconds: int = DEFAULT_STATUS_INTERVAL_SECONDS,
    backup_interval_seconds: int = 0,
) -> dict[str, Any]:
    root = _root(project_dir)
    if agent_is_running(root):
        raise CloudAgentError("Cloud agent is already running for this project.")
    save_config(
        build_config(
            status_interval_seconds=status_interval_seconds,
            backup_interval_seconds=backup_interval_seconds,
        ),
        root,
    )
    ensure_private_dir(log_path(root).parent)

    command = [sys.executable, "-m", "minit.cloud_agent", str(root)]
    kwargs: dict[str, Any] = {
        "cwd": str(root),
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True,
        "env": supervisor_environment(),
    }
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    process = subprocess.Popen(command, **kwargs)

    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        state = load_state(root)
        if state and state.get("pid") == process.pid and state.get("status") == "running":
            return state
        if process.poll() is not None:
            raise CloudAgentError("Cloud agent exited during startup.")
        time.sleep(0.1)
    raise CloudAgentError("Timed out waiting for cloud agent startup.")


def stop_agent(project_dir: Path | None = None) -> dict[str, Any] | None:
    root = _root(project_dir)
    state = load_state(root)
    if state is None:
        return None
    pid = state.get("pid")
    if not _pid_alive(pid):
        state["status"] = "stopped"
        _save_state(state, root)
        return state
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        pass
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if not _pid_alive(pid):
            break
        time.sleep(0.1)
    if _pid_alive(pid):
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
    final = load_state(root) or state
    final["status"] = "stopped"
    _save_state(final, root)
    return final


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python -m minit.cloud_agent <project-dir>", file=sys.stderr)
        return 2
    return run_agent(Path(sys.argv[1]))


if __name__ == "__main__":
    raise SystemExit(main())
