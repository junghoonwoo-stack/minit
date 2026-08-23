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

from minit.environment import supervisor_environment
from minit.private_fs import atomic_write_json, ensure_private_dir, ensure_private_file
from minit.service import load_service_spec
from minit.state import MINIT_DIR

RUNTIME_FILE = "runtime.json"
CONTROL_FILE = "control.json"
LOG_DIR = "logs"
APP_LOG_FILE = "app.log"
SUPERVISOR_LOG_FILE = "supervisor.log"


def _project_root(project_dir: Path | None = None) -> Path:
    return (project_dir or Path.cwd()).resolve()


def runtime_state_path(project_dir: Path | None = None) -> Path:
    return _project_root(project_dir) / MINIT_DIR / RUNTIME_FILE


def control_path(project_dir: Path | None = None) -> Path:
    return _project_root(project_dir) / MINIT_DIR / CONTROL_FILE


def logs_dir(project_dir: Path | None = None) -> Path:
    return _project_root(project_dir) / MINIT_DIR / LOG_DIR


def app_log_path(project_dir: Path | None = None) -> Path:
    return logs_dir(project_dir) / APP_LOG_FILE


def supervisor_log_path(project_dir: Path | None = None) -> Path:
    return logs_dir(project_dir) / SUPERVISOR_LOG_FILE


def _prepare_private_log(path: Path) -> Path:
    ensure_private_dir(path.parent)
    if not path.exists():
        path.touch(mode=0o600, exist_ok=True)
    ensure_private_file(path)
    return path


def load_runtime_state(project_dir: Path | None = None) -> dict[str, Any] | None:
    path = runtime_state_path(project_dir)
    if not path.exists():
        return None
    ensure_private_file(path)
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None


def save_runtime_state(state: dict[str, Any], project_dir: Path | None = None) -> dict[str, Any]:
    atomic_write_json(runtime_state_path(project_dir), state)
    return state


def _write_control(action: str, project_dir: Path | None = None) -> None:
    payload = {
        "action": action,
        "requested_at": datetime.now(timezone.utc).isoformat(),
    }
    atomic_write_json(control_path(project_dir), payload)


def clear_control(project_dir: Path | None = None) -> None:
    try:
        control_path(project_dir).unlink()
    except FileNotFoundError:
        pass


def read_control(project_dir: Path | None = None) -> dict[str, Any] | None:
    path = control_path(project_dir)
    if not path.exists():
        return None
    ensure_private_file(path)
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None


def pid_is_alive(pid: int | None) -> bool:
    if not pid or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def runtime_is_running(project_dir: Path | None = None) -> bool:
    state = load_runtime_state(project_dir)
    return bool(state and pid_is_alive(state.get("supervisor_pid")))


def _is_fresh_runtime_generation(
    state: dict[str, Any] | None,
    *,
    app_id: str,
    previous_started_at: str | None,
) -> bool:
    if not state or state.get("app_id") != app_id:
        return False
    started_at = state.get("started_at")
    return bool(started_at and started_at != previous_started_at)


def _force_terminate(pid: int | None) -> None:
    if not pid or not pid_is_alive(pid):
        return

    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return

    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        return
    for _ in range(20):
        if not pid_is_alive(pid):
            return
        time.sleep(0.1)
    try:
        os.kill(pid, signal.SIGKILL)
    except OSError:
        pass


def start_local_service(project_dir: Path | None = None, timeout_seconds: float = 25.0) -> dict[str, Any]:
    root = _project_root(project_dir)
    spec = load_service_spec(root)
    if spec is None:
        raise RuntimeError("No local service is configured for this project.")
    if runtime_is_running(root):
        raise RuntimeError("The local service is already running.")

    previous_state = load_runtime_state(root)
    previous_started_at = previous_state.get("started_at") if previous_state else None

    clear_control(root)
    ensure_private_dir(logs_dir(root))

    command = [sys.executable, "-m", "minit.supervisor", str(root)]
    popen_kwargs: dict[str, Any] = {
        "cwd": str(root),
        "stdin": subprocess.DEVNULL,
        "close_fds": True,
        "env": supervisor_environment(),
    }
    if os.name == "nt":
        popen_kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_kwargs["start_new_session"] = True

    supervisor_path = _prepare_private_log(supervisor_log_path(root))
    with supervisor_path.open("ab", buffering=0) as supervisor_log:
        popen_kwargs["stdout"] = supervisor_log
        popen_kwargs["stderr"] = subprocess.STDOUT
        process = subprocess.Popen(command, **popen_kwargs)

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        state = load_runtime_state(root)
        fresh = _is_fresh_runtime_generation(
            state,
            app_id=str(spec["app_id"]),
            previous_started_at=previous_started_at,
        )
        if fresh and state is not None:
            status = state.get("status")
            if status == "failed":
                raise RuntimeError(state.get("error") or "Local supervisor failed to start.")
            if status in {"running", "degraded"}:
                return state
            if status == "stopped":
                exit_code = state.get("last_exit_code")
                raise RuntimeError(f"The app stopped during startup (exit code {exit_code}).")

        if process.poll() is not None:
            # On Windows, a Python launcher/redirector PID is not a reliable
            # identity for the long-lived detached supervisor. If a fresh
            # runtime generation has already appeared and its recorded
            # supervisor is alive, continue waiting for its health state.
            if fresh and state is not None and pid_is_alive(state.get("supervisor_pid")):
                time.sleep(0.1)
                continue
            raise RuntimeError("Local supervisor exited during startup.")
        time.sleep(0.1)

    state = load_runtime_state(root)
    health = state.get("health") if state else "unknown"
    raise RuntimeError(f"Timed out waiting for the local app to become ready (health: {health}).")


def stop_local_service(project_dir: Path | None = None, timeout_seconds: float = 10.0) -> dict[str, Any] | None:
    root = _project_root(project_dir)
    state = load_runtime_state(root)
    if state is None:
        return None

    supervisor_pid = state.get("supervisor_pid")
    if not pid_is_alive(supervisor_pid):
        state["status"] = "stopped"
        state["app_pid"] = None
        state["stopped_at"] = state.get("stopped_at") or datetime.now(timezone.utc).isoformat()
        save_runtime_state(state, root)
        return state

    _write_control("stop", root)
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if not pid_is_alive(supervisor_pid):
            break
        time.sleep(0.1)

    if pid_is_alive(supervisor_pid):
        _force_terminate(state.get("app_pid"))
        _force_terminate(supervisor_pid)

    clear_control(root)
    final = load_runtime_state(root) or state
    final["status"] = "stopped"
    final["app_pid"] = None
    final["stopped_at"] = final.get("stopped_at") or datetime.now(timezone.utc).isoformat()
    save_runtime_state(final, root)
    return final


def restart_local_service(project_dir: Path | None = None) -> dict[str, Any]:
    root = _project_root(project_dir)
    stop_local_service(root)
    return start_local_service(root)


def tail_app_log(project_dir: Path | None = None, lines: int = 50) -> list[str]:
    path = app_log_path(project_dir)
    if not path.exists():
        return []
    ensure_private_file(path)
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        content = handle.readlines()
    return [line.rstrip("\n") for line in content[-max(1, lines):]]
