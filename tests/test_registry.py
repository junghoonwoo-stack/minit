import json
from pathlib import Path

import pytest

from minit.registry import RegistryError, list_registered_apps, register_project, registry_path, resolve_registered_project
from minit.service import configure_local_service
from minit.state import create_manifest


def _configured_app(root: Path, name: str, port: int):
    root.mkdir(parents=True)
    create_manifest(root, name=name)
    configure_local_service(["python", "app.py"], port, root)
    return register_project(root)


def test_registry_tracks_multiple_apps_without_commands_or_secrets(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("MINIT_HOME", str(tmp_path / "home"))
    first = _configured_app(tmp_path / "one", "alpha", 8001)
    second = _configured_app(tmp_path / "two", "beta", 8002)

    entries = list_registered_apps()

    assert [entry["name"] for entry in entries] == ["alpha", "beta"]
    assert first["app_id"] != second["app_id"]
    raw = registry_path().read_text(encoding="utf-8")
    assert "command" not in raw
    assert "secret" not in raw.lower()
    assert "log" not in raw.lower()
    payload = json.loads(raw)
    assert len(payload["apps"]) == 2


def test_resolve_registered_project_by_name_or_id_prefix(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("MINIT_HOME", str(tmp_path / "home"))
    entry = _configured_app(tmp_path / "project", "alpha", 8001)

    assert resolve_registered_project("alpha") == (tmp_path / "project").resolve()
    assert resolve_registered_project(entry["app_id"][:10]) == (tmp_path / "project").resolve()


def test_resolve_reports_missing_project(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("MINIT_HOME", str(tmp_path / "home"))
    root = tmp_path / "project"
    _configured_app(root, "alpha", 8001)
    root.rename(tmp_path / "moved")

    with pytest.raises(RegistryError, match="unavailable"):
        resolve_registered_project("alpha")
