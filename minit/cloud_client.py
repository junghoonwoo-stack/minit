from __future__ import annotations

import hashlib
import http.client
import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from minit.backups import BackupError, _backup_path, verify_backup
from minit.cloud_contract import build_cloud_status_payload, validate_cloud_status_payload
from minit.key_store import KeyStore, SystemKeyStore
from minit.private_fs import atomic_write_json, ensure_private_file
from minit.state import MINIT_DIR

CLOUD_CONFIG_FILE = "cloud.json"
CLOUD_CONFIG_SCHEMA_VERSION = 1
TOKEN_KEY_PREFIX = "cloud-admin-token-v1:"


class CloudClientError(RuntimeError):
    pass


def cloud_config_path(project_dir: Path | None = None) -> Path:
    root = (project_dir or Path.cwd()).resolve()
    return root / MINIT_DIR / CLOUD_CONFIG_FILE


def _normalize_base_url(value: str) -> str:
    candidate = value.strip().rstrip("/")
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise CloudClientError("Cloud URL must be an http(s) URL.")
    if parsed.scheme == "http" and parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise CloudClientError("Non-local Minit cloud URLs must use HTTPS.")
    if parsed.query or parsed.fragment or parsed.username or parsed.password:
        raise CloudClientError("Cloud URL must not contain credentials, query parameters, or fragments.")
    return candidate


def _token_key(base_url: str) -> str:
    digest = hashlib.sha256(base_url.encode("utf-8")).hexdigest()[:32]
    return TOKEN_KEY_PREFIX + digest


def configure_cloud(
    base_url: str,
    token: str,
    project_dir: Path | None = None,
    *,
    store: KeyStore | None = None,
) -> dict[str, Any]:
    normalized = _normalize_base_url(base_url)
    if not token or not token.strip():
        raise CloudClientError("Cloud admin token must not be empty.")
    root = (project_dir or Path.cwd()).resolve()
    key_store = store or SystemKeyStore()
    key_store.set(_token_key(normalized), token.encode("utf-8"))
    payload = {
        "schema_version": CLOUD_CONFIG_SCHEMA_VERSION,
        "base_url": normalized,
    }
    atomic_write_json(cloud_config_path(root), payload)
    return payload


def load_cloud_config(project_dir: Path | None = None) -> dict[str, Any] | None:
    path = cloud_config_path(project_dir)
    if not path.exists():
        return None
    ensure_private_file(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CloudClientError("Local cloud configuration is damaged.") from exc
    if payload.get("schema_version") != CLOUD_CONFIG_SCHEMA_VERSION:
        raise CloudClientError("Unsupported local cloud configuration version.")
    base_url = payload.get("base_url")
    if not isinstance(base_url, str):
        raise CloudClientError("Local cloud configuration has no valid URL.")
    payload["base_url"] = _normalize_base_url(base_url)
    return payload


def cloud_is_configured(project_dir: Path | None = None) -> bool:
    return load_cloud_config(project_dir) is not None


def _load_token(base_url: str, store: KeyStore | None = None) -> str:
    key_store = store or SystemKeyStore()
    raw = key_store.get(_token_key(base_url))
    if raw is None:
        raise CloudClientError("Cloud admin token is missing from the OS key store. Re-run `minit cloud configure`.")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CloudClientError("Stored cloud admin token is invalid.") from exc


def _connection(base_url: str) -> tuple[http.client.HTTPConnection, str]:
    parsed = urlparse(base_url)
    host = parsed.hostname
    if host is None:
        raise CloudClientError("Cloud URL has no host.")
    port = parsed.port
    if parsed.scheme == "https":
        conn: http.client.HTTPConnection = http.client.HTTPSConnection(host, port=port, timeout=15)
    else:
        conn = http.client.HTTPConnection(host, port=port, timeout=15)
    prefix = parsed.path.rstrip("/")
    return conn, prefix


def _read_json_response(response: http.client.HTTPResponse) -> Any:
    raw = response.read()
    if response.status < 200 or response.status >= 300:
        detail = raw.decode("utf-8", errors="replace")[:1000]
        raise CloudClientError(f"Cloud request failed ({response.status}): {detail}")
    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CloudClientError("Cloud returned invalid JSON.") from exc


def sync_status(
    project_dir: Path | None = None,
    *,
    store: KeyStore | None = None,
) -> Any:
    root = (project_dir or Path.cwd()).resolve()
    config = load_cloud_config(root)
    if config is None:
        raise CloudClientError("Cloud admin is not configured. Run `minit cloud configure --url ...` first.")
    base_url = config["base_url"]
    token = _load_token(base_url, store)
    payload = validate_cloud_status_payload(build_cloud_status_payload(root))
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")

    conn, prefix = _connection(base_url)
    try:
        conn.request(
            "POST",
            f"{prefix}/v1/status",
            body=body,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Content-Length": str(len(body)),
                "User-Agent": "minit-runtime",
            },
        )
        return _read_json_response(conn.getresponse())
    except OSError as exc:
        raise CloudClientError(f"Could not reach Minit cloud admin service: {exc}") from exc
    finally:
        conn.close()


def upload_backup(
    backup_id: str,
    project_dir: Path | None = None,
    *,
    store: KeyStore | None = None,
) -> Any:
    root = (project_dir or Path.cwd()).resolve()
    config = load_cloud_config(root)
    if config is None:
        raise CloudClientError("Cloud admin is not configured. Run `minit cloud configure --url ...` first.")
    base_url = config["base_url"]
    token = _load_token(base_url, store)

    # Authentication/integrity is checked locally before a blob becomes eligible
    # for remote storage. Only the encrypted .mnb file is transmitted.
    verified = verify_backup(backup_id, root, store=store)
    backup_path = _backup_path(backup_id, root)
    size = backup_path.stat().st_size
    app_id = build_cloud_status_payload(root)["app_id"]

    conn, prefix = _connection(base_url)
    path = f"{prefix}/v1/backups/{app_id}/{backup_id}"
    try:
        conn.putrequest("PUT", path)
        conn.putheader("Authorization", f"Bearer {token}")
        conn.putheader("Content-Type", "application/octet-stream")
        conn.putheader("Content-Length", str(size))
        conn.putheader("User-Agent", "minit-runtime")
        conn.endheaders()
        with backup_path.open("rb") as source:
            while True:
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                conn.send(chunk)
        response = _read_json_response(conn.getresponse())
    except OSError as exc:
        raise CloudClientError(f"Could not upload encrypted backup: {exc}") from exc
    finally:
        conn.close()

    if not verified.get("verified"):
        raise BackupError("Backup was not verified before upload.")
    return response
