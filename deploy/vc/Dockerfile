# syntax=docker/dockerfile:1.7

# Multi-platform index digests are pinned so amd64 CI and arm64 developer
# machines resolve the same reviewed release of each official base image.
ARG NODE_IMAGE=node:24-alpine@sha256:a0b9bf06e4e6193cf7a0f58816cc935ff8c2a908f81e6f1a95432d679c54fbfd
ARG PYTHON_IMAGE=python:3.13.14-slim-trixie@sha256:9662417aace5ae7b8e2609cce472b72a8958e134ba372808abe9cc1a0c0125e6

FROM ${NODE_IMAGE} AS frontend

WORKDIR /src/praxis_vc_react
COPY praxis_vc_react/package.json praxis_vc_react/package-lock.json ./
RUN npm ci
COPY praxis_vc_react/ ./
RUN npm run build


FROM ${PYTHON_IMAGE} AS wheel-builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /src

COPY pyproject.toml setup.py MANIFEST.in README.md ./
COPY requirements/build-py313.lock ./requirements/build-py313.lock
COPY requirements/runtime-py313.lock ./requirements/runtime-py313.lock
COPY praxis_virtualcell ./praxis_virtualcell
COPY praxis_vc_api ./praxis_vc_api
COPY praxis_vc_web ./praxis_vc_web
COPY --from=frontend /src/praxis_vc_react/dist ./praxis_vc_react/dist

# A candidate epoch is mandatory so the container wheel uses the same release
# timestamp contract as scripts/build_release_wheel.sh.
ARG SOURCE_DATE_EPOCH
ENV SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH} \
    PRAXIS_VC_REQUIRE_STATIC=1

# Install the exact build backend from its hash lock. Download every runtime
# dependency as a wheel, then build without a second, implicit PEP 517 resolver.
RUN python -c \
        "import os; value = os.environ.get('SOURCE_DATE_EPOCH', ''); raise SystemExit(0 if value.isdigit() and int(value) >= 315532800 else 'SOURCE_DATE_EPOCH must be a valid release epoch')" \
    && python -m pip download \
        --only-binary=:all: \
        --require-hashes \
        --requirement requirements/build-py313.lock \
        --dest /wheelhouse \
    && python -m pip install \
        --no-index \
        --find-links=/wheelhouse \
        --require-hashes \
        --requirement requirements/build-py313.lock \
    && python -m pip download \
        --only-binary=:all: \
        --require-hashes \
        --requirement requirements/runtime-py313.lock \
        --dest /wheelhouse \
    && python -m pip wheel \
        . \
        --no-deps \
        --no-build-isolation \
        --no-cache-dir \
        --wheel-dir /wheelhouse


FROM ${PYTHON_IMAGE} AS installer

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

COPY --from=wheel-builder /wheelhouse /wheelhouse
COPY requirements/runtime-py313.lock /tmp/runtime-py313.lock

# The installer resolves nothing from an index. Only its populated virtualenv
# is copied onward, so the final image does not retain the temporary wheelhouse.
RUN --network=none python -m venv /opt/venv \
    && /opt/venv/bin/python -m pip install \
        --no-index \
        --find-links=/wheelhouse \
        --require-hashes \
        --requirement /tmp/runtime-py313.lock \
    && /opt/venv/bin/python -m pip install \
        --no-index \
        --no-deps \
        /wheelhouse/praxis_virtualcell-*.whl \
    && /opt/venv/bin/python -m pip check \
    && /opt/venv/bin/praxis-vc --version \
    && /opt/venv/bin/python -c \
        "from importlib.resources import files; index = files('praxis_vc_api').joinpath('static', 'index.html'); raise SystemExit(0 if index.is_file() else 1)"


FROM ${PYTHON_IMAGE} AS runtime

ARG GIT_SHA
LABEL org.opencontainers.image.title="PRAXIS-VirtualCell" \
      org.opencontainers.image.description="Offline-first PRAXIS VirtualCell CLI, API, and web UI" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.revision="${GIT_SHA}"

ENV GIT_SHA=${GIT_SHA} \
    PATH="/opt/venv/bin:${PATH}" \
    NO_PROXY="127.0.0.1,localhost" \
    no_proxy="127.0.0.1,localhost" \
    PRAXIS_VIRTUALCELL_MODE=offline \
    PRAXIS_VC_RUNS=/var/lib/praxis-vc/runs \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY --from=installer /opt/venv /opt/venv

RUN python -c \
        "import os, re; value = os.environ.get('GIT_SHA', ''); raise SystemExit(0 if re.fullmatch(r'[0-9a-f]{40}', value) else 'GIT_SHA must be a full 40-character commit ID')" \
    && groupadd --gid 10001 praxisvc \
    && useradd --uid 10001 --gid 10001 --create-home --shell /usr/sbin/nologin praxisvc \
    && mkdir -p /app /var/lib/praxis-vc/runs \
    && chown -R praxisvc:praxisvc /app /var/lib/praxis-vc

WORKDIR /app
USER 10001:10001
VOLUME ["/var/lib/praxis-vc/runs"]
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=6 \
    CMD ["python", "-c", "import json, sys, urllib.request; opener = urllib.request.build_opener(urllib.request.ProxyHandler({})); response = opener.open('http://127.0.0.1:8000/api/health', timeout=2); payload = json.load(response); sys.exit(0 if response.status == 200 and payload.get('status') == 'ok' else 1)"]

CMD ["praxis-vc", "serve", "--host", "0.0.0.0", "--port", "8000"]
