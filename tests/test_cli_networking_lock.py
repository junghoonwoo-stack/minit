from __future__ import annotations

import threading
import time
from pathlib import Path

import minit.cli as cli


def test_concurrent_first_run_installs_cloudflared_once(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(cli.shutil, "which", lambda _name: None)
    monkeypatch.setattr(cli, "_cache_dir", lambda: tmp_path)

    calls = 0
    calls_lock = threading.Lock()

    def fake_download(destination: Path) -> Path:
        nonlocal calls
        with calls_lock:
            calls += 1
        time.sleep(0.25)
        destination.write_bytes(b"verified-cloudflared")
        return destination

    monkeypatch.setattr(cli, "_download_cloudflared", fake_download)

    results: list[str | None] = []
    errors: list[BaseException] = []

    def worker() -> None:
        try:
            results.append(cli._cloudflared_path(auto_install=True))
        except BaseException as exc:  # pragma: no cover - captured for assertion
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)

    filename = "cloudflared.exe" if cli.os.name == "nt" else "cloudflared"
    installed = tmp_path / filename
    expected = str(installed)
    assert not errors
    assert calls == 1
    assert results == [expected] * 4
    assert installed.read_bytes() == b"verified-cloudflared"
    assert not (tmp_path / ".cloudflared.install.lock").exists()
