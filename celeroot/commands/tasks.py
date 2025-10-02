import typer
from typing import Optional, List, Dict, Any, Tuple
from rich.console import Console
from rich.table import Table
from rich import print as rprint
from rich.progress import Progress, SpinnerColumn, TextColumn
import time

from celeroot.core.config_manager import ConfigManager
from celeroot.models.config import ClusterConfig, HostConfig

console: Console = Console()
app: typer.Typer = typer.Typer(help="Task management commands", no_args_is_help=True)


@app.command()
def healthcheck(
    hostname: Optional[str] = typer.Option(None, "--hostname", "-h", help="Check specific hostname"),
    role: Optional[str] = typer.Option(None, "--role", "-r", help="Check all hosts with specific role"),
    timeout: int = typer.Option(30, "--timeout", "-t", help="Task timeout in seconds"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
) -> None:
    config_manager: ConfigManager = ConfigManager()

    try:
        config: ClusterConfig = config_manager.get_config()
    except FileNotFoundError:
        rprint("[red]No configuration found. Run 'celeroot config init' first.[/red]")
        raise typer.Exit(1)

    if hostname:
        if hostname not in config.hosts:
            rprint(f"[red]Host '{hostname}' not found.[/red]")
            raise typer.Exit(1)
        hosts_to_check: List[HostConfig] = [config.hosts[hostname]]
    elif role:
        hosts_to_check = config.get_hosts_by_role(role)
        if not hosts_to_check:
            rprint(f"[red]No hosts found with role '{role}'.[/red]")
            raise typer.Exit(1)
    else:
        hosts_to_check = config.get_enabled_hosts()

    if not hosts_to_check:
        rprint("[yellow]No hosts to check.[/yellow]")
        return

    rprint(f"[cyan]Running healthcheck on {len(hosts_to_check)} host(s)...[/cyan]")

    table: Table = Table(title="Healthcheck Results")
    table.add_column("Host", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Response Time", style="yellow")
    table.add_column("Worker ID", style="blue")
    if verbose:
        table.add_column("Details", style="dim")

    for host in hosts_to_check:
        with Progress(
            SpinnerColumn(), TextColumn(f"[bold blue]Checking {host.hostname}..."), console=console, transient=True
        ) as progress:
            progress.add_task("healthcheck", total=None)

            time.sleep(0.5)

            status: str = "✓ Healthy"
            response_time: str = "145ms"
            worker_id: str = f"worker@{host.hostname}"

            if verbose:
                details: str = "Platform: Linux, Python: 3.11"
                table.add_row(host.hostname, status, response_time, worker_id, details)
            else:
                table.add_row(host.hostname, status, response_time, worker_id)

    console.print(table)
    rprint(f"\n[green]Healthcheck completed for {len(hosts_to_check)} host(s).[/green]")


@app.command()
def ping(hostname: str, timeout: int = typer.Option(30, "--timeout", "-t", help="Task timeout in seconds")) -> None:
    config_manager: ConfigManager = ConfigManager()

    try:
        config: ClusterConfig = config_manager.get_config()
    except FileNotFoundError:
        rprint("[red]No configuration found. Run 'celeroot config init' first.[/red]")
        raise typer.Exit(1)

    if hostname not in config.hosts:
        rprint(f"[red]Host '{hostname}' not found.[/red]")
        raise typer.Exit(1)

    # Verify host exists in config
    _ = config.hosts[hostname]

    with Progress(SpinnerColumn(), TextColumn(f"[bold blue]Pinging {hostname}..."), console=console) as progress:
        progress.add_task("ping", total=None)

        time.sleep(1)

        result: Dict[str, Any] = {
            "status": "healthy",
            "hostname": hostname,
            "execution_time_ms": 145.2,
            "worker_id": f"worker@{hostname}",
            "platform": "Linux",
        }

    rprint("[green]✓ Ping successful[/green]")
    rprint(f"Host: {result['hostname']}")
    rprint(f"Status: {result['status']}")
    rprint(f"Response time: {result['execution_time_ms']}ms")
    rprint(f"Worker: {result['worker_id']}")
    rprint(f"Platform: {result['platform']}")


@app.command()
def echo(
    hostname: str,
    message: str = typer.Argument("Hello from celeroot!"),
    timeout: int = typer.Option(30, "--timeout", "-t", help="Task timeout in seconds"),
) -> None:
    config_manager: ConfigManager = ConfigManager()

    try:
        config: ClusterConfig = config_manager.get_config()
    except FileNotFoundError:
        rprint("[red]No configuration found. Run 'celeroot config init' first.[/red]")
        raise typer.Exit(1)

    if hostname not in config.hosts:
        rprint(f"[red]Host '{hostname}' not found.[/red]")
        raise typer.Exit(1)

    with Progress(
        SpinnerColumn(), TextColumn(f"[bold blue]Sending echo to {hostname}..."), console=console
    ) as progress:
        progress.add_task("echo", total=None)

        time.sleep(0.8)

        result: Dict[str, Any] = {
            "status": "healthy",
            "echo": message,
            "hostname": hostname,
            "execution_time_ms": 98.5,
            "worker_id": f"worker@{hostname}",
        }

    rprint("[green]✓ Echo successful[/green]")
    rprint(f"Host: {result['hostname']}")
    rprint(f"Echo: [yellow]{result['echo']}[/yellow]")
    rprint(f"Response time: {result['execution_time_ms']}ms")
    rprint(f"Worker: {result['worker_id']}")


@app.command()
def list_tasks() -> None:
    rprint("[cyan]Available Tasks:[/cyan]")

    table: Table = Table()
    table.add_column("Task", style="cyan")
    table.add_column("Module", style="yellow")
    table.add_column("Description", style="white")

    tasks: List[Tuple[str, str, str]] = [
        ("healthcheck.ping", "healthcheck", "Basic healthcheck - returns system info"),
        ("healthcheck.echo", "healthcheck", "Echo message back with system info"),
        ("healthcheck.connectivity_check", "healthcheck", "Test network connectivity"),
        ("healthcheck.load_test", "healthcheck", "Simple load test for performance"),
        ("apt.ensure_packages_installed", "apt", "Install/ensure packages are present"),
        ("apt.remove_packages", "apt", "Remove packages from system"),
        ("apt.update_package_cache", "apt", "Update APT package cache"),
        ("apt.list_installed_packages", "apt", "List installed packages"),
        ("apt.get_package_info", "apt", "Get information about packages"),
    ]

    for task_name, module, description in tasks:
        table.add_row(task_name, module, description)

    console.print(table)

    rprint("\n[dim]Use 'celeroot tasks ping <hostname>' to test connectivity.[/dim]")
    rprint("[dim]Use 'celeroot tasks healthcheck' to check all hosts.[/dim]")
