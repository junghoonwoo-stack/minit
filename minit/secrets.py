from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidTag

from minit.app_keys import get_or_create_app_key
from minit.crypto import decrypt_envelope, encrypt_envelope
from minit.key_store import KeyStore
from minit.state import MINIT_DIR, ensure_manifest

SECRETS_FILE = "secrets.json"
SECRET_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,127}$")


def secrets_path(project_dir: Path | None = None) -> Path:
    root = (project_dir or Path.cwd()).resolve()
    return root / MINIT_DIR / SECRETS_FILE


def _load_secret_envelopes(project_dir: Path | None = None) -> dict[str, dict[str, Any]]:
    path = secrets_path(project_dir)
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise RuntimeError("Local Minit secrets file is invalid.")
    return payload


def _save_secret_envelopes(
    payload: dict[str, dict[str, Any]],
    project_dir: Path | None = None,
) -> None:
    path = secrets_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    if os.name != "nt":
        tmp.chmod(0o600)
    tmp.replace(path)


def _validate_name(name: str) -> None:
    if not SECRET_NAME_RE.fullmatch(name):
        raise ValueError(
            "secret name must look like an environment variable, for example OPENAI_API_KEY"
        )


def set_secret(
    name: str,
    value: str,
    project_dir: Path | None = None,
    *,
    store: KeyStore | None = None,
) -> None:
    _validate_name(name)
    if not isinstance(value, str) or not value:
        raise ValueError("secret value must be a non-empty string")

    root = (project_dir or Path.cwd()).resolve()
    manifest, _ = ensure_manifest(root)
    app_key = get_or_create_app_key(root, store=store)
    envelopes = _load_secret_envelopes(root)
    envelopes[name] = encrypt_envelope(
        value.encode("utf-8"),
        app_key,
        context={
            "type": "app-secret",
            "app_id": manifest["id"],
            "name": name,
        },
    )
    _save_secret_envelopes(envelopes, root)


def get_secret(
    name: str,
    project_dir: Path | None = None,
    *,
    store: KeyStore | None = None,
) -> str | None:
    _validate_name(name)
    root = (project_dir or Path.cwd()).resolve()
    envelopes = _load_secret_envelopes(root)
    envelope = envelopes.get(name)
    if envelope is None:
        return None

    app_key = get_or_create_app_key(root, store=store)
    try:
        plaintext = decrypt_envelope(envelope, app_key)
    except (InvalidTag, KeyError, ValueError) as exc:
        raise RuntimeError(f"Could not decrypt local secret {name}.") from exc
    return plaintext.decode("utf-8")


def list_secret_names(project_dir: Path | None = None) -> list[str]:
    return sorted(_load_secret_envelopes(project_dir))


def delete_secret(name: str, project_dir: Path | None = None) -> bool:
    _validate_name(name)
    envelopes = _load_secret_envelopes(project_dir)
    if name not in envelopes:
        return False
    del envelopes[name]
    _save_secret_envelopes(envelopes, project_dir)
    return True


def get_all_secrets(
    project_dir: Path | None = None,
    *,
    store: KeyStore | None = None,
) -> dict[str, str]:
    root = (project_dir or Path.cwd()).resolve()
    names = list_secret_names(root)
    if not names:
        return {}
    return {
        name: value
        for name in names
        if (value := get_secret(name, root, store=store)) is not None
    }
