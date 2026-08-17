from __future__ import annotations

import socket
from pathlib import Path

import httpx
import typer
from rich.console import Console

app = typer.Typer(no_args_is_help=True, help="Publish small apps from your own computer.")
console = Console()


def _port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.4)
        return sock.connect_ex(("127.0.0.1", port)) == 0


@app.command()
def run(
    port: int = typer.Option(..., "--port", "-p", help="Local HTTP port to publish."),
    relay: str = typer.Option("https://relay.minit.run", help="Minit relay URL."),
):
    """Publish an already-running local web app.

    v0.0.1 validates the local app and describes the intended relay handshake.
    The reverse-tunnel transport is the first implementation milestone.
    """
    if not _port_open(port):
        console.print(f"[red]No app is listening on 127.0.0.1:{port}[/red]")
        raise typer.Exit(1)

    try:
        response = httpx.get(f"http://127.0.0.1:{port}", timeout=2.0)
        status = response.status_code
    except Exception:
        status = "reachable"

    console.print(f"[green]✓[/green] Local app: http://127.0.0.1:{port} ({status})")
    console.print(f"[yellow]→[/yellow] Relay target: {relay}")
    console.print("[dim]Reverse-tunnel transport is not implemented yet; see docs/ARCHITECTURE.md.[/dim]")


@app.command()
def doctor(port: int = typer.Option(..., "--port", "-p")):
    """Check whether a local app is ready for Minit."""
    console.print("Minit doctor")
    console.print(f"  Local port {port}: " + ("[green]ready[/green]" if _port_open(port) else "[red]closed[/red]"))
    console.print(f"  Project directory: {Path.cwd()}")


if __name__ == "__main__":
    app()
