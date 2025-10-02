# Design Decisions

## Architecture Overview

Celeryroot is a system administration framework that uses Celery workers to execute system tasks on local systems. Each system runs its own Celery worker that connects to a remote Redis cluster for task distribution and coordination.

## Key Design Decisions

### 1. Local Execution Model (No SSH)

**Decision**: Execute all tasks locally on the target system rather than remotely via SSH.

**Rationale**:
- Each target system runs its own Celery worker process
- Workers connect to a remote Redis cluster for task coordination
- Eliminates SSH overhead, connection management, and authentication complexity
- Provides better security isolation - each system manages its own privileges
- Scales better - no central bottleneck for command execution
- Simplifies network topology - only Redis connections needed

**Implementation**:
- Workers installed once on each target system (manual deployment)
- Tasks execute using local subprocess calls
- Redis cluster handles task distribution and result storage

### 2. Redis-Centric Communication

**Decision**: Use Redis as the primary communication channel between systems.

**Rationale**:
- Celery's native Redis support provides robust task queuing
- Redis cluster provides high availability and scalability
- Single point of configuration for worker discovery
- Built-in result storage and task state management
- Authorization/authentication handled at Redis level

**Future Considerations**:
- Redis ACLs for fine-grained access control
- Redis Sentinel/Cluster for high availability
- Multiple Redis backends could be supported later

### 3. Host Model Simplification

**Decision**: Host model only contains hostname and description, no connection details.

**Rationale**:
- Connection details no longer needed (no SSH)
- Host identity is primarily for task result organization
- Workers self-identify when connecting to Redis
- Keeps configuration minimal and focused

### 4. Idempotent Operations

**Decision**: All system tasks must be idempotent by design.

**Rationale**:
- Safe to retry operations
- Supports declarative system state management
- Prevents accidental system changes
- Enables convergence-based system management

### 5. Systemd Service Deployment

**Decision**: Deploy workers as systemd services on target systems.

**Rationale**:
- Standard Linux service management
- Automatic restart on failure
- Easy monitoring and logging integration
- Proper process lifecycle management
- Service dependencies (Redis connectivity)

## Security Model

### Current Approach
- Workers run with necessary privileges for system tasks
- Redis connection security handled externally
- Task authorization delegated to Redis ACLs
- Local privilege escalation via sudo where needed

### Future Considerations
- Worker-level authentication tokens
- Task-specific privilege restrictions
- Audit logging for all system changes
- Integration with external identity providers

## Deployment Model

1. **One-time Setup**: Install celeroot worker on each target system
2. **Configuration**: Point workers to Redis cluster
3. **Service Management**: Workers run as systemd services
4. **Task Execution**: Submit tasks via Redis, workers pick up and execute locally

This model provides a distributed, scalable system administration platform without the complexity of SSH-based remote execution.
