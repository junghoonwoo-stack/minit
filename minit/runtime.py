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


def load_runtime_state(project_dir: Path | None = None) -> dict[str, Any] | None:
    path = runtime_state_path(project_dir)
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None


def save_runtime_state(state: dict[str, Any], project_dir: Path | None = None) -> dict[str, Any]:
    path = runtime_state_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2)
        handle.write("\n")
    tmp.replace(path)
    return state


def _write_control(action: str, project_dir: Path | None = None) -> None:
    path = control_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "action": action,
        "requested_at": datetime.now(timezone.utc).isoformat(),
    }
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
    tmp.replace(path)


def clear_control(project_dir: Path | None = None) -> None:
    try:
        control_path(project_dir).unlink()
    except FileNotFoundError:
        pass


def read_control(project_dir: Path | None = None) -> dict[str, Any] | None:
    path = control_path(project_dir)
    if not path.exists():
        return None
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

    clear_control(root)
    logs_dir(root).mkdir(parents=True, exist_ok=True)

    command = [sys.executable, "-m", "minit.supervisor", str(root)]
    popen_kwargs: dict[str, Any] = {
        "cwd": str(root),
        "stdin": subprocess.DEVNULL,
        "close_fds": True,
    }
    if os.name == "nt":
        popen_kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_kwargs["start_new_session"] = True

    with supervisor_log_path(root).open("ab", buffering=0) as supervisor_log:
        popen_kwargs["stdout"] = supervisor_log
        popen_kwargs["stderr"] = subprocess.STDOUT
        process = subprocess.Popen(command, **popen_kwargs)

    # Do not announce a successful deploy merely because the supervisor process
    # exists. Wait until the local app reaches a real health state.
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        state = load_runtime_state(root)
        if state and state.get("supervisor_pid") == process.pid:
            status = state.get("status")
            if status == "failed":
                raise RuntimeError(state.get("error") or "Local supervisor failed to start.")
            if status in {"running", "degraded"}:
                return state
            if status == "stopped":
                exit_code = state.get("last_exit_code")
                raise RuntimeError(f"The app stopped during startup (exit code {exit_code}).")
        if process.poll() is not None:
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
        # Normal operation uses the local control file. This is only a fallback
        # for a wedged supervisor and intentionally remains local to the host.
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
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        content = handle.readlines()
    return [line.rstrip("\n") for line in content[-max(1, lines):]]
