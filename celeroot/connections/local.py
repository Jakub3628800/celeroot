import subprocess
from typing import Tuple


class LocalExecutionError(Exception):
    pass


def execute_command(command: str, sudo: bool = False) -> Tuple[int, str, str]:
    if sudo:
        command = f"sudo {command}"

    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=300)

        return result.returncode, result.stdout.strip(), result.stderr.strip()

    except subprocess.TimeoutExpired:
        raise LocalExecutionError(f"Command timed out: {command}")
    except Exception as e:
        raise LocalExecutionError(f"Failed to execute command: {e}")


def check_command_exists(command: str) -> bool:
    exit_code, _, _ = execute_command(f"which {command}")
    return exit_code == 0
