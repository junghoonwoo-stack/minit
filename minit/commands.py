from __future__ import annotations

import json

import typer

from minit.cloud_contract import build_cloud_status_payload, cloud_cleartext_policy
from minit.main import app, console
from minit.key_store import SecureKeyStoreUnavailable
from minit.recovery import (
    RecoveryError,
    create_recovery_envelope,
    recover_app_key_to_current_device,
    recovery_is_configured,
)

recovery_app = typer.Typer(help="Configure and use a recovery key that Minit servers never receive.")
cloud_app = typer.Typer(help="Inspect the privacy-safe metadata eligible for Minit cloud administration.")
app.add_typer(recovery_app, name="recovery")
app.add_typer(cloud_app, name="cloud")


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


@cloud_app.command("preview")
def cloud_preview():
    """Print the complete cleartext status payload that may be sent to a future Minit admin service."""
    try:
        payload = build_cloud_status_payload()
    except (RuntimeError, ValueError) as exc:
        console.print(f"[red]Could not build cloud status preview:[/red] {exc}")
        raise typer.Exit(1) from exc

    console.print(json.dumps(payload, indent=2, sort_keys=True), markup=False)
    console.print()
    console.print("[bold]Privacy boundary[/bold]")
    for item in cloud_cleartext_policy():
        console.print(f"  ✓ {item}")
    console.print("[dim]Not included: app name, code, commands, file paths/names, data, raw logs, prompts, secrets, keys, inputs or outputs.[/dim]")


@cloud_app.command("status")
def cloud_status():
    """Describe the current cloud-admin implementation state without sending anything."""
    console.print("cloud admin transport: not configured")
    console.print("automatic telemetry upload: disabled")
    console.print("local runtime authority: yes")
    console.print("server-held app/data/recovery keys: no")
    console.print("Use `minit cloud preview` to inspect the exact eligible cleartext payload.")


__all__ = ["app"]
