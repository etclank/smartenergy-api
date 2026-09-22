ARG PYTHON_IMAGE=python:3.13-slim@sha256:8d9d0b8bcf6506481eae4907c18f5e3e7902e629f5f6d684f9e7c32e85e3ddf0

FROM ${PYTHON_IMAGE} AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false

RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential libffi-dev libssl-dev \
 && rm -rf /var/lib/apt/lists/*

RUN pip install "poetry==2.2.1"

ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin"

RUN python -m venv "${VIRTUAL_ENV}"

WORKDIR /build
COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-root --no-ansi \
 && chmod -R a-w "${VIRTUAL_ENV}"


FROM ${PYTHON_IMAGE} AS runtime

ARG VCS_REF=unknown
ARG VERSION=0.1.0
ARG BUILD_DATE=unknown

LABEL org.opencontainers.image.title="SmartEnergy API" \
      org.opencontainers.image.description="FastAPI smart-meter portfolio application" \
      org.opencontainers.image.source="https://github.com/etclank/smartenergy-api" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.base.name="docker.io/library/python:3.13-slim@sha256:8d9d0b8bcf6506481eae4907c18f5e3e7902e629f5f6d684f9e7c32e85e3ddf0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin" \
    HOME=/tmp \
    ENV=prod \
    ROLE=web \
    HOST=0.0.0.0 \
    PORT=8000

RUN groupadd --gid 10001 appuser \
 && useradd --uid 10001 --gid 10001 --no-create-home --home-dir /tmp \
      --shell /usr/sbin/nologin appuser

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY --chown=root:root app ./app
COPY --chown=root:root alembic ./alembic
COPY --chown=root:root alembic.ini ./alembic.ini
COPY --chown=root:root scripts ./scripts
COPY --chown=root:root site ./site

RUN chmod 0555 /app/scripts/prestart.sh \
 && chmod -R a-w /app

USER 10001:10001

EXPOSE 8000 9090

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
  CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.getenv('PORT', '8000') + '/api/health/z', timeout=3).read()"]

STOPSIGNAL SIGTERM
CMD ["/app/scripts/prestart.sh"]
