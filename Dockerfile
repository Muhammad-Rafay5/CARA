# ==============================================================================
# CARA — Cost-Aware Autonomous Research & Report Agent
# Multi-Stage Production Dockerfile
#
# Stage 1 (builder): Installs Python dependencies into a virtual environment.
# Stage 2 (runtime): Copies only the venv + source — no build tools, no root.
#
# SECURITY POSTURE:
#   - Non-root user (cara:cara, UID 1001)
#   - Minimal runtime image (python:3.13-slim)
#   - No build tools or compilers in final image
#   - /tmp noexec via read-only root filesystem (when enforced by orchestrator)
#   - Health check built-in for container orchestrators
# ==============================================================================

# ── Stage 1: Builder ────────────────────────────────────────────────────────
FROM python:3.13-slim AS builder

# Prevent Python from writing .pyc files and enable unbuffered stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

# Install system-level build dependencies (if any compiled packages are needed)
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Copy dependency manifests first (better layer caching)
COPY requirements.txt .

# Create isolated virtual environment and install production dependencies
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt


# ── Stage 2: Runtime ────────────────────────────────────────────────────────
FROM python:3.13-slim AS runtime

# Labels for OCI image metadata
LABEL maintainer="CARA Team" \
      description="Cost-Aware Autonomous Research & Report Agent" \
      version="0.1.0"

# Prevent Python from writing .pyc files and enable unbuffered stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    # Default runtime configuration (overridable via env vars / .env)
    ENVIRONMENT=production \
    LOG_LEVEL=INFO \
    HOST=0.0.0.0 \
    PORT=8000

# Create non-root user for running the application
RUN groupadd --gid 1001 cara && \
    useradd --uid 1001 --gid cara --shell /bin/false --create-home cara

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Create application directories with correct ownership
RUN mkdir -p /app/data/documents /app/data/cache /app/data/evaluations && \
    chown -R cara:cara /app

WORKDIR /app

# Copy application source code
COPY --chown=cara:cara app/ ./app/
COPY --chown=cara:cara frontend/ ./frontend/
COPY --chown=cara:cara .env.example ./.env.example

# Create data directory gitkeep files
RUN touch /app/data/documents/.gitkeep /app/data/cache/.gitkeep /app/data/evaluations/.gitkeep && \
    chown -R cara:cara /app/data

# Switch to non-root user
USER cara

# Expose FastAPI port (Streamlit is exposed via docker-compose on a separate container)
EXPOSE ${PORT}

# Health check — hit the liveness probe every 30 seconds
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/health')" || exit 1

# Default entrypoint: run the FastAPI application via uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--log-level", "info"]
