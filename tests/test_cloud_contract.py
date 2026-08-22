from __future__ import annotations

import json
from pathlib import Path

import pytest

import minit.cloud_contract as cloud_contract
from minit.cloud_contract import build_cloud_status_payload, validate_cloud_status_payload
from minit.service import configure_local_service
from minit.state import ensure_manifest


def test_cloud_payload_excludes_sensitive_local_details(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(cloud_contract, "get_or_create_device_id", lambda: "device-opaque")
    manifest, _ = ensure_manifest(tmp_path)
    configure_local_service(["python", "super-secret-project.py"], 8123, tmp_path)

    payload = build_cloud_status_payload(tmp_path)
    encoded = json.dumps(payload, sort_keys=True)

    assert payload["app_id"] == manifest["id"]
    assert payload["device_id"] == "device-opaque"
    assert "super-secret-project.py" not in encoded
    assert str(tmp_path) not in encoded
    assert "8123" not in encoded
    assert "command" not in encoded
    assert "working_dir" not in encoded
    assert "secret" not in encoded.lower()
    assert "log" not in encoded.lower()


def test_cloud_payload_rejects_unknown_fields():
    payload = {
        "schema_version": 1,
        "app_id": "app",
        "device_id": "device",
        "observed_at": "2026-08-22T00:00:00+00:00",
        "service": {
            "configured": False,
            "running": False,
            "status": "not-configured",
            "health": "unknown",
            "restart_count": 0,
            "autostart": False,
        },
        "resources": {
            "available": False,
            "cpu_percent": None,
            "rss_bytes": None,
            "child_processes": None,
        },
        "history": {"successful_runs": 0, "total_live_seconds": 0},
        "app_name": "should-never-leave-device",
    }

    with pytest.raises(ValueError, match="non-allowlisted"):
        validate_cloud_status_payload(payload)


def test_cloud_payload_rejects_nested_sensitive_extension():
    payload = {
        "schema_version": 1,
        "app_id": "app",
        "device_id": "device",
        "observed_at": "2026-08-22T00:00:00+00:00",
        "service": {
            "configured": False,
            "running": False,
            "status": "not-configured",
            "health": "unknown",
            "restart_count": 0,
            "autostart": False,
            "raw_logs": "oops",
        },
        "resources": {
            "available": False,
            "cpu_percent": None,
            "rss_bytes": None,
            "child_processes": None,
        },
        "history": {"successful_runs": 0, "total_live_seconds": 0},
    }

    with pytest.raises(ValueError, match="non-allowlisted"):
        validate_cloud_status_payload(payload)
