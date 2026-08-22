from datetime import datetime, timezone
from pathlib import Path

from typer.testing import CliRunner

from minit.main import app
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
