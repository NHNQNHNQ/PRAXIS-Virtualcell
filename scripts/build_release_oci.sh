#!/usr/bin/env bash
# Build one network-disabled OCI layout from an exact full wheel + wheelhouse.
set -euo pipefail

PRAXIS_REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PRAXIS_PYTHON_BIN="${PYTHON_BIN:-python3.13}"
PRAXIS_WHEELHOUSE="${1:?usage: build_release_oci.sh WHEELHOUSE OUTPUT.oci.tar}"
PRAXIS_OCI_OUTPUT="${2:?usage: build_release_oci.sh WHEELHOUSE OUTPUT.oci.tar}"
PRAXIS_PLATFORM="linux/arm64"
PRAXIS_PYTHON_IMAGE="python:3.13.14-slim-bookworm@sha256:9d7f287598e1a5a978c015ee176d8216435aaf335ed69ac3c38dd1bbb10e8d64"
PRAXIS_PYTHON_DIGEST="sha256:9d7f287598e1a5a978c015ee176d8216435aaf335ed69ac3c38dd1bbb10e8d64"
# Docker may retain a pulled digest only by image ID while still exposing the
# canonical RepoDigest through inspection. This is a lookup key only: the
# identity check below trusts RepoDigests, never `.Id`.
PRAXIS_PYTHON_LOCAL_LOOKUP="${PRAXIS_PYTHON_DIGEST}"
PRAXIS_BUILD_TMP="$(mktemp -d "${TMPDIR:-/tmp}/praxis-oci-build.XXXXXX")"
PRAXIS_BUILD_WHEELHOUSE="${PRAXIS_BUILD_TMP}/wheelhouse"

cleanup() {
  case "${PRAXIS_BUILD_TMP}" in
    */praxis-oci-build.*) rm -rf -- "${PRAXIS_BUILD_TMP}" ;;
    *) echo "refusing to remove unexpected build directory: ${PRAXIS_BUILD_TMP}" >&2 ;;
  esac
}
trap cleanup EXIT

case "${PRAXIS_WHEELHOUSE}" in
  /*) ;;
  *) echo "wheelhouse must be an absolute out-of-tree path" >&2; exit 1 ;;
esac
case "${PRAXIS_OCI_OUTPUT}" in
  /*) ;;
  *) echo "OCI output must be an absolute out-of-tree path" >&2; exit 1 ;;
esac

if [[ -n "$(git -C "${PRAXIS_REPO_ROOT}" status --porcelain=v1 --untracked-files=normal)" ]]; then
  echo "release OCI requires a clean committed worktree" >&2
  exit 1
fi
if [[ ! -d "${PRAXIS_WHEELHOUSE}" || -L "${PRAXIS_WHEELHOUSE}" ]]; then
  echo "wheelhouse must be a regular directory" >&2
  exit 1
fi
PRAXIS_WHEELHOUSE="$(cd "${PRAXIS_WHEELHOUSE}" && pwd -P)"
case "${PRAXIS_WHEELHOUSE}" in
  "${PRAXIS_REPO_ROOT}"|"${PRAXIS_REPO_ROOT}"/*) echo "wheelhouse must be outside the source repository" >&2; exit 1 ;;
esac
PRAXIS_OCI_PARENT="$(dirname "${PRAXIS_OCI_OUTPUT}")"
if [[ ! -d "${PRAXIS_OCI_PARENT}" || -L "${PRAXIS_OCI_PARENT}" ]]; then
  echo "OCI output parent must be a real existing directory" >&2
  exit 1
fi
PRAXIS_OCI_OUTPUT="$(cd "${PRAXIS_OCI_PARENT}" && pwd -P)/$(basename "${PRAXIS_OCI_OUTPUT}")"
case "${PRAXIS_OCI_OUTPUT}" in
  "${PRAXIS_REPO_ROOT}"|"${PRAXIS_REPO_ROOT}"/*) echo "OCI output must be outside the source repository" >&2; exit 1 ;;
esac
if [[ -e "${PRAXIS_OCI_OUTPUT}" || -L "${PRAXIS_OCI_OUTPUT}" ]]; then
  echo "refusing to overwrite OCI output" >&2
  exit 1
fi
if find "${PRAXIS_WHEELHOUSE}" -mindepth 1 -maxdepth 1 \( ! -type f -o -name '.*' \) -print -quit | grep -q .; then
  echo "wheelhouse must contain only visible regular files" >&2
  exit 1
fi

PRAXIS_DOCKER_HOST="${DOCKER_HOST:-}"
if [[ -n "${PRAXIS_DOCKER_HOST}" && "${PRAXIS_DOCKER_HOST}" != unix://* ]]; then
  echo "refusing non-local Docker endpoint" >&2
  exit 1
fi
PRAXIS_CONTEXT="$(docker context show)"
PRAXIS_CONTEXT_HOST="$(docker context inspect "${PRAXIS_CONTEXT}" --format '{{(index .Endpoints "docker").Host}}')"
if [[ "${PRAXIS_CONTEXT_HOST}" != unix://* ]]; then
  echo "refusing non-local Docker context" >&2
  exit 1
fi
PRAXIS_BUILDER="$(docker buildx ls --format '{{json .}}' | "${PRAXIS_PYTHON_BIN}" -c '
import json, sys
context, platform = sys.argv[1:]
rows = [json.loads(line) for line in sys.stdin if line.strip()]
current = [row for row in rows if row.get("Current") is True]
if not current or any(row != current[0] for row in current):
    raise SystemExit("exactly one current buildx builder is required")
row = current[0]
name = row.get("Name")
if not isinstance(name, str) or not name:
    raise SystemExit("current buildx builder has no name")
nodes = row.get("Nodes") or []
if row.get("Driver") != "docker" or len(nodes) != 1:
    raise SystemExit("current buildx builder is not bound to the local Docker context")
node = nodes[0]
if node.get("Endpoint") != context or node.get("Status") != "running":
    raise SystemExit("current buildx builder is not a running local Docker builder")
if platform not in (node.get("Platforms") or []):
    raise SystemExit(f"current buildx builder does not support {platform}")
print(name)
' "${PRAXIS_CONTEXT}" "${PRAXIS_PLATFORM}")"
PRAXIS_BASE_ARCH="$(docker image inspect "${PRAXIS_PYTHON_LOCAL_LOOKUP}" --format '{{.Architecture}}')"
PRAXIS_BASE_OS="$(docker image inspect "${PRAXIS_PYTHON_LOCAL_LOOKUP}" --format '{{.Os}}')"
PRAXIS_BASE_REFS="$(docker image inspect "${PRAXIS_PYTHON_LOCAL_LOOKUP}" --format '{{join .RepoDigests "\n"}}')"
if [[ "${PRAXIS_BASE_ARCH}" != arm64 || "${PRAXIS_BASE_OS}" != linux ]] || ! grep -Exq "(docker\.io/library/|index\.docker\.io/library/)?python@${PRAXIS_PYTHON_DIGEST}" <<<"${PRAXIS_BASE_REFS}"; then
  echo "required pinned Python base image RepoDigest/target platform is not present locally" >&2
  exit 1
fi

"${PRAXIS_PYTHON_BIN}" -c '
import json, pathlib, sys
manifest = json.loads((pathlib.Path(sys.argv[1]) / "wheelhouse-manifest.json").read_text())
if (
    manifest.get("schema_version") != "praxis.offline-wheelhouse.v1"
    or manifest.get("python_implementation") != "CPython"
    or manifest.get("python_minor") != "3.13"
    or manifest.get("target_profile") != "linux_arm64_cp313"
):
    raise SystemExit("OCI wheelhouse target profile must be linux_arm64_cp313")
' "${PRAXIS_WHEELHOUSE}"

mkdir -p "${PRAXIS_BUILD_WHEELHOUSE}" "$(dirname "${PRAXIS_OCI_OUTPUT}")"
cp -p "${PRAXIS_WHEELHOUSE}"/* "${PRAXIS_BUILD_WHEELHOUSE}/"
PRAXIS_GIT_SHA="$(git -C "${PRAXIS_REPO_ROOT}" rev-parse HEAD)"
PRAXIS_SOURCE_EPOCH="$(git -C "${PRAXIS_REPO_ROOT}" show -s --format=%ct HEAD)"
PRAXIS_PRODUCT_VERSION="$("${PRAXIS_PYTHON_BIN}" -c 'import pathlib,sys,tomllib; print(tomllib.loads(pathlib.Path(sys.argv[1]).read_text())["project"]["version"])' "${PRAXIS_REPO_ROOT}/pyproject.toml")"
"${PRAXIS_PYTHON_BIN}" -c \
  'import os,pathlib,sys; epoch=int(sys.argv[1]); root=pathlib.Path(sys.argv[2]); [os.utime(path,(epoch,epoch)) for path in [*root.iterdir(),root]]' \
  "${PRAXIS_SOURCE_EPOCH}" "${PRAXIS_BUILD_WHEELHOUSE}"

docker buildx build \
  --builder "${PRAXIS_BUILDER}" \
  --file "${PRAXIS_REPO_ROOT}/deploy/vc/Dockerfile.artifact" \
  --platform "${PRAXIS_PLATFORM}" \
  --network none \
  --pull=false \
  --provenance=false \
  --sbom=false \
  --build-context "wheelhouse=${PRAXIS_BUILD_WHEELHOUSE}" \
  --build-arg "PYTHON_IMAGE=${PRAXIS_PYTHON_IMAGE}" \
  --build-arg "GIT_SHA=${PRAXIS_GIT_SHA}" \
  --build-arg "PRODUCT_VERSION=${PRAXIS_PRODUCT_VERSION}" \
  --build-arg "SOURCE_DATE_EPOCH=${PRAXIS_SOURCE_EPOCH}" \
  --output "type=oci,dest=${PRAXIS_OCI_OUTPUT},tar=true" \
  "${PRAXIS_REPO_ROOT}"
