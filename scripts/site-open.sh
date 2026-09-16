#!/usr/bin/env bash
set -euo pipefail
python3 -m webbrowser "http://localhost:${PORT:-5173}/site/"
