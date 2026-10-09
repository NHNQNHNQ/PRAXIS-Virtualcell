#!/usr/bin/env bash
# Build the reproducible full local release wheel: Python runtime + packaged React UI.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3.13}"
if [[ $# -ne 1 ]]; then
  echo "usage: $0 ABSOLUTE_OUTPUT_DIRECTORY" >&2
  exit 1
fi
OUTPUT_DIR="$1"
RELEASE_TMP="$(mktemp -d "${TMPDIR:-/tmp}/praxis-wheel-build.XXXXXX")"
BUILD_ENV="${RELEASE_TMP}/build-env"
SOURCE_DIR="${RELEASE_TMP}/source"
BUILD_WHEELHOUSE="${RELEASE_TMP}/build-wheelhouse"
RELEASE_OFFLINE="${PRAXIS_RELEASE_OFFLINE:-1}"

case "${OUTPUT_DIR}" in
  /*) ;;
  *) echo "release wheel output must be an absolute out-of-tree directory" >&2; exit 1 ;;
esac
OUTPUT_PARENT="$(dirname "${OUTPUT_DIR}")"
if [[ ! -d "${OUTPUT_PARENT}" ]]; then
  echo "release wheel output parent must be a real existing directory" >&2
  exit 1
fi
OUTPUT_DIR="$(cd "${OUTPUT_PARENT}" && pwd -P)/$(basename "${OUTPUT_DIR}")"
case "${OUTPUT_DIR}" in
  "${ROOT_DIR}"|"${ROOT_DIR}"/*) echo "release wheel output must be outside the source repository" >&2; exit 1 ;;
esac

cleanup() {
  case "${RELEASE_TMP}" in
    */praxis-wheel-build.*) rm -rf -- "${RELEASE_TMP}" ;;
    *) echo "refusing to remove unexpected build directory: ${RELEASE_TMP}" >&2 ;;
  esac
}
trap cleanup EXIT

if [[ -n "$(git -C "${ROOT_DIR}" status --porcelain=v1 --untracked-files=normal)" ]]; then
  echo "release wheel requires a clean committed worktree" >&2
  exit 1
fi

if [[ -L "${OUTPUT_DIR}" ]] || { [[ -e "${OUTPUT_DIR}" ]] && [[ ! -d "${OUTPUT_DIR}" || -n "$(find "${OUTPUT_DIR}" -mindepth 1 -maxdepth 1 -print -quit)" ]]; }; then
  echo "release wheel output must be absent or empty" >&2
  exit 1
fi

mkdir -p "${SOURCE_DIR}"
git -C "${ROOT_DIR}" archive --format=tar HEAD | tar -xf - -C "${SOURCE_DIR}"
export SOURCE_DATE_EPOCH="$(git -C "${ROOT_DIR}" log -1 --format=%ct)"

"${PYTHON_BIN}" - <<'PY'
import sys

if sys.implementation.name != "cpython" or sys.version_info[:2] != (3, 13):
    raise SystemExit("P30A release wheel build requires CPython 3.13")
PY
"${PYTHON_BIN}" -m venv "${BUILD_ENV}"
case "${RELEASE_OFFLINE}" in
  1)
    PRAXIS_PIP_CACHE_ROOT="${PRAXIS_PIP_CACHE_ROOT:-$("${PYTHON_BIN}" -m pip cache dir)}"
    PRAXIS_NPM_CACHE_ROOT="${PRAXIS_NPM_CACHE_ROOT:-$(npm config get cache)}"
    [[ -d "${PRAXIS_PIP_CACHE_ROOT}" ]] || { echo "offline pip cache is unavailable" >&2; exit 1; }
    [[ -d "${PRAXIS_NPM_CACHE_ROOT}" ]] || { echo "offline npm cache is unavailable" >&2; exit 1; }
    "${PYTHON_BIN}" "${SOURCE_DIR}/scripts/release_candidate.py" materialize-wheelhouse \
      --lock "${SOURCE_DIR}/requirements/build-py313.lock" \
      --cache-root "${PRAXIS_PIP_CACHE_ROOT}" \
      --output "${BUILD_WHEELHOUSE}" \
      --source-date-epoch "${SOURCE_DATE_EPOCH}" \
      --target-profile macos_arm64_cp313
    "${BUILD_ENV}/bin/python" -m pip install \
      --no-index \
      --find-links "${BUILD_WHEELHOUSE}" \
      --only-binary=:all: \
      --require-hashes \
      --requirement "${SOURCE_DIR}/requirements/build-py313.lock"
    ;;
  0)
    "${BUILD_ENV}/bin/python" -m pip install \
      --only-binary=:all: \
      --require-hashes \
      --requirement "${SOURCE_DIR}/requirements/build-py313.lock"
    ;;
  *)
    echo "PRAXIS_RELEASE_OFFLINE must be exactly 0 or 1" >&2
    exit 1
    ;;
esac

cd "${SOURCE_DIR}/praxis_vc_react"
if [[ "${RELEASE_OFFLINE}" == "1" ]]; then
  npm ci --offline --no-audit --no-fund --cache "${PRAXIS_NPM_CACHE_ROOT}"
else
  npm ci
fi
npm run build

cd "${SOURCE_DIR}"
mkdir -p "${OUTPUT_DIR}"
export PRAXIS_VC_REQUIRE_STATIC=1
"${BUILD_ENV}/bin/python" -m pip wheel \
  . \
  --no-build-isolation \
  --no-deps \
  --no-cache-dir \
  --wheel-dir "${OUTPUT_DIR}"
