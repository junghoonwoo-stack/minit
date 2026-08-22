from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from minit.runtime import app_log_path, clear_control, read_control, save_runtime_state
from minit.service import load_service_spec

HEALTH_INTERVAL_SECONDS = 2.0
STARTUP_GRACE_SECONDS = 20.0
RESTART_DELAY_SECONDS = 1.0


def _port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _process_group_kwargs() -> dict[str, Any]:
    if os.name == "nt":
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def _terminate_process_tree(process: subprocess.Popen[Any] | None) -> None:
    if process is None or process.poll() is not None:
        return

    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return

    try:
        os.killpg(process.pid, signal.SIGTERM)
    except OSError:
        try:
            process.terminate()
        except OSError:
            return

    try:
        process.wait(timeout=5)
        return
    except subprocess.TimeoutExpired:
        pass

    try:
        os.killpg(process.pid, signal.SIGKILL)
    except OSError:
        try:
            process.kill()
        except OSError:
            pass


def _base_state(spec: dict[str, Any], supervisor_pid: int) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "app_id": spec["app_id"],
        "supervisor_pid": supervisor_pid,
        "app_pid": None,
        "status": "starting",
        "health": "starting",
        "port": spec["port"],
        "restart_policy": spec["restart_policy"],
        "restart_count": 0,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "last_app_started_at": None,
        "last_health_at": None,
        "last_exit_code": None,
        "stopped_at": None,
    }


def supervise(project_dir: Path) -> int:
    root = project_dir.resolve()
    spec = load_service_spec(root)
    if spec is None:
        return 2

    clear_control(root)
    app_log_path(root).parent.mkdir(parents=True, exist_ok=True)
    state = _base_state(spec, os.getpid())
    save_runtime_state(state, root)

    app_process: subprocess.Popen[Any] | None = None
    stop_requested = False

    def request_stop(*_args: Any) -> None:
        nonlocal stop_requested
        stop_requested = True

    if os.name != "nt":
        signal.signal(signal.SIGTERM, request_stop)
        signal.signal(signal.SIGINT, request_stop)

    def start_app(log_handle: Any) -> subprocess.Popen[Any]:
        process = subprocess.Popen(
            spec["command"],
            cwd=spec["working_dir"],
            stdin=subprocess.DEVNULL,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            shell=False,
            close_fds=True,
            **_process_group_kwargs(),
        )
        state["app_pid"] = process.pid
        state["status"] = "starting"
        state["health"] = "starting"
        state["last_app_started_at"] = datetime.now(timezone.utc).isoformat()
        save_runtime_state(state, root)
        return process

    try:
        with app_log_path(root).open("ab", buffering=0) as app_log:
            app_process = start_app(app_log)
            app_started_monotonic = time.monotonic()

            while True:
                control = read_control(root)
                if stop_requested or (control and control.get("action") == "stop"):
                    break

                exit_code = app_process.poll()
                if exit_code is not None:
                    state["last_exit_code"] = exit_code
                    state["app_pid"] = None
                    save_runtime_state(state, root)

                    should_restart = spec["restart_policy"] == "always" or (
                        spec["restart_policy"] == "on-failure" and exit_code != 0
                    )
                    if not should_restart:
                        state["status"] = "stopped"
                        state["health"] = "stopped"
                        break

                    state["restart_count"] += 1
                    state["status"] = "restarting"
                    state["health"] = "restarting"
                    save_runtime_state(state, root)
                    time.sleep(RESTART_DELAY_SECONDS)
                    app_process = start_app(app_log)
                    app_started_monotonic = time.monotonic()
                    continue

                healthy = _port_open(spec["port"])
                state["last_health_at"] = datetime.now(timezone.utc).isoformat()
                if healthy:
                    state["status"] = "running"
                    state["health"] = "healthy"
                elif time.monotonic() - app_started_monotonic >= STARTUP_GRACE_SECONDS:
                    # Do not kill a process solely because its configured port is
                    # not yet healthy. Surface the condition locally first.
                    state["status"] = "degraded"
                    state["health"] = "port-unreachable"
                else:
                    state["status"] = "starting"
                    state["health"] = "starting"
                save_runtime_state(state, root)
                time.sleep(HEALTH_INTERVAL_SECONDS)

    except Exception as exc:
        state["status"] = "failed"
        state["health"] = "failed"
        state["error"] = f"{type(exc).__name__}: {exc}"
        save_runtime_state(state, root)
        return 1
    finally:
        _terminate_process_tree(app_process)
        clear_control(root)
        state["app_pid"] = None
        if state.get("status") != "failed":
            state["status"] = "stopped"
            state["health"] = "stopped"
        state["stopped_at"] = datetime.now(timezone.utc).isoformat()
        save_runtime_state(state, root)

    return 0


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python -m minit.supervisor <project-dir>", file=sys.stderr)
        return 2
    return supervise(Path(sys.argv[1]))


if __name__ == "__main__":
    raise SystemExit(main())
