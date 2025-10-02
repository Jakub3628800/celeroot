# Celeryroot Architecture v3.0 - Final Design

## Overview

Celeryroot v3.0 adopts a clean, simple architecture with clear separation of concerns:

- **CLI** (`cl.py`) - Configuration management and scheduler service
- **Config** (`cl.yaml`) - Simple YAML configuration for schedules and workers
- **Scheduler** - Dedicated Celery Beat service managed by CLI
- **Workers** - Pure workers focused on task execution
- **Redis** - Central coordination and task queuing

## Design Decisions

### 1. Dedicated Scheduler Service (Final Choice)

**Architecture:**
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   cl.py     │    │ Celery Beat │    │   Workers   │
│ (CLI Tool)  │───▶│ (Scheduler) │───▶│ (Execution) │
└─────────────┘    └─────────────┘    └─────────────┘
       │                  │                  │
       └──────────────────┼──────────────────┘
                          │
                    ┌─────▼─────┐
                    │   Redis   │
                    │  Cluster  │
                    └───────────┘
```

**Why This Approach:**
- ✅ **Simple**: One scheduler service, easy to manage
- ✅ **Reliable**: Standard Celery Beat, battle-tested
- ✅ **Maintainable**: No complex coordination logic
- ✅ **Predictable**: Single source of truth for schedules
- ✅ **Debuggable**: Easy to monitor and troubleshoot

### 2. CLI-Centric Management

**Core Commands:**
```bash
# Configuration management
uv run cl.py config init                    # Create default cl.yaml
uv run cl.py config edit                    # Edit configuration
uv run cl.py config validate                # Validate configuration
uv run cl.py config show                    # Display configuration

# Scheduler service
uv run cl.py cl.yaml --beat                 # Start scheduler
uv run cl.py cl.yaml --beat --dry-run       # Show what would be scheduled

# Task execution
uv run cl.py task install nginx --targets webserver
uv run cl.py task status                    # Check worker status

# Configuration inspection
uv run cl.py config workers                 # Show worker configuration
uv run cl.py config schedules               # Show schedule configuration
```

### 3. Simple Configuration Format

**cl.yaml Structure:**
```yaml
redis:
  url: redis://localhost:6379/0

workers:
  webserver:
    hostnames: [webserver01, webserver02]
    queue: webserver_tasks
  database:
    hostnames: [dbserver01]
    queue: database_tasks

schedules:
  security_updates:
    cron: "0 2 * * *"
    task: check_security_updates
    targets: [webserver, database]
    description: "Daily security update check"
```

**Benefits:**
- **Readable**: Human-friendly YAML format
- **Simple**: Flat structure, no nested complexity
- **Flexible**: Easy to add new workers/schedules
- **Version-controlled**: Can be committed to git

### 4. Rejected Approaches and Why

#### ❌ Embedded Scheduling in Workers
**Rejected because:**
- Complex coordination logic required
- Difficult to debug which worker runs what
- Race conditions with distributed locks
- Harder to maintain schedule state

#### ❌ External Cron + CLI
**Rejected because:**
- Not GitOps-friendly (system cron vs config files)
- Requires system-level access
- Hard to monitor and manage centrally
- No integration with Celery ecosystem

#### ❌ Multiple Beat Processes with Leader Election
**Rejected because:**
- Over-engineered for the use case
- Complex failure scenarios
- Additional dependencies (etcd, consul, etc.)
- Difficult to debug leadership issues

### 5. Component Responsibilities

#### CLI (`cl.py`)
- **Configuration Management**: Edit, validate, show configuration
- **Scheduler Service**: Start/stop Celery Beat with config
- **Task Execution**: Submit immediate tasks
- **Status Monitoring**: Check worker health

#### Configuration (`cl.yaml`)
- **Worker Definitions**: Hostname to queue mappings
- **Schedule Definitions**: Cron expressions and targets
- **Redis Configuration**: Connection settings
- **Task Parameters**: Default parameters for tasks

#### Scheduler (Celery Beat)
- **Schedule Execution**: Run tasks based on cron expressions
- **Task Submission**: Submit tasks to appropriate queues
- **State Management**: Track last run times
- **Error Handling**: Retry failed schedule submissions

#### Workers
- **Task Execution**: Process tasks from queues
- **Queue Consumption**: Listen to role-specific queues
- **Result Reporting**: Store task results in Redis
- **Health Reporting**: Register with cluster

#### Redis Cluster
- **Task Queuing**: Distribute tasks to workers
- **Result Storage**: Store task execution results
- **Configuration Storage**: Cache configuration data
- **Worker Registration**: Track active workers

## Implementation Benefits

### 1. Operational Simplicity
```bash
# Start infrastructure
docker compose up -d redis worker1 worker2 worker3

# Start scheduler
uv run cl.py cl.yaml --beat

# Deploy configuration changes
vim cl.yaml
uv run cl.py config validate
uv run cl.py cl.yaml --beat  # Restart with new config
```

### 2. Development Workflow
```bash
# Local development
uv run cl.py config init
uv run cl.py config edit
uv run cl.py config validate
uv run cl.py cl.yaml --beat --dry-run  # Test without running

# Production deployment
git commit cl.yaml
git push
# Deploy via CI/CD or manual restart
```

### 3. Monitoring and Debugging
```bash
# Check configuration
uv run cl.py config show
uv run cl.py config schedules

# Monitor scheduler
tail -f celerybeat.log

# Check worker status
uv run cl.py task status

# Manual task execution
uv run cl.py task install nginx --targets webserver
```

## Future Extensions

### 1. Multi-Environment Support
```yaml
environments:
  development:
    redis: redis://dev-redis:6379/0
    workers: {...}
  production:
    redis: redis://prod-redis:6379/0
    workers: {...}
```

### 2. Advanced Scheduling
```yaml
schedules:
  conditional_backup:
    cron: "0 1 * * *"
    task: backup_database
    targets: [database]
    conditions:
      - disk_usage < 80%
      - backup_age > 24h
```

### 3. Task Dependencies
```yaml
schedules:
  backup_workflow:
    tasks:
      - {task: stop_services, targets: [application]}
      - {task: backup_database, targets: [database]}
      - {task: start_services, targets: [application]}
```

## Migration Path

### From v2.0 (Embedded Scheduling)
1. Stop embedded scheduler workers
2. Create `cl.yaml` configuration
3. Start dedicated scheduler: `uv run cl.py cl.yaml --beat`
4. Restart workers without embedded scheduling

### From v1.0 (Separate Beat)
1. Convert `celery_app.py` beat_schedule to `cl.yaml`
2. Stop separate Beat container
3. Start CLI-managed scheduler: `uv run cl.py cl.yaml --beat`

This architecture provides the perfect balance of simplicity, reliability, and maintainability for distributed system administration.
