import typer
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from rich import print as rprint

from celeroot.core.config_manager import ConfigManager
from celeroot.models.config import RoleConfig, ClusterConfig, HostConfig

console: Console = Console()
app: typer.Typer = typer.Typer(help="Role management commands", no_args_is_help=True)


@app.command()
def ls() -> None:
    config_manager: ConfigManager = ConfigManager()

    try:
        config: ClusterConfig = config_manager.get_config()
    except FileNotFoundError:
        rprint("[red]No configuration found. Run 'celeroot config init' first.[/red]")
        raise typer.Exit(1)

    if not config.roles:
        rprint("[yellow]No roles defined.[/yellow]")
        return

    table: Table = Table(title=f"Roles ({len(config.roles)} found)")
    table.add_column("Name", style="cyan", min_width=12)
    table.add_column("Description", style="yellow", min_width=20)
    table.add_column("Queue", style="green", min_width=15)
    table.add_column("Concurrency", style="blue")
    table.add_column("Hosts", style="magenta")
    table.add_column("Tasks", style="white")

    for role_name, role in sorted(config.roles.items()):
        hosts_with_role: List[str] = [h.hostname for h in config.hosts.values() if h.has_role(role_name)]
        hosts_count: str = f"{len(hosts_with_role)} hosts"

        tasks_str: str = ", ".join(role.tasks) if role.tasks else "[dim]none[/dim]"
        if len(tasks_str) > 30:
            tasks_str = tasks_str[:27] + "..."

        table.add_row(
            role.name,
            role.description or "[dim]no description[/dim]",
            role.queue,
            str(role.concurrency),
            hosts_count,
            tasks_str,
        )

    console.print(table)

    rprint(f"\n[dim]Total roles: {len(config.roles)}[/dim]")


@app.command()
def get(role_name: str) -> None:
    config_manager: ConfigManager = ConfigManager()

    try:
        config: ClusterConfig = config_manager.get_config()
    except FileNotFoundError:
        rprint("[red]No configuration found. Run 'celeroot config init' first.[/red]")
        raise typer.Exit(1)

    if role_name not in config.roles:
        rprint(f"[red]Role '{role_name}' not found.[/red]")
        raise typer.Exit(1)

    role: RoleConfig = config.roles[role_name]

    rprint(f"\n[cyan]Role: {role.name}[/cyan]")
    rprint(f"Description: {role.description or '[dim]no description[/dim]'}")
    rprint(f"Queue: {role.queue}")
    rprint(f"Concurrency: {role.concurrency}")
    rprint(f"Max tasks per child: {role.max_tasks_per_child}")

    if role.tasks:
        rprint("\n[yellow]Tasks:[/yellow]")
        for task in sorted(role.tasks):
            rprint(f"  - {task}")
    else:
        rprint("\n[yellow]Tasks:[/yellow] [dim]none[/dim]")

    hosts_with_role: List[HostConfig] = [h for h in config.hosts.values() if h.has_role(role_name)]
    if hosts_with_role:
        rprint(f"\n[green]Hosts with this role ({len(hosts_with_role)}):[/green]")
        for host in sorted(hosts_with_role, key=lambda h: h.hostname):
            status: str = "[green]enabled[/green]" if host.enabled else "[red]disabled[/red]"
            rprint(f"  - {host.hostname} ({host.address}) - {status}")
    else:
        rprint("\n[green]Hosts with this role:[/green] [dim]none[/dim]")


@app.command()
def add(
    name: str,
    description: str = typer.Option("", "--description", "-d", help="Role description"),
    queue: Optional[str] = typer.Option(None, "--queue", "-q", help="Queue name (defaults to <name>_tasks)"),
    concurrency: int = typer.Option(4, "--concurrency", "-c", help="Worker concurrency"),
    max_tasks: int = typer.Option(1000, "--max-tasks", help="Max tasks per child process"),
    tasks: List[str] = typer.Option([], "--task", "-t", help="Tasks this role can execute"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be added without saving"),
) -> None:
    config_manager: ConfigManager = ConfigManager()

    try:
        config: ClusterConfig = config_manager.get_config()
    except FileNotFoundError:
        rprint("[red]No configuration found. Run 'celeroot config init' first.[/red]")
        raise typer.Exit(1)

    if name in config.roles:
        rprint(f"[red]Role '{name}' already exists.[/red]")
        raise typer.Exit(1)

    if not queue:
        queue = f"{name}_tasks"

    role_config: RoleConfig = RoleConfig(
        name=name,
        description=description,
        queue=queue,
        concurrency=concurrency,
        max_tasks_per_child=max_tasks,
        tasks=tasks,
    )

    if dry_run:
        rprint("[yellow]Dry run - would add the following role:[/yellow]")
        rprint(f"Name: {name}")
        rprint(f"Description: {description or '[none]'}")
        rprint(f"Queue: {queue}")
        rprint(f"Concurrency: {concurrency}")
        rprint(f"Max tasks per child: {max_tasks}")
        rprint(f"Tasks: {', '.join(tasks) if tasks else '[none]'}")
        return

    config.add_role(role_config)

    try:
        config_manager.save(config)
        rprint(f"[green]✓ Role '{name}' added successfully.[/green]")

        rprint("\n[yellow]Next steps:[/yellow]")
        rprint("[dim]1. Assign this role to hosts:[/dim]")
        rprint(f"   celeroot hosts add <hostname> --role {name}")
        rprint("[dim]2. Or add role to existing hosts:[/dim]")
        rprint(f"   celeroot hosts assign <hostname> {name}")

    except Exception as e:
        rprint(f"[red]Failed to save configuration: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def rm(role_name: str, force: bool = typer.Option(False, "--force", "-f", help="Remove without confirmation")) -> None:
    config_manager: ConfigManager = ConfigManager()

    try:
        config: ClusterConfig = config_manager.get_config()
    except FileNotFoundError:
        rprint("[red]No configuration found. Run 'celeroot config init' first.[/red]")
        raise typer.Exit(1)

    if role_name not in config.roles:
        rprint(f"[red]Role '{role_name}' not found.[/red]")
        raise typer.Exit(1)

    hosts_with_role: List[HostConfig] = [h for h in config.hosts.values() if h.has_role(role_name)]
    if hosts_with_role:
        rprint(f"[red]Cannot remove role '{role_name}' - it is assigned to {len(hosts_with_role)} host(s):[/red]")
        for host in sorted(hosts_with_role, key=lambda h: h.hostname):
            rprint(f"  - {host.hostname}")
        rprint("\n[yellow]Remove the role from these hosts first:[/yellow]")
        for host in hosts_with_role:
            rprint(f"  celeroot hosts unassign {host.hostname} {role_name}")
        raise typer.Exit(1)

    role: RoleConfig = config.roles[role_name]

    if not force:
        rprint(f"[yellow]This will remove role '{role_name}' ({role.description})[/yellow]")
        rprint(f"Queue: {role.queue}")
        rprint(f"Tasks: {', '.join(role.tasks) if role.tasks else 'none'}")

        if not typer.confirm("Are you sure you want to remove this role?"):
            rprint("[yellow]Operation cancelled.[/yellow]")
            return

    config.remove_role(role_name)

    try:
        config_manager.save(config)
        rprint(f"[green]✓ Role '{role_name}' removed successfully.[/green]")
    except Exception as e:
        rprint(f"[red]Failed to save configuration: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def edit(
    role_name: str,
    description: Optional[str] = typer.Option(None, "--description", "-d", help="New description"),
    queue: Optional[str] = typer.Option(None, "--queue", "-q", help="New queue name"),
    concurrency: Optional[int] = typer.Option(None, "--concurrency", "-c", help="New concurrency"),
    max_tasks: Optional[int] = typer.Option(None, "--max-tasks", help="New max tasks per child"),
    add_task: List[str] = typer.Option([], "--add-task", help="Add a task"),
    remove_task: List[str] = typer.Option([], "--remove-task", help="Remove a task"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show changes without saving"),
) -> None:
    config_manager: ConfigManager = ConfigManager()

    try:
        config: ClusterConfig = config_manager.get_config()
    except FileNotFoundError:
        rprint("[red]No configuration found. Run 'celeroot config init' first.[/red]")
        raise typer.Exit(1)

    if role_name not in config.roles:
        rprint(f"[red]Role '{role_name}' not found.[/red]")
        raise typer.Exit(1)

    role: RoleConfig = config.roles[role_name]
    changes: List[str] = []

    if description is not None:
        old_desc: Optional[str] = role.description
        role.description = description
        changes.append(f"Description: '{old_desc}' → '{description}'")

    if queue is not None:
        old_queue: str = role.queue
        role.queue = queue
        changes.append(f"Queue: '{old_queue}' → '{queue}'")

    if concurrency is not None:
        old_concurrency: int = role.concurrency
        role.concurrency = concurrency
        changes.append(f"Concurrency: {old_concurrency} → {concurrency}")

    if max_tasks is not None:
        old_max_tasks: int = role.max_tasks_per_child
        role.max_tasks_per_child = max_tasks
        changes.append(f"Max tasks per child: {old_max_tasks} → {max_tasks}")

    for task in add_task:
        if task not in role.tasks:
            role.tasks.append(task)
            changes.append(f"Added task: {task}")

    for task in remove_task:
        if task in role.tasks:
            role.tasks.remove(task)
            changes.append(f"Removed task: {task}")

    if not changes:
        rprint("[yellow]No changes specified.[/yellow]")
        return

    if dry_run:
        rprint(f"[yellow]Dry run - would make the following changes to role '{role_name}':[/yellow]")
        for change in changes:
            rprint(f"  - {change}")
        return

    try:
        config_manager.save(config)
        rprint(f"[green]✓ Role '{role_name}' updated successfully.[/green]")
        rprint("[cyan]Changes made:[/cyan]")
        for change in changes:
            rprint(f"  - {change}")
    except Exception as e:
        rprint(f"[red]Failed to save configuration: {e}[/red]")
        raise typer.Exit(1)
