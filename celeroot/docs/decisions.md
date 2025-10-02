# Celeryroot Design Decisions

This document captures all the key design decisions made during the development of celeroot, based on user requirements and architectural discussions.

## Initial Concept & Project Goals

**User Vision**: Create a system administration tool using Celery tasks for Debian/Ubuntu systems, focusing on APT package management with distributed task execution across multiple servers.

**Core Requirements**:
- Distributed task execution across multiple hosts
- APT package management (install, remove, update)
- Task scheduling capabilities
- Simple configuration and management

## Architecture Evolution

### Phase 1: Initial Exploration
- Started with separate Celery Beat container
- Basic worker setup with Redis
- Docker Compose for development environment
- Simple task structure for APT operations

### Phase 2: Embedded Scheduling Attempt
**Decision**: Try embedding Celery Beat into individual workers
**Rationale**: Eliminate single point of failure, make workers self-managing
**Implementation**: Each worker runs scheduling logic in background thread
**Outcome**: Rejected due to complexity of coordination and debugging difficulties

### Phase 3: Final Architecture - CLI-Managed Scheduler
**Decision**: Use dedicated scheduler service managed by CLI
**Rationale**:
- Simple and reliable (standard Celery Beat)
- Easy to manage and debug
- Single source of truth for schedules
- No complex coordination logic required

**Key Quote**: "Actually I changed my mind the scheduler should not be embedded it should be celery beat that is only one service communicating to redis cluster"

## CLI Design Philosophy

### Main Entrypoint Decision
**Requirement**: "there should be one executable in this project, which will be the celeroot.py and that will be the main entrypoint"

**Implementation**:
- Single `celeroot.py` executable
- Multiple subcommands for different functionality
- Typer CLI framework for rich terminal interfaces

### Host-Role Model
**Core Concept**: "each host will have multiple roles, and in the config we will have definition of roles and definition of hosts, where each host will have set of roles and based on that the task scheduling will happen"

**Implementation**:
- Hosts can have multiple roles (webserver, database, application, etc.)
- Roles define queues, concurrency, and available tasks
- Task scheduling targets roles or specific hosts
- Flexible assignment system

### Command Structure
**Requirements**:
- `hosts` subcommand: "hosts ls, hosts add, hosts <name>, hosts rm"
- `roles` subcommand: "similar thing for roles, roles add roles list roles remove"
- **Constraint**: "not possible to remove a role that is still being applied on some host"

### Configuration Management
**Requirement**: "there will be cl.py cli where one will be able to edit the config, which will be cl.yaml"
**Evolution**: Started with `cl.py` and `cl.yaml`, evolved to `celeroot.py` and `celeroot.yaml`

**Key Features**:
- YAML-based configuration
- Configuration validation
- Rich terminal display of configuration data

## Scheduling Architecture

### Scheduler Service Design
**Decision**: "scheduler will be just celery beat that will be part of the cli"
**Implementation**: `celeroot scheduler cl.yaml --beat` starts Celery Beat service

**Key Features**:
- CLI manages scheduler lifecycle
- Dynamic schedule generation from YAML config
- Dry-run mode for testing
- Integration with role-based targeting

### Task Coordination
**Decision**: "The scheduler will be somewhat disconnected basically"
**Implementation**:
- Scheduler submits tasks to Redis queues
- Workers consume from role-specific queues
- Clean separation between scheduling and execution

## Host Management Philosophy

### Adding Hosts
**Requirement**: "Adding will just add to the config and tell you a command that you should run on the host itself via ssh"

**Implementation**:
- `celeroot hosts add` updates configuration
- Displays SSH commands for host setup
- Manual deployment process with clear instructions
- No automatic SSH execution for security

### Code Distribution
**Vision**: "when we add host with cli, we will at the same time distribute the code to the host and we will have to figure out updates"

**Planned Implementation**:
- SSH-based code deployment
- Update mechanism for distributed code
- Service management on remote hosts

## Development Methodology

### Component-Based Development
**Requirement**: "we should basically be able to break it down to individual components such that we can work on them one by one"

**Implementation**:
- Clear component boundaries
- Independent development of features
- Modular architecture with defined interfaces
- Incremental delivery of functionality

### Technology Choices

#### Package Management
**Decision**: "everything should be run with uv, basically don't forget that"
**Implementation**: All commands use `uv run` for consistency

#### CLI Framework
**Decision**: Use Typer for CLI development
**Rationale**: Rich terminal output, type safety, automatic help generation

#### Configuration Format
**Decision**: YAML for human-readable configuration
**Benefits**: Version control friendly, easy to edit, widely understood

## Project Structure

### Module Organization
```
celeroot/
├── celeroot.py           # Main entrypoint
├── commands/               # CLI subcommands
│   ├── hosts.py
│   ├── roles.py
│   ├── config.py
│   └── scheduler.py
├── models/                 # Data models
│   └── config.py
├── core/                   # Core functionality
│   └── config_manager.py
└── docs/                   # Documentation
```

### Documentation Structure
**Decision**: "architecture.md should be in the docs dir"
**Implementation**: All design documents moved to `docs/` directory

## Future Considerations

### Multi-Environment Support
- Production vs development configurations
- Environment-specific host assignments
- Secure secrets management

### Security Features
- SSH key management
- Code signing and verification
- Audit logging

### Operational Features
- Blue-green deployments
- Rolling updates
- Health monitoring
- Drift detection

## Key Principles

1. **Simplicity**: Avoid over-engineering, choose simple solutions
2. **Reliability**: Use battle-tested components (Celery Beat)
3. **Transparency**: Clear command output and instructions
4. **Safety**: Manual deployment steps, validation before changes
5. **Modularity**: Independent components that can be developed separately

## Technology Stack

- **CLI**: Typer + Rich for terminal interfaces
- **Config**: YAML for human-readable configuration
- **Validation**: Pydantic models for type safety
- **Task Queue**: Celery + Redis for distributed execution
- **Package Management**: uv for Python environment management
- **Deployment**: SSH-based manual deployment with clear instructions

This document serves as the authoritative record of all design decisions and requirements that shaped the celeroot project.
