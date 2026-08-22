from __future__ import annotations

import hashlib
import json
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from minit.private_fs import atomic_write_json, ensure_private_dir, ensure_private_file
from minit.runtime import restart_local_service, runtime_is_running, stop_local_service
from minit.state import MINIT_DIR, ensure_manifest

SNAPSHOT_SCHEMA_VERSION = 1
SNAPSHOTS_DIR = "snapshots"
INDEX_FILE = "index.json"
MANIFEST_ENTRY = "_minit_snapshot.json"

SOURCE_EXTENSIONS = {
    ".py", ".pyi", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx",
    ".html", ".htm", ".css", ".scss", ".sass", ".less", ".vue", ".svelte",
    ".go", ".rs", ".java", ".kt", ".kts", ".rb", ".php", ".swift",
    ".c", ".h", ".cc", ".cpp", ".hpp", ".cs", ".sh", ".bash", ".zsh",
    ".ps1", ".sql", ".toml", ".yaml", ".yml", ".json", ".xml", ".ini",
    ".cfg", ".conf", ".md",
}
SOURCE_FILENAMES = {
    "Dockerfile", "Containerfile", "Procfile", "Makefile", "Justfile",
    "Gemfile", "Rakefile", "Pipfile", "poetry.lock", "uv.lock",
    "package-lock.json", "pnpm-lock.yaml", "yarn.lock", ".env.example",
}
EXCLUDED_DIRS = {
    MINIT_DIR, ".git", ".hg", ".svn", ".venv", "venv", "node_modules",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "dist", "build",
}


class SnapshotError(RuntimeError):
    pass


def _root(project_dir: Path | None = None) -> Path:
    return (project_dir or Path.cwd()).resolve()


def snapshots_dir(project_dir: Path | None = None) -> Path:
    return _root(project_dir) / MINIT_DIR / SNAPSHOTS_DIR


def snapshot_index_path(project_dir: Path | None = None) -> Path:
    return snapshots_dir(project_dir) / INDEX_FILE


def snapshot_path(snapshot_id: str, project_dir: Path | None = None) -> Path:
    return snapshots_dir(project_dir) / f"{snapshot_id}.zip"


def _is_source_file(path: Path) -> bool:
    name = path.name
    if name in SOURCE_FILENAMES:
        return True
    if name.startswith("requirements") and name.endswith(".txt"):
        return True
    return path.suffix.lower() in SOURCE_EXTENSIONS


def _iter_source_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        try:
            rel = path.relative_to(root)
        except ValueError:
            continue
        if any(part in EXCLUDED_DIRS for part in rel.parts[:-1]):
            continue
        if path.is_symlink() or not path.is_file():
            continue
        if _is_source_file(path):
            files.append(path)
    return sorted(files, key=lambda item: item.relative_to(root).as_posix())


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load_index(project_dir: Path | None = None) -> list[dict[str, Any]]:
    path = snapshot_index_path(project_dir)
    if not path.exists():
        return []
    ensure_private_file(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SnapshotError("Local snapshot index is damaged.") from exc
    if not isinstance(payload, list):
        raise SnapshotError("Local snapshot index is invalid.")
    return payload


def _save_index(entries: list[dict[str, Any]], project_dir: Path | None = None) -> None:
    atomic_write_json(snapshot_index_path(project_dir), entries)


def create_snapshot(
    project_dir: Path | None = None,
    *,
    label: str | None = None,
    reason: str = "manual",
) -> dict[str, Any]:
    root = _root(project_dir)
    manifest, _ = ensure_manifest(root)
    source_files = _iter_source_files(root)
    if not source_files:
        raise SnapshotError("No source/config files were found to snapshot.")

    snapshot_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    archive_path = snapshot_path(snapshot_id, root)
    ensure_private_dir(archive_path.parent)

    file_manifest: dict[str, dict[str, Any]] = {}
    temp_path = archive_path.with_suffix(".tmp")
    try:
        with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for path in source_files:
                rel = path.relative_to(root).as_posix()
                data = path.read_bytes()
                file_manifest[rel] = {"sha256": _sha256_bytes(data), "size": len(data)}
                archive.writestr(rel, data)

            snapshot_manifest = {
                "schema_version": SNAPSHOT_SCHEMA_VERSION,
                "snapshot_id": snapshot_id,
                "app_id": manifest["id"],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "label": label,
                "reason": reason,
                "scope": "source-config-only",
                "files": file_manifest,
            }
            archive.writestr(
                MANIFEST_ENTRY,
                json.dumps(snapshot_manifest, sort_keys=True, separators=(",", ":")).encode("utf-8"),
            )
        if temp_path.exists():
            if temp_path.stat().st_size == 0:
                raise SnapshotError("Snapshot archive is empty.")
            temp_path.replace(archive_path)
            ensure_private_file(archive_path)
    finally:
        temp_path.unlink(missing_ok=True)

    entry = {
        "snapshot_id": snapshot_id,
        "created_at": snapshot_manifest["created_at"],
        "label": label,
        "reason": reason,
        "file_count": len(file_manifest),
        "archive_bytes": archive_path.stat().st_size,
    }
    entries = _load_index(root)
    entries.append(entry)
    _save_index(entries, root)
    return entry


def list_snapshots(project_dir: Path | None = None) -> list[dict[str, Any]]:
    return list(reversed(_load_index(project_dir)))


def _safe_member_path(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise SnapshotError(f"Unsafe snapshot path: {name}")
    if path.parts[0] in {MINIT_DIR, ".git"}:
        raise SnapshotError(f"Snapshot attempts to write protected path: {name}")
    return path


def _read_snapshot_manifest(archive: zipfile.ZipFile) -> dict[str, Any]:
    try:
        payload = json.loads(archive.read(MANIFEST_ENTRY).decode("utf-8"))
    except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SnapshotError("Snapshot manifest is missing or invalid.") from exc
    if payload.get("schema_version") != SNAPSHOT_SCHEMA_VERSION:
        raise SnapshotError("Unsupported snapshot format.")
    if payload.get("scope") != "source-config-only":
        raise SnapshotError("Snapshot scope is not safe for code rollback.")
    return payload


def restore_snapshot(snapshot_id: str, project_dir: Path | None = None) -> dict[str, Any]:
    root = _root(project_dir)
    app_manifest, _ = ensure_manifest(root)
    archive_path = snapshot_path(snapshot_id, root)
    if not archive_path.exists():
        raise SnapshotError(f"Snapshot not found: {snapshot_id}")
    ensure_private_file(archive_path)

    safety = create_snapshot(root, label="pre-rollback", reason=f"before:{snapshot_id}")
    was_running = runtime_is_running(root)
    if was_running:
        stop_local_service(root)

    restored = 0
    try:
        with zipfile.ZipFile(archive_path, "r") as archive:
            snapshot_manifest = _read_snapshot_manifest(archive)
            if snapshot_manifest.get("app_id") != app_manifest["id"]:
                raise SnapshotError("Snapshot belongs to a different Minit app identity.")

            files = snapshot_manifest.get("files")
            if not isinstance(files, dict):
                raise SnapshotError("Snapshot file manifest is invalid.")

            for name, expected in files.items():
                rel = _safe_member_path(name)
                try:
                    data = archive.read(name)
                except KeyError as exc:
                    raise SnapshotError(f"Snapshot is missing file: {name}") from exc
                if _sha256_bytes(data) != expected.get("sha256"):
                    raise SnapshotError(f"Snapshot integrity check failed: {name}")
                destination = root.joinpath(*rel.parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(data)
                restored += 1
    except Exception:
        if was_running:
            try:
                restart_local_service(root)
            except Exception:
                pass
        raise

    health = "not-running"
    if was_running:
        try:
            state = restart_local_service(root)
            health = str(state.get("health", state.get("status", "unknown")))
        except Exception as exc:
            raise SnapshotError(
                f"Files restored but app did not become healthy. Safety snapshot: {safety['snapshot_id']}. Error: {exc}"
            ) from exc

    return {
        "snapshot_id": snapshot_id,
        "safety_snapshot_id": safety["snapshot_id"],
        "restored_files": restored,
        "service_health": health,
        "note": "Files created after the snapshot were not deleted; .minit/data and other non-source data were untouched.",
    }
