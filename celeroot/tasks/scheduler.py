"""
Scheduler tasks for Celeryroot v2.0

The scheduler worker replaces Celery Beat by pulling schedule configuration
from Redis and executing tasks based on cron expressions.
"""

import json
import redis
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from croniter import croniter
from celery import current_task
from celeroot.config.celery_app import app


class SchedulerManager:
    """Manages scheduled task execution."""

    def __init__(self, redis_url: str = "redis://localhost:6379/0") -> None:
        self.redis: redis.Redis = redis.from_url(redis_url)
        self.config_key: str = "celeroot:cluster:config"
        self.scheduler_state_key: str = "celeroot:scheduler:state"
        self.leader_key: str = "celeroot:scheduler:leader"

    def get_cluster_config(self) -> Optional[Dict[str, Any]]:
        """Get current cluster configuration from Redis."""
        config_json = self.redis.get(self.config_key)
        if config_json:
            return json.loads(config_json)
        return None

    def should_worker_run_schedule(self, schedule: Dict[str, Any], worker_hostname: str) -> bool:
        """Check if this specific worker should run a schedule (simple approach)."""
        import hashlib

        schedule_name = schedule["name"]
        hash_value = int(hashlib.md5(f"{schedule_name}:{worker_hostname}".encode()).hexdigest(), 16)

        return hash_value % 3 == 0

    def get_scheduler_state(self) -> Dict[str, Any]:
        """Get the last execution times for scheduled tasks."""
        state_json = self.redis.get(self.scheduler_state_key)
        if state_json:
            return json.loads(state_json)
        return {}

    def update_scheduler_state(self, schedule_name: str, last_run: datetime) -> None:
        """Update the last execution time for a scheduled task."""
        state = self.get_scheduler_state()
        state[schedule_name] = last_run.isoformat()
        self.redis.set(self.scheduler_state_key, json.dumps(state))

    def should_run_schedule(self, schedule: Dict[str, Any], now: datetime) -> bool:
        """Check if a schedule should run now."""
        cron_expr = schedule["cron"]
        schedule_name = schedule["name"]

        state = self.get_scheduler_state()
        last_run_str = state.get(schedule_name)

        if last_run_str:
            last_run = datetime.fromisoformat(last_run_str)
        else:
            last_run = now - timedelta(days=1)

        cron = croniter(cron_expr, last_run)
        next_run = cron.get_next(datetime)

        return now >= next_run

    def execute_scheduled_task(self, schedule: Dict[str, Any]) -> None:
        """Execute a scheduled task."""
        task_name = schedule["task"]
        targets = schedule.get("targets", [])
        # params = schedule.get("params", {})  # Not used yet

        for target in targets:
            selector = target.get("selector", {})

            matching_workers = self.find_workers_by_selector(selector)

            for worker in matching_workers:
                # host_data = {"hostname": worker["hostname"], "description": f"Scheduled task: {schedule['name']}"}

                if task_name == "check-security-updates":
                    from celeroot.tasks.apt import check_security_updates

                    check_security_updates.delay([worker["hostname"]])

                elif task_name == "cleanup-unused-packages":
                    from celeroot.tasks.apt import cleanup_unused_packages

                    cleanup_unused_packages.delay([worker["hostname"]])

                elif task_name == "backup-databases":
                    pass

                elif task_name == "system-health-check":
                    pass

                elif task_name == "renew-ssl-certificates":
                    pass

    def find_workers_by_selector(self, selector: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find workers matching a label selector."""
        workers = []
        worker_keys = self.redis.keys("celeroot:worker:*")

        for key in worker_keys:
            worker_data = self.redis.get(key)
            if worker_data:
                worker = json.loads(worker_data)

                if self.worker_matches_selector(worker, selector):
                    workers.append(worker)

        return workers

    def worker_matches_selector(self, worker: Dict[str, Any], selector: Dict[str, Any]) -> bool:
        """Check if a worker matches a label selector."""
        labels = selector.get("labels", {})

        for key, value in labels.items():
            worker_labels = worker.get("labels", {})
            if key not in worker_labels or worker_labels[key] != value:
                return False

        return True


@app.task(bind=True)
def schedule_manager(self: Any) -> Dict[str, Any]:
    """Main scheduler task that runs periodically to check for scheduled tasks."""
    worker_hostname = self.request.hostname
    scheduler = SchedulerManager()

    current_task.update_state(state="PROGRESS", meta={"status": f"Checking schedules on {worker_hostname}"})

    config = scheduler.get_cluster_config()
    if not config:
        return {"status": "no_config", "message": "No cluster configuration found"}

    schedules = config.get("spec", {}).get("schedules", [])
    now = datetime.utcnow()
    executed_tasks = []

    for schedule in schedules:
        if not scheduler.should_worker_run_schedule(schedule, worker_hostname):
            continue

        if scheduler.should_run_schedule(schedule, now):
            try:
                scheduler.execute_scheduled_task(schedule)
                scheduler.update_scheduler_state(schedule["name"], now)
                executed_tasks.append(schedule["name"])

                current_task.update_state(
                    state="PROGRESS",
                    meta={"status": f"Executed schedule: {schedule['name']}", "executed_count": len(executed_tasks)},
                )
            except Exception as e:
                current_task.update_state(
                    state="PROGRESS",
                    meta={"status": f"Failed to execute {schedule['name']}: {str(e)}", "error": str(e)},
                )

    return {
        "status": "completed",
        "executed_tasks": executed_tasks,
        "total_schedules": len(schedules),
        "next_check": (now + timedelta(minutes=1)).isoformat(),
    }


@app.task(bind=True)
def scheduler_worker_main(self: Any) -> None:
    """Main entry point for scheduler worker. Runs schedule_manager every minute."""
    current_task.update_state(state="PROGRESS", meta={"status": "Starting scheduler worker"})

    while True:
        try:
            result = schedule_manager.apply()

            current_task.update_state(
                state="PROGRESS", meta={"status": "Schedule check completed", "last_result": result.get()}
            )

            time.sleep(60)

        except Exception as e:
            current_task.update_state(state="PROGRESS", meta={"status": f"Scheduler error: {str(e)}", "error": str(e)})
            time.sleep(60)


# Standalone schedule check task (can be called manually)
@app.task
def check_schedules() -> Any:
    """One-time schedule check (for testing or manual triggers)."""
    return schedule_manager.apply().get()
