#!/usr/bin/env bash
# Start the local offline service after installing the api extra.
set -euo pipefail
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
export PRAXIS_VIRTUALCELL_MODE=offline
echo "PRAXIS-VirtualCell is running."
echo "Local website: http://${HOST}:${PORT}"
echo "Mode: OFFLINE · LLM: disabled · Demo data: examples/"
exec praxis-vc serve --host "${HOST}" --port "${PORT}"
