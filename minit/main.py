from __future__ import annotations

from datetime import datetime

import typer

from minit.cli import _port_open, app, console
from minit.management import local_app_status
from minit.runtime import (
    load_runtime_state,
    restart_local_service,
    runtime_is_running,
    start_local_service,
    stop_local_service,
    tail_app_log,
)
from minit.service import RESTART_POLICIES, configure_local_service, load_service_spec


def _format_duration(total_seconds: int) -> str:
    total_seconds = max(0, int(total_seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


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
        state = start_local_service()
    except (RuntimeError, ValueError) as exc:
        console.print(f"[red]Could not deploy local service:[/red] {exc}")
        raise typer.Exit(1) from exc

    console.print(f"[green]✓ Local service:[/green] {spec['app_id']}")
    console.print(f"[green]✓ Command:[/green]       {' '.join(spec['command'])}")
    console.print(f"[green]✓ Port:[/green]          127.0.0.1:{spec['port']}")
    console.print(f"[green]✓ Supervisor:[/green]    PID {state.get('supervisor_pid')}")
    console.print(f"[green]✓ Status:[/green]        {state.get('status', 'starting')}")
    console.print()
    console.print("[bold]The app now runs from this computer without this terminal.[/bold]")
    console.print("[dim]No code or app data was uploaded by this command.[/dim]")
    console.print("[dim]Use `minit status`, `minit logs`, `minit restart`, or `minit stop` to manage it.[/dim]")
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

    spec = load_service_spec()
    runtime = load_runtime_state()
    if spec is not None:
        console.print()
        console.print("[bold]Local service[/bold]")
        console.print(f"  command:         {' '.join(spec['command'])}")
        console.print(f"  port:            127.0.0.1:{spec['port']}")
        console.print(f"  restart policy:  {spec['restart_policy']}")
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


if __name__ == "__main__":
    app()
