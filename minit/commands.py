from __future__ import annotations

import json

import typer

from minit.backups import BackupError, create_backup, list_backups, restore_backup, verify_backup
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
backup_app = typer.Typer(help="Create and restore locally encrypted mutable-data backups.")
app.add_typer(recovery_app, name="recovery")
app.add_typer(cloud_app, name="cloud")
app.add_typer(backup_app, name="backup")


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


@backup_app.command("create")
def backup_create():
    """Create a streaming encrypted backup of `.minit/data`."""
    try:
        result = create_backup()
    except (BackupError, SecureKeyStoreUnavailable, RuntimeError, ValueError) as exc:
        console.print(f"[red]Could not create encrypted backup:[/red] {exc}")
        raise typer.Exit(1) from exc

    console.print(f"[green]✓ Encrypted backup:[/green] {result['backup_id']}")
    console.print(f"  files:      {result['file_count']}")
    console.print(f"  bytes:      {result['ciphertext_bytes']}")
    console.print(f"  verified:   {'yes' if result['verified'] else 'no'}")
    console.print("[dim]Plaintext archive data was not written to disk. This file is eligible for future blind cloud storage.[/dim]")


@backup_app.command("list")
def backup_list():
    """List local encrypted data backups."""
    try:
        entries = list_backups()
    except BackupError as exc:
        console.print(f"[red]Could not read backup index:[/red] {exc}")
        raise typer.Exit(1) from exc
    if not entries:
        console.print("[dim]No encrypted data backups yet.[/dim]")
        return
    for entry in entries:
        console.print(
            f"{entry['backup_id']}  {entry['created_at']}  {entry['ciphertext_bytes']} bytes  verified={entry.get('verified', False)}",
            markup=False,
        )


@backup_app.command("verify")
def backup_verify(backup_id: str):
    """Authenticate and inspect an encrypted backup without restoring it."""
    try:
        result = verify_backup(backup_id)
    except (BackupError, SecureKeyStoreUnavailable, RuntimeError, ValueError) as exc:
        console.print(f"[red]Backup verification failed:[/red] {exc}")
        raise typer.Exit(1) from exc
    console.print(f"[green]✓ Backup verified:[/green] {result['backup_id']}")
    console.print(f"  files: {result['file_count']}")


@backup_app.command("restore")
def backup_restore(
    backup_id: str,
    yes: bool = typer.Option(False, "--yes", "-y", help="Restore without interactive confirmation."),
):
    """Replace `.minit/data` with a verified encrypted backup."""
    if not yes:
        confirmed = typer.confirm(
            f"Restore {backup_id}? Current .minit/data will be replaced after integrity verification."
        )
        if not confirmed:
            raise typer.Abort()
    try:
        result = restore_backup(backup_id)
    except (BackupError, SecureKeyStoreUnavailable, RuntimeError, ValueError, OSError) as exc:
        console.print(f"[red]Backup restore failed:[/red] {exc}")
        raise typer.Exit(1) from exc
    console.print(f"[green]✓ Restored encrypted backup:[/green] {result['backup_id']}")
    console.print(f"[dim]Managed service restarted: {'yes' if result['service_restarted'] else 'no'}[/dim]")


@cloud_app.command("preview")
def cloud_preview():
    """Print the complete cleartext status payload that may be sent to a future Minit admin service."""
    try:
        payload = build_cloud_status_payload()
    except (RuntimeError, ValueError, BackupError) as exc:
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
