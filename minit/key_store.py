from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Protocol

import keyring
from keyring.errors import KeyringError

from minit.crypto import KEY_BYTES, generate_key

KEYRING_SERVICE = "minit-runtime"
DEVICE_ROOT_KEY_NAME = "device-root-v1"

TRUSTED_KEYRING_MODULE_PREFIXES = (
    "keyring.backends.macOS",
    "keyring.backends.Windows",
    "keyring.backends.SecretService",
    "keyring.backends.libsecret",
    "keyring.backends.kwallet",
)


class SecureKeyStoreUnavailable(RuntimeError):
    pass


class KeyStore(Protocol):
    def get(self, name: str) -> bytes | None: ...

    def set(self, name: str, value: bytes) -> None: ...

    def delete(self, name: str) -> None: ...


@dataclass(frozen=True)
class KeyStoreStatus:
    backend: str
    trusted: bool
    reason: str


def system_key_store_status() -> KeyStoreStatus:
    backend = keyring.get_keyring()
    backend_type = type(backend)
    module = backend_type.__module__
    name = f"{module}.{backend_type.__name__}"
    trusted = any(module.startswith(prefix) for prefix in TRUSTED_KEYRING_MODULE_PREFIXES)
    if trusted:
        return KeyStoreStatus(name, True, "recognized OS-backed keyring backend")
    return KeyStoreStatus(
        name,
        False,
        "backend is not in Minit's fail-closed OS-keyring allowlist",
    )


class SystemKeyStore:
    """Store key material in an approved operating-system keyring backend.

    Minit intentionally fails closed rather than silently falling back to a
    plaintext file or an unknown third-party keyring backend.
    """

    def __init__(self) -> None:
        status = system_key_store_status()
        if not status.trusted:
            raise SecureKeyStoreUnavailable(
                f"No approved OS key store is available ({status.backend}: {status.reason})."
            )

    def get(self, name: str) -> bytes | None:
        try:
            encoded = keyring.get_password(KEYRING_SERVICE, name)
        except KeyringError as exc:
            raise SecureKeyStoreUnavailable(f"Could not read OS key store: {exc}") from exc
        if encoded is None:
            return None
        try:
            return base64.urlsafe_b64decode(encoded.encode("ascii"))
        except Exception as exc:
            raise SecureKeyStoreUnavailable("Stored Minit key material is invalid.") from exc

    def set(self, name: str, value: bytes) -> None:
        encoded = base64.urlsafe_b64encode(value).decode("ascii")
        try:
            keyring.set_password(KEYRING_SERVICE, name, encoded)
        except KeyringError as exc:
            raise SecureKeyStoreUnavailable(f"Could not write OS key store: {exc}") from exc

    def delete(self, name: str) -> None:
        try:
            keyring.delete_password(KEYRING_SERVICE, name)
        except keyring.errors.PasswordDeleteError:
            return
        except KeyringError as exc:
            raise SecureKeyStoreUnavailable(f"Could not update OS key store: {exc}") from exc


def get_or_create_device_root_key(store: KeyStore | None = None) -> bytes:
    key_store = store or SystemKeyStore()
    existing = key_store.get(DEVICE_ROOT_KEY_NAME)
    if existing is not None:
        if len(existing) != KEY_BYTES:
            raise SecureKeyStoreUnavailable("Stored device root key has an invalid length.")
        return existing

    key = generate_key()
    key_store.set(DEVICE_ROOT_KEY_NAME, key)
    # Read-after-write catches degenerate backends that pretend to accept data.
    confirmed = key_store.get(DEVICE_ROOT_KEY_NAME)
    if confirmed != key:
        raise SecureKeyStoreUnavailable("OS key store did not persist the device root key reliably.")
    return key
