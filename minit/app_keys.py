from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidTag

from minit.crypto import decrypt_envelope, encrypt_envelope, generate_key
from minit.key_store import KeyStore, get_or_create_device_root_key
from minit.state import MINIT_DIR, ensure_manifest

APP_KEY_FILE = "app-key.json"


def app_key_path(project_dir: Path | None = None) -> Path:
    root = (project_dir or Path.cwd()).resolve()
    return root / MINIT_DIR / APP_KEY_FILE


def _write_private_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
    if os.name != "nt":
        tmp.chmod(0o600)
    tmp.replace(path)


def get_or_create_app_key(
    project_dir: Path | None = None,
    *,
    store: KeyStore | None = None,
) -> bytes:
    root = (project_dir or Path.cwd()).resolve()
    manifest, _ = ensure_manifest(root)
    root_key = get_or_create_device_root_key(store)
    path = app_key_path(root)
    context = {
        "type": "app-key",
        "app_id": manifest["id"],
    }

    if path.exists():
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
        if len(app_key) != 32:
            raise RuntimeError("Local app key has an invalid length.")
        return app_key

    app_key = generate_key()
    envelope = encrypt_envelope(app_key, root_key, context=context)
    _write_private_json(path, envelope)
    return app_key
