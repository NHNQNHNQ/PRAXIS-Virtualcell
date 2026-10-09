"""Opt-in smoke tests for the built Linux release image.

Run explicitly with::

    PRAXIS_RUN_DOCKER_SMOKE=1 pytest \
      praxis_virtualcell/tests/test_linux_docker_smoke.py \
      --run-integration -o addopts='' -q -ra

The host may be Linux or Docker Desktop; the artifact under test is always a
Linux container. Every image/container name is unique, labelled, and cleaned
only after its ownership and immutable ID have been verified.
"""

from __future__ import annotations

import base64
import json
import os
import re
import shutil
import subprocess
import time
import tomllib
import uuid
from dataclasses import dataclass
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ENABLED = os.environ.get("PRAXIS_RUN_DOCKER_SMOKE") == "1"
_RUN_ID = uuid.uuid4().hex
_OWNER_LABEL = "io.praxis-virtualcell.smoke-run"
_IMAGE_TAG = f"praxis-vc-smoke:{_RUN_ID}"
_CONTAINER_NAME = f"praxis-vc-smoke-{_RUN_ID}"

_QUICK_TIMEOUT = 60
_BUILD_TIMEOUT = 1200
_START_TIMEOUT = 90

_CONTAINER_HTTP_PROBE = """
import base64
import http.client
import json
import sys

method, path, payload = sys.argv[1:4]
connection = http.client.HTTPConnection("127.0.0.1", 8000, timeout=10)
body = payload.encode("utf-8") if payload else None
headers = {"Content-Type": "application/json"} if body else {}
connection.request(method, path, body=body, headers=headers)
response = connection.getresponse()
content = response.read()
print(json.dumps({
    "status": response.status,
    "content_type": response.getheader("content-type", ""),
    "body": base64.b64encode(content).decode("ascii"),
}))
"""

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _ENABLED,
        reason="set PRAXIS_RUN_DOCKER_SMOKE=1 to build and run the Linux release image",
    ),
]


@dataclass(frozen=True)
class BuiltImage:
    tag: str
    image_id: str
    git_sha: str
    product_version: str


@dataclass(frozen=True)
class RunningContainer:
    container_id: str
    image: BuiltImage


@dataclass(frozen=True)
class ContainerResponse:
    status: int
    content_type: str
    body: bytes


def _run(
    command: list[str],
    *,
    cwd: Path | None = None,
    timeout: int = _QUICK_TIMEOUT,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _inspect(kind: str, reference: str) -> dict | None:
    command = ["docker"]
    if kind == "image":
        command.extend(["image", "inspect"])
    else:
        command.append("inspect")
    result = _run([*command, reference])
    if result.returncode != 0:
        diagnostic = f"{result.stdout}\n{result.stderr}".lower()
        if "no such" in diagnostic or "not found" in diagnostic:
            return None
        raise AssertionError(f"docker {kind} inspect failed for {reference}: {result.stderr}")
    documents = json.loads(result.stdout)
    return documents[0] if documents else None


def _owned(document: dict | None, immutable_id: str) -> bool:
    if document is None or document.get("Id") != immutable_id:
        return False
    labels = document.get("Config", {}).get("Labels") or document.get("Labels") or {}
    return labels.get(_OWNER_LABEL) == _RUN_ID


def _remove_owned_container(reference: str) -> None:
    document = _inspect("container", reference)
    if document is None:
        return
    container_id = document["Id"]
    assert _owned(document, container_id), (
        f"refusing to remove unowned container reference: {reference}"
    )
    removed = _run(["docker", "rm", "--force", "--volumes", container_id])
    assert removed.returncode == 0, f"owned container cleanup failed: {removed.stderr}"


def _remove_owned_image(reference: str) -> None:
    document = _inspect("image", reference)
    if document is None:
        return
    image_id = document["Id"]
    assert _owned(document, image_id), f"refusing to remove unowned image reference: {reference}"
    removed = _run(["docker", "image", "rm", "--no-prune", image_id])
    assert removed.returncode == 0, f"owned image cleanup failed: {removed.stderr}"


def _container_http(
    container_id: str,
    path: str,
    *,
    data: dict | None = None,
) -> ContainerResponse:
    assert path.startswith("/") and "://" not in path, f"invalid container path: {path!r}"
    payload = "" if data is None else json.dumps(data, separators=(",", ":"))
    result = _run(
        [
            "docker",
            "exec",
            container_id,
            "python",
            "-c",
            _CONTAINER_HTTP_PROBE,
            "GET" if data is None else "POST",
            path,
            payload,
        ]
    )
    assert result.returncode == 0, (
        f"container HTTP probe failed for {path}:\n"
        f"stdout:\n{result.stdout[-2000:]}\nstderr:\n{result.stderr[-2000:]}"
    )
    document = json.loads(result.stdout)
    return ContainerResponse(
        status=int(document["status"]),
        content_type=str(document["content_type"]),
        body=base64.b64decode(document["body"], validate=True),
    )


def _container_json(
    container_id: str,
    path: str,
    *,
    data: dict | None = None,
) -> tuple[int, dict]:
    response = _container_http(container_id, path, data=data)
    return response.status, json.loads(response.body.decode("utf-8"))


def _wait_for_health(container_id: str, *, timeout: int = _START_TIMEOUT) -> dict:
    deadline = time.monotonic() + timeout
    last_error = "service did not respond"
    while time.monotonic() < deadline:
        try:
            status, payload = _container_json(container_id, "/api/health")
            if status == 200 and payload.get("status") == "ok":
                return payload
            last_error = f"HTTP {status}: {payload}"
        except (AssertionError, OSError, ValueError) as error:
            last_error = repr(error)
        time.sleep(1)
    raise AssertionError(f"container health timeout: {last_error}")


@pytest.fixture(scope="module")
def docker_daemon() -> None:
    assert shutil.which("docker"), "PRAXIS_RUN_DOCKER_SMOKE=1 but docker CLI is unavailable"
    configured_host = os.environ.get("DOCKER_HOST", "")
    assert not configured_host or configured_host.startswith("unix://"), (
        f"refusing to send the release build to non-local DOCKER_HOST={configured_host!r}"
    )

    context = _run(["docker", "context", "show"])
    assert context.returncode == 0, context.stderr
    context_name = context.stdout.strip()
    inspected_context = _run(["docker", "context", "inspect", context_name])
    assert inspected_context.returncode == 0, inspected_context.stderr
    context_document = json.loads(inspected_context.stdout)[0]
    endpoint = context_document["Endpoints"]["docker"]["Host"]
    assert endpoint.startswith("unix://"), (
        f"refusing to send the release build to non-local Docker endpoint={endpoint!r}"
    )

    result = _run(["docker", "info"], timeout=_QUICK_TIMEOUT)
    assert result.returncode == 0, (
        "PRAXIS_RUN_DOCKER_SMOKE=1 but Docker daemon is unavailable:\n"
        f"{result.stderr[-4000:]}"
    )


@pytest.fixture(scope="module")
def docker_image(docker_daemon: None, request: pytest.FixtureRequest) -> BuiltImage:
    request.addfinalizer(lambda: _remove_owned_image(_IMAGE_TAG))

    status = _run(
        ["git", "status", "--porcelain=v1", "--untracked-files=normal"],
        cwd=_REPO_ROOT,
    )
    assert status.returncode == 0, status.stderr
    protected_untracked = {"?? .claude/", "?? string.jpeg"}
    unexpected = [line for line in status.stdout.splitlines() if line not in protected_untracked]
    assert not unexpected, (
        "release image requires a committed worktree; unexpected status entries: "
        f"{unexpected}"
    )

    git_sha_result = _run(["git", "rev-parse", "HEAD"], cwd=_REPO_ROOT)
    assert git_sha_result.returncode == 0, git_sha_result.stderr
    git_sha = git_sha_result.stdout.strip()

    epoch_result = _run(["git", "show", "-s", "--format=%ct", "HEAD"], cwd=_REPO_ROOT)
    assert epoch_result.returncode == 0, epoch_result.stderr
    source_date_epoch = epoch_result.stdout.strip()

    config = tomllib.loads((_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    product_version = config["project"]["version"]

    build = _run(
        [
            "docker",
            "build",
            "--file",
            "deploy/vc/Dockerfile",
            "--tag",
            _IMAGE_TAG,
            "--label",
            f"{_OWNER_LABEL}={_RUN_ID}",
            "--build-arg",
            f"GIT_SHA={git_sha}",
            "--build-arg",
            f"SOURCE_DATE_EPOCH={source_date_epoch}",
            ".",
        ],
        cwd=_REPO_ROOT,
        timeout=_BUILD_TIMEOUT,
    )
    assert build.returncode == 0, (
        f"docker build failed (stdout):\n{build.stdout[-6000:]}\n"
        f"docker build failed (stderr):\n{build.stderr[-6000:]}"
    )

    document = _inspect("image", _IMAGE_TAG)
    assert document is not None, "built image cannot be inspected"
    image_id = document["Id"]
    assert _owned(document, image_id), "built image is missing its unique ownership label"

    return BuiltImage(_IMAGE_TAG, image_id, git_sha, product_version)


@pytest.fixture(scope="module")
def running_container(
    docker_image: BuiltImage,
    request: pytest.FixtureRequest,
) -> RunningContainer:
    request.addfinalizer(lambda: _remove_owned_container(_CONTAINER_NAME))

    started = _run(
        [
            "docker",
            "run",
            "--detach",
            "--name",
            _CONTAINER_NAME,
            "--label",
            f"{_OWNER_LABEL}={_RUN_ID}",
            "--network",
            "none",
            docker_image.tag,
        ]
    )
    assert started.returncode == 0, started.stderr
    container_id = started.stdout.strip()
    assert container_id, "docker run returned no container ID"

    document = _inspect("container", container_id)
    assert _owned(document, container_id), "container is missing its unique ownership label"
    assert document and document["HostConfig"]["NetworkMode"] == "none"

    running = RunningContainer(container_id, docker_image)
    try:
        _wait_for_health(running.container_id)
    except AssertionError as error:
        logs = _run(["docker", "logs", container_id])
        raise AssertionError(
            f"{error}\ncontainer stdout:\n{logs.stdout[-4000:]}\n"
            f"container stderr:\n{logs.stderr[-4000:]}"
        ) from error
    return running


def test_image_metadata_and_runtime_contract(docker_image: BuiltImage) -> None:
    document = _inspect("image", docker_image.image_id)
    assert document is not None
    config = document["Config"]
    assert config["User"] == "10001:10001"
    assert config["Labels"]["org.opencontainers.image.revision"] == docker_image.git_sha
    assert config["Healthcheck"]["Test"][0] == "CMD"
    assert config["Env"]
    assert "PRAXIS_VC_RUNS=/var/lib/praxis-vc/runs" in config["Env"]


def test_container_is_non_root_and_runs_installed_wheel(running_container: RunningContainer) -> None:
    user = _run(["docker", "exec", running_container.container_id, "id", "-u"])
    group = _run(["docker", "exec", running_container.container_id, "id", "-g"])
    assert user.returncode == group.returncode == 0
    assert user.stdout.strip() == group.stdout.strip() == "10001"

    request_path = _run(
        [
            "docker",
            "exec",
            running_container.container_id,
            "python",
            "-c",
            (
                "from importlib.resources import files; "
                "print(files('praxis_virtualcell').joinpath('examples', "
                "'norman_mock_request.json'))"
            ),
        ]
    )
    assert request_path.returncode == 0, request_path.stderr

    output_dir = "/var/lib/praxis-vc/runs/container-cli-smoke"
    run = _run(
        [
            "docker",
            "exec",
            running_container.container_id,
            "praxis-vc",
            "run",
            "--request",
            request_path.stdout.strip(),
            "--mode",
            "offline",
            "--out",
            output_dir,
        ]
    )
    assert run.returncode == 0, run.stderr
    for name in ("report.md", "report.json", "trace.json", "provenance.json"):
        present = _run(
            ["docker", "exec", running_container.container_id, "test", "-s", f"{output_dir}/{name}"]
        )
        assert present.returncode == 0, f"missing or empty installed-wheel output: {name}"


def test_container_health_matches_candidate(running_container: RunningContainer) -> None:
    payload = _wait_for_health(running_container.container_id)
    assert payload["product_version"] == running_container.image.product_version
    assert payload["git_sha"] == running_container.image.git_sha
    assert payload["mode"] == "offline"
    assert payload["llm_enabled"] is False

    health = _run(
        [
            "docker",
            "inspect",
            "--format",
            "{{.State.Health.Status}}",
            running_container.container_id,
        ]
    )
    deadline = time.monotonic() + _START_TIMEOUT
    while health.stdout.strip() != "healthy" and time.monotonic() < deadline:
        time.sleep(1)
        health = _run(
            [
                "docker",
                "inspect",
                "--format",
                "{{.State.Health.Status}}",
                running_container.container_id,
            ]
        )
    assert health.returncode == 0 and health.stdout.strip() == "healthy"


def test_container_serves_hashed_web_assets(running_container: RunningContainer) -> None:
    root = _container_http(running_container.container_id, "/")
    assert root.status == 200
    html = root.body.decode("utf-8")

    assets = set(
        re.findall(
            r'(?:src|href)="(/assets/[A-Za-z0-9_.-]+-[A-Za-z0-9_-]{8,}\.(?:js|css))"',
            html,
        )
    )
    assert any(path.endswith(".js") for path in assets), html
    assert any(path.endswith(".css") for path in assets), html
    for path in assets:
        response = _container_http(running_container.container_id, path)
        assert response.status == 200
        content_type = response.content_type.split(";", 1)[0]
        if path.endswith(".js"):
            assert content_type in {"text/javascript", "application/javascript"}
        else:
            assert content_type == "text/css"
        assert response.body
        assert not response.body.lstrip().lower().startswith(b"<!doctype html"), path


def test_container_offline_api_report(running_container: RunningContainer) -> None:
    request = {
        "species": "human",
        "perturbation_type": "gene",
        "perturbation_targets": ["AHR"],
        "input_modality": "scRNA",
        "output_modality": "delta_expression",
        "task_type": "predict_delta_expression",
    }
    status, job = _container_json(
        running_container.container_id,
        "/api/jobs",
        data={"request": request, "mode": "offline"},
    )
    assert status == 200
    job_id = job["job_id"]

    report_status, report = _container_json(
        running_container.container_id,
        f"/api/reports/{job_id}",
    )
    assert report_status == 200
    assert report["structured_report"]
    assert report["llm_used_for_prediction"] is False

    response = _container_http(
        running_container.container_id,
        f"/api/reports/{job_id}/markdown",
    )
    markdown = response.body.decode("utf-8")
    assert response.status == 200
    assert "text/markdown" in response.content_type
    assert "# PRAXIS-VirtualCell Report" in markdown
