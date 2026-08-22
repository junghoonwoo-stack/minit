from pathlib import Path

import pytest

from minit.app_keys import get_or_create_app_key
from minit.crypto import generate_key
from minit.recovery import (
    RecoveryError,
    create_recovery_envelope,
    encode_recovery_key,
    recover_app_key_to_current_device,
    recovery_path,
)


class MemoryKeyStore:
    def __init__(self):
        self.values: dict[str, bytes] = {}

    def get(self, name: str) -> bytes | None:
        return self.values.get(name)

    def set(self, name: str, value: bytes) -> None:
        self.values[name] = value

    def delete(self, name: str) -> None:
        self.values.pop(name, None)


def test_recovery_key_is_not_written_to_recovery_envelope(tmp_path: Path):
    first_device = MemoryKeyStore()

    recovery_key = create_recovery_envelope(tmp_path, store=first_device)
    disk_text = recovery_path(tmp_path).read_text(encoding="utf-8")

    assert recovery_key.startswith("minit-recovery-v1:")
    assert recovery_key not in disk_text


def test_user_held_recovery_key_rewraps_same_app_key_for_new_device(tmp_path: Path):
    first_device = MemoryKeyStore()
    original_app_key = get_or_create_app_key(tmp_path, store=first_device)
    recovery_key = create_recovery_envelope(tmp_path, store=first_device)

    second_device = MemoryKeyStore()
    recover_app_key_to_current_device(recovery_key, tmp_path, store=second_device)
    recovered = get_or_create_app_key(tmp_path, store=second_device)

    assert recovered == original_app_key
    assert second_device.values != first_device.values


def test_wrong_recovery_key_cannot_unlock_app(tmp_path: Path):
    first_device = MemoryKeyStore()
    create_recovery_envelope(tmp_path, store=first_device)
    wrong_key = encode_recovery_key(generate_key())

    with pytest.raises(RecoveryError, match="did not unlock"):
        recover_app_key_to_current_device(wrong_key, tmp_path, store=MemoryKeyStore())


def test_recovery_create_refuses_to_silently_rotate_existing_key(tmp_path: Path):
    store = MemoryKeyStore()
    create_recovery_envelope(tmp_path, store=store)

    with pytest.raises(RecoveryError, match="already configured"):
        create_recovery_envelope(tmp_path, store=store)
