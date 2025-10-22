#!/usr/bin/env bash
set -euo pipefail

ROLE="${ROLE:-web}"  # Default role is 'web'
echo "[prestart] Starting SmartEnergy in ROLE=${ROLE}"
echo "[prestart] ENV=${ENV:-} DATABASE_URL=${DATABASE_URL:-<empty>} REDIS_URL=${REDIS_URL:-<empty>}"

# Wait for Postgres if needed
if [[ "${DATABASE_URL:-}" == postgresql* ]]; then
  echo "[prestart] Waiting for PostgreSQL to be ready..."
  ATTEMPTS=0
  until pg_isready -h "$(echo "$DATABASE_URL" | sed -E 's|.*@([^:/]+).*|\1|')" \
                    -p "$(echo "$DATABASE_URL" | sed -E 's|.*:([0-9]+)/.*|\1|')" \
                    -U "$(echo "$DATABASE_URL" | sed -E 's|.*//([^:]+):.*|\1|')" >/dev/null 2>&1; do
    ATTEMPTS=$((ATTEMPTS + 1))
    if [ $ATTEMPTS -ge 15 ]; then
      echo "[prestart] Postgres not ready after 15 attempts, continuing anyway..."
      break
    fi
    echo "  → attempt $ATTEMPTS: waiting for DB..."
    sleep 2
  done
fi

# ------------------------------------------
# Role-based startup
# ------------------------------------------
if [[ "$ROLE" == "worker" ]]; then
  echo "[prestart] Launching Celery worker + Beat..."
  exec celery -A app.tasks.worker.celery_app worker --beat --loglevel=info

else
  echo "[prestart] Initializing database..."
  python -m scripts.init_db

  echo "[prestart] Starting FastAPI (Uvicorn)..."
  exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
fi
