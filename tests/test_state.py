from pathlib import Path

from minit.state import create_manifest, load_manifest, manifest_path


def test_manifest_persists_app_identity(tmp_path: Path):
    manifest = create_manifest(tmp_path, name="demo-app")

    assert manifest["name"] == "demo-app"
    assert manifest["runtime"] == "local"
    assert manifest["provider"] == "auto"
    assert manifest_path(tmp_path).exists()

    loaded = load_manifest(tmp_path)
    assert loaded is not None
    assert loaded["id"] == manifest["id"]
