# Celeryroot Architecture v2.0

## Overview

Celeryroot v2.0 is redesigned as a distributed infrastructure management platform with a clear separation of concerns:

- **CLI**: Central control plane for cluster orchestration and configuration management
- **Redis Cluster**: Data plane for task distribution and state management
- **Workers**: Autonomous execution plane that pulls configuration and executes tasks

## Architecture Principles

### 1. CLI as Control Plane
The `celeroot` CLI serves as the primary interface for all cluster operations:

```bash
# Cluster lifecycle
celeroot cluster init
celeroot cluster deploy
celeroot cluster status
celeroot cluster destroy

# Configuration management
celeroot config apply -f cluster.yaml
celeroot config validate -f cluster.yaml
celeroot config diff -f cluster.yaml

# Worker management
celeroot workers list
celeroot workers add --hostname webserver01 --role webserver
celeroot workers remove webserver01
celeroot workers scale --role webserver --replicas 3

# Task execution (imperative)
celeroot task run install-package --target webserver01 --package nginx
celeroot task status <task-id>
celeroot task logs <task-id>
```

### 2. GitOps-Style Configuration

Infrastructure is defined declaratively in YAML:

```yaml
# cluster.yaml
apiVersion: celeroot.io/v1
kind: Cluster
metadata:
  name: production

spec:
  redis:
    replicas: 3
    memory: "1Gi"
    persistence: true

  workers:
    - name: webservers
      role: webserver
      replicas: 2
      selector:
        labels:
          tier: web
      tasks:
        - apt-management
        - nginx-config

    - name: databases
      role: database
      replicas: 1
      selector:
        labels:
          tier: data
      tasks:
        - apt-management
        - mysql-management

  schedules:
    - name: security-updates
      cron: "0 2 * * *"
      task: check-security-updates
      targets: all

    - name: backup-configs
      cron: "0 3 * * 0"
      task: backup-configurations
      targets:
        role: database
```

### 3. Self-Managing Workers

Workers operate autonomously:
- Pull configuration from Redis on startup
- Self-register with cluster
- Report health and status
- Auto-discover available tasks
- Handle task failures and retries

### 4. Simple Scheduling (No Leader Election)

**Three Simple Options:**

**Option A: System Cron + CLI (Recommended)**
```bash
# /etc/cron.d/celeroot
0 2 * * * celeroot task run check-security-updates --target role:all
0 3 * * 0 celeroot task run cleanup-unused-packages --target role:all
```

**Option B: Single Scheduler Worker**
```yaml
workers:
  - name: scheduler
    role: scheduler
    replicas: 1  # Just one instance, restart if it fails
```

**Option C: Distributed Scheduling**
```python
# Each worker handles some schedules based on hostname hash
def should_worker_run_schedule(schedule_name, hostname):
    import hashlib
    hash_val = int(hashlib.md5(f"{schedule_name}:{hostname}".encode()).hexdigest(), 16)
    return hash_val % 3 == 0  # Simple distribution
```

### 5. Task Distribution Strategy

**Queue-Based Routing:**
```yaml
# Tasks routed by role
queues:
  webserver_queue:
    - webserver_tasks.*
  database_queue:
    - database_tasks.*
  all_queue:
    - system_tasks.*
```

**Label-Based Targeting:**
```yaml
# Workers selected by labels
targets:
  - selector:
      role: webserver
      environment: production
  - selector:
      hostname: webserver01
```

## Component Architecture

### CLI Control Plane

```
┌─────────────────┐
│  celeroot CLI │
│                 │
│ ┌─────────────┐ │
│ │ cluster mgmt│ │
│ │ config mgmt │ │
│ │ worker mgmt │ │
│ │ task exec   │ │
│ └─────────────┘ │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ Redis Cluster   │
│ ┌─────────────┐ │
│ │ Tasks Queue │ │
│ │ Config Store│ │
│ │ Worker Reg. │ │
│ │ Results     │ │
│ └─────────────┘ │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ Worker Nodes    │
│ ┌─────────────┐ │
│ │ Config Pull │ │
│ │ Task Exec   │ │
│ │ Health Rep. │ │
│ │ Auto-heal   │ │
│ └─────────────┘ │
└─────────────────┘
```

### Data Flow

1. **Configuration Deployment:**
   ```
   CLI → YAML Parse → Redis Config Store → Workers Pull Config
   ```

2. **Task Execution:**
   ```
   CLI Task Submit → Redis Queue → Worker Pull → Execute → Results Store
   ```

3. **Health Monitoring:**
   ```
   Workers → Health Reports → Redis → CLI Status Commands
   ```

## Implementation Phases

### Phase 1: CLI Control Plane
- Restructure CLI as orchestration tool
- Add cluster lifecycle commands
- Implement configuration validation
- Worker management commands

### Phase 2: Configuration Management
- YAML schema definition
- Configuration parsing and validation
- Redis-based configuration store
- GitOps workflow support

### Phase 3: Self-Managing Workers
- Configuration pull mechanism
- Worker self-registration
- Health reporting
- Auto-discovery of tasks

### Phase 4: Advanced Features
- Multi-tenancy support
- RBAC and security
- Monitoring and observability
- Plugin system for custom tasks

## Benefits

1. **Infrastructure as Code**: Declarative configuration management
2. **GitOps Ready**: Version-controlled infrastructure changes
3. **Self-Healing**: Workers auto-recover and self-manage
4. **Scalable**: Horizontal scaling of both Redis and workers
5. **Observable**: Built-in monitoring and health checks
6. **Extensible**: Plugin architecture for custom functionality

This architecture provides a foundation for enterprise-grade distributed system administration while maintaining simplicity for smaller deployments.
