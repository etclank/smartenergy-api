#!/usr/bin/env bash
set -euo pipefail

if [[ "${ROLE:-web}" == "worker" ]]; then
  exec celery -A app.tasks.worker.celery_app worker --beat --loglevel=info
fi

python -m scripts.init_db
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
