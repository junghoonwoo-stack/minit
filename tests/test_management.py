from datetime import datetime, timezone
from pathlib import Path

from minit.management import local_app_status, should_suggest_persistent_local_service
from minit.state import create_manifest, record_publish_start, record_publish_stop


def test_local_app_status_uses_local_manifest(tmp_path: Path):
    create_manifest(tmp_path, name="demo-app")
    started = datetime(2026, 8, 22, 6, 0, 0, tzinfo=timezone.utc)
    record_publish_start(tmp_path, started_at=started)
    record_publish_stop(
        started,
        tmp_path,
        stopped_at=datetime(2026, 8, 22, 6, 5, 0, tzinfo=timezone.utc),
    )

    status = local_app_status(tmp_path)

    assert status is not None
    assert status["name"] == "demo-app"
    assert status["runtime"] == "local"
    assert status["successful_runs"] == 1
    assert status["total_live_seconds"] == 300
    assert status["source"] == "local-manifest"


def test_first_short_run_does_not_suggest_persistent_service(tmp_path: Path):
    create_manifest(tmp_path, name="demo-app")
    started = datetime(2026, 8, 22, 6, 0, 0, tzinfo=timezone.utc)
    record_publish_start(tmp_path, started_at=started)
    record_publish_stop(
        started,
        tmp_path,
        stopped_at=datetime(2026, 8, 22, 6, 5, 0, tzinfo=timezone.utc),
    )

    assert not should_suggest_persistent_local_service(tmp_path)


def test_second_successful_run_suggests_persistent_service(tmp_path: Path):
    create_manifest(tmp_path, name="demo-app")
    first = datetime(2026, 8, 22, 6, 0, 0, tzinfo=timezone.utc)
    second = datetime(2026, 8, 22, 7, 0, 0, tzinfo=timezone.utc)

    record_publish_start(tmp_path, started_at=first)
    record_publish_stop(
        first,
        tmp_path,
        stopped_at=datetime(2026, 8, 22, 6, 1, 0, tzinfo=timezone.utc),
    )
    record_publish_start(tmp_path, started_at=second)

    assert should_suggest_persistent_local_service(tmp_path)


def test_long_live_session_suggests_persistent_service(tmp_path: Path):
    create_manifest(tmp_path, name="demo-app")
    started = datetime(2026, 8, 22, 6, 0, 0, tzinfo=timezone.utc)
    record_publish_start(tmp_path, started_at=started)
    record_publish_stop(
        started,
        tmp_path,
        stopped_at=datetime(2026, 8, 22, 6, 31, 0, tzinfo=timezone.utc),
    )

    assert should_suggest_persistent_local_service(tmp_path)
