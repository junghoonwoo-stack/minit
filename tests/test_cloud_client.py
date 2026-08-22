from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from minit.backups import create_backup, data_dir
from minit.cloud_client import configure_cloud, sync_status, upload_backup


class MemoryKeyStore:
    def __init__(self) -> None:
        self.values: dict[str, bytes] = {}

    def get(self, name: str) -> bytes | None:
        return self.values.get(name)

    def set(self, name: str, value: bytes) -> None:
        self.values[name] = bytes(value)

    def delete(self, name: str) -> None:
        self.values.pop(name, None)


class CaptureHandler(BaseHTTPRequestHandler):
    status_payload: dict | None = None
    backup_payload: bytes | None = None
    auth_headers: list[str] = []

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def _reply(self, payload: dict) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers["Content-Length"])
        raw = self.rfile.read(length)
        type(self).status_payload = json.loads(raw.decode("utf-8"))
        type(self).auth_headers.append(self.headers.get("Authorization", ""))
        self._reply({"status": "stored"})

    def do_PUT(self) -> None:  # noqa: N802
        length = int(self.headers["Content-Length"])
        type(self).backup_payload = self.rfile.read(length)
        type(self).auth_headers.append(self.headers.get("Authorization", ""))
        self._reply({"status": "stored", "ciphertext_bytes": length})


def _server() -> tuple[ThreadingHTTPServer, threading.Thread]:
    CaptureHandler.status_payload = None
    CaptureHandler.backup_payload = None
    CaptureHandler.auth_headers = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), CaptureHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def test_status_sync_sends_only_allowlisted_metadata(tmp_path: Path, monkeypatch):
    store = MemoryKeyStore()
    monkeypatch.setenv("MINIT_HOME", str(tmp_path / "home"))
    server, thread = _server()
    try:
        url = f"http://127.0.0.1:{server.server_port}"
        configure_cloud(url, "test-admin-token", tmp_path, store=store)
        result = sync_status(tmp_path, store=store)
        assert result == {"status": "stored"}

        payload = CaptureHandler.status_payload
        assert payload is not None
        encoded = json.dumps(payload, sort_keys=True).lower()
        assert "command" not in encoded
        assert "working_dir" not in encoded
        assert "secret" not in encoded
        assert "log" not in encoded
        assert str(tmp_path).lower() not in encoded
        assert CaptureHandler.auth_headers == ["Bearer test-admin-token"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_backup_upload_transmits_ciphertext_not_plaintext(tmp_path: Path, monkeypatch):
    store = MemoryKeyStore()
    monkeypatch.setenv("MINIT_HOME", str(tmp_path / "home"))
    data = data_dir(tmp_path)
    data.mkdir(parents=True)
    (data / "customer.txt").write_bytes(b"TOP-SECRET-CUSTOMER-DATA")
    created = create_backup(tmp_path, store=store)

    server, thread = _server()
    try:
        url = f"http://127.0.0.1:{server.server_port}"
        configure_cloud(url, "test-admin-token", tmp_path, store=store)
        result = upload_backup(created["backup_id"], tmp_path, store=store)
        assert result["status"] == "stored"
        uploaded = CaptureHandler.backup_payload
        assert uploaded is not None
        assert uploaded.startswith(b"MINITB01")
        assert b"TOP-SECRET-CUSTOMER-DATA" not in uploaded
        assert b"customer.txt" not in uploaded
        assert CaptureHandler.auth_headers == ["Bearer test-admin-token"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
