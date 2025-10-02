from typing import Dict, Any
from celery import Celery
from celery.schedules import crontab
from .settings import settings

app: Celery = Celery("celeroot")

app.conf.update(
    broker_url=settings.celery_broker_url,
    result_backend=settings.celery_result_backend,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,
    task_soft_time_limit=25 * 60,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
)

beat_schedule: Dict[str, Dict[str, Any]] = {
    "update-package-cache": {
        "task": "celeroot.tasks.apt.update_package_cache",
        "schedule": crontab(hour=2, minute=0),
        "kwargs": {"hosts": ["webserver01", "dbserver01", "appserver01"]},
    },
    "weekly-security-check": {
        "task": "celeroot.tasks.apt.check_security_updates",
        "schedule": crontab(hour=6, minute=0, day_of_week=1),
        "kwargs": {"hosts": ["webserver01", "dbserver01", "appserver01"]},
    },
    "monthly-cleanup": {
        "task": "celeroot.tasks.apt.cleanup_unused_packages",
        "schedule": crontab(hour=3, minute=0, day_of_week=0, day_of_month="1-7"),
        "kwargs": {"hosts": ["webserver01", "dbserver01", "appserver01"]},
    },
}

app.conf.beat_schedule = beat_schedule

app.autodiscover_tasks(["celeroot.tasks"])


if __name__ == "__main__":
    app.start()
