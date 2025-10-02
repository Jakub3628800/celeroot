import re
from typing import List, Dict, Any
from celery import current_task
from celeroot.config.celery_app import app
from celeroot.models.host import Host
from celeroot.connections.local import execute_command, check_command_exists


class AptTaskError(Exception):
    pass


def parse_apt_list(output: str) -> Dict[str, str]:
    packages: Dict[str, str] = {}
    for line in output.strip().split("\n"):
        if not line or line.startswith("WARNING") or line.startswith("Listing"):
            continue

        match = re.match(r"^(\S+)/(\S+)\s+(\S+)", line)
        if match:
            package_name: str = match.group(1)
            version: str = match.group(3)
            packages[package_name] = version

    return packages


@app.task(bind=True)
def ensure_packages_installed(
    self, host_data: Dict[str, Any], packages: List[str], update_cache: bool = True
) -> Dict[str, Any]:
    host: Host = Host(**host_data)

    if not check_command_exists("apt"):
        raise AptTaskError("apt command not found on local system")

    result: Dict[str, Any] = {
        "host": str(host),
        "packages": packages,
        "installed": [],
        "already_installed": [],
        "failed": [],
        "cache_updated": False,
    }

    try:
        if update_cache:
            current_task.update_state(state="PROGRESS", meta={"status": "Updating package cache"})
            exit_code, stdout, stderr = execute_command("apt update", sudo=True)
            if exit_code != 0:
                raise AptTaskError(f"Failed to update package cache: {stderr}")
            result["cache_updated"] = True

        current_task.update_state(state="PROGRESS", meta={"status": "Checking installed packages"})
        exit_code, stdout, stderr = execute_command("apt list --installed")
        if exit_code != 0:
            raise AptTaskError(f"Failed to list installed packages: {stderr}")

        installed_packages = parse_apt_list(stdout)

        for package in packages:
            if package in installed_packages:
                result["already_installed"].append(package)
                continue

            current_task.update_state(state="PROGRESS", meta={"status": f"Installing package: {package}"})

            exit_code, stdout, stderr = execute_command(f"apt install -y {package}", sudo=True)

            if exit_code == 0:
                result["installed"].append(package)
            else:
                result["failed"].append({"package": package, "error": stderr})

        return result

    except Exception as e:
        raise AptTaskError(f"Task failed: {str(e)}")


@app.task(bind=True)
def ensure_packages_removed(
    self, host_data: Dict[str, Any], packages: List[str], purge: bool = False
) -> Dict[str, Any]:
    host: Host = Host(**host_data)

    if not check_command_exists("apt"):
        raise AptTaskError("apt command not found on local system")

    result = {
        "host": str(host),
        "packages": packages,
        "removed": [],
        "already_removed": [],
        "failed": [],
    }

    try:
        current_task.update_state(state="PROGRESS", meta={"status": "Checking installed packages"})
        exit_code, stdout, stderr = execute_command("apt list --installed")
        if exit_code != 0:
            raise AptTaskError(f"Failed to list installed packages: {stderr}")

        installed_packages = parse_apt_list(stdout)

        for package in packages:
            if package not in installed_packages:
                result["already_removed"].append(package)
                continue

            current_task.update_state(state="PROGRESS", meta={"status": f"Removing package: {package}"})

            action = "purge" if purge else "remove"
            exit_code, stdout, stderr = execute_command(f"apt {action} -y {package}", sudo=True)

            if exit_code == 0:
                result["removed"].append(package)
            else:
                result["failed"].append({"package": package, "error": stderr})

        return result

    except Exception as e:
        raise AptTaskError(f"Task failed: {str(e)}")


@app.task
def get_package_info(host_data: dict, package: str) -> Dict[str, Any]:
    host = Host(**host_data)

    if not check_command_exists("apt"):
        raise AptTaskError("apt command not found on local system")

    exit_code, stdout, stderr = execute_command(f"apt show {package}")

    if exit_code != 0:
        return {"package": package, "found": False, "error": stderr}

    info = {"package": package, "found": True, "host": str(host)}
    for line in stdout.split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            info[key.strip().lower().replace("-", "_")] = value.strip()

    return info


@app.task
def update_package_cache(hosts: List[str]) -> Dict[str, Any]:
    """Update APT package cache on specified hosts - scheduled task."""
    results = {}

    for hostname in hosts:
        host = Host(hostname=hostname, description=f"Scheduled cache update for {hostname}")

        try:
            if not check_command_exists("apt"):
                results[hostname] = {"success": False, "error": "apt command not found"}
                continue

            exit_code, stdout, stderr = execute_command("apt update", sudo=True)

            if exit_code == 0:
                results[hostname] = {
                    "success": True,
                    "message": "Package cache updated successfully",
                    "timestamp": str(host),
                }
            else:
                results[hostname] = {"success": False, "error": f"Failed to update cache: {stderr}"}

        except Exception as e:
            results[hostname] = {"success": False, "error": str(e)}

    return results


@app.task
def check_security_updates(hosts: List[str]) -> Dict[str, Any]:
    """Check for available security updates on specified hosts - scheduled task."""
    results = {}

    for hostname in hosts:
        host = Host(hostname=hostname, description=f"Scheduled security check for {hostname}")

        try:
            if not check_command_exists("apt"):
                results[hostname] = {"success": False, "error": "apt command not found"}
                continue

            exit_code, stdout, stderr = execute_command("apt list --upgradable")

            if exit_code == 0:
                upgradeable_packages = []
                security_packages = []

                for line in stdout.strip().split("\n"):
                    if "/" in line and "upgradable" in line:
                        package_name = line.split("/")[0]
                        upgradeable_packages.append(package_name)

                        if any(keyword in line.lower() for keyword in ["security", "urgent", "critical"]):
                            security_packages.append(package_name)

                results[hostname] = {
                    "success": True,
                    "upgradeable_count": len(upgradeable_packages),
                    "security_count": len(security_packages),
                    "upgradeable_packages": upgradeable_packages[:10],
                    "security_packages": security_packages,
                    "timestamp": str(host),
                }
            else:
                results[hostname] = {"success": False, "error": f"Failed to check updates: {stderr}"}

        except Exception as e:
            results[hostname] = {"success": False, "error": str(e)}

    return results


@app.task
def cleanup_unused_packages(hosts: List[str]) -> Dict[str, Any]:
    """Clean up unused packages and APT cache on specified hosts - scheduled task."""
    results = {}

    for hostname in hosts:
        host = Host(hostname=hostname, description=f"Scheduled cleanup for {hostname}")

        try:
            if not check_command_exists("apt"):
                results[hostname] = {"success": False, "error": "apt command not found"}
                continue

            cleanup_results = {}

            exit_code, stdout, stderr = execute_command("apt autoremove -y", sudo=True)
            cleanup_results["autoremove"] = {"success": exit_code == 0, "output": stdout if exit_code == 0 else stderr}

            exit_code, stdout, stderr = execute_command("apt autoclean", sudo=True)
            cleanup_results["autoclean"] = {"success": exit_code == 0, "output": stdout if exit_code == 0 else stderr}

            overall_success = all(result["success"] for result in cleanup_results.values())

            results[hostname] = {"success": overall_success, "cleanup_results": cleanup_results, "timestamp": str(host)}

        except Exception as e:
            results[hostname] = {"success": False, "error": str(e)}

    return results
