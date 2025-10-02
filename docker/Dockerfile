# docker/Dockerfile
FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System deps (build tools kept minimal on slim)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy only dependency manifests first for better layer caching
COPY pyproject.toml poetry.lock* /app/

# Install Poetry & prod deps only
RUN pip install "poetry==2.2.1" \
 && poetry config virtualenvs.create false \
 && poetry install --no-interaction --no-ansi --no-root --without dev

# Now copy the app source
COPY . /app

# Ensure prestart script is executable (runs alembic)
RUN chmod +x /app/scripts/prestart.sh

EXPOSE 8000

# Respect Render's PORT; do migrations each boot
CMD /app/scripts/prestart.sh && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
