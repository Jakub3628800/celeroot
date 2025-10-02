# Celeryroot v3.0 - Complete Design Specification

## Project Vision

Celeryroot is a **GitOps-ready distributed system administration platform** that provides:
- **Declarative Configuration**: Infrastructure as code via `cl.yaml`
- **Automatic Code Distribution**: Deploy worker code to hosts automatically
- **Centralized Scheduling**: Single scheduler with distributed execution
- **Host Lifecycle Management**: Add, remove, update hosts via CLI
- **Simple Operations**: One CLI tool for everything

## Core Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Developer     │    │  Administrator  │    │   Operations    │
│   Machine       │    │    Machine      │    │    Hosts        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │ git push              │ cl.py commands        │ workers
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Git Repository │───▶│   CLI Control   │───▶│  Target Hosts   │
│   cl.yaml       │    │     Plane       │    │  celery workers │
│   tasks/*       │    │   cl.py tool    │    │  code deployed  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                               │
                               ▼
                    ┌─────────────────┐
                    │ Redis Cluster   │
                    │ coordination    │
                    └─────────────────┘
```

## CLI Design - Complete Feature Set

### 1. Configuration Management
```bash
# Initialize project
cl.py config init                           # Create cl.yaml template
cl.py config validate                       # Validate configuration
cl.py config show                          # Display current config
cl.py config edit                          # Open editor for config

# Inspect configuration
cl.py config workers                        # Show worker configuration
cl.py config schedules                     # Show schedule configuration
cl.py config hosts                         # Show all registered hosts
```

### 2. Host Management (New)
```bash
# Add new hosts
cl.py host add webserver03 --role webserver --ssh-key ~/.ssh/id_rsa
cl.py host add dbserver02 --role database --user admin --port 2222

# Manage existing hosts
cl.py host list                            # Show all hosts and status
cl.py host remove webserver03              # Remove host from config
cl.py host update webserver01 --role application  # Change host role
cl.py host status                          # Check connectivity to all hosts

# Code deployment
cl.py host deploy --target webserver03     # Deploy code to specific host
cl.py host deploy --role webserver         # Deploy code to all webserver hosts
cl.py host deploy --all                    # Deploy code to all hosts
cl.py host deploy --check                  # Check if code is up to date
```

### 3. Scheduler Service
```bash
# Scheduler operations
cl.py beat cl.yaml                          # Start scheduler service
cl.py beat cl.yaml --dry-run               # Show what would be scheduled
cl.py beat cl.yaml --loglevel debug        # Start with debug logging
cl.py beat stop                            # Stop running scheduler
cl.py beat status                          # Check scheduler status
```

### 4. Task Execution
```bash
# Immediate tasks
cl.py task install nginx --target webserver01      # Install on specific host
cl.py task install nginx --role webserver          # Install on all webservers
cl.py task remove nginx --target webserver01       # Remove from specific host
cl.py task status                                  # Check worker status
cl.py task logs --task-id abc123                   # Show task logs
cl.py task kill --task-id abc123                   # Kill running task
```

### 5. Cluster Operations (New)
```bash
# Cluster management
cl.py cluster init                          # Initialize new cluster
cl.py cluster status                        # Show cluster health
cl.py cluster scale webserver --replicas 3  # Scale worker role
cl.py cluster backup                        # Backup cluster configuration
cl.py cluster restore backup.yaml           # Restore from backup

# Monitoring
cl.py cluster monitor                       # Live cluster monitoring
cl.py cluster logs                          # Aggregate logs
cl.py cluster metrics                       # Show performance metrics
```

## Enhanced cl.yaml Configuration

### Extended Configuration Format
```yaml
# Cluster metadata
cluster:
  name: production
  version: "1.0"
  description: "Production infrastructure"

# Redis configuration
redis:
  url: redis://redis-cluster:6379/0
  backup:
    enabled: true
    schedule: "0 4 * * *"

# SSH configuration for code deployment
ssh:
  default_user: celeroot
  default_key: ~/.ssh/celeroot_rsa
  default_port: 22
  timeout: 30

# Host definitions with SSH details
hosts:
  webserver01:
    role: webserver
    address: 10.0.1.10
    ssh:
      user: admin
      key: ~/.ssh/webserver_key
      port: 22
    tags:
      environment: production
      datacenter: us-east-1

  webserver02:
    role: webserver
    address: 10.0.1.11
    ssh:
      user: ubuntu
      port: 2222
    tags:
      environment: production
      datacenter: us-east-1

  dbserver01:
    role: database
    address: 10.0.2.10
    tags:
      environment: production
      backup: required

# Worker role definitions
workers:
  webserver:
    queue: webserver_tasks
    concurrency: 4
    max_tasks_per_child: 1000
    tasks:
      - apt_management
      - nginx_management
      - ssl_management

  database:
    queue: database_tasks
    concurrency: 2
    max_tasks_per_child: 500
    tasks:
      - apt_management
      - mysql_management
      - backup_tasks

# Code deployment configuration
deployment:
  target_directory: /opt/celeroot
  service_name: celeroot-worker
  restart_command: systemctl restart celeroot-worker
  health_check_url: http://localhost:8000/health

# Scheduled tasks
schedules:
  security_updates:
    cron: "0 2 * * *"
    task: check_security_updates
    targets:
      - role: webserver
      - role: database
    params:
      auto_install: false
      notify: true
    description: "Daily security update check"

  backup_databases:
    cron: "0 1 * * *"
    task: backup_databases
    targets:
      - tags:
          backup: required
    params:
      compression: true
      retention_days: 30
    description: "Nightly database backup"

# Monitoring and alerting
monitoring:
  health_check_interval: 300  # seconds
  alert_channels:
    - email: ops@company.com
    - slack: "#alerts"

  metrics:
    - name: task_execution_time
      threshold: 300  # seconds
    - name: queue_size
      threshold: 1000  # tasks
```

## Host Management & Code Distribution

### 1. Automatic Code Distribution
When adding a host, the CLI automatically:

```bash
cl.py host add webserver03 --role webserver --address 10.0.1.12
```

**What happens internally:**
1. **SSH Connection**: Test SSH connectivity to host
2. **Prerequisites**: Install Python, uv, Redis client
3. **Code Distribution**: Copy current codebase to host
4. **Service Setup**: Install systemd service for celery worker
5. **Configuration**: Deploy worker configuration
6. **Health Check**: Verify worker starts and connects to Redis
7. **Registration**: Add host to cl.yaml and commit changes

### 2. Code Update Mechanism
```bash
cl.py host deploy --all
```

**Deployment Process:**
1. **Version Check**: Compare local code version with remote
2. **Delta Sync**: Only copy changed files (rsync-style)
3. **Dependency Update**: Run `uv sync` on remote hosts
4. **Service Restart**: Gracefully restart worker services
5. **Health Verification**: Ensure workers reconnect successfully
6. **Rollback**: Automatic rollback if health checks fail

### 3. Host Discovery
```bash
cl.py host discover --network 10.0.0.0/16 --port 22
```

**Discovery Process:**
1. **Network Scan**: Find hosts with SSH open
2. **SSH Probe**: Test SSH connectivity
3. **System Info**: Gather OS, Python version, resources
4. **Compatibility Check**: Verify host can run celeroot
5. **Interactive Add**: Prompt to add discovered hosts

## GitOps Workflow Integration

### 1. Development Workflow
```bash
# Developer workflow
git clone celeroot-config
cd celeroot-config

# Edit configuration
vim cl.yaml
cl.py config validate

# Test locally
cl.py beat cl.yaml --dry-run

# Commit changes
git add cl.yaml
git commit -m "Add new webserver hosts"
git push origin main
```

### 2. CD Pipeline Integration
```bash
# CI/CD pipeline (GitHub Actions, GitLab CI, etc.)
name: Deploy Celeryroot
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Validate Configuration
        run: cl.py config validate
      - name: Deploy to Hosts
        run: cl.py host deploy --all
      - name: Restart Scheduler
        run: cl.py beat restart cl.yaml
```

### 3. Configuration Drift Detection
```bash
cl.py cluster drift                         # Check if hosts match config
cl.py cluster reconcile                     # Fix configuration drift
cl.py cluster backup --auto                 # Automatic backup before changes
```

## Security & Production Features

### 1. SSH Key Management
```yaml
ssh:
  key_rotation:
    enabled: true
    schedule: "0 3 1 * *"  # Monthly
    backup_keys: 3
```

### 2. Code Signing & Verification
```bash
cl.py config sign --key production.pem      # Sign configuration
cl.py host deploy --verify                  # Verify signatures before deploy
```

### 3. Secrets Management
```yaml
secrets:
  provider: vault  # or aws-secrets, azure-kv
  endpoint: https://vault.company.com
  path: celeroot/production
```

### 4. Audit Logging
```bash
cl.py audit logs                           # Show all administrative actions
cl.py audit export --since 2024-01-01     # Export audit logs
```

## Production Deployment Patterns

### 1. Blue-Green Deployment
```bash
cl.py cluster create green --clone blue    # Create green cluster
cl.py host deploy --cluster green          # Deploy to green
cl.py cluster switch green                 # Switch traffic to green
cl.py cluster destroy blue                 # Clean up blue cluster
```

### 2. Rolling Updates
```bash
cl.py host deploy --strategy rolling       # Deploy one host at a time
cl.py host deploy --strategy canary        # Deploy to subset first
```

### 3. Multi-Environment Support
```bash
cl.py --env production config show         # Show production config
cl.py --env staging host deploy --all      # Deploy to staging
cl.py --env development beat cl.yaml       # Run development scheduler
```

This design makes celeroot a complete infrastructure management platform that can scale from development to enterprise production environments while maintaining simplicity and reliability.
