from __future__ import annotations

import hmac
import json
import os
import re
import sqlite3
import struct
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

APP = FastAPI(title="Minit Cloud Admin", version="0.1.0")

BACKUP_MAGIC = b"MINITB01"
HEADER_LENGTH_BYTES = 4
MAX_HEADER_BYTES = 16 * 1024 * 1024
BACKUP_ID_RE = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$")
DEFAULT_MAX_BACKUP_BYTES = 5 * 1024 * 1024 * 1024


def _data_root() -> Path:
    root = Path(os.environ.get("MINIT_CLOUD_DATA_DIR", "./cloud-data")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _db_path() -> Path:
    return _data_root() / "admin.sqlite3"


def _backup_root() -> Path:
    root = _data_root() / "backups"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS latest_status (
            app_id TEXT NOT NULL,
            device_id TEXT NOT NULL,
            observed_at TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            PRIMARY KEY (app_id, device_id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS backup_objects (
            app_id TEXT NOT NULL,
            backup_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            ciphertext_bytes INTEGER NOT NULL,
            PRIMARY KEY (app_id, backup_id)
        )
        """
    )
    return conn


def _expected_token() -> str:
    token = os.environ.get("MINIT_ADMIN_TOKEN", "")
    if not token:
        raise HTTPException(status_code=503, detail="MINIT_ADMIN_TOKEN is not configured")
    return token


def require_admin_token(authorization: Annotated[str | None, Header()] = None) -> None:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    supplied = authorization.removeprefix("Bearer ")
    if not hmac.compare_digest(supplied, _expected_token()):
        raise HTTPException(status_code=401, detail="invalid bearer token")


class ServiceStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")
    configured: bool
    running: bool
    status: str = Field(max_length=64)
    health: str = Field(max_length=64)
    restart_count: int = Field(ge=0)
    autostart: bool


class ResourceStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")
    available: bool
    cpu_percent: float | int | None = Field(default=None, ge=0)
    rss_bytes: int | None = Field(default=None, ge=0)
    child_processes: int | None = Field(default=None, ge=0)


class HistoryStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")
    successful_runs: int = Field(ge=0)
    total_live_seconds: int = Field(ge=0)


class BackupStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")
    available: bool
    backup_id: str | None = Field(default=None, max_length=64)
    created_at: str | None = Field(default=None, max_length=64)
    ciphertext_bytes: int | None = Field(default=None, ge=0)


class StatusPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: int = Field(ge=1, le=1)
    app_id: UUID
    device_id: UUID
    observed_at: datetime
    service: ServiceStatus
    resources: ResourceStatus
    history: HistoryStatus
    backup: BackupStatus


@APP.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@APP.post("/v1/status", dependencies=[Depends(require_admin_token)])
def put_status(payload: StatusPayload) -> dict[str, str]:
    encoded = payload.model_dump_json()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO latest_status(app_id, device_id, observed_at, payload_json)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(app_id, device_id) DO UPDATE SET
              observed_at=excluded.observed_at,
              payload_json=excluded.payload_json
            """,
            (str(payload.app_id), str(payload.device_id), payload.observed_at.isoformat(), encoded),
        )
        conn.commit()
    return {"status": "stored"}


@APP.get("/v1/status", dependencies=[Depends(require_admin_token)])
def get_status() -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT payload_json FROM latest_status ORDER BY observed_at DESC"
        ).fetchall()
    return [json.loads(row["payload_json"]) for row in rows]


def _safe_backup_id(value: str) -> str:
    if not BACKUP_ID_RE.fullmatch(value):
        raise HTTPException(status_code=400, detail="invalid backup id")
    return value


def _safe_app_id(value: str) -> str:
    try:
        return str(UUID(value))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid app id") from exc


def _inspect_backup_header(path: Path, expected_app_id: str, expected_backup_id: str) -> dict[str, Any]:
    with path.open("rb") as handle:
        if handle.read(len(BACKUP_MAGIC)) != BACKUP_MAGIC:
            raise HTTPException(status_code=400, detail="not a Minit encrypted backup")
        raw_length = handle.read(HEADER_LENGTH_BYTES)
        if len(raw_length) != HEADER_LENGTH_BYTES:
            raise HTTPException(status_code=400, detail="truncated backup header")
        header_length = struct.unpack(">I", raw_length)[0]
        if header_length <= 0 or header_length > MAX_HEADER_BYTES:
            raise HTTPException(status_code=400, detail="invalid backup header length")
        header_bytes = handle.read(header_length)
        if len(header_bytes) != header_length:
            raise HTTPException(status_code=400, detail="truncated backup header")
        try:
            header = json.loads(header_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=400, detail="invalid backup header") from exc

    if header.get("format") != "minit-data-backup" or header.get("algorithm") != "AES-256-GCM":
        raise HTTPException(status_code=400, detail="unsupported backup format")
    if header.get("app_id") != expected_app_id or header.get("backup_id") != expected_backup_id:
        raise HTTPException(status_code=400, detail="backup identity mismatch")
    created_at = header.get("created_at")
    if not isinstance(created_at, str) or len(created_at) > 64:
        raise HTTPException(status_code=400, detail="invalid backup timestamp")
    return {"created_at": created_at}


@APP.put("/v1/backups/{app_id}/{backup_id}", dependencies=[Depends(require_admin_token)])
async def upload_backup(app_id: str, backup_id: str, request: Request) -> dict[str, Any]:
    app_id = _safe_app_id(app_id)
    backup_id = _safe_backup_id(backup_id)
    app_dir = _backup_root() / app_id
    app_dir.mkdir(parents=True, exist_ok=True)
    destination = app_dir / f"{backup_id}.mnb"
    if destination.exists():
        raise HTTPException(status_code=409, detail="backup already exists")

    max_bytes = int(os.environ.get("MINIT_MAX_BACKUP_BYTES", DEFAULT_MAX_BACKUP_BYTES))
    written = 0
    fd, temp_name = tempfile.mkstemp(prefix=f".{backup_id}.", suffix=".upload", dir=app_dir)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "wb") as output:
            async for chunk in request.stream():
                written += len(chunk)
                if written > max_bytes:
                    raise HTTPException(status_code=413, detail="backup exceeds configured maximum")
                output.write(chunk)
            output.flush()
            os.fsync(output.fileno())

        header = _inspect_backup_header(temp_path, app_id, backup_id)
        temp_path.replace(destination)
        with _connect() as conn:
            conn.execute(
                """
                INSERT INTO backup_objects(app_id, backup_id, created_at, ciphertext_bytes)
                VALUES (?, ?, ?, ?)
                """,
                (app_id, backup_id, header["created_at"], written),
            )
            conn.commit()
    finally:
        temp_path.unlink(missing_ok=True)

    return {
        "status": "stored",
        "app_id": app_id,
        "backup_id": backup_id,
        "ciphertext_bytes": written,
    }


@APP.get("/v1/backups/{app_id}", dependencies=[Depends(require_admin_token)])
def list_backups(app_id: str) -> list[dict[str, Any]]:
    app_id = _safe_app_id(app_id)
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT backup_id, created_at, ciphertext_bytes
            FROM backup_objects
            WHERE app_id=?
            ORDER BY created_at DESC
            """,
            (app_id,),
        ).fetchall()
    return [dict(row) for row in rows]


@APP.get("/v1/backups/{app_id}/{backup_id}", dependencies=[Depends(require_admin_token)])
def download_backup(app_id: str, backup_id: str) -> Response:
    app_id = _safe_app_id(app_id)
    backup_id = _safe_backup_id(backup_id)
    path = _backup_root() / app_id / f"{backup_id}.mnb"
    if not path.exists():
        raise HTTPException(status_code=404, detail="backup not found")
    return FileResponse(path, media_type="application/octet-stream", filename=f"{backup_id}.mnb")


app = APP
