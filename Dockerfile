FROM python:3.12-slim

# Install system dependencies including sudo for testing
RUN apt-get update && apt-get install -y --no-install-recommends \
    sudo=1.9.13p3-3+deb12u1 \
    curl=7.88.1-10+deb12u8 \
    wget=1.21.3-1+b2 \
    vim=2:9.0.1378-2 \
    htop=3.2.2-2 \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Create celeroot user and add to sudo group
RUN useradd -m -s /bin/bash celeroot && \
    usermod -aG sudo celeroot && \
    echo "celeroot ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Install dependencies and change ownership to celeroot user
RUN uv sync && \
    chown -R celeroot:celeroot /app

# Switch to celeroot user
USER celeroot

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"

# Default command - run celery worker
CMD ["uv", "run", "celery", "-A", "celeroot.config.celery_app", "worker", "--loglevel=info", "--hostname=worker@%h"]
