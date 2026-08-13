#!/usr/bin/env python3
"""Execute and attest one offline, unpublished local release candidate.

This is the positive counterpart to ``run_local_rc.py``.  It accepts only
write-new output and local dependency/scanner inputs; it never accepts caller
artifacts, test evidence, status, signatures, tags, publication, or deployment
claims.  Any missing or failed stage leaves ``LOCAL_RC_INCOMPLETE``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
import uuid
from pathlib import Path
from typing import Any

import release_candidate

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent
_RECORD_NAME = "full-local-rc-record.json"
_GATES = release_candidate._TEST_GATES
_TRIVY_VERSION = "0.73.0"
_TIMEOUT = 3600
_CONTAINER_TIMEOUT = 120
_SAFE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]*")
_TRIVY_BINARY_SHA256 = "6b61392e1798f42a66fc78ddf4829b5d26500d259439bb00ae10ed93217ff38f"
_TRIVY_DB_SHA256 = "0b61160b26b1b3df00c743bc285772ce679c96990ed196e44ae9eb34caa84d09"
_TRIVY_DB_METADATA_SHA256 = "774b552eac247d84cf7ae56a6195c1e8b3570d561d4bbac0db8c0dbf045bf38f"
_VULNERABILITY_POLICY = "release/p30a/vulnerability-policy.json"


class FullLocalRcError(RuntimeError):
    """Stable fail-closed error carrying the stage that could not pass."""

    def __init__(self, stage: str, detail: str) -> None:
        super().__init__(detail)
        self.stage = stage
        self.detail = detail


def _canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _file_record(path: Path, relative_to: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink() or path.stat().st_nlink != 1:
        raise FullLocalRcError("artifact_integrity", "release output contains an unsafe file")
    return {
        "path": path.relative_to(relative_to).as_posix(),
        "size": path.stat().st_size,
        "sha256": _sha256_file(path),
    }


def _write_new_json(path: Path, value: Any) -> None:
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if nofollow is None:
        raise FullLocalRcError("output", "platform lacks safe no-follow file creation")
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | nofollow, 0o600)
    except OSError as error:
        raise FullLocalRcError("output", "unable to create write-new result") from error
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(_canonical_json_bytes(value))
            stream.flush()
            os.fsync(stream.fileno())
            os.fchmod(stream.fileno(), 0o644)
    except OSError as error:
        raise FullLocalRcError("output", "unable to persist write-new result") from error


def _new_output(repo: Path, output: Path) -> Path:
    if not output.is_absolute() or output.exists() or output.is_symlink():
        raise FullLocalRcError("output", "output must be an absent absolute directory")
    parent = output.parent
    if not parent.is_dir() or parent.is_symlink():
        raise FullLocalRcError("output", "output parent must be a real existing directory")
    resolved_parent = parent.resolve()
    resolved = resolved_parent / output.name
    repo = repo.resolve()
    git_dir = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--absolute-git-dir"],
        capture_output=True,
        check=False,
        text=True,
    )
    if git_dir.returncode != 0:
        raise FullLocalRcError("source", "source is not a Git worktree")
    forbidden = (repo, Path(git_dir.stdout.strip()).resolve())
    if any(resolved == root or root in resolved.parents for root in forbidden):
        raise FullLocalRcError("output", "output must be outside source and Git metadata")
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if nofollow is None:
        raise FullLocalRcError("output", "platform lacks safe no-follow directory creation")
    try:
        parent_fd = os.open(
            resolved_parent,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | nofollow,
        )
        try:
            os.mkdir(output.name, 0o700, dir_fd=parent_fd)
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
    except OSError as error:
        raise FullLocalRcError("output", "unable to create write-new output") from error
    return resolved


def _input_directory(path: Path, label: str) -> Path:
    if not path.is_absolute() or not path.is_dir() or path.is_symlink():
        raise FullLocalRcError("inputs", f"{label} must be an absolute real directory")
    return path.resolve()


def _input_file(path: Path, label: str, *, executable: bool = False) -> Path:
    if not path.is_absolute() or not path.is_file() or path.is_symlink():
        raise FullLocalRcError("inputs", f"{label} must be an absolute regular file")
    if executable and not os.access(path, os.X_OK):
        raise FullLocalRcError("inputs", f"{label} is not executable")
    return path.resolve()


def _clean_text(value: str, roots: tuple[Path, ...]) -> str:
    text = value
    for root in sorted(roots, key=lambda item: len(str(item)), reverse=True):
        text = text.replace(str(root), "<LOCAL>")
    text = text.replace(str(Path.home()), "<HOME>")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return " | ".join(lines[-4:])[-1200:] or "command failed"


def _run(
    command: list[str],
    *,
    stage: str,
    cwd: Path,
    env: dict[str, str],
    roots: tuple[Path, ...],
    timeout: int = _TIMEOUT,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    print(f"[full-rc] {stage}", flush=True)
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            capture_output=True,
            check=False,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise FullLocalRcError(stage, f"{stage} could not execute") from error
    if check and result.returncode != 0:
        detail = _clean_text(f"{result.stdout}\n{result.stderr}", roots)
        raise FullLocalRcError(stage, detail)
    return result


def _tool(name: str) -> Path:
    path = shutil.which(name)
    if path is None:
        raise FullLocalRcError("inputs", f"required local tool is unavailable: {name}")
    return Path(path).resolve()


def _environment(tmp: Path, pip_cache: Path, npm_cache: Path) -> dict[str, str]:
    tool_dirs = [
        Path(sys.executable).parent,
        *(_tool(name).parent for name in ("git", "bash", "tar", "npm", "node", "docker")),
        Path("/usr/bin"),
        Path("/bin"),
        Path("/usr/sbin"),
        Path("/sbin"),
    ]
    path = os.pathsep.join(dict.fromkeys(str(item) for item in tool_dirs))
    home = os.environ.get("HOME")
    if not home or not Path(home).is_dir():
        raise FullLocalRcError("inputs", "a real local HOME is required for Docker and Playwright")
    return {
        "PATH": path,
        "HOME": home,
        "LANG": "C",
        "LC_ALL": "C",
        "TZ": "UTC",
        "CI": "1",
        "TMPDIR": str(tmp),
        "PYTHONDONTWRITEBYTECODE": "1",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "PRAXIS_RELEASE_OFFLINE": "1",
        "PRAXIS_PIP_CACHE_ROOT": str(pip_cache),
        "PRAXIS_NPM_CACHE_ROOT": str(npm_cache),
        "NO_PROXY": "127.0.0.1,localhost",
        "no_proxy": "127.0.0.1,localhost",
    }


def _test_environment(env: dict[str, str]) -> dict[str, str]:
    """Keep runner-private PRAXIS settings out of product test processes."""

    return {key: value for key, value in env.items() if not key.startswith("PRAXIS_")}


def _identity(repo: Path) -> dict[str, Any]:
    try:
        source_sha, source_tree, epoch = release_candidate._require_clean_committed_repo(repo)
        release_candidate._require_exact_head_file(repo, Path(__file__), "scripts/run_full_local_rc.py")
    except release_candidate.ReleaseContractError as error:
        raise FullLocalRcError("source", str(error)) from error
    if sys.implementation.name != "cpython" or sys.version_info[:2] != (3, 13):
        raise FullLocalRcError("source", "full local RC requires CPython 3.13")
    return {"source_sha": source_sha, "source_tree": source_tree, "source_date_epoch": epoch}


def _product_version(repo: Path) -> str:
    try:
        version = tomllib.loads((repo / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    except (OSError, KeyError, tomllib.TOMLDecodeError) as error:
        raise FullLocalRcError("source", "product version is unavailable") from error
    if type(version) is not str or _SAFE_NAME.fullmatch(version) is None:
        raise FullLocalRcError("source", "product version is invalid")
    return version


def _load_vulnerability_policy(repo: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    path = repo / _VULNERABILITY_POLICY
    try:
        release_candidate._require_exact_head_file(repo, path, _VULNERABILITY_POLICY)
        policy = release_candidate._load_json(path)
    except release_candidate.ReleaseContractError as error:
        raise FullLocalRcError("vulnerability_policy", str(error)) from error
    expected = {
        "schema_version",
        "policy_id",
        "scanner",
        "database",
        "required_scopes",
        "acceptance",
        "claim_ceiling",
    }
    if type(policy) is not dict or set(policy) != expected:
        raise FullLocalRcError("vulnerability_policy", "vulnerability policy schema differs")
    if (
        policy["schema_version"] != "praxis.local-rc-vulnerability-policy.v1"
        or policy["policy_id"] != "no-known-remediation-available-v1"
        or policy["scanner"] != {"name": "Trivy", "version": _TRIVY_VERSION, "binary_sha256": _TRIVY_BINARY_SHA256}
        or policy["database"]
        != {
            "format": "aquasecurity/trivy-db-v2",
            "sha256": _TRIVY_DB_SHA256,
            "metadata_sha256": _TRIVY_DB_METADATA_SHA256,
            "as_of": "2026-08-13T13:03:34.300611711Z",
        }
        or policy["required_scopes"]
        != [
            "npm_exact_lock_including_development_dependencies",
            "python_build_and_runtime_exact_locks",
            "exact_runtime_oci",
        ]
        or policy["acceptance"]
        != {
            "blocking_rule": "any_finding_with_nonempty_fixed_version",
            "all_severities_in_scope": True,
            "all_findings_must_be_retained": True,
            "zero_findings_required": False,
            "unresolved_findings_without_a_known_fix": "recorded_nonblocking",
        }
        or policy["claim_ceiling"]
        != {
            "passed_does_not_mean_vulnerability_free": True,
            "security_supported": False,
            "published": False,
            "production_authorized": False,
        }
    ):
        raise FullLocalRcError("vulnerability_policy", "vulnerability policy is not the frozen local RC policy")
    return policy, {
        "path": _VULNERABILITY_POLICY,
        "size": path.stat().st_size,
        "sha256": _sha256_file(path),
    }


def _clone_exact_source(
    repo: Path,
    destination: Path,
    source_sha: str,
    *,
    env: dict[str, str],
    roots: tuple[Path, ...],
) -> None:
    _run(
        ["git", "clone", "--local", "--no-hardlinks", "--no-checkout", str(repo), str(destination)],
        stage="test_source_clone",
        cwd=repo,
        env=env,
        roots=roots,
    )
    _run(
        ["git", "checkout", "--detach", source_sha],
        stage="test_source_checkout",
        cwd=destination,
        env=env,
        roots=roots,
    )
    try:
        cloned_sha, _, _ = release_candidate._require_clean_committed_repo(destination)
    except release_candidate.ReleaseContractError as error:
        raise FullLocalRcError("test_source_checkout", str(error)) from error
    if cloned_sha != source_sha:
        raise FullLocalRcError("test_source_checkout", "test source differs from the exact release source")


def _verify_test_source(
    test_source: Path, identity: dict[str, Any], *, env: dict[str, str], roots: tuple[Path, ...]
) -> None:
    for arguments, expected in (
        (("rev-parse", "HEAD"), identity["source_sha"]),
        (("rev-parse", "HEAD^{tree}"), identity["source_tree"]),
    ):
        result = _run(
            ["git", *arguments],
            stage="verify_test_source",
            cwd=test_source,
            env=env,
            roots=roots,
        )
        if result.stdout.strip() != expected:
            raise FullLocalRcError("verify_test_source", "test source identity changed during gate execution")
    _run(
        ["git", "diff", "--exit-code", "--no-ext-diff", "HEAD", "--", "."],
        stage="verify_test_source",
        cwd=test_source,
        env=env,
        roots=roots,
    )


def _build_source_archives(
    repo: Path,
    output: Path,
    identity: dict[str, Any],
    version: str,
    *,
    env: dict[str, str],
    roots: tuple[Path, ...],
) -> tuple[Path, Path, dict[str, Any]]:
    destinations: list[Path] = []
    for name in ("source-a", "source-b"):
        parent = output / "artifacts" / name
        parent.mkdir(parents=True)
        destination = parent / f"praxis-virtualcell-{version}.tar.gz"
        source_env = {
            **env,
            "PYTHON_BIN": sys.executable,
            "PRAXIS_SOURCE_ARCHIVE_ROOT": str(repo),
            "PRAXIS_SOURCE_ARCHIVE_REF": identity["source_sha"],
        }
        _run(
            ["bash", "scripts/build_release_source_archive.sh", str(destination)],
            stage=f"build_{name}",
            cwd=repo,
            env=source_env,
            roots=roots,
        )
        destinations.append(destination)
    first, second = destinations
    first_sha, second_sha = _sha256_file(first), _sha256_file(second)
    if first_sha != second_sha or first.stat().st_size != second.stat().st_size:
        raise FullLocalRcError("source_reproducibility", "source archives are not byte-identical")
    comparison = {
        "schema_version": "praxis.source-reproducibility.v1",
        "source_sha": identity["source_sha"],
        "filename": first.name,
        "first": {"size": first.stat().st_size, "sha256": first_sha},
        "second": {"size": second.stat().st_size, "sha256": second_sha},
        "identical": True,
    }
    comparison_path = output / "evidence" / "source-reproducibility.json"
    comparison_path.parent.mkdir(parents=True)
    _write_new_json(comparison_path, comparison)
    return first, second, comparison


def _only_wheel(directory: Path) -> Path:
    wheels = sorted(directory.glob("*.whl"))
    if len(wheels) != 1 or wheels[0].is_symlink():
        raise FullLocalRcError("wheel", "wheel build did not produce exactly one regular wheel")
    return wheels[0]


def _build_wheels(
    repo: Path,
    output: Path,
    identity: dict[str, Any],
    *,
    env: dict[str, str],
    roots: tuple[Path, ...],
) -> tuple[Path, Path, dict[str, Any]]:
    wheels: list[Path] = []
    for name in ("wheel-a", "wheel-b"):
        destination = output / "artifacts" / name
        wheel_env = {**env, "PYTHON_BIN": sys.executable}
        _run(
            ["bash", "scripts/build_release_wheel.sh", str(destination)],
            stage=f"build_{name}",
            cwd=repo,
            env=wheel_env,
            roots=roots,
            timeout=1800,
        )
        wheels.append(_only_wheel(destination))
    first, second = wheels
    try:
        comparison = release_candidate.compare_wheels(first, second, source_sha=identity["source_sha"])
    except release_candidate.ReleaseContractError as error:
        raise FullLocalRcError("wheel_reproducibility", str(error)) from error
    if comparison["identical"] is not True:
        raise FullLocalRcError("wheel_reproducibility", "release wheels are not byte-identical")
    path = output / "evidence" / "wheel-reproducibility.json"
    _write_new_json(path, comparison)
    return first, second, comparison


def _materialize_wheelhouse(
    repo: Path,
    cache: Path,
    output: Path,
    locks: tuple[str, ...],
    profile: str,
    epoch: int,
) -> None:
    try:
        release_candidate.materialize_wheelhouse(
            lock_paths=tuple(repo / relative for relative in locks),
            cache_root=cache,
            output_dir=output,
            source_date_epoch=epoch,
            target_profile=profile,
        )
    except release_candidate.ReleaseContractError as error:
        raise FullLocalRcError("wheelhouse", str(error)) from error


def _create_venv(
    path: Path,
    *,
    stage: str,
    cwd: Path,
    env: dict[str, str],
    roots: tuple[Path, ...],
) -> Path:
    _run(
        [sys.executable, "-m", "venv", str(path)],
        stage=stage,
        cwd=cwd,
        env=env,
        roots=roots,
    )
    return path / "bin" / "python"


def _pip_install_lock(
    python: Path,
    wheelhouse: Path,
    lock: Path,
    *,
    stage: str,
    cwd: Path,
    env: dict[str, str],
    roots: tuple[Path, ...],
) -> None:
    _run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--no-index",
            "--find-links",
            str(wheelhouse),
            "--only-binary=:all:",
            "--require-hashes",
            "--requirement",
            str(lock),
        ],
        stage=stage,
        cwd=cwd,
        env=env,
        roots=roots,
        timeout=1800,
    )


def _gate(
    gates: dict[str, dict[str, str]],
    name: str,
    command: list[str],
    *,
    command_label: str,
    summary: str,
    cwd: Path,
    env: dict[str, str],
    roots: tuple[Path, ...],
    timeout: int = _TIMEOUT,
) -> None:
    try:
        _run(command, stage=f"gate_{name}", cwd=cwd, env=env, roots=roots, timeout=timeout)
    except FullLocalRcError:
        gates[name] = {"status": "failed", "command": command_label, "summary": f"{name} failed"}
        raise
    gates[name] = {"status": "passed", "command": command_label, "summary": summary}


def _run_test_gates(
    repo: Path,
    test_source: Path,
    tmp: Path,
    cache: Path,
    npm_cache: Path,
    epoch: int,
    gates: dict[str, dict[str, str]],
    *,
    env: dict[str, str],
    roots: tuple[Path, ...],
) -> None:
    wheelhouse = tmp / "dev-wheelhouse"
    _materialize_wheelhouse(
        test_source,
        cache,
        wheelhouse,
        ("requirements/build-py313.lock", "requirements/dev-py313.lock"),
        "macos_arm64_cp313",
        epoch,
    )
    venv = tmp / "dev-env"
    python = _create_venv(venv, stage="create_dev_env", cwd=test_source, env=env, roots=roots)
    _pip_install_lock(
        python,
        wheelhouse,
        test_source / "requirements" / "build-py313.lock",
        stage="install_build_lock",
        cwd=test_source,
        env=env,
        roots=roots,
    )
    _pip_install_lock(
        python,
        wheelhouse,
        test_source / "requirements" / "dev-py313.lock",
        stage="install_dev_lock",
        cwd=test_source,
        env=env,
        roots=roots,
    )
    _run(
        [str(python), "-m", "pip", "install", "--no-build-isolation", "--no-deps", "-e", "."],
        stage="install_test_source",
        cwd=test_source,
        env=env,
        roots=roots,
    )
    test_env = _test_environment(env)
    _gate(
        gates,
        "pip_check",
        [str(python), "-m", "pip", "check"],
        command_label="python -m pip check (exact dev environment)",
        summary="exact dev dependency graph passed pip check",
        cwd=test_source,
        env=test_env,
        roots=roots,
    )
    _gate(
        gates,
        "ruff",
        [str(venv / "bin" / "ruff"), "check", "."],
        command_label="ruff check .",
        summary="repository lint passed",
        cwd=test_source,
        env=test_env,
        roots=roots,
    )
    packaging_tests = [
        "praxis_virtualcell/tests/test_release_candidate.py",
        "praxis_virtualcell/tests/test_release_source_archive.py",
        "praxis_virtualcell/tests/test_release_finalizer.py",
        "praxis_virtualcell/tests/test_local_rc_runner.py",
        "praxis_virtualcell/tests/test_full_local_rc.py",
    ]
    _gate(
        gates,
        "packaging",
        [str(python), "-m", "pytest", *packaging_tests, "-o", "addopts=", "-q", "-p", "no:cacheprovider"],
        command_label="pytest release packaging contract suite",
        summary="release packaging contract suite passed",
        cwd=test_source,
        env=test_env,
        roots=roots,
    )
    _gate(
        gates,
        "core",
        [
            str(python),
            "-m",
            "pytest",
            "praxis_virtualcell/tests",
            "-m",
            "not llm",
            "-o",
            "addopts=",
            "-q",
            "-ra",
            "-p",
            "no:cacheprovider",
        ],
        command_label='pytest praxis_virtualcell/tests -m "not llm"',
        summary="VirtualCell core suite passed with external gates left disabled",
        cwd=test_source,
        env=test_env,
        roots=roots,
    )
    _gate(
        gates,
        "legacy",
        [
            str(python),
            "-m",
            "pytest",
            "tests",
            "-m",
            "not (integration or llm or remote)",
            "-o",
            "addopts=",
            "-q",
            "-ra",
            "-p",
            "no:cacheprovider",
        ],
        command_label='pytest tests -m "not (integration or llm or remote)"',
        summary="legacy unit suite passed with external gates disabled",
        cwd=test_source,
        env=test_env,
        roots=roots,
    )
    frontend = test_source / "praxis_vc_react"
    frontend_env = {
        **test_env,
        "npm_config_cache": str(npm_cache),
        "PRAXIS_VC_TEST_PYTHON": str(python),
    }
    try:
        for stage, command in (
            ("frontend_install", ["npm", "ci", "--offline", "--no-audit", "--no-fund"]),
            ("frontend_typecheck", ["npm", "run", "typecheck"]),
            ("frontend_lint", ["npm", "run", "lint"]),
            ("frontend_build", ["npm", "run", "build"]),
            ("frontend_e2e", ["npm", "run", "e2e"]),
        ):
            _run(command, stage=stage, cwd=frontend, env=frontend_env, roots=roots, timeout=1800)
    except FullLocalRcError:
        gates["frontend"] = {
            "status": "failed",
            "command": "npm ci --offline; typecheck; lint; build; e2e",
            "summary": "frontend gate failed",
        }
        raise
    gates["frontend"] = {
        "status": "passed",
        "command": "npm ci --offline; npm run typecheck; lint; build; e2e",
        "summary": "frontend typecheck, lint, build, bundle and Playwright suite passed",
    }


def _clean_install_gate(
    repo: Path,
    tmp: Path,
    wheelhouse: Path,
    wheel: Path,
    gates: dict[str, dict[str, str]],
    *,
    env: dict[str, str],
    roots: tuple[Path, ...],
) -> None:
    venv = tmp / "release-env"
    python = _create_venv(venv, stage="create_release_env", cwd=repo, env=env, roots=roots)
    _pip_install_lock(
        python,
        wheelhouse,
        repo / "requirements" / "runtime-py313.lock",
        stage="install_runtime_lock",
        cwd=repo,
        env=env,
        roots=roots,
    )
    _run(
        [str(python), "-m", "pip", "install", "--no-index", "--no-deps", str(wheel)],
        stage="install_release_wheel",
        cwd=tmp,
        env=env,
        roots=roots,
    )
    try:
        _run(
            [str(python), "-m", "pip", "check"],
            stage="release_pip_check",
            cwd=tmp,
            env=env,
            roots=roots,
        )
        _run(
            [str(python), str(repo / "scripts" / "verify_release_install.py")],
            stage="verify_release_install",
            cwd=tmp,
            env=env,
            roots=roots,
        )
    except FullLocalRcError:
        gates["wheel"] = {
            "status": "failed",
            "command": "offline locked runtime install and verify_release_install.py",
            "summary": "wheel clean-install gate failed",
        }
        raise
    gates["wheel"] = {
        "status": "passed",
        "command": "offline locked runtime install and verify_release_install.py",
        "summary": "byte-identical wheel passed isolated install, pip check, CLI, API and static asset verification",
    }


def _build_oci(
    repo: Path,
    output: Path,
    wheelhouse: Path,
    identity: dict[str, Any],
    *,
    env: dict[str, str],
    roots: tuple[Path, ...],
) -> tuple[Path, Path, dict[str, Any]]:
    destinations = (
        output / "artifacts" / "release-a.oci.tar",
        output / "artifacts" / "release-b.oci.tar",
    )
    for index, destination in enumerate(destinations, start=1):
        _run(
            ["bash", "scripts/build_release_oci.sh", str(wheelhouse), str(destination)],
            stage=f"build_oci_{index}",
            cwd=repo,
            env={**env, "PYTHON_BIN": sys.executable},
            roots=roots,
            timeout=1800,
        )
    first, second = destinations
    try:
        comparison = release_candidate.compare_oci_layouts(
            first,
            second,
            source_sha=identity["source_sha"],
        )
    except release_candidate.ReleaseContractError as error:
        raise FullLocalRcError("oci_reproducibility", str(error)) from error
    if comparison["identical"] is not True:
        raise FullLocalRcError("oci_reproducibility", "OCI manifest/config/layer identities differ")
    _write_new_json(output / "evidence" / "oci-reproducibility.json", comparison)
    return first, second, comparison


def _docker_inspect(reference: str, *, cwd: Path, env: dict[str, str], roots: tuple[Path, ...]) -> dict | None:
    result = _run(
        ["docker", "image", "inspect", reference],
        stage="docker_image_inspect",
        cwd=cwd,
        env=env,
        roots=roots,
        check=False,
    )
    if result.returncode != 0:
        return None
    documents = json.loads(result.stdout)
    return documents[0] if documents else None


def _container_probe_script() -> str:
    return r"""import json, os, re, urllib.error, urllib.request
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
def request(path, payload=None):
    data = None if payload is None else json.dumps(payload, separators=(",", ":")).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:8000" + path,
        data=data,
        headers={"Content-Type":"application/json"},
    )
    try:
        with opener.open(req, timeout=10) as response:
            return response.status, response.read(), response.headers.get("content-type", "")
    except urllib.error.HTTPError as error:
        return error.code, error.read(), error.headers.get("content-type", "")
status, body, _ = request("/api/health")
assert status == 200 and json.loads(body)["status"] == "ok"
status, body, _ = request("/")
assert status == 200
asset = re.search(rb'(?:src|href)="([^"]+assets/[^"]+)"', body).group(1).decode()
assert request(asset)[0] == 200
direct = {
    "request": {
        "schema_version": "vc.request.v2",
        "request_id": "rc-container",
        "species": {
            "schema_version": "vc.species-ref.v1",
            "taxonomy_id": "NCBITaxon:999999999",
            "scientific_name": "test-only organism",
            "common_name": None,
        },
        "cell_context": {
            "schema_version": "vc.cell-context.v1",
            "cell_type_name": None,
            "cell_type_id": None,
            "tissue_name": None,
            "tissue_id": None,
            "attributes": {},
        },
        "input_modality": {
            "schema_version": "vc.modality.v1",
            "name": "test_input",
            "ontology_id": None,
            "unit": "dimensionless",
            "feature_namespace": "TestFeature",
        },
        "output_modality": {
            "schema_version": "vc.modality.v1",
            "name": "test_output",
            "ontology_id": None,
            "unit": "dimensionless",
            "feature_namespace": "TestFeature",
        },
        "perturbation": {
            "schema_version": "vc.perturbation.v1",
            "kind": "gene",
            "targets": ["TEST:1"],
            "dose_value": None,
            "dose_unit": None,
            "timepoint": None,
        },
        "task": {
            "schema_version": "vc.task.v1",
            "task_type": "test_scalar_task",
            "requested_outputs": ["test_output"],
        },
        "baseline_context": None,
        "metadata": {},
        "constraints": {},
    },
    "mode": "offline",
    "enable_llm_report": False,
    "pack_id": "test-only-pack",
    "pack_version": "0.0.0",
    "submission_contract": "vc.direct-v2-execution.v1",
}
status, body, _ = request("/api/jobs", direct)
assert status == 503 and json.loads(body) == {"detail":"direct_v2_factory_unconfigured"}
legacy = {
    "request": {
        "species": "human",
        "perturbation_type": "gene",
        "perturbation_targets": ["AHR"],
        "input_modality": "scRNA",
        "output_modality": "delta_expression",
        "task_type": "predict_delta_expression",
    },
    "mode": "offline",
}
status, body, _ = request("/api/jobs", legacy)
assert status == 200 and json.loads(body)["job_id"]
assert os.getuid() == 10001
print("artifact-bound-container-smoke-ok")"""


def _load_and_smoke_image(
    repo: Path,
    oci: Path,
    identity: dict[str, Any],
    version: str,
    gates: dict[str, dict[str, str]],
    *,
    env: dict[str, str],
    roots: tuple[Path, ...],
) -> tuple[str, bool]:
    try:
        oci_identity = release_candidate.read_oci_identity(oci)
    except release_candidate.ReleaseContractError as error:
        raise FullLocalRcError("container", str(error)) from error
    # Docker Desktop's containerd store addresses a loaded OCI image by its
    # manifest digest. The config digest remains bound inside that manifest.
    image_id = oci_identity.manifest_digest
    existed = _docker_inspect(image_id, cwd=repo, env=env, roots=roots) is not None
    _run(
        ["docker", "image", "load", "--platform", "linux/arm64", "--input", str(oci)],
        stage="load_exact_oci",
        cwd=repo,
        env=env,
        roots=roots,
        timeout=600,
    )
    document = _docker_inspect(image_id, cwd=repo, env=env, roots=roots)
    config = (document or {}).get("Config", {})
    labels = config.get("Labels") or {}
    if (
        document is None
        or document.get("Id") != image_id
        or document.get("Architecture") != "arm64"
        or document.get("Os") != "linux"
        or config.get("User") != "10001:10001"
        or labels.get("org.opencontainers.image.revision") != identity["source_sha"]
        or labels.get("org.opencontainers.image.version") != version
    ):
        if not existed:
            _run(
                ["docker", "image", "rm", "--no-prune", image_id],
                stage="remove_invalid_loaded_image",
                cwd=repo,
                env=env,
                roots=roots,
                check=False,
            )
        raise FullLocalRcError("container", "loaded image differs from the exact OCI identity")
    name = f"praxis-vc-full-rc-{identity['source_sha'][:12]}-{os.getpid()}"
    owner = f"{identity['source_sha']}:{uuid.uuid4().hex}"
    container_id = ""
    try:
        result = _run(
            [
                "docker",
                "run",
                "--detach",
                "--platform",
                "linux/arm64",
                "--name",
                name,
                "--network",
                "none",
                "--label",
                f"io.praxis-virtualcell.full-rc={owner}",
                image_id,
            ],
            stage="start_exact_oci",
            cwd=repo,
            env=env,
            roots=roots,
        )
        container_id = result.stdout.strip()
        deadline = time.monotonic() + _CONTAINER_TIMEOUT
        while time.monotonic() < deadline:
            probe = _run(
                ["docker", "exec", container_id, "python", "-c", _container_probe_script()],
                stage="probe_exact_oci",
                cwd=repo,
                env=env,
                roots=roots,
                check=False,
            )
            if probe.returncode == 0:
                break
            time.sleep(2)
        else:
            raise FullLocalRcError("container", "artifact-bound container did not become healthy")
        _run(
            ["docker", "exec", container_id, "python", "-m", "pip", "check"],
            stage="container_pip_check",
            cwd=repo,
            env=env,
            roots=roots,
        )
    except FullLocalRcError:
        gates["container"] = {
            "status": "failed",
            "command": "docker load exact OCI and run internal HTTP/pip smoke",
            "summary": "artifact-bound container gate failed",
        }
        raise
    finally:
        if container_id:
            try:
                inspected = _run(
                    ["docker", "inspect", container_id],
                    stage="inspect_owned_container",
                    cwd=repo,
                    env=env,
                    roots=roots,
                )
                container = json.loads(inspected.stdout)[0]
                actual_owner = (container.get("Config", {}).get("Labels") or {}).get("io.praxis-virtualcell.full-rc")
                if (
                    container.get("Id") != container_id
                    or container.get("Image") != image_id
                    or container.get("HostConfig", {}).get("NetworkMode") != "none"
                    or actual_owner != owner
                ):
                    raise FullLocalRcError("container_cleanup", "refusing to remove an unowned container")
                _run(
                    ["docker", "rm", "--force", "--volumes", container_id],
                    stage="remove_owned_container",
                    cwd=repo,
                    env=env,
                    roots=roots,
                )
            except (FullLocalRcError, IndexError, json.JSONDecodeError) as error:
                gates["container"] = {
                    "status": "failed",
                    "command": "docker load exact OCI and run internal HTTP/pip smoke",
                    "summary": "artifact-bound container cleanup failed",
                }
                if isinstance(error, FullLocalRcError):
                    raise
                raise FullLocalRcError("container_cleanup", "owned container inspection failed") from error
        if sys.exc_info()[0] is not None and not existed:
            _run(
                ["docker", "image", "rm", "--no-prune", image_id],
                stage="remove_failed_loaded_image",
                cwd=repo,
                env=env,
                roots=roots,
                check=False,
            )
    gates["container"] = {
        "status": "passed",
        "command": "docker load exact OCI and run internal HTTP/pip smoke",
        "summary": "exact OCI config identity passed non-root API, UI, direct-v2 fail-closed and pip smoke",
    }
    return image_id, existed


def _remove_loaded_image(
    image_id: str,
    *,
    repo: Path,
    env: dict[str, str],
    roots: tuple[Path, ...],
) -> None:
    _run(
        ["docker", "image", "rm", "--no-prune", image_id],
        stage="remove_loaded_image",
        cwd=repo,
        env=env,
        roots=roots,
    )
    if _docker_inspect(image_id, cwd=repo, env=env, roots=roots) is not None:
        raise FullLocalRcError("container_cleanup", "loaded image remained after removal")


def _trivy_document(
    path: Path,
    *,
    artifact_type: str,
    artifact_name: str | None = None,
    required_target_suffix: str | None = None,
    image_id: str | None = None,
) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise FullLocalRcError("vulnerability_scan", "Trivy output is invalid") from error
    required = {
        "SchemaVersion",
        "Trivy",
        "ReportID",
        "CreatedAt",
        "ArtifactName",
        "ArtifactType",
        "Results",
    }
    if (
        type(document) is not dict
        or not required.issubset(document)
        or document["SchemaVersion"] != 2
        or document["ArtifactType"] != artifact_type
        or type(document["Trivy"]) is not dict
        or document["Trivy"].get("Version") != _TRIVY_VERSION
        or type(document["ReportID"]) is not str
        or not document["ReportID"]
        or type(document["CreatedAt"]) is not str
        or not document["CreatedAt"]
        or type(document["ArtifactName"]) is not str
        or not document["ArtifactName"]
        or type(document["Results"]) is not list
        or not document["Results"]
    ):
        raise FullLocalRcError("vulnerability_scan", "Trivy output has an invalid schema")
    if artifact_name is not None and document["ArtifactName"] != artifact_name:
        raise FullLocalRcError("vulnerability_scan", "Trivy output differs from the requested artifact")
    targets = [
        result.get("Target")
        for result in document["Results"]
        if type(result) is dict and type(result.get("Target")) is str
    ]
    if required_target_suffix is not None and not any(target.endswith(required_target_suffix) for target in targets):
        raise FullLocalRcError("vulnerability_scan", "Trivy filesystem report lacks required lock coverage")
    if image_id is not None:
        metadata = document.get("Metadata")
        observed_ids = {document.get("ArtifactID")}
        if type(metadata) is dict:
            observed_ids.add(metadata.get("ImageID"))
        if image_id not in observed_ids:
            raise FullLocalRcError("vulnerability_scan", "Trivy image report differs from the exact OCI image")
    return document


def _python_lock_components(repo: Path) -> tuple[tuple[str, str], ...]:
    components: dict[str, str] = {}
    for name in ("build-py313.lock", "runtime-py313.lock"):
        try:
            locked = release_candidate.parse_hash_lock(repo / "requirements" / name)
        except release_candidate.ReleaseContractError as error:
            raise FullLocalRcError("vulnerability_scan", str(error)) from error
        for component in locked:
            previous = components.setdefault(component.name, component.version)
            if previous != component.version:
                raise FullLocalRcError("vulnerability_scan", "Python locks contain conflicting versions")
    if len(components) != 36:
        raise FullLocalRcError("vulnerability_scan", "Python build/runtime lock component coverage changed")
    return tuple(sorted(components.items()))


def _python_lock_sbom(repo: Path) -> tuple[dict[str, Any], tuple[tuple[str, str], ...]]:
    components = _python_lock_components(repo)
    return (
        {
            "bomFormat": "CycloneDX",
            "specVersion": "1.6",
            "version": 1,
            "metadata": {
                "component": {
                    "type": "application",
                    "name": "praxis-virtualcell-python-build-runtime-locks",
                    "version": _product_version(repo),
                }
            },
            "components": [
                {
                    "type": "library",
                    "name": name,
                    "version": version,
                    "purl": f"pkg:pypi/{name}@{version}",
                }
                for name, version in components
            ],
        },
        components,
    )


def _npm_lock_components(repo: Path) -> tuple[tuple[str, str], ...]:
    try:
        document = release_candidate._load_json(repo / "praxis_vc_react" / "package-lock.json")
    except release_candidate.ReleaseContractError as error:
        raise FullLocalRcError("vulnerability_scan", str(error)) from error
    packages = document.get("packages") if type(document) is dict else None
    if type(packages) is not dict:
        raise FullLocalRcError("vulnerability_scan", "npm lock package inventory is invalid")
    components: list[tuple[str, str]] = []
    for package_path, raw in packages.items():
        if not package_path:
            continue
        if type(raw) is not dict or type(raw.get("version")) is not str:
            raise FullLocalRcError("vulnerability_scan", "npm lock component is invalid")
        name = raw.get("name")
        if type(name) is not str:
            name = package_path.rsplit("node_modules/", 1)[-1]
        components.append((name, raw["version"]))
    result = tuple(sorted(components))
    if len(result) != 121 or len(set(result)) != len(result):
        raise FullLocalRcError("vulnerability_scan", "npm lock component coverage changed")
    return result


def _trivy_package_components(document: dict[str, Any], result_type: str) -> tuple[tuple[str, str], ...]:
    results = [result for result in document["Results"] if type(result) is dict and result.get("Type") == result_type]
    if len(results) != 1 or type(results[0].get("Packages")) is not list:
        raise FullLocalRcError("vulnerability_scan", "Trivy package inventory is incomplete")
    components: list[tuple[str, str]] = []
    for package in results[0]["Packages"]:
        if type(package) is not dict or type(package.get("Name")) is not str or type(package.get("Version")) is not str:
            raise FullLocalRcError("vulnerability_scan", "Trivy package identity is invalid")
        components.append((package["Name"], package["Version"]))
    return tuple(sorted(components))


def _vulnerabilities(documents: tuple[tuple[str, dict[str, Any]], ...]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for scope, document in documents:
        for result in document.get("Results") or []:
            if type(result) is not dict:
                raise FullLocalRcError("vulnerability_scan", "Trivy result entry is invalid")
            target = str(result.get("Target") or "unknown")
            result_type = str(result.get("Type") or "unknown")
            for vulnerability in result.get("Vulnerabilities") or []:
                if type(vulnerability) is not dict:
                    raise FullLocalRcError("vulnerability_scan", "Trivy vulnerability entry is invalid")
                data_source = vulnerability.get("DataSource")
                findings.append(
                    {
                        "scope": scope,
                        "target": target,
                        "type": result_type,
                        "vulnerability_id": str(vulnerability.get("VulnerabilityID") or "unknown"),
                        "package": str(vulnerability.get("PkgName") or "unknown"),
                        "installed_version": str(vulnerability.get("InstalledVersion") or "unknown"),
                        "fixed_version": str(vulnerability.get("FixedVersion") or ""),
                        "severity": str(vulnerability.get("Severity") or "UNKNOWN"),
                        "status": str(vulnerability.get("Status") or "unknown"),
                        "data_source": (
                            str(data_source.get("Name") or "unknown") if type(data_source) is dict else "unknown"
                        ),
                    }
                )
    return sorted(findings, key=lambda item: tuple(item.values()))


def _evaluate_vulnerability_policy(
    findings: list[dict[str, Any]],
    policy: dict[str, Any],
) -> dict[str, Any]:
    if policy["acceptance"]["blocking_rule"] != "any_finding_with_nonempty_fixed_version":
        raise FullLocalRcError("vulnerability_policy", "unsupported vulnerability acceptance rule")
    blocking = [finding for finding in findings if finding["fixed_version"]]
    return {
        "policy_id": policy["policy_id"],
        "status": "failed_known_remediation_available" if blocking else "passed_with_unresolved_unfixed_findings",
        "finding_count": len(findings),
        "blocking_finding_count": len(blocking),
        "unresolved_unfixed_finding_count": len(findings) - len(blocking),
        "zero_findings": not findings,
        "passed_does_not_mean_vulnerability_free": True,
        "security_supported": False,
    }


def _validate_trivy(trivy: Path, cache: Path, *, env: dict[str, str], roots: tuple[Path, ...]) -> dict[str, Any]:
    binary_sha256 = _sha256_file(trivy)
    if binary_sha256 != _TRIVY_BINARY_SHA256:
        raise FullLocalRcError("vulnerability_scan", "Trivy binary identity differs from the frozen scanner")
    version = _run(
        [str(trivy), "--version"],
        stage="trivy_version",
        cwd=_REPO_ROOT,
        env=env,
        roots=roots,
    )
    if f"Version: {_TRIVY_VERSION}" not in version.stdout:
        raise FullLocalRcError("vulnerability_scan", f"Trivy must be exactly {_TRIVY_VERSION}")
    database_dir = cache / "db"
    if not database_dir.is_dir() or database_dir.is_symlink() or database_dir.resolve().parent != cache:
        raise FullLocalRcError("vulnerability_scan", "Trivy database directory is unsafe")
    database = database_dir / "trivy.db"
    metadata_path = database_dir / "metadata.json"
    for path in (database, metadata_path):
        if not path.is_file() or path.is_symlink():
            raise FullLocalRcError("vulnerability_scan", "dated Trivy database is incomplete")
    database_sha256 = _sha256_file(database)
    metadata_sha256 = _sha256_file(metadata_path)
    if database_sha256 != _TRIVY_DB_SHA256 or metadata_sha256 != _TRIVY_DB_METADATA_SHA256:
        raise FullLocalRcError("vulnerability_scan", "Trivy database identity differs from the frozen input")
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        updated = metadata["UpdatedAt"]
    except (OSError, KeyError, json.JSONDecodeError) as error:
        raise FullLocalRcError("vulnerability_scan", "Trivy database metadata is invalid") from error
    if type(updated) is not str or not updated:
        raise FullLocalRcError("vulnerability_scan", "Trivy database update time is invalid")
    if updated != "2026-08-13T13:03:34.300611711Z":
        raise FullLocalRcError("vulnerability_scan", "Trivy database date differs from the frozen policy")
    return {
        "binary_sha256": binary_sha256,
        "database_sha256": database_sha256,
        "database_metadata_sha256": metadata_sha256,
        "database_as_of": updated,
    }


def _run_vulnerability_scan(
    repo: Path,
    output: Path,
    trivy: Path,
    cache: Path,
    image_id: str,
    trivy_identity: dict[str, Any],
    policy: dict[str, Any],
    *,
    env: dict[str, str],
    roots: tuple[Path, ...],
) -> dict[str, Any]:
    npm_path = output / "evidence" / "trivy-npm-lock.json"
    evidence = output / "evidence"
    python_sbom_path = evidence / "python-build-runtime-locks.cdx.json"
    python_path = evidence / "trivy-python-locks.json"
    image_path = output / "evidence" / "trivy-image.json"
    python_sbom, expected_python = _python_lock_sbom(repo)
    _write_new_json(python_sbom_path, python_sbom)
    expected_npm = _npm_lock_components(repo)
    common = [
        str(trivy),
        "--cache-backend",
        "memory",
        "--cache-dir",
        str(cache),
        "--disable-telemetry",
        "--skip-version-check",
    ]
    _run(
        [
            *common,
            "fs",
            "--skip-db-update",
            "--skip-java-db-update",
            "--skip-vex-repo-update",
            "--offline-scan",
            "--include-dev-deps",
            "--scanners",
            "vuln",
            "--format",
            "json",
            "--output",
            str(npm_path),
            "--exit-code",
            "0",
            "praxis_vc_react/package-lock.json",
        ],
        stage="trivy_npm_lock",
        cwd=repo,
        env=env,
        roots=roots,
        timeout=1800,
    )
    _run(
        [
            *common,
            "sbom",
            "--skip-db-update",
            "--skip-java-db-update",
            "--skip-vex-repo-update",
            "--offline-scan",
            "--scanners",
            "vuln",
            "--format",
            "json",
            "--output",
            str(python_path),
            "--exit-code",
            "0",
            python_sbom_path.name,
        ],
        stage="trivy_python_locks",
        cwd=evidence,
        env=env,
        roots=roots,
        timeout=1800,
    )
    _run(
        [
            *common,
            "image",
            "--skip-db-update",
            "--skip-java-db-update",
            "--skip-vex-repo-update",
            "--offline-scan",
            "--scanners",
            "vuln",
            "--image-src",
            "docker",
            "--format",
            "json",
            "--output",
            str(image_path),
            "--exit-code",
            "0",
            image_id,
        ],
        stage="trivy_image",
        cwd=repo,
        env=env,
        roots=roots,
        timeout=1800,
    )
    if (
        _sha256_file(trivy) != trivy_identity["binary_sha256"]
        or _sha256_file(cache / "db" / "trivy.db") != trivy_identity["database_sha256"]
        or _sha256_file(cache / "db" / "metadata.json") != trivy_identity["database_metadata_sha256"]
    ):
        raise FullLocalRcError("vulnerability_scan", "Trivy scanner or database changed during the scan")
    npm_document = _trivy_document(
        npm_path,
        artifact_type="filesystem",
        artifact_name="praxis_vc_react/package-lock.json",
        required_target_suffix="package-lock.json",
    )
    python_document = _trivy_document(
        python_path,
        artifact_type="cyclonedx",
        artifact_name=python_sbom_path.name,
        required_target_suffix="Python",
    )
    if _trivy_package_components(npm_document, "npm") != expected_npm:
        raise FullLocalRcError("vulnerability_scan", "Trivy npm inventory differs from the exact lock")
    if _trivy_package_components(python_document, "python-pkg") != expected_python:
        raise FullLocalRcError("vulnerability_scan", "Trivy Python inventory differs from the exact locks")
    image_document = _trivy_document(
        image_path,
        artifact_type="container_image",
        image_id=image_id,
    )
    findings = _vulnerabilities(
        (
            ("npm_exact_lock_including_development_dependencies", npm_document),
            ("python_build_and_runtime_exact_locks", python_document),
            ("exact_runtime_oci", image_document),
        )
    )
    policy_result = _evaluate_vulnerability_policy(findings, policy)
    audit = {
        "schema_version": "praxis.vulnerability-audit.v1",
        "database": f"aquasecurity/trivy-db-v2 via trivy-{_TRIVY_VERSION}",
        "database_sha256": trivy_identity["database_sha256"],
        "database_as_of": trivy_identity["database_as_of"],
        "findings": findings,
        "status": "passed" if policy_result["blocking_finding_count"] == 0 else "failed",
    }
    _write_new_json(output / "evidence" / "vulnerability-audit.json", audit)
    _write_new_json(output / "evidence" / "vulnerability-policy-result.json", policy_result)
    if policy_result["blocking_finding_count"]:
        raise FullLocalRcError(
            "vulnerability_scan",
            f"Trivy reported {policy_result['blocking_finding_count']} findings with known remediation",
        )
    return {**audit, "policy_result": policy_result}


def _test_evidence(identity: dict[str, Any], gates: dict[str, dict[str, str]]) -> dict[str, Any]:
    if set(gates) != set(_GATES) or any(gates[name].get("status") != "passed" for name in _GATES):
        raise FullLocalRcError("test_evidence", "not every required release test gate passed")
    return {
        "schema_version": "praxis.release-test-evidence.v1",
        "source_sha": identity["source_sha"],
        "gates": {name: gates[name] for name in _GATES},
    }


def _verify_sums(bundle: Path) -> None:
    sums_path = bundle / "SHA256SUMS"
    try:
        lines = sums_path.read_text(encoding="ascii").splitlines()
    except (OSError, UnicodeError) as error:
        raise FullLocalRcError("release_bundle", "release SHA256SUMS is unreadable") from error
    observed: set[str] = set()
    for line in lines:
        digest, separator, filename = line.partition("  ")
        path = bundle / filename
        if (
            separator != "  "
            or re.fullmatch(r"[0-9a-f]{64}", digest) is None
            or not filename
            or "/" in filename
            or filename in observed
            or not path.is_file()
            or path.is_symlink()
            or _sha256_file(path) != digest
        ):
            raise FullLocalRcError("release_bundle", "release SHA256SUMS verification failed")
        observed.add(filename)
    expected = {path.name for path in bundle.iterdir() if path.name != "SHA256SUMS"}
    if observed != expected:
        raise FullLocalRcError("release_bundle", "release SHA256SUMS coverage is incomplete")


def _emit_and_verify_bundle(
    repo: Path,
    output: Path,
    identity: dict[str, Any],
    source: Path,
    wheel: Path,
    oci: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    bundle = output / "release-bundle"
    try:
        manifest = release_candidate.emit_release_metadata(
            repo=repo,
            capabilities_path=repo / "release" / "p30a" / "capability-classification.json",
            lock_paths=(
                repo / "requirements" / "build-py313.lock",
                repo / "requirements" / "runtime-py313.lock",
            ),
            npm_lock_path=repo / "praxis_vc_react" / "package-lock.json",
            wheelhouse_manifest_path=output / "wheelhouse-linux" / "wheelhouse-manifest.json",
            artifact_paths=(source, wheel, oci),
            output_dir=bundle,
            test_evidence_path=output / "evidence" / "test-evidence.json",
            wheel_comparison_path=output / "evidence" / "wheel-reproducibility.json",
            oci_comparison_path=output / "evidence" / "oci-reproducibility.json",
            vulnerability_report_path=output / "evidence" / "vulnerability-audit.json",
        )
    except release_candidate.ReleaseContractError as error:
        raise FullLocalRcError("release_bundle", str(error)) from error
    if (
        manifest.get("source_sha") != identity["source_sha"]
        or manifest.get("status") != "LOCAL_RC_INCOMPLETE"
        or manifest.get("software_rc_gates_passed") is not False
        or manifest.get("unverified_supplied_claims_complete") is not True
        or manifest.get("dependency_audit_status") != "passed"
        or manifest.get("artifact_set_complete") is not True
        or manifest.get("science_qualified_badge") is not False
        or any(manifest.get(name) is not False for name in ("published", "signed", "tag_created", "deployed"))
    ):
        raise FullLocalRcError("release_bundle", "metadata generator did not validate the complete supplied evidence")
    _verify_sums(bundle)
    manifest_path = bundle / "release-manifest.json"
    persisted = json.loads(manifest_path.read_text(encoding="utf-8"))
    if persisted != manifest:
        raise FullLocalRcError("release_bundle", "persisted release manifest differs from verified bytes")
    expected = {source.name: source, wheel.name: wheel, oci.name: oci}
    for artifact in manifest["artifacts"]:
        candidate = bundle / artifact["filename"]
        source_path = expected.get(artifact["filename"])
        if source_path is None or _sha256_file(candidate) != _sha256_file(source_path):
            raise FullLocalRcError("release_bundle", "release bundle artifact bytes drifted")
    return manifest, _file_record(manifest_path, output)


def _success_record(
    output: Path,
    identity: dict[str, Any],
    gates: dict[str, dict[str, str]],
    manifest: dict[str, Any],
    manifest_record: dict[str, Any],
    source_comparison: dict[str, Any],
    wheel_comparison: dict[str, Any],
    oci_comparison: dict[str, Any],
    vulnerability: dict[str, Any],
    trivy_identity: dict[str, Any],
    policy_record: dict[str, Any],
) -> dict[str, Any]:
    if (
        set(gates) != set(_GATES)
        or any(gates[name].get("status") != "passed" for name in _GATES)
        or source_comparison.get("identical") is not True
        or wheel_comparison.get("identical") is not True
        or oci_comparison.get("identical") is not True
        or vulnerability.get("status") != "passed"
        or manifest.get("unverified_supplied_claims_complete") is not True
    ):
        raise FullLocalRcError("acceptance", "full local RC acceptance prerequisites are incomplete")
    bundle = output / "release-bundle"
    return {
        "schema_version": "praxis.full-local-rc.v1",
        "status": "LOCAL_RC_UNPUBLISHED",
        "source": identity,
        "gates": {name: gates[name] for name in _GATES},
        "reproducibility": {
            "source_archive": source_comparison,
            "wheel": wheel_comparison,
            "oci": oci_comparison,
        },
        "release_bundle": {
            "manifest": manifest_record,
            "sha256sums": _file_record(bundle / "SHA256SUMS", output),
            "metadata_generator_status": manifest["status"],
            "metadata_generator_cannot_attest_execution": True,
            "artifacts": [_file_record(bundle / item["filename"], output) for item in manifest["artifacts"]],
        },
        "vulnerability_audit": {
            "status": vulnerability["status"],
            "policy": policy_record,
            "policy_result": vulnerability["policy_result"],
            "database_sha256": vulnerability["database_sha256"],
            "database_as_of": vulnerability["database_as_of"],
            "trivy_binary_sha256": trivy_identity["binary_sha256"],
            "database_metadata_sha256": trivy_identity["database_metadata_sha256"],
            "npm_lock_report": _file_record(output / "evidence" / "trivy-npm-lock.json", output),
            "python_lock_sbom": _file_record(
                output / "evidence" / "python-build-runtime-locks.cdx.json",
                output,
            ),
            "python_lock_report": _file_record(output / "evidence" / "trivy-python-locks.json", output),
            "image_report": _file_record(output / "evidence" / "trivy-image.json", output),
        },
        "software_rc_gates_passed": True,
        "security_supported": False,
        "science_qualified_badge": False,
        "published": False,
        "signed": False,
        "tag_created": False,
        "deployed": False,
    }


def _incomplete_record(
    identity: dict[str, Any] | None,
    gates: dict[str, dict[str, str]],
    error: FullLocalRcError,
) -> dict[str, Any]:
    return {
        "schema_version": "praxis.full-local-rc.v1",
        "status": "LOCAL_RC_INCOMPLETE",
        "source": identity,
        "gates": {
            name: gates.get(
                name,
                {"status": "not_run", "command": "not reached", "summary": "blocked by an earlier gate"},
            )
            for name in _GATES
        },
        "blocker": {"stage": error.stage, "detail": error.detail},
        "software_rc_gates_passed": False,
        "security_supported": False,
        "science_qualified_badge": False,
        "published": False,
        "signed": False,
        "tag_created": False,
        "deployed": False,
    }


def run_full_local_rc(
    *,
    output_dir: Path,
    pip_cache_root: Path,
    npm_cache_root: Path,
    trivy_path: Path,
    trivy_cache_root: Path,
) -> dict[str, Any]:
    """Build, execute, independently verify, and record one exact local RC."""

    repo = _REPO_ROOT.resolve()
    output: Path | None = None
    identity: dict[str, Any] | None = None
    gates: dict[str, dict[str, str]] = {}
    tmp: Path | None = None
    loaded_image: tuple[str, bool] | None = None
    env: dict[str, str] = {}
    roots: tuple[Path, ...] = ()
    try:
        output = _new_output(repo, output_dir)
        pip_cache = _input_directory(pip_cache_root, "pip cache")
        npm_cache = _input_directory(npm_cache_root, "npm cache")
        trivy_cache = _input_directory(trivy_cache_root, "Trivy cache")
        trivy = _input_file(trivy_path, "Trivy", executable=True)
        tmp = Path(tempfile.mkdtemp(prefix="praxis-full-local-rc.", dir="/private/tmp"))
        roots = (repo, output, tmp, pip_cache, npm_cache, trivy_cache, trivy)
        env = _environment(tmp, pip_cache, npm_cache)
        identity = _identity(repo)
        version = _product_version(repo)
        policy, policy_record = _load_vulnerability_policy(repo)
        trivy_identity = _validate_trivy(trivy, trivy_cache, env=env, roots=roots)
        source_a, _, source_comparison = _build_source_archives(repo, output, identity, version, env=env, roots=roots)
        wheel_a, _, wheel_comparison = _build_wheels(repo, output, identity, env=env, roots=roots)
        mac_wheelhouse = output / "wheelhouse-macos"
        linux_wheelhouse = output / "wheelhouse-linux"
        _materialize_wheelhouse(
            repo,
            pip_cache,
            mac_wheelhouse,
            ("requirements/build-py313.lock", "requirements/runtime-py313.lock"),
            "macos_arm64_cp313",
            identity["source_date_epoch"],
        )
        _materialize_wheelhouse(
            repo,
            pip_cache,
            linux_wheelhouse,
            ("requirements/build-py313.lock", "requirements/runtime-py313.lock"),
            "linux_arm64_cp313",
            identity["source_date_epoch"],
        )
        project_wheel = linux_wheelhouse / wheel_a.name
        shutil.copyfile(wheel_a, project_wheel)
        os.chmod(project_wheel, 0o644)
        os.utime(project_wheel, (identity["source_date_epoch"], identity["source_date_epoch"]))
        _clean_install_gate(repo, tmp, mac_wheelhouse, wheel_a, gates, env=env, roots=roots)
        test_source = tmp / "test-source"
        _clone_exact_source(repo, test_source, identity["source_sha"], env=env, roots=roots)
        _run_test_gates(
            repo,
            test_source,
            tmp,
            pip_cache,
            npm_cache,
            identity["source_date_epoch"],
            gates,
            env=env,
            roots=roots,
        )
        _verify_test_source(test_source, identity, env=env, roots=roots)
        oci_a, _, oci_comparison = _build_oci(
            repo,
            output,
            linux_wheelhouse,
            identity,
            env=env,
            roots=roots,
        )
        image_id, image_existed = _load_and_smoke_image(
            repo,
            oci_a,
            identity,
            version,
            gates,
            env=env,
            roots=roots,
        )
        loaded_image = (image_id, image_existed)
        vulnerability = _run_vulnerability_scan(
            repo,
            output,
            trivy,
            trivy_cache,
            image_id,
            trivy_identity,
            policy,
            env=env,
            roots=roots,
        )
        if not image_existed:
            _remove_loaded_image(image_id, repo=repo, env=env, roots=roots)
        loaded_image = None
        evidence = _test_evidence(identity, gates)
        _write_new_json(output / "evidence" / "test-evidence.json", evidence)
        manifest, manifest_record = _emit_and_verify_bundle(repo, output, identity, source_a, wheel_a, oci_a)
        current_identity = _identity(repo)
        if current_identity != identity:
            raise FullLocalRcError("source", "source identity changed during the full RC run")
        record = _success_record(
            output,
            identity,
            gates,
            manifest,
            manifest_record,
            source_comparison,
            wheel_comparison,
            oci_comparison,
            vulnerability,
            trivy_identity,
            policy_record,
        )
        _write_new_json(output / _RECORD_NAME, record)
        print(f"[full-rc] accepted {identity['source_sha']}", flush=True)
        return record
    except (FullLocalRcError, release_candidate.ReleaseContractError) as raw_error:
        error = (
            raw_error
            if isinstance(raw_error, FullLocalRcError)
            else FullLocalRcError("release_contract", str(raw_error))
        )
        if output is not None and not (output / _RECORD_NAME).exists():
            _write_new_json(output / _RECORD_NAME, _incomplete_record(identity, gates, error))
        if isinstance(raw_error, FullLocalRcError):
            raise
        raise error from raw_error
    finally:
        if loaded_image is not None and not loaded_image[1] and env and roots:
            _run(
                ["docker", "image", "rm", "--no-prune", loaded_image[0]],
                stage="remove_loaded_image",
                cwd=repo,
                env=env,
                roots=roots,
                check=False,
            )
        if tmp is not None and tmp.parent == Path("/private/tmp") and tmp.name.startswith("praxis-full-local-rc."):
            shutil.rmtree(tmp, ignore_errors=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pip-cache-root", type=Path, required=True)
    parser.add_argument("--npm-cache-root", type=Path, required=True)
    parser.add_argument("--trivy", type=Path, required=True)
    parser.add_argument("--trivy-cache", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        run_full_local_rc(
            output_dir=arguments.output,
            pip_cache_root=arguments.pip_cache_root,
            npm_cache_root=arguments.npm_cache_root,
            trivy_path=arguments.trivy,
            trivy_cache_root=arguments.trivy_cache,
        )
    except FullLocalRcError as error:
        print(f"full_local_rc_error[{error.stage}]: {error.detail}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
