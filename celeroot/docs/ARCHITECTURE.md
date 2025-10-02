# Celeryroot Architecture

## Overview

Celeryroot is a distributed system administration tool for Debian/Ubuntu systems using Celery task queues. The architecture enables both scheduled automated maintenance and on-demand system administration across multiple servers.

## Core Design Principles

### 1. Idempotent Tasks
All tasks are designed to be idempotent - they can be run multiple times safely without adverse effects. For example:
- Package installation checks if packages are already installed before attempting installation
- System updates can be run repeatedly without breaking the system
- Configuration changes verify current state before applying modifications

### 2. Dual Task Submission Model
The system supports two primary modes of task execution:

**Scheduled Tasks (Celery Beat):**
- Automated, periodic maintenance tasks
- Security updates, compliance checks, routine maintenance
- Runs on predictable schedules (daily, weekly, monthly)
- Examples: nightly security updates, weekly package cleanup

**On-Demand Tasks (CLI):**
- Immediate task execution for urgent operations
- Manual system administration tasks
- Emergency fixes and deployments
- Interactive debugging and troubleshooting

### 3. Worker Role-Based Routing
Workers are organized by server roles using queue-based routing:

**Queue Strategy:**
- Each server role has dedicated queues (webserver, database, application)
- Tasks are routed to appropriate queues based on target server type
- Workers consume from role-specific queues ensuring proper task distribution

**Broadcast Support:**
- Critical tasks (security patches, emergency updates) can be broadcast to all workers
- System-wide configuration changes use broadcast routing
- Maintenance windows can target all or subset of workers

## Component Architecture

### Core Components

1. **Redis Broker**
   - Central message broker and result backend
   - Handles task queuing and result storage
   - Provides persistence for task state and results

2. **Celery Workers**
   - Execute tasks on target systems
   - Simulate different server roles (webserver01, dbserver01, appserver01)
   - Run with appropriate system privileges for package management

3. **Celery Beat Scheduler**
   - Manages scheduled task execution
   - Configurable schedules for routine maintenance
   - Handles recurring system administration tasks

4. **CLI Interface**
   - Python-based command-line tool for task submission
   - Provides immediate task execution capabilities
   - Returns task IDs for monitoring and result retrieval

5. **Development Container**
   - Interactive development and testing environment
   - Task debugging and result inspection
   - Development workflow support

### Task Flow

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Celery Beat │    │ CLI Tool    │    │ Interactive │
│ (Scheduled) │    │ (On-demand) │    │ (Dev/Debug) │
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                  │                  │
       └──────────────────┼──────────────────┘
                          │
                    ┌─────▼─────┐
                    │   Redis   │
                    │  Broker   │
                    └─────┬─────┘
                          │
       ┌──────────────────┼──────────────────┐
       │                  │                  │
┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐
│  Worker 1   │    │  Worker 2   │    │  Worker 3   │
│(webserver01)│    │(dbserver01) │    │(appserver01)│
└─────────────┘    └─────────────┘    └─────────────┘
```

## Implementation Strategy

### Current Focus: APT Package Management
- Install, remove, and query packages across worker nodes
- Progress tracking for long-running operations
- Error handling and rollback capabilities
- Cache management to avoid conflicts between workers

### Future Extensions
- File system operations (backup, cleanup, permissions)
- Service management (start, stop, restart, status)
- Configuration management (template deployment, validation)
- Security monitoring (vulnerability scanning, compliance checks)
- Log aggregation and analysis

## Configuration Management

### Queue Configuration
- Role-based queues for different server types
- Broadcast queues for system-wide operations
- Priority queues for urgent tasks

### Task Routing Rules
- Automatic routing based on task type and target
- Hostname-based routing for specific server targeting
- Fallback routing for unspecified targets

### Scheduling Configuration
- Cron-like schedules for recurring tasks
- Maintenance windows for disruptive operations
- Timezone handling for distributed deployments

## Benefits

1. **Scalability**: Add workers dynamically to handle increased load
2. **Reliability**: Task persistence and retry mechanisms ensure completion
3. **Flexibility**: Both automated and manual task execution modes
4. **Monitoring**: Full task tracking and result inspection
5. **Safety**: Idempotent operations prevent accidental system damage
6. **Distribution**: Manage multiple servers from central location

This architecture provides a robust foundation for distributed system administration while maintaining simplicity and operational safety.
