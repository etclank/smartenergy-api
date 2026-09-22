# -----------------------------
# SmartEnergy API — Dockerfile
# -----------------------------
FROM python:3.13-slim AS base

# Environment config
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/usr/local/bin:$PATH"

WORKDIR /app

# -----------------------------
# System dependencies
# -----------------------------
# build-essential, gcc: compile native deps
# curl: for health/debug usage
# postgresql-client: available for manual database diagnostics
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libffi-dev \
    libssl-dev \
    python3-dev \
    curl \
    postgresql-client \
 && rm -rf /var/lib/apt/lists/*

# -----------------------------
# Install Poetry and dependencies
# -----------------------------
COPY pyproject.toml poetry.lock* /app/

RUN pip install "poetry==2.2.1" \
 && poetry config virtualenvs.create false \
 && poetry install --no-interaction --no-ansi --no-root --without dev

# -----------------------------
# Copy application source
# -----------------------------
COPY . /app
RUN useradd --create-home --uid 10001 appuser \
 && mkdir -p /app/logs /app/backups \
 && chown -R appuser:appuser /app
USER appuser

# Ensure prestart script is executable
RUN chmod +x /app/scripts/prestart.sh

# -----------------------------
# Optional environment variables for flexibility
# -----------------------------
ARG APP_MODULE="app.main:app"
ENV APP_MODULE=${APP_MODULE}
ENV HOST=0.0.0.0
ENV PORT=8000

# -----------------------------
# Healthcheck (basic HTTP ping)
# -----------------------------
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
  CMD curl -fs http://localhost:${PORT:-8000}/api/health/z || exit 1

# -----------------------------
# Expose API and private metrics ports
# -----------------------------
EXPOSE 8000 9090

# -----------------------------
# Entrypoint
# -----------------------------
# Default entrypoint runs prestart.sh, which starts Uvicorn without changing
# the database schema. Run Alembic as a separate deployment step.
#
# ROLE selects the web, worker, or Beat process without combining roles.
CMD ["/app/scripts/prestart.sh"]
