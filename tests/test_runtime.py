import json
import os
from pathlib import Path

from minit.runtime import (
    _is_fresh_runtime_generation,
    app_log_path,
    load_runtime_state,
    pid_is_alive,
    process_create_time,
    runtime_state_path,
    save_runtime_state,
    stop_local_service,
    tail_app_log,
)


def test_runtime_state_is_project_local(tmp_path: Path):
    state = {
        "supervisor_pid": None,
        "app_pid": None,
        "status": "stopped",
        "health": "stopped",
    }

    save_runtime_state(state, tmp_path)

    assert runtime_state_path(tmp_path) == tmp_path / ".minit" / "runtime.json"
    assert load_runtime_state(tmp_path) == state


def test_fresh_runtime_generation_does_not_require_launcher_pid_identity():
    state = {
        "app_id": "app-1",
        "supervisor_pid": 5678,
        "started_at": "2026-08-23T11:20:05+00:00",
        "status": "running",
        "health": "healthy",
    }

    assert _is_fresh_runtime_generation(
        state,
        app_id="app-1",
        previous_started_at="2026-08-23T11:19:00+00:00",
    )
    assert not _is_fresh_runtime_generation(
        state,
        app_id="app-1",
        previous_started_at=state["started_at"],
    )
    assert not _is_fresh_runtime_generation(
        state,
        app_id="another-app",
        previous_started_at=None,
    )


def test_pid_liveness_is_bound_to_process_generation():
    pid = os.getpid()
    created_at = process_create_time(pid)

    assert created_at is not None
    assert pid_is_alive(pid, created_at)
    assert not pid_is_alive(pid, created_at + 60.0)


def test_app_logs_are_kept_under_local_minit_directory(tmp_path: Path):
    path = app_log_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text("one\ntwo\nthree\n", encoding="utf-8")

    assert path == tmp_path / ".minit" / "logs" / "app.log"
    assert tail_app_log(tmp_path, lines=2) == ["two", "three"]


def test_stop_marks_stale_runtime_state_stopped(tmp_path: Path):
    save_runtime_state(
        {
            "supervisor_pid": 999999999,
            "app_pid": 999999998,
            "status": "running",
            "health": "healthy",
            "stopped_at": None,
        },
        tmp_path,
    )

    final = stop_local_service(tmp_path)

    assert final is not None
    assert final["status"] == "stopped"
    assert final["app_pid"] is None
    assert final["stopped_at"] is not None


def test_runtime_state_file_contains_no_remote_credentials_by_default(tmp_path: Path):
    save_runtime_state(
        {
            "supervisor_pid": None,
            "app_pid": None,
            "status": "stopped",
            "health": "stopped",
        },
        tmp_path,
    )

    content = json.loads(runtime_state_path(tmp_path).read_text(encoding="utf-8"))
    assert "token" not in content
    assert "secret" not in content
    assert "api_key" not in content
