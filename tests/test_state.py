import json
from datetime import datetime, timezone
from pathlib import Path

from minit.state import (
    SCHEMA_VERSION,
    create_manifest,
    load_manifest,
    manifest_path,
    record_publish_start,
    record_publish_stop,
)


def test_manifest_persists_app_identity(tmp_path: Path):
    manifest = create_manifest(tmp_path, name="demo-app")

    assert manifest["schema_version"] == SCHEMA_VERSION
    assert manifest["name"] == "demo-app"
    assert manifest["runtime"] == "local"
    assert manifest["provider"] == "auto"
    assert manifest["publish_history"]["successful_runs"] == 0
    assert manifest["publish_history"]["total_live_seconds"] == 0
    assert manifest_path(tmp_path).exists()

    loaded = load_manifest(tmp_path)
    assert loaded is not None
    assert loaded["id"] == manifest["id"]
    assert loaded["schema_version"] == SCHEMA_VERSION


def test_legacy_manifest_loads_with_current_defaults(tmp_path: Path):
    path = manifest_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "id": "legacy-id",
                "name": "legacy-app",
                "created_at": "2026-01-01T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )

    loaded = load_manifest(tmp_path)

    assert loaded is not None
    assert loaded["id"] == "legacy-id"
    assert loaded["schema_version"] == SCHEMA_VERSION
    assert loaded["runtime"] == "local"
    assert loaded["provider"] == "auto"
    assert loaded["publish_history"]["successful_runs"] == 0
    assert loaded["publish_history"]["first_started_at"] is None


def test_publish_history_is_recorded_locally(tmp_path: Path):
    create_manifest(tmp_path, name="demo-app")
    started = datetime(2026, 8, 18, 12, 0, 0, tzinfo=timezone.utc)
    stopped = datetime(2026, 8, 18, 12, 7, 30, tzinfo=timezone.utc)

    after_start = record_publish_start(tmp_path, started_at=started)
    assert after_start["publish_history"]["successful_runs"] == 1
    assert after_start["publish_history"]["first_started_at"] == started.isoformat()
    assert after_start["publish_history"]["last_started_at"] == started.isoformat()

    after_stop = record_publish_stop(started, tmp_path, stopped_at=stopped)
    assert after_stop is not None
    assert after_stop["publish_history"]["last_stopped_at"] == stopped.isoformat()
    assert after_stop["publish_history"]["total_live_seconds"] == 450


def test_publish_history_accumulates_runs_and_duration(tmp_path: Path):
    create_manifest(tmp_path, name="demo-app")
    first = datetime(2026, 8, 18, 12, 0, 0, tzinfo=timezone.utc)
    second = datetime(2026, 8, 19, 12, 0, 0, tzinfo=timezone.utc)

    record_publish_start(tmp_path, started_at=first)
    record_publish_stop(first, tmp_path, stopped_at=datetime(2026, 8, 18, 12, 5, 0, tzinfo=timezone.utc))
    record_publish_start(tmp_path, started_at=second)
    final = record_publish_stop(second, tmp_path, stopped_at=datetime(2026, 8, 19, 12, 10, 0, tzinfo=timezone.utc))

    assert final is not None
    assert final["publish_history"]["successful_runs"] == 2
    assert final["publish_history"]["first_started_at"] == first.isoformat()
    assert final["publish_history"]["last_started_at"] == second.isoformat()
    assert final["publish_history"]["total_live_seconds"] == 900
