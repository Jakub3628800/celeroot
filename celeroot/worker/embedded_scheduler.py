"""
Embedded scheduler for Celeryroot workers.

Each worker runs scheduling logic in a background thread, eliminating the need
for a separate Celery Beat process. Workers coordinate via Redis to prevent
duplicate execution of scheduled tasks.
"""

import json
import time
import threading
import hashlib
import redis
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from croniter import croniter
import logging

logger = logging.getLogger(__name__)


class EmbeddedScheduler:
    """Scheduler that runs embedded within each worker process."""

    def __init__(self, worker_hostname: str, redis_url: str = "redis://localhost:6379/0") -> None:
        self.worker_hostname = worker_hostname
        self.redis = redis.from_url(redis_url)
        self.config_key = "celeroot:cluster:config"
        self.schedule_lock_prefix = "celeroot:schedule:lock:"
        self.schedule_state_prefix = "celeroot:schedule:state:"
        self.running = False
        self.scheduler_thread = None

    def start(self) -> None:
        """Start the embedded scheduler in a background thread."""
        if self.running:
            return

        self.running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        logger.info(f"Embedded scheduler started on worker {self.worker_hostname}")

    def stop(self) -> None:
        """Stop the embedded scheduler."""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        logger.info(f"Embedded scheduler stopped on worker {self.worker_hostname}")

    def _scheduler_loop(self) -> None:
        """Main scheduler loop that runs in background thread."""
        while self.running:
            try:
                self._check_and_execute_schedules()
            except Exception as e:
                logger.error(f"Scheduler error on {self.worker_hostname}: {e}")

            time.sleep(30)

    def _check_and_execute_schedules(self) -> None:
        """Check for schedules that need to run and execute them."""
        config = self._get_cluster_config()
        if not config:
            return

        schedules = config.get("spec", {}).get("schedules", [])
        now = datetime.utcnow()

        for schedule in schedules:
            if self._should_worker_handle_schedule(schedule) and self._should_schedule_run(schedule, now):
                if self._try_acquire_schedule_lock(schedule["name"], now):
                    try:
                        self._execute_schedule(schedule)
                        self._update_schedule_state(schedule["name"], now)
                        logger.info(f"Executed schedule '{schedule['name']}' on {self.worker_hostname}")
                    except Exception as e:
                        logger.error(f"Failed to execute schedule '{schedule['name']}': {e}")
                    finally:
                        self._release_schedule_lock(schedule["name"])

    def _get_cluster_config(self) -> Optional[Dict]:
        """Get cluster configuration from Redis."""
        try:
            config_json = self.redis.get(self.config_key)
            if config_json:
                return json.loads(config_json)
        except Exception as e:
            logger.error(f"Failed to get cluster config: {e}")
        return None

    def _should_worker_handle_schedule(self, schedule: Dict) -> bool:
        """Determine if this worker should handle a specific schedule."""
        schedule_name = schedule["name"]

        hash_input = f"{schedule_name}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)

        worker_hash = int(hashlib.md5(self.worker_hostname.encode()).hexdigest(), 16)

        return (hash_value % 10) == (worker_hash % 10)

    def _should_schedule_run(self, schedule: Dict, now: datetime) -> bool:
        """Check if a schedule should run based on its cron expression."""
        cron_expr = schedule["cron"]
        schedule_name = schedule["name"]

        last_run = self._get_schedule_last_run(schedule_name)
        if not last_run:
            last_run = now - timedelta(days=1)

        try:
            cron = croniter(cron_expr, last_run)
            next_run = cron.get_next(datetime)
            return now >= next_run
        except Exception as e:
            logger.error(f"Invalid cron expression '{cron_expr}' for schedule '{schedule_name}': {e}")
            return False

    def _try_acquire_schedule_lock(self, schedule_name: str, now: datetime, ttl: int = 300) -> bool:
        """Try to acquire a distributed lock for executing a schedule."""
        lock_key = f"{self.schedule_lock_prefix}{schedule_name}"
        lock_value = f"{self.worker_hostname}:{now.isoformat()}"

        result = self.redis.set(lock_key, lock_value, nx=True, ex=ttl)
        return bool(result)

    def _release_schedule_lock(self, schedule_name: str) -> None:
        """Release the distributed lock for a schedule."""
        lock_key = f"{self.schedule_lock_prefix}{schedule_name}"
        try:
            self.redis.delete(lock_key)
        except Exception as e:
            logger.error(f"Failed to release lock for schedule '{schedule_name}': {e}")

    def _get_schedule_last_run(self, schedule_name: str) -> Optional[datetime]:
        """Get the last run time for a schedule."""
        state_key = f"{self.schedule_state_prefix}{schedule_name}"
        try:
            last_run_str = self.redis.get(state_key)
            if last_run_str:
                return datetime.fromisoformat(last_run_str.decode())
        except Exception as e:
            logger.error(f"Failed to get last run time for schedule '{schedule_name}': {e}")
        return None

    def _update_schedule_state(self, schedule_name: str, run_time: datetime) -> None:
        """Update the last run time for a schedule."""
        state_key = f"{self.schedule_state_prefix}{schedule_name}"
        try:
            self.redis.set(state_key, run_time.isoformat())
        except Exception as e:
            logger.error(f"Failed to update state for schedule '{schedule_name}': {e}")

    def _execute_schedule(self, schedule: Dict) -> None:
        """Execute a scheduled task."""
        task_name = schedule["task"]
        targets = schedule.get("targets", [])
        params = schedule.get("params", {})

        logger.info(f"Executing schedule '{schedule['name']}' - task '{task_name}'")

        target_workers = []
        for target in targets:
            workers = self._find_workers_by_selector(target.get("selector", {}))
            target_workers.extend(workers)

        unique_workers = {w["hostname"]: w for w in target_workers}.values()

        for worker in unique_workers:
            try:
                self._submit_task_to_worker(task_name, worker, params)
            except Exception as e:
                logger.error(f"Failed to submit task '{task_name}' to worker '{worker['hostname']}': {e}")

    def _find_workers_by_selector(self, selector: Dict) -> List[Dict]:
        """Find workers matching a label selector."""
        workers = []
        try:
            worker_keys = self.redis.keys("celeroot:worker:*")
            for key in worker_keys:
                worker_data = self.redis.get(key)
                if worker_data:
                    worker = json.loads(worker_data)
                    if self._worker_matches_selector(worker, selector):
                        workers.append(worker)
        except Exception as e:
            logger.error(f"Failed to find workers by selector: {e}")
        return workers

    def _worker_matches_selector(self, worker: Dict, selector: Dict) -> bool:
        """Check if a worker matches a label selector."""
        labels = selector.get("labels", {})
        worker_labels = worker.get("labels", {})

        if "role" in selector:
            if worker.get("role") != selector["role"]:
                return False

        for key, value in labels.items():
            if key not in worker_labels or worker_labels[key] != value:
                return False

        return True

    def _submit_task_to_worker(self, task_name: str, worker: Dict, params: Dict) -> None:
        """Submit a task to a specific worker."""

        # host_data = {"hostname": worker["hostname"], "description": f"Scheduled task: {task_name}"}

        if task_name == "check-security-updates":
            from celeroot.tasks.apt import check_security_updates

            check_security_updates.delay([worker["hostname"]])

        elif task_name == "cleanup-unused-packages":
            from celeroot.tasks.apt import cleanup_unused_packages

            cleanup_unused_packages.delay([worker["hostname"]])

        elif task_name == "update-package-cache":
            from celeroot.tasks.apt import update_package_cache

            update_package_cache.delay([worker["hostname"]])

        else:
            logger.warning(f"Unknown task name: {task_name}")


# Global scheduler instance
_scheduler: Optional[EmbeddedScheduler] = None


def start_embedded_scheduler(worker_hostname: str, redis_url: str = "redis://localhost:6379/0") -> None:
    """Start the embedded scheduler for this worker."""
    global _scheduler
    if _scheduler is None:
        _scheduler = EmbeddedScheduler(worker_hostname, redis_url)
        _scheduler.start()


def stop_embedded_scheduler() -> None:
    """Stop the embedded scheduler for this worker."""
    global _scheduler
    if _scheduler:
        _scheduler.stop()
        _scheduler = None


def get_scheduler_status() -> Dict:
    """Get status of the embedded scheduler."""
    global _scheduler
    if _scheduler:
        return {
            "running": _scheduler.running,
            "worker_hostname": _scheduler.worker_hostname,
            "thread_alive": _scheduler.scheduler_thread.is_alive() if _scheduler.scheduler_thread else False,
        }
    return {"running": False}
