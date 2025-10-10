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
# - build-essential, gcc: required for compiling some Python deps
# - curl: for health/debug usage
# - postgresql-client: provides pg_isready for prestart.sh
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

# Ensure prestart script is executable
RUN chmod +x /app/scripts/prestart.sh

EXPOSE 8000

# -----------------------------
# Entrypoint
# -----------------------------
# The prestart script:
#  - Waits for Postgres
#  - Runs lightweight DB init (create_all + seed)
#  - Starts Uvicorn
CMD ["/app/scripts/prestart.sh"]
