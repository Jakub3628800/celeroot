import typer
from typing import Optional, List, Dict
from rich.console import Console
from rich.table import Table
from rich import print as rprint

from celeroot.core.config_manager import ConfigManager
from celeroot.models.config import HostConfig, SSHConfig, ClusterConfig

console: Console = Console()
app: typer.Typer = typer.Typer(help="Host management commands", no_args_is_help=True)


@app.command()
def ls(
    role: Optional[str] = typer.Option(None, "--role", "-r", help="Filter by role"),
    tag: Optional[str] = typer.Option(None, "--tag", "-t", help="Filter by tag (key=value)"),
    enabled_only: bool = typer.Option(True, "--enabled-only/--all", help="Show only enabled hosts"),
) -> None:
    config_manager: ConfigManager = ConfigManager()

    try:
        config: ClusterConfig = config_manager.get_config()
    except FileNotFoundError:
        rprint("[red]No configuration found. Run 'celeroot config init' first.[/red]")
        raise typer.Exit(1)

    hosts: List[HostConfig] = list(config.hosts.values())

    if enabled_only:
        hosts = [h for h in hosts if h.enabled]

    if role:
        hosts = [h for h in hosts if h.has_role(role)]

    if tag:
        try:
            key: str
            value: str
            key, value = tag.split("=", 1)
            hosts = [h for h in hosts if h.tags.get(key) == value]
        except ValueError:
            rprint("[red]Tag filter must be in format 'key=value'[/red]")
            raise typer.Exit(1)

    if not hosts:
        rprint("[yellow]No hosts found matching the criteria.[/yellow]")
        return

    table: Table = Table(title=f"Hosts ({len(hosts)} found)")
    table.add_column("Hostname", style="cyan", min_width=12)
    table.add_column("Address", style="green", min_width=15)
    table.add_column("Roles", style="yellow", min_width=20)
    table.add_column("Status", style="magenta")
    table.add_column("Tags", style="blue")

    for host in sorted(hosts, key=lambda h: h.hostname):
        roles_str: str = ", ".join(sorted(host.roles)) if host.roles else "[dim]none[/dim]"
        status: str = "[green]enabled[/green]" if host.enabled else "[red]disabled[/red]"

        tags_str: str = ""
        if host.tags:
            tags_list: List[str] = [f"{k}={v}" for k, v in sorted(host.tags.items())]
            tags_str = ", ".join(tags_list)
        else:
            tags_str = "[dim]none[/dim]"

        table.add_row(host.hostname, host.address, roles_str, status, tags_str)

    console.print(table)

    total_hosts: int = len(config.hosts)
    enabled_hosts: int = len([h for h in config.hosts.values() if h.enabled])

    rprint(f"\n[dim]Total hosts: {total_hosts} | Enabled: {enabled_hosts} | Showing: {len(hosts)}[/dim]")


@app.command()
def get(hostname: str) -> None:
    config_manager: ConfigManager = ConfigManager()

    try:
        config: ClusterConfig = config_manager.get_config()
    except FileNotFoundError:
        rprint("[red]No configuration found. Run 'celeroot config init' first.[/red]")
        raise typer.Exit(1)

    if hostname not in config.hosts:
        rprint(f"[red]Host '{hostname}' not found.[/red]")
        raise typer.Exit(1)

    host: HostConfig = config.hosts[hostname]

    rprint(f"\n[cyan]Host: {host.hostname}[/cyan]")
    rprint(f"Address: {host.address}")
    rprint(f"Status: {'[green]enabled[/green]' if host.enabled else '[red]disabled[/red]'}")

    if host.roles:
        rprint(f"Roles: {', '.join(sorted(host.roles))}")
    else:
        rprint("Roles: [dim]none[/dim]")

    rprint("\n[yellow]SSH Configuration:[/yellow]")
    rprint(f"  User: {host.ssh.user}")
    rprint(f"  Port: {host.ssh.port}")
    rprint(f"  Key: {host.ssh.key_path or '[dim]default[/dim]'}")
    rprint(f"  Timeout: {host.ssh.timeout}s")

    if host.tags:
        rprint("\n[blue]Tags:[/blue]")
        for key, value in sorted(host.tags.items()):
            rprint(f"  {key}: {value}")
    else:
        rprint("\n[blue]Tags:[/blue] [dim]none[/dim]")


@app.command()
def add(
    hostname: str,
    address: str,
    roles: List[str] = typer.Option([], "--role", "-r", help="Assign roles to the host"),
    ssh_user: str = typer.Option("celeroot", "--user", "-u", help="SSH user"),
    ssh_port: int = typer.Option(22, "--port", "-p", help="SSH port"),
    ssh_key: Optional[str] = typer.Option(None, "--key", "-k", help="SSH private key path"),
    tags: List[str] = typer.Option([], "--tag", "-t", help="Tags in format key=value"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be added without saving"),
) -> None:
    config_manager: ConfigManager = ConfigManager()

    try:
        config: ClusterConfig = config_manager.get_config()
    except FileNotFoundError:
        rprint("[red]No configuration found. Run 'celeroot config init' first.[/red]")
        raise typer.Exit(1)

    if hostname in config.hosts:
        rprint(f"[red]Host '{hostname}' already exists.[/red]")
        raise typer.Exit(1)

    for role in roles:
        if role not in config.roles:
            rprint(f"[red]Role '{role}' does not exist. Available roles: {', '.join(config.roles.keys())}[/red]")
            raise typer.Exit(1)

    parsed_tags: Dict[str, str] = {}
    for tag in tags:
        try:
            key: str
            value: str
            key, value = tag.split("=", 1)
            parsed_tags[key] = value
        except ValueError:
            rprint(f"[red]Invalid tag format '{tag}'. Use 'key=value'.[/red]")
            raise typer.Exit(1)

    ssh_config: SSHConfig = SSHConfig(
        user=ssh_user,
        port=ssh_port,
        key_path=ssh_key,
    )

    host_config: HostConfig = HostConfig(
        hostname=hostname, address=address, roles=set(roles), ssh=ssh_config, tags=parsed_tags
    )

    if dry_run:
        rprint("[yellow]Dry run - would add the following host:[/yellow]")
        rprint(f"Hostname: {hostname}")
        rprint(f"Address: {address}")
        rprint(f"Roles: {', '.join(sorted(roles)) if roles else 'none'}")
        rprint(f"SSH: {ssh_user}@{address}:{ssh_port}")
        rprint(f"Tags: {', '.join(f'{k}={v}' for k, v in parsed_tags.items()) if parsed_tags else 'none'}")
        return

    config.add_host(host_config)

    try:
        config_manager.save(config)
        rprint(f"[green]✓ Host '{hostname}' added to configuration.[/green]")

        rprint(f"\n[yellow]Next steps - Run these commands on {hostname}:[/yellow]")
        rprint("[cyan]# 1. Install prerequisites[/cyan]")
        rprint(f"ssh {ssh_user}@{address} 'sudo apt update && sudo apt install -y python3 python3-pip'")

        rprint("\n[cyan]# 2. Install uv (Python package manager)[/cyan]")
        rprint(f"ssh {ssh_user}@{address} 'curl -LsSf https://astral.sh/uv/install.sh | sh'")

        rprint("\n[cyan]# 3. Create celeroot user and directories[/cyan]")
        rprint(f"ssh {ssh_user}@{address} 'sudo useradd -m -s /bin/bash celeroot'")
        rprint(f"ssh {ssh_user}@{address} 'sudo mkdir -p /opt/celeroot'")
        rprint(f"ssh {ssh_user}@{address} 'sudo chown celeroot:celeroot /opt/celeroot'")

        rprint("\n[cyan]# 4. Deploy celeroot code (run from your local machine)[/cyan]")
        rprint(f"celeroot deploy {hostname}")

        rprint("\n[dim]After completing these steps, the host will be ready to run celeroot workers.[/dim]")

    except Exception as e:
        rprint(f"[red]Failed to save configuration: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def rm(hostname: str, force: bool = typer.Option(False, "--force", "-f", help="Remove without confirmation")) -> None:
    config_manager: ConfigManager = ConfigManager()

    try:
        config: ClusterConfig = config_manager.get_config()
    except FileNotFoundError:
        rprint("[red]No configuration found. Run 'celeroot config init' first.[/red]")
        raise typer.Exit(1)

    if hostname not in config.hosts:
        rprint(f"[red]Host '{hostname}' not found.[/red]")
        raise typer.Exit(1)

    host: HostConfig = config.hosts[hostname]

    if not force:
        rprint(
            f"[yellow]This will remove host '{hostname}' ({host.address}) with roles: {', '.join(sorted(host.roles))}[/yellow]"
        )

        if not typer.confirm("Are you sure you want to remove this host?"):
            rprint("[yellow]Operation cancelled.[/yellow]")
            return

    config.remove_host(hostname)

    try:
        config_manager.save(config)
        rprint(f"[green]✓ Host '{hostname}' removed successfully.[/green]")
    except Exception as e:
        rprint(f"[red]Failed to save configuration: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def roles(hostname: Optional[str] = typer.Argument(None, help="Hostname to show roles for")) -> None:
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

        host: HostConfig = config.hosts[hostname]
        rprint(f"\n[cyan]Roles for {hostname}:[/cyan]")

        if host.roles:
            for role in sorted(host.roles):
                role_config = config.roles.get(role)
                if role_config:
                    rprint(f"  [green]{role}[/green] - {role_config.description}")
                else:
                    rprint(f"  [red]{role}[/red] - [dim]role not defined[/dim]")
        else:
            rprint("  [dim]No roles assigned[/dim]")
    else:
        table: Table = Table(title="Role Assignments")
        table.add_column("Role", style="cyan")
        table.add_column("Description", style="yellow")
        table.add_column("Hosts", style="green")

        for role_name, role_config in sorted(config.roles.items()):
            hosts_with_role: List[str] = [h.hostname for h in config.hosts.values() if h.has_role(role_name)]
            hosts_str: str = ", ".join(sorted(hosts_with_role)) if hosts_with_role else "[dim]none[/dim]"

            table.add_row(role_name, role_config.description or "[dim]no description[/dim]", hosts_str)

        console.print(table)
