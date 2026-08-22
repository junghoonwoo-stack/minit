import json
import zipfile
from pathlib import Path

import pytest

from minit.snapshots import SnapshotError, create_snapshot, list_snapshots, restore_snapshot, snapshot_path
from minit.state import create_manifest


def test_snapshot_captures_source_but_not_minit_data(tmp_path: Path):
    create_manifest(tmp_path, name="demo")
    (tmp_path / "app.py").write_text("print('v1')\n", encoding="utf-8")
    data_dir = tmp_path / ".minit" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "app.db").write_text("important-data", encoding="utf-8")

    entry = create_snapshot(tmp_path, label="v1")

    with zipfile.ZipFile(snapshot_path(entry["snapshot_id"], tmp_path), "r") as archive:
        names = set(archive.namelist())

    assert "app.py" in names
    assert ".minit/data/app.db" not in names
    assert list_snapshots(tmp_path)[0]["label"] == "v1"


def test_restore_overwrites_source_and_preserves_data(tmp_path: Path):
    create_manifest(tmp_path, name="demo")
    app = tmp_path / "app.py"
    app.write_text("print('v1')\n", encoding="utf-8")
    data_dir = tmp_path / ".minit" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    db = data_dir / "app.db"
    db.write_text("data-v1", encoding="utf-8")

    entry = create_snapshot(tmp_path, label="v1")
    app.write_text("print('v2')\n", encoding="utf-8")
    db.write_text("data-v2", encoding="utf-8")

    result = restore_snapshot(entry["snapshot_id"], tmp_path)

    assert app.read_text(encoding="utf-8") == "print('v1')\n"
    assert db.read_text(encoding="utf-8") == "data-v2"
    assert result["restored_files"] == 1
    assert result["safety_snapshot_id"] != entry["snapshot_id"]


def test_restore_does_not_delete_files_created_later(tmp_path: Path):
    create_manifest(tmp_path, name="demo")
    (tmp_path / "app.py").write_text("print('v1')\n", encoding="utf-8")
    entry = create_snapshot(tmp_path)
    later = tmp_path / "later.py"
    later.write_text("print('later')\n", encoding="utf-8")

    restore_snapshot(entry["snapshot_id"], tmp_path)

    assert later.exists()


def test_restore_rejects_tampered_snapshot_content(tmp_path: Path):
    create_manifest(tmp_path, name="demo")
    (tmp_path / "app.py").write_text("print('v1')\n", encoding="utf-8")
    entry = create_snapshot(tmp_path)
    archive_path = snapshot_path(entry["snapshot_id"], tmp_path)

    with zipfile.ZipFile(archive_path, "r") as archive:
        manifest = json.loads(archive.read("_minit_snapshot.json"))

    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("app.py", b"tampered")
        archive.writestr("_minit_snapshot.json", json.dumps(manifest))

    with pytest.raises(SnapshotError, match="integrity"):
        restore_snapshot(entry["snapshot_id"], tmp_path)
