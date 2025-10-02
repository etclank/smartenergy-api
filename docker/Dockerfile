# docker/Dockerfile
FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps (psycopg needs libpq on some platforms; slim is usually fine)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml poetry.lock* /app/
RUN pip install --upgrade pip && pip install "poetry==2.2.1"
RUN poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi --no-root

COPY . /app

# Ensure prestart script is executable
RUN chmod +x /app/scripts/prestart.sh

EXPOSE 8000
# Respect Render's PORT, default to 8000 locally
CMD /app/scripts/prestart.sh && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
