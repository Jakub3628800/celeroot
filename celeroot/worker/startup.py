"""
Worker startup script that initializes embedded scheduling.

This script is called when a Celery worker starts up to initialize
the embedded scheduler and register the worker with the cluster.
"""

import os
import json
import signal
import logging
from datetime import datetime

from celery.signals import worker_ready, worker_shutdown
from celeroot.worker.embedded_scheduler import start_embedded_scheduler, stop_embedded_scheduler

logger = logging.getLogger(__name__)


class WorkerStartup:
    """Handles worker initialization and cleanup."""

    def __init__(self) -> None:
        self.worker_hostname = os.environ.get("CELERY_WORKER_HOSTNAME", "unknown")
        self.worker_role = os.environ.get("CELERY_WORKER_ROLE", "worker")
        self.redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

    def initialize_worker(self) -> None:
        """Initialize the worker on startup."""
        logger.info(f"Initializing worker {self.worker_hostname} with role {self.worker_role}")

        self._register_worker()

        start_embedded_scheduler(self.worker_hostname, self.redis_url)

        self._setup_signal_handlers()

        logger.info(f"Worker {self.worker_hostname} initialization complete")

    def _register_worker(self) -> None:
        """Register this worker with the Redis cluster."""
        try:
            import redis

            redis_client = redis.from_url(self.redis_url)

            worker_data = {
                "hostname": self.worker_hostname,
                "role": self.worker_role,
                "started": datetime.utcnow().isoformat(),
                "last_seen": datetime.utcnow().isoformat(),
                "status": "active",
                "labels": {"role": self.worker_role, "environment": os.environ.get("ENVIRONMENT", "development")},
            }

            worker_key = f"celeroot:worker:{self.worker_hostname}"
            redis_client.set(worker_key, json.dumps(worker_data))

            redis_client.expire(worker_key, 300)

            logger.info(f"Worker {self.worker_hostname} registered with cluster")

        except Exception as e:
            logger.error(f"Failed to register worker: {e}")

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""

        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down worker {self.worker_hostname}")
            self.cleanup_worker()
            exit(0)

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

    def cleanup_worker(self) -> None:
        """Cleanup worker on shutdown."""
        logger.info(f"Cleaning up worker {self.worker_hostname}")

        stop_embedded_scheduler()

        try:
            import redis

            redis_client = redis.from_url(self.redis_url)
            worker_key = f"celeroot:worker:{self.worker_hostname}"
            redis_client.delete(worker_key)
            logger.info(f"Worker {self.worker_hostname} unregistered from cluster")
        except Exception as e:
            logger.error(f"Failed to unregister worker: {e}")


# Global startup instance
_startup = None


def initialize_worker() -> None:
    """Initialize the worker - called from Celery worker startup."""
    global _startup
    if _startup is None:
        _startup = WorkerStartup()
        _startup.initialize_worker()


def cleanup_worker() -> None:
    """Cleanup worker - called on shutdown."""
    global _startup
    if _startup:
        _startup.cleanup_worker()


# Celery signal handlers
@worker_ready.connect
def worker_ready_handler(sender=None, **kwargs) -> None:
    """Called when worker is ready to accept tasks."""
    initialize_worker()


@worker_shutdown.connect
def worker_shutdown_handler(sender=None, **kwargs) -> None:
    """Called when worker is shutting down."""
    cleanup_worker()
