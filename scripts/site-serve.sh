#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-5173}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.."; pwd)/site"

echo "Serving static site from: $ROOT"
echo "URL: http://localhost:${PORT}"
echo "Tip: In the backend .env set FRONTEND_ORIGINS=[\"http://localhost:${PORT}\",\"http://127.0.0.1:${PORT}\"]"
echo

cd "$ROOT"
python3 -m http.server "${PORT}"
