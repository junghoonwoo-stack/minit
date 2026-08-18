import json
from pathlib import Path

from minit.state import SCHEMA_VERSION, create_manifest, load_manifest, manifest_path


def test_manifest_persists_app_identity(tmp_path: Path):
    manifest = create_manifest(tmp_path, name="demo-app")

    assert manifest["schema_version"] == SCHEMA_VERSION
    assert manifest["name"] == "demo-app"
    assert manifest["runtime"] == "local"
    assert manifest["provider"] == "auto"
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
