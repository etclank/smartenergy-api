#!/usr/bin/env bash
set -euo pipefail

echo "[prestart] ENV=${ENV:-} DATABASE_URL=${DATABASE_URL:-<empty>} SEED_DEMO=${SEED_DEMO:-1}"

# Skip if no DB URL
if [ -z "${DATABASE_URL:-}" ]; then
  echo "[prestart] DATABASE_URL not set; skipping migrations & seed."
else
  case "$DATABASE_URL" in
    sqlite+aiosqlite:///:memory:*|sqlite:///:memory:*)
      echo "[prestart] In-memory SQLite; skipping migrations & seed."
      ;;
    *)
      echo "[prestart] Running Alembic migrations..."
      alembic upgrade head

      if [ "${SEED_DEMO:-1}" = "1" ]; then
        echo "[prestart] Seeding demo data..."
        # Use -m so imports work relative to /app
        if ! python -m scripts.seed_demo; then
          echo "[prestart] Seeding failed (non-fatal); continuing."
        fi
      else
        echo "[prestart] SEED_DEMO=0; skipping demo seed."
      fi
      ;;
  esac
fi

echo "[prestart] Starting app..."
