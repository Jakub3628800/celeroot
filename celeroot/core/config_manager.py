import yaml
from pathlib import Path
from typing import Optional, Dict, Any, List
from rich.console import Console

from celeroot.models.config import ClusterConfig

console: Console = Console()


def get_global_config_path() -> str:
    try:
        from celeroot import __main__

        return __main__.get_config_file()
    except (ImportError, AttributeError):
        return "celeroot.yml"


class ConfigManager:
    def __init__(self, config_path: Optional[str] = None) -> None:
        if config_path:
            self.config_path: Path = Path(config_path)
        else:
            self.config_path: Path = Path(get_global_config_path())
        self._config: Optional[ClusterConfig] = None

    def load(self) -> ClusterConfig:
        if not self.config_path.exists():
            console.print(f"[red]Configuration file {self.config_path} not found![/red]")
            console.print("[yellow]Run 'celeroot config init' to create a default configuration.[/yellow]")
            raise FileNotFoundError(f"Configuration file {self.config_path} not found")

        try:
            with open(self.config_path, "r") as f:
                data: Dict[str, Any] = yaml.safe_load(f)
                self._config = ClusterConfig(**data)
                return self._config
        except yaml.YAMLError as e:
            console.print(f"[red]Error parsing YAML configuration: {e}[/red]")
            raise
        except Exception as e:
            console.print(f"[red]Error loading configuration: {e}[/red]")
            raise

    def save(self, config: ClusterConfig) -> None:
        try:
            data: Dict[str, Any] = config.model_dump()

            for host_data in data.get("hosts", {}).values():
                if "roles" in host_data and isinstance(host_data["roles"], set):
                    host_data["roles"] = sorted(list(host_data["roles"]))

            with open(self.config_path, "w") as f:
                yaml.dump(data, f, default_flow_style=False, indent=2, sort_keys=True)

            self._config = config
            console.print(f"[green]Configuration saved to {self.config_path}[/green]")
        except Exception as e:
            console.print(f"[red]Error saving configuration: {e}[/red]")
            raise

    def get_config(self) -> ClusterConfig:
        if self._config is None:
            self._config = self.load()
        return self._config

    def create_default_config(self) -> ClusterConfig:
        from celeroot.models.config import HostConfig, RoleConfig, ScheduleConfig, RedisConfig

        config: ClusterConfig = ClusterConfig(
            name="default-cluster",
            description="Default celeroot cluster configuration",
            redis=RedisConfig(url="redis://localhost:6379/0", host="localhost", port=6379, db=0),
        )

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

        return config

    def validate(self) -> bool:
        try:
            config: ClusterConfig = self.get_config()
            errors: List[str] = config.validate_config()

            if errors:
                console.print("[red]Configuration validation failed:[/red]")
                for error in errors:
                    console.print(f"  [red]✗[/red] {error}")
                return False
            else:
                console.print("[green]✓ Configuration is valid[/green]")
                return True
        except Exception as e:
            console.print(f"[red]Error during validation: {e}[/red]")
            return False
