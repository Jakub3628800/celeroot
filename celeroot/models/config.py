from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field


class SSHConfig(BaseModel):
    user: str = "celeroot"
    key_path: Optional[str] = None
    port: int = 22
    timeout: int = 30


class HostConfig(BaseModel):
    hostname: str
    address: str
    roles: Set[str] = Field(default_factory=set)
    ssh: SSHConfig = Field(default_factory=SSHConfig)
    tags: Dict[str, str] = Field(default_factory=dict)
    enabled: bool = True

    def has_role(self, role: str) -> bool:
        return role in self.roles

    def add_role(self, role: str) -> None:
        self.roles.add(role)

    def remove_role(self, role: str) -> None:
        self.roles.discard(role)


class RoleConfig(BaseModel):
    name: str
    description: str = ""
    queue: str
    concurrency: int = 4
    max_tasks_per_child: int = 1000
    tasks: List[str] = Field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.queue:
            self.queue = f"{self.name}_tasks"


class ScheduleConfig(BaseModel):
    name: str
    cron: str
    task: str
    target_roles: List[str] = Field(default_factory=list)
    target_hosts: List[str] = Field(default_factory=list)
    target_tags: Dict[str, str] = Field(default_factory=dict)
    params: Dict[str, Any] = Field(default_factory=dict)
    description: str = ""
    enabled: bool = True


class RedisConfig(BaseModel):
    url: str = "redis://localhost:6379/0"
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    timeout: int = 10
    socket_connect_timeout: int = 5
    socket_keepalive: bool = True
    socket_keepalive_options: Dict[str, int] = Field(default_factory=dict)
    max_connections: int = 50


class ClusterConfig(BaseModel):
    name: str = "default"
    version: str = "1.0.0"
    description: str = ""

    redis: RedisConfig = Field(default_factory=RedisConfig)

    hosts: Dict[str, HostConfig] = Field(default_factory=dict)
    roles: Dict[str, RoleConfig] = Field(default_factory=dict)

    schedules: Dict[str, ScheduleConfig] = Field(default_factory=dict)

    def get_hosts_by_role(self, role: str) -> List[HostConfig]:
        return [host for host in self.hosts.values() if host.has_role(role)]

    def get_hosts_by_tags(self, tags: Dict[str, str]) -> List[HostConfig]:
        matching_hosts: List[HostConfig] = []
        for host in self.hosts.values():
            if all(host.tags.get(key) == value for key, value in tags.items()):
                matching_hosts.append(host)
        return matching_hosts

    def get_enabled_hosts(self) -> List[HostConfig]:
        return [host for host in self.hosts.values() if host.enabled]

    def add_host(self, host: HostConfig) -> None:
        self.hosts[host.hostname] = host

    def remove_host(self, hostname: str) -> bool:
        if hostname in self.hosts:
            del self.hosts[hostname]
            return True
        return False

    def add_role(self, role: RoleConfig) -> None:
        self.roles[role.name] = role

    def remove_role(self, role_name: str) -> bool:
        if role_name in self.roles:
            for host in self.hosts.values():
                host.remove_role(role_name)
            del self.roles[role_name]
            return True
        return False

    def validate_config(self) -> List[str]:
        errors: List[str] = []

        for host in self.hosts.values():
            for role in host.roles:
                if role not in self.roles:
                    errors.append(f"Host {host.hostname} has undefined role: {role}")

        for schedule in self.schedules.values():
            for role in schedule.target_roles:
                if role not in self.roles:
                    errors.append(f"Schedule {schedule.name} targets undefined role: {role}")

        for schedule in self.schedules.values():
            for hostname in schedule.target_hosts:
                if hostname not in self.hosts:
                    errors.append(f"Schedule {schedule.name} targets undefined host: {hostname}")

        return errors
