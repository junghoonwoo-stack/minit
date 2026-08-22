from __future__ import annotations

import json
from pathlib import Path

from cryptography.exceptions import InvalidTag

from minit.crypto import KEY_BYTES, decrypt_envelope, encrypt_envelope, generate_key
from minit.key_store import KeyStore, get_or_create_device_root_key
from minit.private_fs import atomic_write_json, ensure_private_file
from minit.state import MINIT_DIR, ensure_manifest

APP_KEY_FILE = "app-key.json"


def app_key_path(project_dir: Path | None = None) -> Path:
    root = (project_dir or Path.cwd()).resolve()
    return root / MINIT_DIR / APP_KEY_FILE


def _context(app_id: str) -> dict[str, str]:
    return {"type": "app-key", "app_id": app_id}


def wrap_app_key_for_device(
    app_key: bytes,
    project_dir: Path | None = None,
    *,
    store: KeyStore | None = None,
) -> None:
    if len(app_key) != KEY_BYTES:
        raise ValueError("app key has an invalid length")
    root = (project_dir or Path.cwd()).resolve()
    manifest, _ = ensure_manifest(root)
    root_key = get_or_create_device_root_key(store)
    envelope = encrypt_envelope(app_key, root_key, context=_context(manifest["id"]))
    atomic_write_json(app_key_path(root), envelope)


def get_or_create_app_key(
    project_dir: Path | None = None,
    *,
    store: KeyStore | None = None,
) -> bytes:
    root = (project_dir or Path.cwd()).resolve()
    manifest, _ = ensure_manifest(root)
    root_key = get_or_create_device_root_key(store)
    path = app_key_path(root)
    context = _context(manifest["id"])

    if path.exists():
        ensure_private_file(path)
        with path.open("r", encoding="utf-8") as handle:
            envelope = json.load(handle)
        if envelope.get("context") != context:
            raise RuntimeError("Local app key is not bound to this Minit app identity.")
        try:
            app_key = decrypt_envelope(envelope, root_key)
        except (InvalidTag, KeyError, ValueError) as exc:
            raise RuntimeError(
                "Could not unlock the local app key. The OS root key may have changed or the key file may be damaged."
            ) from exc
        if len(app_key) != KEY_BYTES:
            raise RuntimeError("Local app key has an invalid length.")
        return app_key

    app_key = generate_key()
    wrap_app_key_for_device(app_key, root, store=store)
    return app_key
