from __future__ import annotations

import os
import platform
import re
import shutil
import socket
import subprocess
import tarfile
import tempfile
import urllib.request
from pathlib import Path

import typer
from rich.console import Console

app = typer.Typer(no_args_is_help=True, help="Publish local apps from your own computer.")
console = Console()

COMMON_PORTS = (3000, 5173, 8000, 8080, 8501, 8888)
URL_RE = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")
CLOUDFLARED_RELEASE_BASE = "https://github.com/cloudflare/cloudflared/releases/latest/download"


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
    return root / "bin"


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


def _download_cloudflared(destination: Path) -> Path:
    asset, compressed = _cloudflared_asset()
    url = f"{CLOUDFLARED_RELEASE_BASE}/{asset}"
    destination.parent.mkdir(parents=True, exist_ok=True)

    console.print("[dim]First run: preparing Minit networking...[/dim]")

    with tempfile.TemporaryDirectory(prefix="minit-") as tmp:
        downloaded = Path(tmp) / asset
        urllib.request.urlretrieve(url, downloaded)

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
        return str(_download_cloudflared(cached))
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
    try:
        assert process.stdout is not None
        for line in process.stdout:
            match = URL_RE.search(line)
            if match and not published_url:
                published_url = match.group(0)
                console.print()
                console.print(f"[bold green]✓ Live URL:[/bold green] {published_url}")
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
    console.print(f"  directory:   {Path.cwd()}")


if __name__ == "__main__":
    app()
