from __future__ import annotations

import base64
import io
import json
import os
import shutil
import struct
import tarfile
import uuid
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from minit.app_keys import get_or_create_app_key
from minit.crypto import KEY_BYTES, decrypt_envelope, encrypt_envelope, generate_key
from minit.key_store import KeyStore
from minit.private_fs import PRIVATE_FILE_MODE, atomic_write_json, ensure_private_dir, ensure_private_file
from minit.runtime import runtime_is_running, start_local_service, stop_local_service
from minit.state import MINIT_DIR, ensure_manifest

BACKUP_DIR = "backups"
BACKUP_INDEX = "index.json"
BACKUP_MAGIC = b"MINITB01"
BACKUP_SCHEMA_VERSION = 1
HEADER_LENGTH_BYTES = 4
GCM_NONCE_BYTES = 12
GCM_TAG_BYTES = 16
FORMAT_NAME = "minit-data-backup"
ALGORITHM = "AES-256-GCM"


class BackupError(RuntimeError):
    pass


def data_dir(project_dir: Path | None = None) -> Path:
    root = (project_dir or Path.cwd()).resolve()
    return root / MINIT_DIR / "data"


def backup_dir(project_dir: Path | None = None) -> Path:
    root = (project_dir or Path.cwd()).resolve()
    return root / MINIT_DIR / BACKUP_DIR


def backup_index_path(project_dir: Path | None = None) -> Path:
    return backup_dir(project_dir) / BACKUP_INDEX


def _canonical_json(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _new_backup_id() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}-{uuid.uuid4().hex[:8]}"


def _backup_path(backup_id: str, project_dir: Path | None = None) -> Path:
    return backup_dir(project_dir) / f"{backup_id}.mnb"


def _safe_member_name(name: str) -> bool:
    path = PurePosixPath(name)
    return bool(name) and not path.is_absolute() and ".." not in path.parts


def _tar_filter(info: tarfile.TarInfo) -> tarfile.TarInfo | None:
    if info.issym() or info.islnk() or info.isdev():
        return None
    # Do not preserve owner identities from the source machine.
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    return info


class _EncryptingWriter(io.RawIOBase):
    def __init__(self, output: BinaryIO, encryptor: Any) -> None:
        self._output = output
        self._encryptor = encryptor

    def writable(self) -> bool:
        return True

    def write(self, data: bytes | bytearray) -> int:
        raw = bytes(data)
        encrypted = self._encryptor.update(raw)
        if encrypted:
            self._output.write(encrypted)
        return len(raw)

    def flush(self) -> None:
        self._output.flush()


class _DecryptingReader(io.RawIOBase):
    def __init__(self, source: BinaryIO, decryptor: Any, ciphertext_bytes: int) -> None:
        self._source = source
        self._decryptor = decryptor
        self._remaining = ciphertext_bytes
        self._finalized = False
        self._buffer = bytearray()

    def readable(self) -> bool:
        return True

    def _finish(self) -> None:
        if self._finalized:
            return
        try:
            tail = self._decryptor.finalize()
        except InvalidTag as exc:
            raise BackupError("Encrypted backup failed integrity verification.") from exc
        if tail:
            self._buffer.extend(tail)
        self._finalized = True

    def readinto(self, target: bytearray | memoryview) -> int:
        view = memoryview(target)
        while not self._buffer and not self._finalized:
            if self._remaining <= 0:
                self._finish()
                break
            chunk = self._source.read(min(1024 * 1024, self._remaining))
            if not chunk:
                raise BackupError("Encrypted backup ended before the expected authentication tag.")
            self._remaining -= len(chunk)
            plain = self._decryptor.update(chunk)
            if plain:
                self._buffer.extend(plain)

        if not self._buffer:
            return 0
        count = min(len(view), len(self._buffer))
        view[:count] = self._buffer[:count]
        del self._buffer[:count]
        return count

    def drain(self) -> None:
        scratch = bytearray(1024 * 1024)
        while self.readinto(scratch):
            pass


def _load_index(project_dir: Path | None = None) -> list[dict[str, Any]]:
    path = backup_index_path(project_dir)
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BackupError("Local backup index is damaged.") from exc
    if not isinstance(payload, list):
        raise BackupError("Local backup index is invalid.")
    return payload


def _save_index(entries: list[dict[str, Any]], project_dir: Path | None = None) -> None:
    atomic_write_json(backup_index_path(project_dir), entries, sort_keys=True)


def list_backups(project_dir: Path | None = None) -> list[dict[str, Any]]:
    return list(reversed(_load_index(project_dir)))


def latest_backup_summary(project_dir: Path | None = None) -> dict[str, Any] | None:
    entries = _load_index(project_dir)
    if not entries:
        return None
    latest = entries[-1]
    return {
        "backup_id": latest["backup_id"],
        "created_at": latest["created_at"],
        "ciphertext_bytes": int(latest["ciphertext_bytes"]),
    }


def _write_backup_stream(
    output_path: Path,
    source_data_dir: Path,
    *,
    app_id: str,
    backup_id: str,
    app_key: bytes,
) -> dict[str, Any]:
    backup_key = generate_key()
    if len(backup_key) != KEY_BYTES:
        raise BackupError("Generated backup key has an invalid length.")
    nonce = os.urandom(GCM_NONCE_BYTES)
    created_at = datetime.now(timezone.utc).isoformat()
    key_envelope = encrypt_envelope(
        backup_key,
        app_key,
        context={"type": "backup-data-key", "app_id": app_id, "backup_id": backup_id},
    )
    header: dict[str, Any] = {
        "schema_version": BACKUP_SCHEMA_VERSION,
        "format": FORMAT_NAME,
        "algorithm": ALGORITHM,
        "app_id": app_id,
        "backup_id": backup_id,
        "created_at": created_at,
        "compression": "tar-gzip",
        "nonce": base64.urlsafe_b64encode(nonce).decode("ascii"),
        "key_envelope": key_envelope,
    }
    header_bytes = _canonical_json(header)
    if len(header_bytes) > 16 * 1024 * 1024:
        raise BackupError("Backup header is unexpectedly large.")

    ensure_private_dir(output_path.parent)
    temp_path = output_path.with_name(f".{output_path.name}.{uuid.uuid4().hex}.tmp")
    file_count = 0
    try:
        with temp_path.open("wb") as output:
            output.write(BACKUP_MAGIC)
            output.write(struct.pack(">I", len(header_bytes)))
            output.write(header_bytes)

            encryptor = Cipher(algorithms.AES(backup_key), modes.GCM(nonce)).encryptor()
            encryptor.authenticate_additional_data(header_bytes)
            writer = _EncryptingWriter(output, encryptor)
            with tarfile.open(fileobj=writer, mode="w|gz") as archive:
                if source_data_dir.exists():
                    for path in sorted(source_data_dir.rglob("*")):
                        if path.is_symlink():
                            continue
                        relative = path.relative_to(source_data_dir).as_posix()
                        if not relative:
                            continue
                        archive.add(path, arcname=relative, recursive=False, filter=_tar_filter)
                        if path.is_file():
                            file_count += 1
            final = encryptor.finalize()
            if final:
                output.write(final)
            output.write(encryptor.tag)
            output.flush()
            os.fsync(output.fileno())
        if os.name != "nt":
            temp_path.chmod(PRIVATE_FILE_MODE)
        temp_path.replace(output_path)
        ensure_private_file(output_path)
    finally:
        temp_path.unlink(missing_ok=True)

    return {
        "backup_id": backup_id,
        "created_at": created_at,
        "ciphertext_bytes": output_path.stat().st_size,
        "file_count": file_count,
        "path": str(output_path),
    }


def _open_decrypted_reader(
    backup_path: Path,
    *,
    app_id: str,
    app_key: bytes,
) -> tuple[dict[str, Any], BinaryIO, _DecryptingReader]:
    source = backup_path.open("rb")
    try:
        magic = source.read(len(BACKUP_MAGIC))
        if magic != BACKUP_MAGIC:
            raise BackupError("Not a Minit encrypted backup.")
        raw_length = source.read(HEADER_LENGTH_BYTES)
        if len(raw_length) != HEADER_LENGTH_BYTES:
            raise BackupError("Encrypted backup header is truncated.")
        header_length = struct.unpack(">I", raw_length)[0]
        if header_length <= 0 or header_length > 16 * 1024 * 1024:
            raise BackupError("Encrypted backup header length is invalid.")
        header_bytes = source.read(header_length)
        if len(header_bytes) != header_length:
            raise BackupError("Encrypted backup header is truncated.")
        try:
            header = json.loads(header_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise BackupError("Encrypted backup header is invalid.") from exc

        if (
            header.get("schema_version") != BACKUP_SCHEMA_VERSION
            or header.get("format") != FORMAT_NAME
            or header.get("algorithm") != ALGORITHM
            or header.get("app_id") != app_id
        ):
            raise BackupError("Encrypted backup does not match this app or format.")
        backup_id = header.get("backup_id")
        if not isinstance(backup_id, str):
            raise BackupError("Encrypted backup ID is invalid.")
        envelope = header.get("key_envelope")
        expected_context = {"type": "backup-data-key", "app_id": app_id, "backup_id": backup_id}
        if not isinstance(envelope, dict) or envelope.get("context") != expected_context:
            raise BackupError("Encrypted backup key envelope is not bound to this app/backup.")
        try:
            backup_key = decrypt_envelope(envelope, app_key)
        except (InvalidTag, KeyError, ValueError) as exc:
            raise BackupError("Could not unlock encrypted backup data key.") from exc
        if len(backup_key) != KEY_BYTES:
            raise BackupError("Encrypted backup data key has an invalid length.")
        try:
            nonce = base64.urlsafe_b64decode(header["nonce"].encode("ascii"))
        except Exception as exc:
            raise BackupError("Encrypted backup nonce is invalid.") from exc
        if len(nonce) != GCM_NONCE_BYTES:
            raise BackupError("Encrypted backup nonce has an invalid length.")

        ciphertext_start = source.tell()
        source.seek(0, os.SEEK_END)
        end = source.tell()
        if end - ciphertext_start < GCM_TAG_BYTES:
            raise BackupError("Encrypted backup payload is truncated.")
        source.seek(end - GCM_TAG_BYTES)
        tag = source.read(GCM_TAG_BYTES)
        ciphertext_bytes = end - GCM_TAG_BYTES - ciphertext_start
        source.seek(ciphertext_start)

        decryptor = Cipher(algorithms.AES(backup_key), modes.GCM(nonce, tag)).decryptor()
        decryptor.authenticate_additional_data(_canonical_json(header))
        reader = _DecryptingReader(source, decryptor, ciphertext_bytes)
        return header, source, reader
    except Exception:
        source.close()
        raise


def verify_backup(
    backup_id: str,
    project_dir: Path | None = None,
    *,
    store: KeyStore | None = None,
) -> dict[str, Any]:
    root = (project_dir or Path.cwd()).resolve()
    manifest, _ = ensure_manifest(root)
    app_key = get_or_create_app_key(root, store=store)
    path = _backup_path(backup_id, root)
    if not path.exists():
        raise BackupError(f"Backup not found: {backup_id}")
    ensure_private_file(path)

    header, source, reader = _open_decrypted_reader(path, app_id=manifest["id"], app_key=app_key)
    file_count = 0
    try:
        buffered = io.BufferedReader(reader, buffer_size=1024 * 1024)
        with tarfile.open(fileobj=buffered, mode="r|gz") as archive:
            for member in archive:
                if not _safe_member_name(member.name) or member.issym() or member.islnk() or member.isdev():
                    raise BackupError("Encrypted backup contains an unsafe archive member.")
                if member.isfile():
                    file_count += 1
        reader.drain()
    except (tarfile.TarError, OSError) as exc:
        raise BackupError("Encrypted backup archive is invalid.") from exc
    finally:
        source.close()

    return {
        "backup_id": header["backup_id"],
        "created_at": header["created_at"],
        "ciphertext_bytes": path.stat().st_size,
        "file_count": file_count,
        "verified": True,
    }


def create_backup(
    project_dir: Path | None = None,
    *,
    store: KeyStore | None = None,
) -> dict[str, Any]:
    root = (project_dir or Path.cwd()).resolve()
    manifest, _ = ensure_manifest(root)
    app_key = get_or_create_app_key(root, store=store)
    source = data_dir(root)
    ensure_private_dir(source)
    output_root = ensure_private_dir(backup_dir(root))
    backup_id = _new_backup_id()
    output_path = output_root / f"{backup_id}.mnb"

    was_running = runtime_is_running(root)
    if was_running:
        stop_local_service(root)

    try:
        result = _write_backup_stream(
            output_path,
            source,
            app_id=manifest["id"],
            backup_id=backup_id,
            app_key=app_key,
        )
        verified = verify_backup(backup_id, root, store=store)
        result["verified"] = bool(verified["verified"])
        entries = _load_index(root)
        entries.append(
            {
                "schema_version": 1,
                "backup_id": backup_id,
                "created_at": result["created_at"],
                "ciphertext_bytes": result["ciphertext_bytes"],
                "file_count": result["file_count"],
                "verified": True,
            }
        )
        _save_index(entries, root)
        return result
    finally:
        if was_running:
            start_local_service(root)


def _extract_verified_backup(
    backup_path: Path,
    destination: Path,
    *,
    app_id: str,
    app_key: bytes,
) -> None:
    header, source, reader = _open_decrypted_reader(backup_path, app_id=app_id, app_key=app_key)
    del header
    ensure_private_dir(destination)
    try:
        buffered = io.BufferedReader(reader, buffer_size=1024 * 1024)
        with tarfile.open(fileobj=buffered, mode="r|gz") as archive:
            for member in archive:
                if not _safe_member_name(member.name) or member.issym() or member.islnk() or member.isdev():
                    raise BackupError("Encrypted backup contains an unsafe archive member.")
                target = destination / Path(*PurePosixPath(member.name).parts)
                if member.isdir():
                    ensure_private_dir(target)
                    continue
                if not member.isfile():
                    continue
                ensure_private_dir(target.parent)
                extracted = archive.extractfile(member)
                if extracted is None:
                    raise BackupError(f"Could not read backup member: {member.name}")
                with target.open("wb") as output:
                    shutil.copyfileobj(extracted, output, length=1024 * 1024)
                    output.flush()
                    os.fsync(output.fileno())
                ensure_private_file(target)
        reader.drain()
    except (tarfile.TarError, OSError) as exc:
        raise BackupError("Encrypted backup restore failed.") from exc
    finally:
        source.close()


def restore_backup(
    backup_id: str,
    project_dir: Path | None = None,
    *,
    store: KeyStore | None = None,
) -> dict[str, Any]:
    root = (project_dir or Path.cwd()).resolve()
    manifest, _ = ensure_manifest(root)
    app_key = get_or_create_app_key(root, store=store)
    path = _backup_path(backup_id, root)
    if not path.exists():
        raise BackupError(f"Backup not found: {backup_id}")

    # Verify before touching current data.
    verify_backup(backup_id, root, store=store)
    current = data_dir(root)
    staging = root / MINIT_DIR / f"restore-{backup_id}-{uuid.uuid4().hex[:8]}"
    old = root / MINIT_DIR / f"data-before-restore-{uuid.uuid4().hex[:8]}"
    was_running = runtime_is_running(root)
    if was_running:
        stop_local_service(root)

    try:
        _extract_verified_backup(path, staging, app_id=manifest["id"], app_key=app_key)
        if current.exists():
            current.replace(old)
        try:
            staging.replace(current)
        except Exception:
            if old.exists() and not current.exists():
                old.replace(current)
            raise
        shutil.rmtree(old, ignore_errors=True)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        if was_running:
            start_local_service(root)

    return {"backup_id": backup_id, "restored": True, "service_restarted": was_running}
