#!/usr/bin/env python3

import typer
from typing import Optional
from pathlib import Path
from rich.console import Console
from rich.table import Table

from celeroot.commands import hosts, config, roles, tasks

console: Console = Console()

config_file_path: Optional[str] = None

app: typer.Typer = typer.Typer(name="celeroot", help="Distributed system administration platform", no_args_is_help=True)

app.add_typer(hosts.app, name="hosts")
app.add_typer(config.app, name="config")
app.add_typer(roles.app, name="roles")
app.add_typer(tasks.app, name="tasks")


@app.callback()
def main(
    config: Optional[str] = typer.Option(
        None, "--config", "-c", help="Configuration file path (default: celeroot.yml in current directory)"
    ),
) -> None:
    global config_file_path

    if config:
        config_file_path = config
    else:
        config_file_path = "celeroot.yml"

    import sys

    if len(sys.argv) > 1 and not (len(sys.argv) >= 3 and sys.argv[1] == "config" and sys.argv[2] == "init"):
        config_path: Path = Path(config_file_path)
        if not config_path.exists():
            console.print(f"[red]Configuration file '{config_file_path}' not found![/red]")
            console.print("[yellow]Run 'celeroot config init' to create a new configuration.[/yellow]")
            raise typer.Exit(1)


def get_config_file() -> str:
    return config_file_path or "celeroot.yml"


@app.command()
def version() -> None:
    console.print("[green]Celeroot v1.0.0[/green]")
    console.print("Distributed system administration platform")


@app.command()
def status() -> None:
    console.print("[cyan]Cluster Status[/cyan]")

    table: Table = Table(title="Celeroot Cluster Overview")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Details", style="yellow")

    table.add_row("Redis", "Connected", "redis://localhost:6379/0")
    table.add_row("Scheduler", "Running", "3 schedules active")
    table.add_row("Workers", "Active", "5 hosts, 12 workers")

    console.print(table)


if __name__ == "__main__":
    app()
