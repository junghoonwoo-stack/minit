from __future__ import annotations

from datetime import datetime

import typer

from minit.app_keys import get_or_create_app_key
from minit.autostart import AutostartUnavailable, autostart_info, disable_autostart, enable_autostart
from minit.cli import _port_open, app, console
from minit.key_store import SecureKeyStoreUnavailable, system_key_store_status
from minit.management import local_app_status
from minit.private_fs import harden_private_tree
from minit.runtime import (
    load_runtime_state,
    restart_local_service,
    runtime_is_running,
    start_local_service,
    stop_local_service,
    tail_app_log,
)
from minit.secrets import delete_secret, list_secret_names, set_secret
from minit.service import RESTART_POLICIES, configure_local_service, load_service_spec
from minit.snapshots import SnapshotError, create_snapshot, list_snapshots, restore_snapshot
from minit.state import MINIT_DIR

security_app = typer.Typer(help="Inspect and initialize local key protection.")
secret_app = typer.Typer(help="Manage encrypted secrets for this local app.")
autostart_app = typer.Typer(help="Start this local app automatically when the user session starts.")
snapshot_app = typer.Typer(help="Create and restore local source/config snapshots.")
app.add_typer(security_app, name="security")
app.add_typer(secret_app, name="secret")
app.add_typer(autostart_app, name="autostart")
app.add_typer(snapshot_app, name="snapshot")


def _format_duration(total_seconds: int) -> str:
    total_seconds = max(0, int(total_seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def _format_bytes(value: int | float | None) -> str:
    if value is None:
        return "unknown"
    size = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(size) < 1024.0 or unit == "TB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024.0
    return f"{size:.1f} TB"


def _format_time(value: str | None) -> str:
    if not value:
        return "never"
    try:
        return datetime.fromisoformat(value).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    except ValueError:
        return value


@app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def deploy(
    ctx: typer.Context,
    port: int = typer.Option(..., "--port", "-p", help="Local HTTP port the managed app will listen on."),
    restart_policy: str = typer.Option(
        "on-failure",
        "--restart",
        help="Restart policy: never, on-failure, or always.",
    ),
):
    """Keep an app running on this computer after the terminal closes.

    Pass the app command after `--`, for example:
    `minit deploy --port 8000 -- python app.py`

    This command does not upload the app or create a permanent public endpoint.
    """
    command = list(ctx.args)
    if not command:
        console.print("[red]No app command provided.[/red]")
        console.print("Example: [bold]minit deploy --port 8000 -- python app.py[/bold]")
        raise typer.Exit(2)

    if restart_policy not in RESTART_POLICIES:
        console.print(f"[red]Unknown restart policy:[/red] {restart_policy}")
        console.print("Choose: never, on-failure, always")
        raise typer.Exit(2)

    if _port_open(port):
        console.print(f"[red]Port 127.0.0.1:{port} is already in use.[/red]")
        console.print("Stop the existing local process before handing this app to Minit.")
        raise typer.Exit(1)

    try:
        spec = configure_local_service(command, port, restart_policy=restart_policy)
        harden_private_tree(spec_path_parent := __import__("pathlib").Path.cwd() / MINIT_DIR)
        state = start_local_service()
    except (RuntimeError, ValueError) as exc:
        console.print(f"[red]Could not deploy local service:[/red] {exc}")
        raise typer.Exit(1) from exc

    console.print(f"[green]✓ Local service:[/green] {spec['app_id']}")
    console.print(f"[green]✓ Command:[/green]       {' '.join(spec['command'])}")
    console.print(f"[green]✓ Port:[/green]          127.0.0.1:{spec['port']}")
    console.print(f"[green]✓ Supervisor:[/green]    PID {state.get('supervisor_pid')}")
    console.print(f"[green]✓ Status:[/green]        {state.get('status', 'starting')}")
    console.print(f"[green]✓ Environment:[/green]   {spec.get('environment_policy', 'minimal')}")
    console.print()
    console.print("[bold]The app now runs from this computer without this terminal.[/bold]")
    console.print("[dim]No code or app data was uploaded by this command.[/dim]")
    console.print("[dim]Arbitrary shell environment variables are not inherited by the managed app.[/dim]")
    console.print("[dim]Use `minit secret set NAME` to add an app secret from the local encrypted store.[/dim]")
    console.print("[dim]Use `minit status`, `minit logs`, `minit restart`, or `minit stop` to manage it.[/dim]")
    console.print("[dim]Use `minit autostart install` if this app should return after login/reboot.[/dim]")
    console.print("[dim]Use `minit run --port <port>` separately for temporary public sharing.[/dim]")


@app.command()
def status():
    """Show locally recorded app and service status."""
    current = local_app_status()
    if current is None:
        console.print("[yellow]This project is not initialized yet.[/yellow]")
        console.print("Run [bold]minit init[/bold], [bold]minit run[/bold], or [bold]minit deploy[/bold] first.")
        raise typer.Exit(1)

    console.print(f"[bold]{current['name']}[/bold]")
    console.print(f"  app id:          {current['app_id']}")
    console.print(f"  runtime:         {current['runtime']}")
    console.print(f"  successful runs: {current['successful_runs']}")
    console.print(f"  total live time: {_format_duration(current['total_live_seconds'])}")
    console.print(f"  last started:    {_format_time(current['last_started_at'])}")
    console.print(f"  last stopped:    {_format_time(current['last_stopped_at'])}")
    console.print(f"  local secrets:   {len(list_secret_names())} encrypted")

    spec = load_service_spec()
    runtime = load_runtime_state()
    if spec is not None:
        console.print()
        console.print("[bold]Local service[/bold]")
        console.print(f"  command:         {' '.join(spec['command'])}")
        console.print(f"  port:            127.0.0.1:{spec['port']}")
        console.print(f"  restart policy:  {spec['restart_policy']}")
        console.print(f"  environment:     {spec.get('environment_policy', 'minimal')}")
        console.print(f"  autostart:       {'enabled' if spec.get('autostart') else 'disabled'}")
        if runtime is None:
            console.print("  process:         configured, not started")
        else:
            alive = runtime_is_running()
            process_status = runtime.get("status", "unknown") if alive else "stopped"
            console.print(f"  process:         {process_status}")
            console.print(f"  health:          {runtime.get('health', 'unknown')}")
            console.print(f"  supervisor pid:  {runtime.get('supervisor_pid') if alive else '-'}")
            console.print(f"  app pid:         {runtime.get('app_pid') if alive else '-'}")
            console.print(f"  restarts:        {runtime.get('restart_count', 0)}")
            metrics = runtime.get("metrics", {})
            if alive and metrics.get("available"):
                cpu = metrics.get("cpu_percent")
                cpu_text = f"{cpu:.1f}%" if isinstance(cpu, (int, float)) else "unknown"
                console.print(f"  CPU:             {cpu_text}")
                console.print(f"  memory:          {_format_bytes(metrics.get('rss_bytes'))}")
                console.print(f"  child processes: {metrics.get('child_processes', 0)}")

    console.print("  status source:   local only")


@app.command()
def stop():
    """Stop the Minit-managed local service."""
    if load_service_spec() is None:
        console.print("[yellow]No local service is configured for this project.[/yellow]")
        raise typer.Exit(1)

    state = stop_local_service()
    if state is None:
        console.print("[yellow]No local service runtime state was found.[/yellow]")
        return
    console.print("[green]✓ Local service stopped.[/green]")


@app.command()
def restart():
    """Restart the Minit-managed local service."""
    if load_service_spec() is None:
        console.print("[yellow]No local service is configured for this project.[/yellow]")
        raise typer.Exit(1)
    try:
        state = restart_local_service()
    except RuntimeError as exc:
        console.print(f"[red]Could not restart local service:[/red] {exc}")
        raise typer.Exit(1) from exc
    console.print(f"[green]✓ Local service restarted.[/green] PID {state.get('supervisor_pid')}")


@app.command(name="logs")
def logs_command(
    lines: int = typer.Option(50, "--lines", "-n", min=1, max=5000, help="Number of recent app log lines."),
):
    """Show recent logs stored on this computer."""
    log_lines = tail_app_log(lines=lines)
    if not log_lines:
        console.print("[yellow]No local app logs found yet.[/yellow]")
        return
    for line in log_lines:
        console.print(line, markup=False)


@autostart_app.command("install")
def autostart_install():
    """Install a user-level login/boot entry for the configured local service."""
    try:
        info = enable_autostart()
    except (AutostartUnavailable, OSError, __import__("subprocess").CalledProcessError) as exc:
        console.print(f"[red]Could not install autostart:[/red] {exc}")
        raise typer.Exit(1) from exc
    console.print(f"[green]✓ Autostart installed:[/green] {info.identifier}")
    console.print(f"[dim]Platform: {info.platform}; no app secret values are stored in the autostart entry.[/dim]")
    console.print("[dim]The entry takes effect for the user session; system-wide/root privileges are not required by Minit.[/dim]")


@autostart_app.command("status")
def autostart_status():
    """Show whether the current app has a user-level autostart entry."""
    try:
        info = autostart_info()
    except AutostartUnavailable as exc:
        console.print(f"[yellow]{exc}[/yellow]")
        raise typer.Exit(1) from exc
    console.print(f"platform:   {info.platform}")
    console.print(f"identifier: {info.identifier}")
    console.print(f"installed:  {'yes' if info.installed else 'no'}")
    if info.path is not None:
        console.print(f"path:       {info.path}")


@autostart_app.command("remove")
def autostart_remove():
    """Remove the current app's user-level autostart entry."""
    try:
        info = disable_autostart()
    except (AutostartUnavailable, OSError) as exc:
        console.print(f"[red]Could not remove autostart:[/red] {exc}")
        raise typer.Exit(1) from exc
    console.print(f"[green]✓ Autostart removed:[/green] {info.identifier}")


@snapshot_app.command("create")
def snapshot_create(label: str | None = typer.Option(None, "--label", "-l")):
    """Create a local source/config snapshot. Mutable app data is not included."""
    try:
        entry = create_snapshot(label=label)
    except SnapshotError as exc:
        console.print(f"[red]Could not create snapshot:[/red] {exc}")
        raise typer.Exit(1) from exc
    console.print(f"[green]✓ Snapshot:[/green] {entry['snapshot_id']}")
    console.print(f"  files: {entry['file_count']}")
    console.print(f"  size:  {_format_bytes(entry['archive_bytes'])}")
    console.print("[dim]Scope: source/config only. .minit/data and non-source data are untouched.[/dim]")


@snapshot_app.command("list")
def snapshot_list():
    """List local source/config snapshots."""
    try:
        entries = list_snapshots()
    except SnapshotError as exc:
        console.print(f"[red]Could not read snapshots:[/red] {exc}")
        raise typer.Exit(1) from exc
    if not entries:
        console.print("[dim]No local snapshots yet.[/dim]")
        return
    for entry in entries:
        label = f"  {entry['label']}" if entry.get("label") else ""
        console.print(f"{entry['snapshot_id']}  {entry['file_count']} files{label}", markup=False)


@app.command()
def rollback(snapshot_id: str = typer.Argument(..., help="Snapshot ID from `minit snapshot list`.")):
    """Safely restore source/config files from a local snapshot."""
    try:
        result = restore_snapshot(snapshot_id)
    except SnapshotError as exc:
        console.print(f"[red]Rollback failed:[/red] {exc}")
        raise typer.Exit(1) from exc
    console.print(f"[green]✓ Rolled back to:[/green] {result['snapshot_id']}")
    console.print(f"[green]✓ Safety snapshot:[/green] {result['safety_snapshot_id']}")
    console.print(f"[green]✓ Restored files:[/green] {result['restored_files']}")
    console.print(f"[green]✓ Service health:[/green] {result['service_health']}")
    console.print(f"[dim]{result['note']}[/dim]")


@security_app.command("doctor")
def security_doctor():
    """Check whether Minit can use an approved OS-backed key store."""
    status_info = system_key_store_status()
    console.print("[bold]Minit security doctor[/bold]")
    console.print(f"  backend: {status_info.backend}")
    console.print(f"  trusted: {'yes' if status_info.trusted else 'no'}")
    console.print(f"  reason:  {status_info.reason}")
    if not status_info.trusted:
        console.print("[yellow]Minit will refuse to create encrypted local secrets on this backend.[/yellow]")
        raise typer.Exit(1)


@security_app.command("init")
def security_init():
    """Create/verify the local device root key and this app's wrapped app key."""
    try:
        get_or_create_app_key()
    except (SecureKeyStoreUnavailable, RuntimeError) as exc:
        console.print(f"[red]Could not initialize local key protection:[/red] {exc}")
        raise typer.Exit(1) from exc
    console.print("[green]✓ Local key protection initialized.[/green]")
    console.print("[dim]The device root key stays in the operating-system key store.[/dim]")
    console.print("[yellow]Recovery is not implemented yet. Losing the local root key can make encrypted secrets unrecoverable.[/yellow]")


@security_app.command("harden")
def security_harden():
    """Re-apply owner-only permissions to existing local Minit state."""
    from pathlib import Path

    root = Path.cwd() / MINIT_DIR
    harden_private_tree(root)
    console.print(f"[green]✓ Hardened local Minit state:[/green] {root}")
    console.print("[dim]POSIX uses owner-only permissions. Windows ACL hardening is a separate pending implementation.[/dim]")


@secret_app.command("set")
def secret_set(name: str = typer.Argument(..., help="Environment-style secret name, e.g. OPENAI_API_KEY.")):
    """Encrypt and store an app secret locally. The value is entered via a hidden prompt."""
    value = typer.prompt(f"Value for {name}", hide_input=True, confirmation_prompt=False)
    try:
        set_secret(name, value)
    except (SecureKeyStoreUnavailable, RuntimeError, ValueError) as exc:
        console.print(f"[red]Could not store local secret:[/red] {exc}")
        raise typer.Exit(1) from exc
    console.print(f"[green]✓ Stored encrypted local secret:[/green] {name}")
    console.print("[dim]The plaintext value was not written to service.json or uploaded anywhere.[/dim]")


@secret_app.command("list")
def secret_list():
    """List local secret names without decrypting values."""
    names = list_secret_names()
    if not names:
        console.print("[dim]No local app secrets configured.[/dim]")
        return
    for name in names:
        console.print(name, markup=False)


@secret_app.command("delete")
def secret_delete(name: str):
    """Delete an encrypted local app secret."""
    try:
        removed = delete_secret(name)
    except (RuntimeError, ValueError) as exc:
        console.print(f"[red]Could not delete local secret:[/red] {exc}")
        raise typer.Exit(1) from exc
    if removed:
        console.print(f"[green]✓ Deleted local secret:[/green] {name}")
    else:
        console.print(f"[yellow]Secret not found:[/yellow] {name}")


if __name__ == "__main__":
    app()
