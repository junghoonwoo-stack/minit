from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from minit.main import app
from minit.registry import register_project, resolve_registered_project
from minit.service import configure_local_service, load_service_spec
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
    monkeypatch.setenv("MINIT_HOME", str(tmp_path / "home"))

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


def test_deploy_auto_detects_static_app(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MINIT_HOME", str(tmp_path / "home"))
    (tmp_path / "index.html").write_text("<h1>hello</h1>", encoding="utf-8")

    with patch("minit.main._port_open", return_value=False), patch(
        "minit.main.start_local_service",
        return_value={"supervisor_pid": 1234, "status": "running"},
    ):
        result = runner.invoke(app, ["deploy"])

    assert result.exit_code == 0
    assert "Detected:" in result.stdout
    assert "static" in result.stdout
    spec = load_service_spec(tmp_path)
    assert spec is not None
    assert spec["port"] == 8000
    assert spec["command"] == ["python", "-m", "http.server", "8000", "--bind", "127.0.0.1"]


def test_repeated_one_command_deploy_is_idempotent_for_running_minit_service(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MINIT_HOME", str(tmp_path / "home"))
    create_manifest(tmp_path, name="demo-app")
    configure_local_service(["python", "app.py"], 8000, tmp_path)

    with patch("minit.main.runtime_is_running", return_value=True), patch(
        "minit.main.load_runtime_state", return_value={"status": "running"}
    ), patch("minit.main.start_local_service") as start_mock, patch(
        "minit.main._port_open"
    ) as port_mock:
        result = runner.invoke(app, ["deploy"])

    assert result.exit_code == 0
    assert "Already running" in result.stdout
    assert "No redeploy was needed" in result.stdout
    start_mock.assert_not_called()
    port_mock.assert_not_called()


def test_deploy_ambiguous_project_fails_cleanly(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["deploy"])

    assert result.exit_code == 2
    assert "Could not auto-detect" in result.stdout


def test_deploy_refuses_to_take_over_an_occupied_port(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    with patch("minit.main._port_open", return_value=True):
        result = runner.invoke(
            app,
            ["deploy", "--port", "8000", "--", "python", "app.py"],
        )

    assert result.exit_code == 1
    assert "already in use" in result.stdout


def test_ls_and_targeted_status_work_outside_project(tmp_path: Path, monkeypatch):
    home = tmp_path / "home"
    project = tmp_path / "apps" / "alpha"
    elsewhere = tmp_path / "elsewhere"
    project.mkdir(parents=True)
    elsewhere.mkdir()
    monkeypatch.setenv("MINIT_HOME", str(home))

    create_manifest(project, name="alpha")
    configure_local_service(["python", "app.py"], 8123, project)
    register_project(project)
    monkeypatch.chdir(elsewhere)

    listed = runner.invoke(app, ["ls"])
    status = runner.invoke(app, ["status", "alpha"])

    assert listed.exit_code == 0
    assert "alpha" in listed.stdout
    assert "8123" in listed.stdout
    assert resolve_registered_project("alpha") == project.resolve()
    assert status.exit_code == 0
    assert "alpha" in status.stdout
    assert "project:" in status.stdout
    assert "status source:   local only" in status.stdout


def test_open_targeted_app_uses_local_address_only(tmp_path: Path, monkeypatch):
    home = tmp_path / "home"
    project = tmp_path / "apps" / "alpha"
    elsewhere = tmp_path / "elsewhere"
    project.mkdir(parents=True)
    elsewhere.mkdir()
    monkeypatch.setenv("MINIT_HOME", str(home))
    create_manifest(project, name="alpha")
    configure_local_service(["python", "app.py"], 8123, project)
    register_project(project)
    monkeypatch.chdir(elsewhere)

    with patch("minit.main.runtime_is_running", return_value=True), patch(
        "minit.main._port_open", return_value=True
    ), patch("minit.main.webbrowser.open", return_value=True) as browser_open:
        result = runner.invoke(app, ["open", "alpha"])

    assert result.exit_code == 0
    assert "http://127.0.0.1:8123" in result.stdout
    assert "no public sharing" in result.stdout
    browser_open.assert_called_once_with("http://127.0.0.1:8123")
