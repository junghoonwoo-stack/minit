from __future__ import annotations

from pathlib import Path

import pytest

from minit.backups import BackupError, create_backup, data_dir, list_backups, restore_backup, verify_backup


class MemoryKeyStore:
    def __init__(self) -> None:
        self.values: dict[str, bytes] = {}

    def get(self, name: str) -> bytes | None:
        return self.values.get(name)

    def set(self, name: str, value: bytes) -> None:
        self.values[name] = bytes(value)

    def delete(self, name: str) -> None:
        self.values.pop(name, None)


def test_encrypted_backup_round_trip_preserves_local_data(tmp_path: Path):
    store = MemoryKeyStore()
    data = data_dir(tmp_path)
    data.mkdir(parents=True)
    (data / "state.db").write_bytes(b"private-state-v1")
    nested = data / "uploads"
    nested.mkdir()
    (nested / "report.txt").write_text("confidential report", encoding="utf-8")

    created = create_backup(tmp_path, store=store)
    assert created["verified"] is True
    assert created["file_count"] == 2

    backup_file = tmp_path / ".minit" / "backups" / f"{created['backup_id']}.mnb"
    raw = backup_file.read_bytes()
    assert b"private-state-v1" not in raw
    assert b"confidential report" not in raw
    assert b"state.db" not in raw
    assert b"report.txt" not in raw

    (data / "state.db").write_bytes(b"changed")
    (nested / "report.txt").unlink()
    (data / "new.txt").write_text("new data", encoding="utf-8")

    restored = restore_backup(created["backup_id"], tmp_path, store=store)
    assert restored["restored"] is True
    assert (data / "state.db").read_bytes() == b"private-state-v1"
    assert (data / "uploads" / "report.txt").read_text(encoding="utf-8") == "confidential report"
    assert not (data / "new.txt").exists()


def test_backup_tampering_is_rejected_before_restore(tmp_path: Path):
    store = MemoryKeyStore()
    data = data_dir(tmp_path)
    data.mkdir(parents=True)
    (data / "state.db").write_bytes(b"important")

    created = create_backup(tmp_path, store=store)
    backup_file = tmp_path / ".minit" / "backups" / f"{created['backup_id']}.mnb"
    raw = bytearray(backup_file.read_bytes())
    raw[-32] ^= 0x01
    backup_file.write_bytes(raw)

    with pytest.raises(BackupError, match="integrity"):
        verify_backup(created["backup_id"], tmp_path, store=store)

    assert (data / "state.db").read_bytes() == b"important"


def test_backup_index_contains_only_operational_metadata(tmp_path: Path):
    store = MemoryKeyStore()
    data = data_dir(tmp_path)
    data.mkdir(parents=True)
    (data / "customer-secret-name.txt").write_text("payload", encoding="utf-8")

    created = create_backup(tmp_path, store=store)
    entries = list_backups(tmp_path)
    assert entries[0]["backup_id"] == created["backup_id"]
    assert "path" not in entries[0]
    assert "customer-secret-name.txt" not in str(entries[0])
