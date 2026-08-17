from __future__ import annotations

import re
import shutil
import socket
import subprocess
import sys
from pathlib import Path

import httpx
import typer
from rich.console import Console

app = typer.Typer(no_args_is_help=True, help="Publish local apps from your own computer.")
console = Console()

COMMON_PORTS = (3000, 5173, 8000, 8080, 8501, 8888)
URL_RE = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")


def _port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _detect_port() -> int | None:
    for port in COMMON_PORTS:
        if _port_open(port):
            return port
    return None


def _cloudflared_path() -> str | None:
    return shutil.which("cloudflared")


def _install_hint() -> str:
    if sys.platform == "darwin":
        return "Install cloudflared first: brew install cloudflared"
    if sys.platform.startswith("win"):
        return "Install cloudflared first: winget install --id Cloudflare.cloudflared"
    return "Install cloudflared first using Cloudflare's official package for your Linux distribution."


def _check_http(port: int) -> str:
    try:
        response = httpx.get(f"http://127.0.0.1:{port}", timeout=2.0, follow_redirects=True)
        return str(response.status_code)
    except Exception:
        return "reachable"


def _start_quick_tunnel(port: int) -> None:
    binary = _cloudflared_path()
    if not binary:
        console.print(f"[red]cloudflared was not found.[/red]\n{_install_hint()}")
        console.print("[dim]Minit v0.1 uses Cloudflare Quick Tunnel as its temporary relay transport.[/dim]")
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
                console.print(f"[green]✓ Compute:[/green]  this PC")
                console.print("[green]✓ Status:[/green]   live while this terminal and PC stay on")
                console.print()
                console.print("[bold]Send the URL to your first users.[/bold]")
                console.print("[dim]Press Ctrl+C to stop publishing.[/dim]")

            if "ERR" in line or "error" in line.lower():
                console.print(f"[dim]{line.rstrip()}[/dim]")

        return_code = process.wait()
        if return_code and not published_url:
            console.print("[red]Could not create a public tunnel.[/red]")
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
    console.print(f"  cloudflared: {'[green]ready[/green]' if _cloudflared_path() else '[red]missing[/red]'}")
    if selected_port:
        console.print(f"  local app:   [green]127.0.0.1:{selected_port}[/green]")
    else:
        console.print("  local app:   [yellow]not detected[/yellow]")
    console.print(f"  directory:   {Path.cwd()}")
    if not _cloudflared_path():
        console.print(f"\n{_install_hint()}")


if __name__ == "__main__":
    app()
