from __future__ import annotations

from pathlib import Path

import pytest

import minit.cloud_agent as cloud_agent
from minit.cloud_agent import CloudAgentError, build_config, load_state, run_agent


def test_cloud_agent_backup_is_disabled_by_default():
    config = build_config()
    assert config["status_interval_seconds"] == 60
    assert config["backup_interval_seconds"] == 0


def test_cloud_agent_rejects_aggressive_or_ambiguous_schedules():
    with pytest.raises(CloudAgentError, match="at least 30"):
        build_config(status_interval_seconds=5)
    with pytest.raises(CloudAgentError, match="at least 1 hour"):
        build_config(backup_interval_seconds=300)


def test_cloud_failure_is_recorded_locally_without_touching_app_runtime(tmp_path: Path, monkeypatch):
    class StopLoop(BaseException):
        pass

    calls = {"sync": 0, "backup": 0}

    def fail_sync(project_dir=None):
        calls["sync"] += 1
        raise RuntimeError("cloud unavailable")

    def unexpected_backup(project_dir=None):
        calls["backup"] += 1
        raise AssertionError("automatic backup must be disabled")

    def stop_after_iteration(_seconds: float):
        raise StopLoop()

    monkeypatch.setattr(cloud_agent, "sync_status", fail_sync)
    monkeypatch.setattr(cloud_agent, "create_backup", unexpected_backup)
    monkeypatch.setattr(cloud_agent.time, "sleep", stop_after_iteration)

    with pytest.raises(StopLoop):
        run_agent(tmp_path)

    state = load_state(tmp_path)
    assert state is not None
    assert state["status"] == "stopped"
    assert state["last_status_sync_ok"] is False
    assert "cloud unavailable" in state["last_status_error"]
    assert calls == {"sync": 1, "backup": 0}
