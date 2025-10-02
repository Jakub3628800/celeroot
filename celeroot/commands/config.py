from celeroot.models.config import ClusterConfig
import typer
import subprocess
import os
from pathlib import Path
from typing import Optional, List
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table
from rich import print as rprint

from celeroot.core.config_manager import ConfigManager

console: Console = Console()
app: typer.Typer = typer.Typer(help="Configuration management commands", no_args_is_help=True)


@app.command()
def init(
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing configuration"),
    interactive: bool = typer.Option(True, "--interactive/--no-interactive", help="Use interactive setup"),
) -> None:
    config_manager: ConfigManager = ConfigManager()
    config_path: Path = config_manager.config_path

    if config_path.exists() and not force:
        rprint(f"[red]Configuration file '{config_path}' already exists![/red]")
        rprint("[yellow]Use --force to overwrite existing configuration.[/yellow]")
        raise typer.Exit(1)

    try:
        if interactive:
            config: ClusterConfig = _interactive_config_setup()
        else:
            config = config_manager.create_default_config()

        config_manager.save(config)

        rprint(f"[green]✓ Configuration initialized: {config_path}[/green]")

        if not interactive:
            rprint("[yellow]Edit the configuration file to match your environment.[/yellow]")

        rprint("\n[cyan]Created configuration with:[/cyan]")
        rprint(f"  - Cluster: {config.name}")
        rprint(f"  - Redis: {config.redis.url}")
        rprint(f"  - Roles: {len(config.roles)}")
        rprint(f"  - Hosts: {len(config.hosts)}")
        rprint(f"  - Schedules: {len(config.schedules)}")

    except Exception as e:
        rprint(f"[red]Failed to initialize configuration: {e}[/red]")
        raise typer.Exit(1)


def _interactive_config_setup() -> ClusterConfig:
    from celeroot.models.config import ClusterConfig, RedisConfig

    rprint("[cyan]Celeryroot Configuration Setup[/cyan]")
    rprint("Let's create your celeroot configuration interactively.\n")

    cluster_name: str = typer.prompt("Enter cluster name", default="production")

    cluster_description: str = typer.prompt("Enter cluster description (optional)", default="", show_default=False)

    rprint("\n[yellow]Redis Configuration[/yellow]")
    redis_host: str = typer.prompt("Redis host", default="localhost")

    redis_port: int = typer.prompt("Redis port", default=6379, type=int)

    redis_db: int = typer.prompt("Redis database number", default=0, type=int)

    redis_password_input: str = typer.prompt(
        "Redis password (optional, press Enter to skip)", default="", show_default=False, hide_input=True
    )
    redis_password: Optional[str] = None if not redis_password_input.strip() else redis_password_input

    rprint("\n[dim]Connection Options (press Enter for defaults):[/dim]")

    redis_timeout: int = typer.prompt("Connection timeout (seconds)", default=10, type=int)

    redis_socket_timeout: int = typer.prompt("Socket connect timeout (seconds)", default=5, type=int)

    redis_max_connections: int = typer.prompt("Max connections", default=50, type=int)

    redis_keepalive: bool = typer.confirm("Enable socket keepalive?", default=True)

    if redis_password:
        redis_url: str = f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
    else:
        redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"

    config: ClusterConfig = ClusterConfig(
        name=cluster_name,
        description=cluster_description,
        redis=RedisConfig(
            url=redis_url,
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            timeout=redis_timeout,
            socket_connect_timeout=redis_socket_timeout,
            socket_keepalive=redis_keepalive,
            max_connections=redis_max_connections,
        ),
    )

    add_examples: bool = typer.confirm("\nWould you like to add example roles and hosts?", default=True)

    if add_examples:
        from celeroot.models.config import HostConfig, RoleConfig, ScheduleConfig

        webserver_role: RoleConfig = RoleConfig(
            name="webserver",
            description="Web server role",
            queue="webserver_tasks",
            tasks=["apt_management", "nginx_management", "ssl_management", "healthcheck"],
        )

        database_role: RoleConfig = RoleConfig(
            name="database",
            description="Database server role",
            queue="database_tasks",
            concurrency=2,
            tasks=["apt_management", "mysql_management", "backup_management", "healthcheck"],
        )

        config.add_role(webserver_role)
        config.add_role(database_role)

        web_host: HostConfig = HostConfig(
            hostname="web01",
            address="10.0.1.10",
            roles={"webserver"},
            tags={"environment": "production", "datacenter": "us-east-1"},
        )

        db_host: HostConfig = HostConfig(
            hostname="db01",
            address="10.0.2.10",
            roles={"database"},
            tags={"environment": "production", "datacenter": "us-east-1"},
        )

        config.add_host(web_host)
        config.add_host(db_host)

        security_schedule: ScheduleConfig = ScheduleConfig(
            name="security_updates",
            cron="0 2 * * *",
            task="check_security_updates",
            target_roles=["webserver", "database"],
            description="Daily security update check",
        )

        config.schedules[security_schedule.name] = security_schedule

    rprint("\n[green]Configuration ready![/green]")
    return config


@app.command()
def show() -> None:
    config_manager: ConfigManager = ConfigManager()

    try:
        config_manager.get_config()

        rprint(f"[cyan]Configuration file:[/cyan] {config_manager.config_path}")

        with open(config_manager.config_path, "r") as f:
            content: str = f.read()

        syntax: Syntax = Syntax(content, "yaml", theme="monokai", line_numbers=True)
        console.print(syntax)

    except FileNotFoundError:
        rprint(f"[red]Configuration file '{config_manager.config_path}' not found![/red]")
        rprint("[yellow]Run 'celeroot config init' to create a new configuration.[/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        rprint(f"[red]Error loading configuration: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def validate() -> None:
    config_manager: ConfigManager = ConfigManager()

    try:
        if config_manager.validate():
            config: ClusterConfig = config_manager.get_config()

            table: Table = Table(title="Configuration Summary")
            table.add_column("Section", style="cyan")
            table.add_column("Count", style="green")
            table.add_column("Details", style="yellow")

            table.add_row("Cluster", "1", f"'{config.name}' - {config.description}")
            table.add_row(
                "Hosts", str(len(config.hosts)), f"{len([h for h in config.hosts.values() if h.enabled])} enabled"
            )
            table.add_row("Roles", str(len(config.roles)), ", ".join(config.roles.keys()))
            table.add_row(
                "Schedules",
                str(len(config.schedules)),
                f"{len([s for s in config.schedules.values() if s.enabled])} enabled",
            )

            console.print(table)
        else:
            raise typer.Exit(1)

    except FileNotFoundError:
        rprint(f"[red]Configuration file '{config_manager.config_path}' not found![/red]")
        rprint("[yellow]Run 'celeroot config init' to create a new configuration.[/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        rprint(f"[red]Error during validation: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def edit() -> None:
    config_manager: ConfigManager = ConfigManager()
    config_path: Path = config_manager.config_path

    if not config_path.exists():
        rprint(f"[red]Configuration file '{config_path}' not found![/red]")
        rprint("[yellow]Run 'celeroot config init' to create a new configuration.[/yellow]")
        raise typer.Exit(1)

    editors: List[str] = ["$EDITOR", "code", "vim", "nano", "vi"]

    for editor in editors:
        if editor.startswith("$"):
            editor_name: Optional[str] = os.environ.get(editor[1:])
            if not editor_name:
                continue
            editor = editor_name

        try:
            subprocess.run([editor, str(config_path)], check=True)
            rprint(f"[green]✓ Configuration edited with {editor}[/green]")
            rprint("[yellow]Run 'celeroot config validate' to check your changes.[/yellow]")
            return
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue

    rprint("[red]Could not find a suitable editor. Please edit the file manually:[/red]")
    rprint(f"[yellow]{config_path.absolute()}[/yellow]")


@app.command()
def path() -> None:
    config_manager: ConfigManager = ConfigManager()
    rprint(f"[cyan]Configuration file:[/cyan] {config_manager.config_path.absolute()}")

    if config_manager.config_path.exists():
        rprint("[green]✓ File exists[/green]")
    else:
        rprint("[red]✗ File does not exist[/red]")
        rprint("[yellow]Run 'celeroot config init' to create it.[/yellow]")
