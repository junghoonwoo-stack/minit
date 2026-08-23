from __future__ import annotations

import hashlib
import os
import platform
import re
import shutil
import socket
import subprocess
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import typer
from rich.console import Console

from minit.state import (
    create_manifest,
    ensure_manifest,
    load_manifest,
    manifest_path,
    record_publish_start,
    record_publish_stop,
)

app = typer.Typer(no_args_is_help=True, help="Publish local apps from your own computer.")

_ASCII_FALLBACKS = str.maketrans(
    {
        "✓": "OK",
        "→": "->",
        "—": "-",
        "–": "-",
        "…": "...",
        "•": "*",
    }
)


class MinitConsole(Console):
    """Rich console that degrades Minit's decorative glyphs safely.

    Some Windows hosts still expose a cp1252-style console even when the
    underlying application is healthy. Operational CLI output must never turn
    a successful deploy into a failure just because a decorative glyph such as
    a check mark is not representable by that stream.
    """

    def _safe_string(self, value: str) -> str:
        encoding = getattr(self.file, "encoding", None) or "utf-8"
        try:
            value.encode(encoding)
            return value
        except (LookupError, UnicodeEncodeError):
            simplified = value.translate(_ASCII_FALLBACKS)
            try:
                simplified.encode(encoding)
                return simplified
            except (LookupError, UnicodeEncodeError):
                return simplified.encode(encoding, errors="replace").decode(encoding, errors="replace")

    def print(self, *objects: Any, **kwargs: Any) -> None:
        safe_objects = tuple(self._safe_string(obj) if isinstance(obj, str) else obj for obj in objects)
        super().print(*safe_objects, **kwargs)


console = MinitConsole(safe_box=True)

COMMON_PORTS = (3000, 5173, 8000, 8080, 8501, 8888)
URL_RE = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")

# Pin the helper we execute on the user's machine and verify the downloaded
# release asset before running it. Update these values together.
CLOUDFLARED_VERSION = "2026.7.3"
CLOUDFLARED_RELEASE_BASE = f"https://github.com/cloudflare/cloudflared/releases/download/{CLOUDFLARED_VERSION}"
CLOUDFLARED_SHA256 = {
    "cloudflared-windows-amd64.exe": "8635da433b6df8194746e88ed9d2589566c20e38bfc2a80e431a348b7c765841",
    "cloudflared-darwin-amd64.tgz": "70d1c8684fa6d14b5843787ec8d1ea8e18b23650e424f4ea43d849a506487c3b",
    "cloudflared-darwin-arm64.tgz": "90c5a4f914d705fd70c135dba6d80b1791d254b08d6d4136301941f88330dd09",
    "cloudflared-linux-amd64": "9d71c677db00134c1bd4144b7783486b654ad281b1ea62b4972098d19f770f17",
    "cloudflared-linux-arm64": "65259e652a7bea08bf5df603233ab22b8bf3116af8df9f9206209af6a1b955c0",
}
INSTALL_LOCK_TIMEOUT_SECONDS = 120.0
INSTALL_LOCK_STALE_SECONDS = 300.0


def _port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _detect_port() -> int | None:
    for port in COMMON_PORTS:
        if _port_open(port):
            return port
    return None


def _cache_dir() -> Path:
    root = Path(os.environ.get("MINIT_HOME", Path.home() / ".minit"))
    return root / "bin" / CLOUDFLARED_VERSION


def _cloudflared_asset() -> tuple[str, bool]:
    system = platform.system().lower()
    machine = platform.machine().lower()

    if machine in {"x86_64", "amd64"}:
        arch = "amd64"
    elif machine in {"arm64", "aarch64"}:
        arch = "arm64"
    else:
        raise RuntimeError(f"Unsupported CPU architecture: {machine}")

    if system == "windows":
        if arch != "amd64":
            raise RuntimeError("Automatic tunnel setup currently supports Windows x64 only.")
        return "cloudflared-windows-amd64.exe", False
    if system == "darwin":
        return f"cloudflared-darwin-{arch}.tgz", True
    if system == "linux":
        return f"cloudflared-linux-{arch}", False

    raise RuntimeError(f"Unsupported operating system: {system}")


def _verify_sha256(path: Path, expected: str) -> bool:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().lower() == expected.lower()


def _download_cloudflared(destination: Path) -> Path:
    asset, compressed = _cloudflared_asset()
    expected_sha256 = CLOUDFLARED_SHA256.get(asset)
    if expected_sha256 is None:
        raise RuntimeError(f"No trusted checksum configured for {asset}.")

    url = f"{CLOUDFLARED_RELEASE_BASE}/{asset}"
    destination.parent.mkdir(parents=True, exist_ok=True)

    console.print("[dim]First run: preparing Minit networking...[/dim]")

    with tempfile.TemporaryDirectory(prefix="minit-") as tmp:
        downloaded = Path(tmp) / asset
        urllib.request.urlretrieve(url, downloaded)

        if not _verify_sha256(downloaded, expected_sha256):
            raise RuntimeError("Downloaded networking helper failed SHA256 verification.")

        if compressed:
            with tarfile.open(downloaded, "r:gz") as archive:
                member = next((m for m in archive.getmembers() if Path(m.name).name == "cloudflared"), None)
                if member is None:
                    raise RuntimeError("Downloaded tunnel package did not contain cloudflared.")
                extracted = archive.extractfile(member)
                if extracted is None:
                    raise RuntimeError("Could not extract tunnel binary.")
                with destination.open("wb") as out:
                    shutil.copyfileobj(extracted, out)
        else:
            shutil.copy2(downloaded, destination)

    if os.name != "nt":
        destination.chmod(0o755)
    return destination


def _install_lock_path(cached: Path) -> Path:
    return cached.with_name(f".{cached.name}.install.lock")


def _try_remove_stale_install_lock(lock_path: Path) -> None:
    try:
        age = time.time() - lock_path.stat().st_mtime
    except FileNotFoundError:
        return
    if age > INSTALL_LOCK_STALE_SECONDS:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def _install_cloudflared_once(cached: Path) -> str:
    cached.parent.mkdir(parents=True, exist_ok=True)
    lock_path = _install_lock_path(cached)
    deadline = time.monotonic() + INSTALL_LOCK_TIMEOUT_SECONDS

    while True:
        if cached.exists():
            return str(cached)

        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            _try_remove_stale_install_lock(lock_path)
            if time.monotonic() >= deadline:
                raise RuntimeError("Timed out waiting for another Minit process to prepare networking.")
            time.sleep(0.1)
            continue

        try:
            os.write(fd, f"pid={os.getpid()}\n".encode("ascii"))
            os.close(fd)
            fd = -1
            if cached.exists():
                return str(cached)
            return str(_download_cloudflared(cached))
        finally:
            if fd >= 0:
                os.close(fd)
            try:
                lock_path.unlink()
            except FileNotFoundError:
                pass


def _cloudflared_path(auto_install: bool = True) -> str | None:
    system_binary = shutil.which("cloudflared")
    if system_binary:
        return system_binary

    filename = "cloudflared.exe" if os.name == "nt" else "cloudflared"
    cached = _cache_dir() / filename
    if cached.exists():
        return str(cached)

    if not auto_install:
        return None

    try:
        return _install_cloudflared_once(cached)
    except Exception as exc:
        console.print(f"[red]Minit could not prepare networking automatically:[/red] {exc}")
        return None


def _check_http(port: int) -> str:
    try:
        request = urllib.request.Request(f"http://127.0.0.1:{port}", method="GET")
        with urllib.request.urlopen(request, timeout=2.0) as response:
            return str(response.status)
    except Exception:
        return "reachable"


def _public_url_reachable(url: str) -> bool:
    request = urllib.request.Request(url, method="GET", headers={"User-Agent": "minit-readiness-check"})
    try:
        with urllib.request.urlopen(request, timeout=3.0):
            return True
    except urllib.error.HTTPError:
        # DNS/TLS/routing succeeded. The app may intentionally return 4xx/5xx.
        return True
    except Exception:
        return False


def _wait_for_public_url(url: str, attempts: int = 12, delay_seconds: float = 1.0) -> bool:
    for attempt in range(attempts):
        if _public_url_reachable(url):
            return True
        if attempt < attempts - 1:
            time.sleep(delay_seconds)
    return False


def _record_publish_started() -> datetime | None:
    started_at = datetime.now(timezone.utc)
    try:
        record_publish_start(started_at=started_at)
        return started_at
    except Exception:
        # Local history must never block the core publish flow.
        return None


def _record_publish_stopped(started_at: datetime | None) -> None:
    if started_at is None:
        return
    try:
        record_publish_stop(started_at)
    except Exception:
        # Local history is best-effort and is never telemetry.
        pass


def _start_quick_tunnel(port: int) -> None:
    binary = _cloudflared_path(auto_install=True)
    if not binary:
        console.print("[red]Could not start Minit networking.[/red]")
        raise typer.Exit(2)

    command = [
        binary,
        "tunnel",
        "--url",
        f"http://127.0.0.1:{port}",
        "--no-autoupdate",
    ]

    console.print("[yellow]→[/yellow] Creating public link...")
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    published_url: str | None = None
    publish_started_at: datetime | None = None
    try:
        assert process.stdout is not None
        for line in process.stdout:
            match = URL_RE.search(line)
            if match and not published_url:
                published_url = match.group(0)
                console.print("[yellow]→[/yellow] Waiting for public link to become reachable...")
                ready = _wait_for_public_url(published_url)

                console.print()
                if ready:
                    publish_started_at = _record_publish_started()
                    console.print(f"[bold green]✓ Live URL:[/bold green] {published_url}")
                else:
                    console.print(f"[bold yellow]✓ URL created:[/bold yellow] {published_url}")
                    console.print("[yellow]  It may need a few more seconds before it is reachable.[/yellow]")
                console.print("[green]✓ Compute:[/green]  this PC")
                console.print("[green]✓ Status:[/green]   live while this terminal and PC stay on")
                console.print()
                console.print("[bold]Send the URL to your users.[/bold]")
                console.print("[dim]Press Ctrl+C to stop publishing.[/dim]")

            if "ERR" in line or "error" in line.lower():
                console.print(f"[dim]{line.rstrip()}[/dim]")

        return_code = process.wait()
        if return_code and not published_url:
            console.print("[red]Could not create a public link.[/red]")
            raise typer.Exit(return_code)
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping Minit...[/yellow]")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        console.print("[green]✓ Link closed.[/green]")
    finally:
        _record_publish_stopped(publish_started_at)


@app.command()
def init(name: str | None = typer.Option(None, "--name", "-n", help="App name. Defaults to the current directory name.")):
    """Create a persistent Minit app identity for this project."""
    existing = load_manifest()
    if existing:
        console.print(f"[yellow]Minit app already initialized:[/yellow] {existing['name']} ({existing['id']})")
        return

    manifest = create_manifest(name=name)
    console.print(f"[green]✓ Initialized:[/green] {manifest['name']}")
    console.print(f"[dim]App ID: {manifest['id']}[/dim]")
    console.print(f"[dim]Saved to {manifest_path()}[/dim]")


@app.command()
def info():
    """Show the current Minit app identity and runtime."""
    manifest = load_manifest()
    if not manifest:
        console.print("[yellow]This project is not initialized yet.[/yellow]")
        console.print("Run [bold]minit init[/bold] or simply [bold]minit run[/bold].")
        return

    console.print(f"[bold]{manifest['name']}[/bold]")
    console.print(f"  app id:   {manifest['id']}")
    console.print(f"  runtime:  {manifest.get('runtime', 'local')}")
    console.print(f"  provider: {manifest.get('provider', 'auto')}")


@app.command()
def run(
    port: int | None = typer.Option(None, "--port", "-p", help="Local HTTP port. Auto-detected when omitted."),
):
    """Publish an already-running local web app to a shareable URL."""
    selected_port = port or _detect_port()
    if selected_port is None:
        console.print("[red]No local web app found.[/red]")
        console.print("Start your app first, then run [bold]minit run --port <port>[/bold].")
        raise typer.Exit(1)

    if not _port_open(selected_port):
        console.print(f"[red]No app is listening on 127.0.0.1:{selected_port}[/red]")
        raise typer.Exit(1)

    manifest, created = ensure_manifest()
    if created:
        console.print(f"[dim]Created Minit app identity: {manifest['name']}[/dim]")

    status = _check_http(selected_port)
    console.print(f"[green]✓ Local app:[/green] http://127.0.0.1:{selected_port} ({status})")
    _start_quick_tunnel(selected_port)


@app.command()
def doctor(
    port: int | None = typer.Option(None, "--port", "-p", help="Local HTTP port. Auto-detected when omitted."),
):
    """Check whether this computer is ready to publish with Minit."""
    selected_port = port or _detect_port()
    console.print("[bold]Minit doctor[/bold]")
    console.print("  networking:  [green]ready[/green]" if _cloudflared_path(auto_install=False) else "  networking:  [yellow]will prepare automatically on first run[/yellow]")
    if selected_port:
        console.print(f"  local app:   [green]127.0.0.1:{selected_port}[/green]")
    else:
        console.print("  local app:   [yellow]not detected[/yellow]")
    console.print(f"  app identity: {'[green]ready[/green]' if load_manifest() else '[yellow]will create automatically[/yellow]'}")
    console.print(f"  directory:   {Path.cwd()}")


if __name__ == "__main__":
    app()
