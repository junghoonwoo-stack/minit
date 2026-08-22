from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from minit.main import app
from minit.service import load_service_spec
from minit.state import create_manifest, record_publish_start, record_publish_stop

runner = CliRunner()


def test_status_reads_local_management_state(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    create_manifest(tmp_path, name="demo-app")
    started = datetime(2026, 8, 22, 6, 0, 0, tzinfo=timezone.utc)
    record_publish_start(tmp_path, started_at=started)
    record_publish_stop(
        started,
        tmp_path,
        stopped_at=datetime(2026, 8, 22, 6, 2, 5, tzinfo=timezone.utc),
    )

    result = runner.invoke(app, ["status"])

    assert result.exit_code == 0
    assert "demo-app" in result.stdout
    assert "successful runs: 1" in result.stdout
    assert "total live time: 2m 5s" in result.stdout
    assert "status source:   local only" in result.stdout


def test_status_fails_cleanly_without_manifest(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["status"])

    assert result.exit_code == 1
    assert "not initialized" in result.stdout


def test_deploy_configures_local_service_without_upload(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    with patch("minit.main._port_open", return_value=False), patch(
        "minit.main.start_local_service",
        return_value={"supervisor_pid": 1234, "status": "starting"},
    ):
        result = runner.invoke(
            app,
            ["deploy", "--port", "8000", "--", "python", "app.py"],
        )

    assert result.exit_code == 0
    assert "without this terminal" in result.stdout
    assert "No code or app data was uploaded" in result.stdout

    spec = load_service_spec(tmp_path)
    assert spec is not None
    assert spec["command"] == ["python", "app.py"]
    assert spec["port"] == 8000


def test_deploy_requires_explicit_app_command(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["deploy", "--port", "8000"])

    assert result.exit_code == 2
    assert "No app command provided" in result.stdout


def test_deploy_refuses_to_take_over_an_occupied_port(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    with patch("minit.main._port_open", return_value=True):
        result = runner.invoke(
            app,
            ["deploy", "--port", "8000", "--", "python", "app.py"],
        )

    assert result.exit_code == 1
    assert "already in use" in result.stdout
