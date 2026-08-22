from __future__ import annotations

import typer

from minit.main import app, console
from minit.key_store import SecureKeyStoreUnavailable
from minit.recovery import (
    RecoveryError,
    create_recovery_envelope,
    recover_app_key_to_current_device,
    recovery_is_configured,
)

recovery_app = typer.Typer(help="Configure and use a recovery key that Minit servers never receive.")
app.add_typer(recovery_app, name="recovery")


@recovery_app.command("create")
def recovery_create():
    """Create a one-time user-held recovery key for this app."""
    try:
        recovery_key = create_recovery_envelope()
    except (RecoveryError, SecureKeyStoreUnavailable, RuntimeError) as exc:
        console.print(f"[red]Could not create recovery key:[/red] {exc}")
        raise typer.Exit(1) from exc

    console.print("[green]✓ Recovery envelope created locally.[/green]")
    console.print()
    console.print("[bold]Store this recovery key somewhere outside this computer:[/bold]")
    console.print(recovery_key, markup=False)
    console.print()
    console.print("[yellow]Minit does not store this key and cannot recover it for you.[/yellow]")
    console.print("[dim]The local recovery envelope contains ciphertext only; the recovery key itself is not written to disk.[/dim]")


@recovery_app.command("status")
def recovery_status():
    """Show whether a local recovery envelope exists. Never displays key material."""
    console.print(f"configured: {'yes' if recovery_is_configured() else 'no'}")
    console.print("server-held recovery key: no")


@recovery_app.command("restore")
def recovery_restore():
    """Re-wrap this app's key for the current device using a user-held recovery key."""
    recovery_key = typer.prompt("Recovery key", hide_input=True, confirmation_prompt=False)
    try:
        recover_app_key_to_current_device(recovery_key)
    except (RecoveryError, SecureKeyStoreUnavailable, RuntimeError, ValueError) as exc:
        console.print(f"[red]Could not recover app key:[/red] {exc}")
        raise typer.Exit(1) from exc

    console.print("[green]✓ App key recovered for this device.[/green]")
    console.print("[dim]The recovered app key was re-wrapped with this device's OS-backed root key.[/dim]")


__all__ = ["app"]
