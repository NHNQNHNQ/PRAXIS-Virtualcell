#!/usr/bin/env bash
# Build one deterministic P30A source archive from a clean exact Git HEAD.
set -euo pipefail

if [[ -n "${PRAXIS_SOURCE_ARCHIVE_ROOT:-}" ]]; then
  ROOT_DIR="$(cd "${PRAXIS_SOURCE_ARCHIVE_ROOT}" && pwd -P)"
else
  ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
fi
PYTHON_BIN="${PYTHON_BIN:-python3.13}"
SOURCE_REF="${PRAXIS_SOURCE_ARCHIVE_REF:-HEAD}"

fail() {
  echo "$*" >&2
  exit 1
}

if [[ $# -ne 1 ]]; then
  fail "usage: $0 ABSOLUTE_OUTPUT_ARCHIVE"
fi

[[ "$(git -C "${ROOT_DIR}" rev-parse --show-toplevel)" == "${ROOT_DIR}" ]] \
  || fail "source archive builder must run from the repository root"
[[ -z "$(git -C "${ROOT_DIR}" status --porcelain=v1 --untracked-files=normal)" ]] \
  || fail "source archive requires a clean committed worktree"
SOURCE_SHA="$(git -C "${ROOT_DIR}" rev-parse HEAD)"
if [[ "${SOURCE_REF}" == "HEAD" ]]; then
  SOURCE_REF="${SOURCE_SHA}"
else
  [[ "${SOURCE_REF}" =~ ^[0-9a-f]{40}$ ]] || fail "source archive reference must be an exact SHA"
  [[ "${SOURCE_REF}" == "${SOURCE_SHA}" ]] || fail "source archive reference no longer matches HEAD"
fi

SOURCE_EPOCH="$(git -C "${ROOT_DIR}" show -s --format=%ct "${SOURCE_REF}")"
[[ "${SOURCE_EPOCH}" =~ ^[0-9]+$ ]] || fail "source commit timestamp is invalid"
PRODUCT_VERSION="$("${PYTHON_BIN}" - "${ROOT_DIR}" "${SOURCE_REF}" <<'PY'
from __future__ import annotations

import re
import subprocess
import sys
import tomllib

root, source_ref = sys.argv[1:]
project = tomllib.loads(
    subprocess.check_output(["git", "-C", root, "show", f"{source_ref}:pyproject.toml"]).decode("utf-8")
)
version = project.get("project", {}).get("version")
if not isinstance(version, str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]*", version) is None:
    raise SystemExit("source pyproject.toml has an unsafe project version")
print(version)
PY
)"
ARCHIVE_NAME="praxis-virtualcell-${PRODUCT_VERSION}.tar.gz"

OUTPUT_PATH="$1"
case "${OUTPUT_PATH}" in
  /*) ;;
  *) fail "source archive output must be an absolute out-of-tree path" ;;
esac

[[ "$(basename "${OUTPUT_PATH}")" == "${ARCHIVE_NAME}" ]] \
  || fail "source archive filename must be ${ARCHIVE_NAME}"
OUTPUT_DIR="$(dirname "${OUTPUT_PATH}")"
if [[ ! -d "${OUTPUT_DIR}" ]]; then
  fail "source archive output parent must be a real directory"
fi
OUTPUT_DIR="$(cd "${OUTPUT_DIR}" && pwd -P)"
OUTPUT_PATH="${OUTPUT_DIR}/${ARCHIVE_NAME}"
case "${OUTPUT_PATH}" in
  "${ROOT_DIR}"|"${ROOT_DIR}"/*) fail "source archive output must be outside the source repository" ;;
esac
GIT_DIR="$(git -C "${ROOT_DIR}" rev-parse --absolute-git-dir)"
GIT_DIR="$(cd "${GIT_DIR}" && pwd -P)"
case "${OUTPUT_PATH}" in
  "${GIT_DIR}"|"${GIT_DIR}"/*) fail "source archive output cannot be inside Git metadata" ;;
esac
[[ ! -e "${OUTPUT_PATH}" && ! -L "${OUTPUT_PATH}" ]] \
  || fail "source archive output already exists: ${OUTPUT_PATH}"

TAR_PATH=""
ARCHIVE_TMP=""
cleanup() {
  [[ -z "${TAR_PATH}" ]] || rm -f -- "${TAR_PATH}"
  [[ -z "${ARCHIVE_TMP}" ]] || rm -f -- "${ARCHIVE_TMP}"
}
trap cleanup EXIT

TAR_PATH="$(mktemp "${OUTPUT_DIR}/.${ARCHIVE_NAME}.tar.XXXXXX")"
ARCHIVE_TMP="$(mktemp "${OUTPUT_DIR}/.${ARCHIVE_NAME}.tmp.XXXXXX")"
PREFIX="praxis-virtualcell-${PRODUCT_VERSION}/"
git -C "${ROOT_DIR}" archive --format=tar --prefix="${PREFIX}" "${SOURCE_REF}" > "${TAR_PATH}"

"${PYTHON_BIN}" - "${TAR_PATH}" "${ARCHIVE_TMP}" "${SOURCE_EPOCH}" "${PREFIX}" <<'PY'
from __future__ import annotations

import gzip
import os
import sys
import tarfile
from pathlib import PurePosixPath

tar_path, archive_path, epoch_text, prefix = sys.argv[1:]
epoch = int(epoch_text)
names: set[str] = set()
with tarfile.open(tar_path, "r:") as source, open(archive_path, "wb") as destination:
    with gzip.GzipFile(filename="", mode="wb", fileobj=destination, mtime=epoch, compresslevel=9) as compressed:
        with tarfile.open(fileobj=compressed, mode="w", format=tarfile.GNU_FORMAT) as archive:
            for member in source:
                if member.name == prefix[:-1] and member.isdir():
                    continue
                path = PurePosixPath(member.name)
                if member.issym() or member.islnk():
                    raise SystemExit(f"Git archive contains an unsupported link: {member.name}")
                if (
                    not member.name.startswith(prefix)
                    or member.name in names
                    or path.is_absolute()
                    or any(part in {"", ".", "..", ".DS_Store"} or part.startswith("._") for part in path.parts)
                    or not (member.isfile() or member.isdir())
                ):
                    raise SystemExit("Git archive contains an unsafe source member")
                names.add(member.name)
                if member.isdir():
                    continue
                stream = source.extractfile(member)
                if stream is None:
                    raise SystemExit(f"Git archive member is unreadable: {member.name}")
                normalized = tarfile.TarInfo(member.name)
                normalized.size = member.size
                normalized.mode = member.mode & 0o777
                normalized.mtime = epoch
                normalized.uid = normalized.gid = 0
                normalized.uname = normalized.gname = ""
                archive.addfile(normalized, stream)
required = {prefix + "pyproject.toml", prefix + "praxis_virtualcell/__init__.py"}
if not required.issubset(names):
    raise SystemExit("Git archive lacks required release source members")
os.chmod(archive_path, 0o644)
os.utime(archive_path, (epoch, epoch))
PY

# link(2) publishes without replacing a concurrent or pre-existing target.
[[ "$(git -C "${ROOT_DIR}" rev-parse HEAD)" == "${SOURCE_REF}" ]] \
  || fail "source archive reference changed before publish"
[[ -z "$(git -C "${ROOT_DIR}" status --porcelain=v1 --untracked-files=normal)" ]] \
  || fail "source archive worktree changed before publish"
ln -- "${ARCHIVE_TMP}" "${OUTPUT_PATH}" \
  || fail "source archive output already exists or cannot be safely published"
rm -f -- "${ARCHIVE_TMP}"
ARCHIVE_TMP=""
rm -f -- "${TAR_PATH}"
TAR_PATH=""

printf '%s\n' "${OUTPUT_PATH}"
