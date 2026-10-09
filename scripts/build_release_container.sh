#!/usr/bin/env bash
# Build the release container from one committed candidate identity.
set -euo pipefail

PRAXIS_REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PRAXIS_IMAGE_TAG="${1:-praxis-virtualcell:local}"

unexpected=()
while IFS= read -r line; do
  case "${line}" in
    "?? .claude/"|"?? string.jpeg") ;;
    "") ;;
    *) unexpected+=("${line}") ;;
  esac
done < <(git -C "${PRAXIS_REPO_ROOT}" status --porcelain=v1 --untracked-files=normal)

if ((${#unexpected[@]})); then
  printf '%s\n' "release container requires a committed worktree:" >&2
  printf '  %s\n' "${unexpected[@]}" >&2
  exit 1
fi

PRAXIS_GIT_SHA="$(git -C "${PRAXIS_REPO_ROOT}" rev-parse HEAD)"
PRAXIS_SOURCE_EPOCH="$(git -C "${PRAXIS_REPO_ROOT}" show -s --format=%ct HEAD)"

exec docker build \
  --file "${PRAXIS_REPO_ROOT}/deploy/vc/Dockerfile" \
  --tag "${PRAXIS_IMAGE_TAG}" \
  --build-arg "GIT_SHA=${PRAXIS_GIT_SHA}" \
  --build-arg "SOURCE_DATE_EPOCH=${PRAXIS_SOURCE_EPOCH}" \
  "${PRAXIS_REPO_ROOT}"
