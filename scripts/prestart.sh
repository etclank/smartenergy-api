#!/usr/bin/env bash
set -euo pipefail

case "${ROLE:-web}" in
  web)
    exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
    ;;
  worker)
    exec celery -A app.tasks.worker.celery_app worker --concurrency=1 --loglevel=info
    ;;
  beat)
    exec celery -A app.tasks.worker.celery_app beat --loglevel=info --schedule=/tmp/celerybeat-schedule
    ;;
  *)
    echo "Unsupported ROLE: ${ROLE}" >&2
    exit 64
    ;;
esac
