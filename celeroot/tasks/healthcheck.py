import time
import platform
import socket
from datetime import datetime
from typing import Dict, Any

from celeroot.config.celery_app import app


@app.task(bind=True)
def ping(self: Any) -> Dict[str, Any]:
    start_time: float = time.time()

    try:
        system_info: Dict[str, Any] = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "hostname": socket.gethostname(),
            "platform": platform.system(),
            "platform_release": platform.release(),
            "python_version": platform.python_version(),
            "task_id": self.request.id,
            "worker_id": self.request.hostname,
            "execution_time_ms": round((time.time() - start_time) * 1000, 2),
        }

        return system_info

    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "task_id": self.request.id,
            "execution_time_ms": round((time.time() - start_time) * 1000, 2),
        }


@app.task(bind=True)
def connectivity_check(self: Any, host: str = "8.8.8.8", port: int = 53, timeout: int = 5) -> Dict[str, Any]:
    start_time: float = time.time()

    try:
        sock: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result: int = sock.connect_ex((host, port))
        sock.close()

        connectivity_ok: bool = result == 0

        return {
            "status": "healthy" if connectivity_ok else "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "connectivity": {
                "target_host": host,
                "target_port": port,
                "reachable": connectivity_ok,
                "timeout": timeout,
            },
            "hostname": socket.gethostname(),
            "task_id": self.request.id,
            "worker_id": self.request.hostname,
            "execution_time_ms": round((time.time() - start_time) * 1000, 2),
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "connectivity": {"target_host": host, "target_port": port, "reachable": False, "timeout": timeout},
            "task_id": self.request.id,
            "execution_time_ms": round((time.time() - start_time) * 1000, 2),
        }


@app.task(bind=True)
def echo(self: Any, message: str = "Hello from celeroot!") -> Dict[str, Any]:
    start_time: float = time.time()

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "echo": message,
        "hostname": socket.gethostname(),
        "task_id": self.request.id,
        "worker_id": self.request.hostname,
        "execution_time_ms": round((time.time() - start_time) * 1000, 2),
    }


@app.task(bind=True)
def load_test(self: Any, duration: int = 1, cpu_intensive: bool = False) -> Dict[str, Any]:
    start_time: float = time.time()

    try:
        count: int = 0
        if cpu_intensive:
            end_time: float = time.time() + duration
            while time.time() < end_time:
                count += 1
                _ = sum(i**2 for i in range(100))
        else:
            time.sleep(duration)

        execution_time: float = time.time() - start_time

        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "load_test": {
                "requested_duration": duration,
                "actual_duration": round(execution_time, 2),
                "cpu_intensive": cpu_intensive,
                "operations_count": count if cpu_intensive else None,
            },
            "hostname": socket.gethostname(),
            "task_id": self.request.id,
            "worker_id": self.request.hostname,
            "execution_time_ms": round(execution_time * 1000, 2),
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "task_id": self.request.id,
            "execution_time_ms": round((time.time() - start_time) * 1000, 2),
        }
