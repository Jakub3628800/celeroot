# Docker Compose Testing Setup

This setup provides a complete testing environment for celeroot using Docker Compose.

## Architecture

- **Redis**: Central message broker and result backend
- **3 Workers**: Simulating different servers (webserver01, dbserver01, appserver01)
- **Celery Beat**: Scheduler for automated/recurring tasks
- **Redis Commander**: Web UI for monitoring Redis at http://localhost:8081
- **Dev Container**: For running test scripts and interactive development

## Quick Start

### Using Makefile (Recommended)

1. **Complete setup:**
   ```bash
   make dev-setup
   ```

2. **Run full test suite:**
   ```bash
   make dev-test
   ```

3. **Check status:**
   ```bash
   make cli-status
   ```

### Using Docker Compose Directly

1. **Build and start all services:**
   ```bash
   docker compose up -d
   ```

2. **Check service status:**
   ```bash
   docker compose logs worker1
   docker compose logs worker2
   docker compose logs worker3
   docker compose logs beat
   ```

3. **Test CLI tool:**
   ```bash
   docker compose exec dev uv run python cli.py status
   docker compose exec dev uv run python cli.py apt install --hostname webserver01 htop vim
   ```

4. **Run test script:**
   ```bash
   docker compose exec dev python test_compose.py
   ```

5. **Monitor Redis (optional):**
   Open http://localhost:8081 in your browser

6. **Stop everything:**
   ```bash
   docker compose down
   ```

## Makefile Commands

For convenience, use these Makefile targets:

```bash
make help              # Show all available commands
make up               # Start all services
make down             # Stop all services
make cli-status       # Check worker status
make quick-install    # Test package installation
make quick-info       # Test package info query
make logs-beat        # View scheduler logs
make monitor          # Open Redis Commander
make clean            # Stop and remove volumes
```

## Interactive Testing

To run commands interactively in the dev container:

```bash
# Shell into dev container
docker compose exec dev bash

# Run Python REPL with celeroot
cd /app
python -c "
from celeroot.tasks.apt import *
from celeroot.models.host import Host

host = Host(hostname='webserver01', description='Test server')
result = ensure_packages_installed.delay(host.model_dump(), ['nginx'])
print(f'Task ID: {result.id}')
print(f'Result: {result.get()}')
"
```

## Individual Worker Testing

Test a specific worker:

```bash
# Test worker1 (webserver01)
docker compose exec worker1 apt list --installed | grep curl

# Check worker logs
docker compose logs -f worker1
```

## CLI Usage

The celeroot CLI provides on-demand task execution:

```bash
# Check worker status
docker compose exec dev uv run python cli.py status

# Install packages
docker compose exec dev uv run python cli.py apt install --hostname webserver01 --wait htop nginx

# Remove packages
docker compose exec dev uv run python cli.py apt remove --hostname webserver01 --wait htop

# Get package info
docker compose exec dev uv run python cli.py apt info --hostname webserver01 nginx
```

## Scheduled Tasks

Celery Beat runs these scheduled tasks:
- **Daily** (2 AM UTC): Update package cache on all hosts
- **Weekly** (Monday 6 AM UTC): Check for security updates
- **Monthly** (First Sunday 3 AM UTC): Clean up unused packages

View scheduled task logs:
```bash
docker compose logs beat
```

## Development Workflow

1. Make code changes in your local directory
2. Changes are automatically reflected in containers (volume mounted)
3. Restart services if needed: `docker compose restart worker1 worker2 worker3 beat`
4. Test changes with CLI or test script

## Troubleshooting

- **Workers not starting**: Check `docker compose logs worker1`
- **Redis connection issues**: Ensure Redis is running: `docker compose ps redis`
- **Permission issues**: Check if celeroot user has sudo access in container
- **APT cache issues**: Workers have separate APT caches to avoid conflicts

## Cleanup

Remove all data and start fresh:

```bash
docker compose down -v  # Removes volumes
docker compose build --no-cache  # Rebuild images
docker compose up -d
```
