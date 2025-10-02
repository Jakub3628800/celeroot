"""
Scheduled tasks for Celeryroot v3.0

These tasks are designed to be called by the CLI scheduler service.
They are simple, focused tasks that operate on lists of hostnames.
"""

from typing import List, Dict, Any, Optional
from celery import current_task
from celeroot.config.celery_app import app
from celeroot.tasks.apt import update_package_cache
from celeroot.tasks.apt import check_security_updates as apt_check_security_updates
from celeroot.tasks.apt import cleanup_unused_packages as apt_cleanup_unused_packages


@app.task(bind=True)
def check_security_updates(self: Any, hostnames: List[str], description: str = "") -> Dict[str, Any]:
    """Check for security updates on specified hosts."""
    current_task.update_state(
        state="PROGRESS",
        meta={"status": f"Checking security updates on {len(hostnames)} hosts", "description": description},
    )

    results = {}
    for hostname in hostnames:
        try:
            result = apt_check_security_updates.delay([hostname])
            results[hostname] = {"task_id": result.id, "status": "submitted"}
        except Exception as e:
            results[hostname] = {"status": "failed", "error": str(e)}

    return {"description": description, "total_hosts": len(hostnames), "results": results, "status": "completed"}


@app.task(bind=True)
def cleanup_unused_packages(self: Any, hostnames: List[str], description: str = "") -> Dict[str, Any]:
    """Clean up unused packages on specified hosts."""
    current_task.update_state(
        state="PROGRESS", meta={"status": f"Cleaning up packages on {len(hostnames)} hosts", "description": description}
    )

    results = {}
    for hostname in hostnames:
        try:
            result = apt_cleanup_unused_packages.delay([hostname])
            results[hostname] = {"task_id": result.id, "status": "submitted"}
        except Exception as e:
            results[hostname] = {"status": "failed", "error": str(e)}

    return {"description": description, "total_hosts": len(hostnames), "results": results, "status": "completed"}


@app.task(bind=True)
def health_check(self: Any, hostnames: List[str], description: str = "") -> Dict[str, Any]:
    """Perform health checks on specified hosts."""
    current_task.update_state(
        state="PROGRESS", meta={"status": f"Health checking {len(hostnames)} hosts", "description": description}
    )

    results = {}
    for hostname in hostnames:
        try:
            from celeroot.config.celery_app import app as celery_app

            worker_name = f"worker@{hostname}"
            ping_results = celery_app.control.ping([worker_name], timeout=5)

            if ping_results and ping_results[0].get(worker_name):
                results[hostname] = {"status": "healthy", "response": ping_results[0][worker_name]}
            else:
                results[hostname] = {"status": "unhealthy", "error": "No response to ping"}
        except Exception as e:
            results[hostname] = {"status": "error", "error": str(e)}

    return {"description": description, "total_hosts": len(hostnames), "results": results, "status": "completed"}


@app.task(bind=True)
def update_system_packages(self: Any, hostnames: List[str], description: str = "") -> Dict[str, Any]:
    """Update system packages on specified hosts."""
    current_task.update_state(
        state="PROGRESS", meta={"status": f"Updating packages on {len(hostnames)} hosts", "description": description}
    )

    results = {}
    for hostname in hostnames:
        try:
            result = update_package_cache.delay([hostname])
            results[hostname] = {"task_id": result.id, "status": "submitted"}
        except Exception as e:
            results[hostname] = {"status": "failed", "error": str(e)}

    return {"description": description, "total_hosts": len(hostnames), "results": results, "status": "completed"}


@app.task(bind=True)
def backup_configurations(self: Any, hostnames: List[str], description: str = "") -> Dict[str, Any]:
    """Backup configurations on specified hosts."""
    current_task.update_state(
        state="PROGRESS",
        meta={"status": f"Backing up configurations on {len(hostnames)} hosts", "description": description},
    )

    results = {}
    for hostname in hostnames:
        results[hostname] = {"status": "not_implemented", "message": "Backup functionality not yet implemented"}

    return {"description": description, "total_hosts": len(hostnames), "results": results, "status": "completed"}


@app.task(bind=True)
def restart_services(
    self: Any, hostnames: List[str], services: Optional[List[str]] = None, description: str = ""
) -> Dict[str, Any]:
    """Restart services on specified hosts."""
    services = services or ["nginx", "mysql"]

    current_task.update_state(
        state="PROGRESS", meta={"status": f"Restarting services on {len(hostnames)} hosts", "description": description}
    )

    results = {}
    for hostname in hostnames:
        results[hostname] = {
            "status": "not_implemented",
            "services": services,
            "message": "Service restart functionality not yet implemented",
        }

    return {
        "description": description,
        "total_hosts": len(hostnames),
        "services": services,
        "results": results,
        "status": "completed",
    }
