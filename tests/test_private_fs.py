import os
from pathlib import Path

from minit.private_fs import atomic_write_json, ensure_private_dir, harden_private_tree


def test_private_writes_use_owner_only_permissions_on_posix(tmp_path: Path):
    root = tmp_path / ".minit"
    path = root / "state.json"
    atomic_write_json(path, {"ok": True})

    assert path.read_text(encoding="utf-8").strip().startswith("{")
    if os.name != "nt":
        assert root.stat().st_mode & 0o777 == 0o700
        assert path.stat().st_mode & 0o777 == 0o600


def test_harden_private_tree_repairs_existing_permissions(tmp_path: Path):
    root = tmp_path / ".minit"
    nested = ensure_private_dir(root / "logs")
    file_path = nested / "app.log"
    file_path.write_text("hello", encoding="utf-8")

    if os.name != "nt":
        root.chmod(0o755)
        nested.chmod(0o755)
        file_path.chmod(0o644)

    harden_private_tree(root)

    if os.name != "nt":
        assert root.stat().st_mode & 0o777 == 0o700
        assert nested.stat().st_mode & 0o777 == 0o700
        assert file_path.stat().st_mode & 0o777 == 0o600
