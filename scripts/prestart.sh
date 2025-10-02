#!/usr/bin/env bash
set -euo pipefail

echo "[prestart] ENV=${ENV:-} DATABASE_URL=${DATABASE_URL:-<empty>}"

# Skip migrations when DATABASE_URL is empty or an in-memory sqlite URL
if [ -z "${DATABASE_URL:-}" ]; then
  echo "[prestart] DATABASE_URL not set; skipping migrations."
else
  case "$DATABASE_URL" in
    sqlite+aiosqlite:///:memory:*|sqlite:///:memory:*)
      echo "[prestart] In-memory SQLite detected; skipping migrations."
      ;;
    *)
      echo "[prestart] Running Alembic migrations..."
      alembic upgrade head
      ;;
  esac
fi

echo "[prestart] Starting app..."
