#!/usr/bin/env bash
# Build the reproducible full local release wheel: Python runtime + packaged React UI.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3.13}"
OUTPUT_DIR="${1:-${ROOT_DIR}/dist}"

cd "${ROOT_DIR}/praxis_vc_react"
npm ci
npm run build

cd "${ROOT_DIR}"
mkdir -p "${OUTPUT_DIR}"
export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-$(git log -1 --format=%ct)}"
export PRAXIS_VC_REQUIRE_STATIC=1
"${PYTHON_BIN}" -m pip wheel . --no-deps --no-cache-dir --wheel-dir "${OUTPUT_DIR}"
