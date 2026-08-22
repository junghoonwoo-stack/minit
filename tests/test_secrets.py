from pathlib import Path

from minit.app_keys import app_key_path, get_or_create_app_key
from minit.crypto import generate_key
from minit.secrets import delete_secret, get_secret, list_secret_names, secrets_path, set_secret


class MemoryKeyStore:
    def __init__(self):
        self.values = {}

    def get(self, name: str):
        return self.values.get(name)

    def set(self, name: str, value: bytes):
        self.values[name] = value

    def delete(self, name: str):
        self.values.pop(name, None)


def test_app_key_is_wrapped_on_disk_not_plaintext(tmp_path: Path):
    store = MemoryKeyStore()
    app_key = get_or_create_app_key(tmp_path, store=store)

    raw = app_key_path(tmp_path).read_bytes()
    assert app_key not in raw
    assert get_or_create_app_key(tmp_path, store=store) == app_key


def test_root_key_loss_prevents_unlocking_app_key(tmp_path: Path):
    first_store = MemoryKeyStore()
    get_or_create_app_key(tmp_path, store=first_store)

    replacement_store = MemoryKeyStore()
    replacement_store.set("device-root-v1", generate_key())

    try:
        get_or_create_app_key(tmp_path, store=replacement_store)
    except RuntimeError as exc:
        assert "Could not unlock the local app key" in str(exc)
    else:
        raise AssertionError("A different root key must not unlock the app key")


def test_secret_value_is_encrypted_and_round_trips(tmp_path: Path):
    store = MemoryKeyStore()
    value = "sk-this-must-not-appear-on-disk"

    set_secret("OPENAI_API_KEY", value, tmp_path, store=store)

    raw = secrets_path(tmp_path).read_text(encoding="utf-8")
    assert value not in raw
    assert "OPENAI_API_KEY" in raw
    assert get_secret("OPENAI_API_KEY", tmp_path, store=store) == value
    assert list_secret_names(tmp_path) == ["OPENAI_API_KEY"]


def test_secret_is_bound_to_name_and_app_context(tmp_path: Path):
    store = MemoryKeyStore()
    set_secret("TOKEN_A", "alpha", tmp_path, store=store)

    raw_path = secrets_path(tmp_path)
    raw = raw_path.read_text(encoding="utf-8").replace('"TOKEN_A"', '"TOKEN_B"', 1)
    raw_path.write_text(raw, encoding="utf-8")

    try:
        get_secret("TOKEN_B", tmp_path, store=store)
    except RuntimeError:
        pass
    else:
        raise AssertionError("Renaming a secret envelope must invalidate authentication")


def test_delete_secret_removes_ciphertext_entry(tmp_path: Path):
    store = MemoryKeyStore()
    set_secret("TOKEN", "alpha", tmp_path, store=store)
    assert delete_secret("TOKEN", tmp_path)
    assert list_secret_names(tmp_path) == []
