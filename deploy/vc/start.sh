#!/usr/bin/env bash
# 本地起 PRAXIS-VirtualCell(offline)。需先 pip install '.[api]'。
set -euo pipefail
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
export PRAXIS_VIRTUALCELL_MODE=offline
echo "PRAXIS-VirtualCell is running."
echo "Local website: http://${HOST}:${PORT}"
echo "Mode: OFFLINE · LLM: disabled · Demo data: examples/"
exec praxis-vc serve --host "${HOST}" --port "${PORT}"
