from __future__ import annotations

from datetime import datetime

import typer

from minit.cli import app, console
from minit.management import local_app_status


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


@app.command()
def status():
    """Show locally recorded app management status."""
    current = local_app_status()
    if current is None:
        console.print("[yellow]This project is not initialized yet.[/yellow]")
        console.print("Run [bold]minit init[/bold] or [bold]minit run[/bold] first.")
        raise typer.Exit(1)

    console.print(f"[bold]{current['name']}[/bold]")
    console.print(f"  app id:          {current['app_id']}")
    console.print(f"  runtime:         {current['runtime']}")
    console.print(f"  successful runs: {current['successful_runs']}")
    console.print(f"  total live time: {_format_duration(current['total_live_seconds'])}")
    console.print(f"  last started:    {_format_time(current['last_started_at'])}")
    console.print(f"  last stopped:    {_format_time(current['last_stopped_at'])}")
    console.print("  status source:   local only")


if __name__ == "__main__":
    app()
