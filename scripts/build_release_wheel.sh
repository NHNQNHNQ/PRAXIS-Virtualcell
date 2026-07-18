#!/usr/bin/env bash
# Build the reproducible full local release wheel: Python runtime + packaged React UI.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3.13}"
OUTPUT_DIR="${1:-${ROOT_DIR}/dist}"
RELEASE_TMP="$(mktemp -d "${TMPDIR:-/tmp}/praxis-wheel-build.XXXXXX")"
BUILD_ENV="${RELEASE_TMP}/build-env"
SOURCE_DIR="${RELEASE_TMP}/source"

case "${OUTPUT_DIR}" in
  /*) ;;
  *) OUTPUT_DIR="${ROOT_DIR}/${OUTPUT_DIR}" ;;
esac

cleanup() {
  case "${RELEASE_TMP}" in
    */praxis-wheel-build.*) rm -rf -- "${RELEASE_TMP}" ;;
    *) echo "refusing to remove unexpected build directory: ${RELEASE_TMP}" >&2 ;;
  esac
}
trap cleanup EXIT

if ! git -C "${ROOT_DIR}" diff --quiet || ! git -C "${ROOT_DIR}" diff --cached --quiet; then
  echo "release wheel requires a committed tracked worktree" >&2
  exit 1
fi

mkdir -p "${SOURCE_DIR}"
git -C "${ROOT_DIR}" archive --format=tar HEAD | tar -xf - -C "${SOURCE_DIR}"

"${PYTHON_BIN}" -m venv "${BUILD_ENV}"
"${BUILD_ENV}/bin/python" -m pip install \
  --only-binary=:all: \
  --require-hashes \
  --requirement "${SOURCE_DIR}/requirements/build-py313.lock"

cd "${SOURCE_DIR}/praxis_vc_react"
npm ci
npm run build

cd "${SOURCE_DIR}"
mkdir -p "${OUTPUT_DIR}"
export SOURCE_DATE_EPOCH="$(git -C "${ROOT_DIR}" log -1 --format=%ct)"
export PRAXIS_VC_REQUIRE_STATIC=1
"${BUILD_ENV}/bin/python" -m pip wheel \
  . \
  --no-build-isolation \
  --no-deps \
  --no-cache-dir \
  --wheel-dir "${OUTPUT_DIR}"
