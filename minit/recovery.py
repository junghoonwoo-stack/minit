from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidTag

from minit.app_keys import get_or_create_app_key, wrap_app_key_for_device
from minit.crypto import KEY_BYTES, decrypt_envelope, encrypt_envelope, generate_key
from minit.key_store import KeyStore
from minit.private_fs import atomic_write_json, ensure_private_file
from minit.state import MINIT_DIR, ensure_manifest

RECOVERY_FILE = "recovery.json"
RECOVERY_PREFIX = "minit-recovery-v1:"


class RecoveryError(RuntimeError):
    pass


def recovery_path(project_dir: Path | None = None) -> Path:
    root = (project_dir or Path.cwd()).resolve()
    return root / MINIT_DIR / RECOVERY_FILE


def encode_recovery_key(key: bytes) -> str:
    if len(key) != KEY_BYTES:
        raise ValueError("recovery key has an invalid length")
    return RECOVERY_PREFIX + base64.urlsafe_b64encode(key).decode("ascii").rstrip("=")


def decode_recovery_key(value: str) -> bytes:
    candidate = value.strip()
    if not candidate.startswith(RECOVERY_PREFIX):
        raise RecoveryError("Recovery key has an invalid prefix.")
    encoded = candidate[len(RECOVERY_PREFIX):]
    encoded += "=" * ((4 - len(encoded) % 4) % 4)
    try:
        key = base64.urlsafe_b64decode(encoded.encode("ascii"))
    except Exception as exc:
        raise RecoveryError("Recovery key is not valid base64url data.") from exc
    if len(key) != KEY_BYTES:
        raise RecoveryError("Recovery key has an invalid length.")
    return key


def _context(app_id: str) -> dict[str, str]:
    return {"type": "recovery-app-key", "app_id": app_id}


def create_recovery_envelope(
    project_dir: Path | None = None,
    *,
    store: KeyStore | None = None,
) -> str:
    root = (project_dir or Path.cwd()).resolve()
    manifest, _ = ensure_manifest(root)
    path = recovery_path(root)
    if path.exists():
        raise RecoveryError(
            "Recovery is already configured for this app. Rotation is not implemented yet; refusing to invalidate the existing recovery key."
        )

    app_key = get_or_create_app_key(root, store=store)
    recovery_key = generate_key()
    envelope = encrypt_envelope(app_key, recovery_key, context=_context(manifest["id"]))
    payload: dict[str, Any] = {
        "schema_version": 1,
        "app_id": manifest["id"],
        "envelope": envelope,
    }
    atomic_write_json(path, payload)
    return encode_recovery_key(recovery_key)


def recovery_is_configured(project_dir: Path | None = None) -> bool:
    return recovery_path(project_dir).exists()


def recover_app_key_to_current_device(
    recovery_key_value: str,
    project_dir: Path | None = None,
    *,
    store: KeyStore | None = None,
) -> None:
    root = (project_dir or Path.cwd()).resolve()
    manifest, _ = ensure_manifest(root)
    path = recovery_path(root)
    if not path.exists():
        raise RecoveryError("No recovery envelope exists for this app.")
    ensure_private_file(path)

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RecoveryError("Recovery envelope is damaged.") from exc

    if payload.get("schema_version") != 1 or payload.get("app_id") != manifest["id"]:
        raise RecoveryError("Recovery envelope does not match this Minit app identity.")
    envelope = payload.get("envelope")
    if not isinstance(envelope, dict) or envelope.get("context") != _context(manifest["id"]):
        raise RecoveryError("Recovery envelope context is invalid.")

    recovery_key = decode_recovery_key(recovery_key_value)
    try:
        app_key = decrypt_envelope(envelope, recovery_key)
    except (InvalidTag, KeyError, ValueError) as exc:
        raise RecoveryError("Recovery key did not unlock this app.") from exc
    if len(app_key) != KEY_BYTES:
        raise RecoveryError("Recovered app key has an invalid length.")

    wrap_app_key_for_device(app_key, root, store=store)
