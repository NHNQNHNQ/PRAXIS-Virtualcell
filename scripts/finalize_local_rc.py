#!/usr/bin/env python3
"""Offline P30A local-RC preflight with a write-new negative result record.

This is intentionally a preflight, not a release command.  It never downloads,
publishes, signs, pushes, tags, deploys, builds an OCI image, or accepts
caller-supplied artifacts or test evidence.  A later runner may execute the
artifact-aware gates after independently revalidating the source; this
preflight can only leave a local RC incomplete.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import release_candidate

_SCRIPT_DIR = Path(__file__).resolve().parent
_FINALIZER_REPO_ROOT = _SCRIPT_DIR.parent
_LOCK_RELATIVES = (
    "requirements/build-py313.lock",
    "requirements/runtime-py313.lock",
)
_WHEELHOUSE_PROFILES = ("macos_arm64_cp313", "linux_arm64_cp313")
_PROTECTED_OUTPUT_ROOTS = (
    Path("/Volumes/T7/PRAXIS-virtualcell/old"),
    Path("/Users/mzy/Projects/PRAXIS-virtualcell-p9"),
    Path("/Users/mzy/Projects/PRAXIS-virtualcell"),
    Path("/Users/mzy/Projects/PRAXIS-virtualcell-recovery-20260718"),
)
_GATE_NAMES = (
    "core",
    "legacy",
    "frontend",
    "ruff",
    "pip_check",
    "packaging",
    "wheel",
    "source_archive",
    "container",
)
_FORBIDDEN_OUTPUT_ROOTS = (".git",)


class FinalizerError(ValueError):
    """Stable fail-closed error for finalizer invocation inputs."""


def _canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()


def _git_output(repo: Path, *arguments: str) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(repo), *arguments],
        capture_output=True,
        check=False,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _observed_identity(repo: Path) -> dict[str, Any]:
    return {
        "head": _git_output(repo, "rev-parse", "HEAD"),
        "tree": _git_output(repo, "rev-parse", "HEAD^{tree}"),
        "epoch": _git_output(repo, "show", "-s", "--format=%ct", "HEAD"),
    }


def _exact_identity(repo: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        source_sha, source_tree, source_epoch = release_candidate._require_clean_committed_repo(repo)
    except release_candidate.ReleaseContractError as error:
        return None, str(error)
    return {
        "source_sha": source_sha,
        "source_tree": source_tree,
        "source_date_epoch": source_epoch,
    }, None


def _safe_output_dir(repo: Path, output_dir: Path) -> Path:
    if not output_dir.is_absolute():
        raise FinalizerError("finalizer output must be an absolute out-of-tree directory")
    if output_dir.exists() or output_dir.is_symlink():
        raise FinalizerError("finalizer output must be write-new and absent")
    parent = output_dir.parent
    if not parent.is_dir():
        raise FinalizerError("finalizer output parent must be an existing directory")
    resolved_parent = parent.resolve()
    resolved = resolved_parent / output_dir.name
    repo_root = repo.resolve()
    git_dir_text = _git_output(repo_root, "rev-parse", "--absolute-git-dir")
    if git_dir_text is None:
        raise FinalizerError("finalizer repository is not a Git worktree")
    forbidden = (
        repo_root,
        Path(git_dir_text).resolve(),
        *(root.resolve() for root in _PROTECTED_OUTPUT_ROOTS),
    )
    for root in forbidden:
        if resolved == root or root in resolved.parents:
            raise FinalizerError("finalizer output must be outside source, Git metadata, and protected roots")
    if any(part in _FORBIDDEN_OUTPUT_ROOTS for part in resolved.parts):
        raise FinalizerError("finalizer output path is unsafe")
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if nofollow is None:
        raise FinalizerError("platform lacks safe no-follow output creation")
    try:
        parent_fd = os.open(
            resolved_parent,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | nofollow,
        )
    except OSError as error:
        raise FinalizerError("finalizer output parent is unavailable") from error
    try:
        try:
            os.mkdir(output_dir.name, 0o700, dir_fd=parent_fd)
        except FileExistsError as error:
            raise FinalizerError("finalizer output must be write-new and absent") from error
    finally:
        os.close(parent_fd)
    return resolved


def _cache_root(
    explicit: Path | None,
    *,
    command: tuple[str, ...],
    label: str,
) -> tuple[Path | None, str | None]:
    if explicit is not None:
        if not explicit.is_absolute():
            return None, f"{label} must be an absolute directory"
        candidate = explicit.resolve()
    else:
        result = subprocess.run(command, capture_output=True, check=False, text=True)
        if result.returncode != 0 or not result.stdout.strip():
            return None, f"{label} query failed"
        candidate = Path(result.stdout.strip()).resolve()
    if not candidate.is_dir():
        return None, f"{label} is unavailable"
    return candidate, None


def _blocker(
    *,
    code: str,
    dependency: str,
    detail: str,
    target_profile: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "code": code,
        "dependency": dependency,
        "detail": detail,
    }
    if target_profile is not None:
        result["target_profile"] = target_profile
    return result


def _gate_records(blockers: list[dict[str, Any]], *, npm_cache_available: bool) -> dict[str, dict[str, Any]]:
    blocker_codes = {str(blocker["code"]) for blocker in blockers}
    root_blocked = bool(
        blocker_codes
        & {
            "python_interpreter_not_cpython313",
            "source_not_clean_exact_head",
            "source_identity_changed_during_preflight",
            "lock_not_exact_head",
        }
    )
    records = {name: {"status": "not_run", "reason_code": "precheck_only_not_executed"} for name in _GATE_NAMES}
    if root_blocked:
        return {
            name: {
                "status": "blocked_dependency",
                "reason_code": "source_or_interpreter_preflight_failed",
            }
            for name in _GATE_NAMES
        }
    if not npm_cache_available:
        records["frontend"] = {
            "status": "blocked_dependency",
            "reason_code": "offline_npm_cache_unavailable",
        }
    wheel_cache_unavailable = "offline_wheel_cache_unavailable" in blocker_codes
    macos_wheelhouse_incomplete = any(
        blocker.get("code") == "offline_wheel_cache_incomplete" and blocker.get("target_profile") == "macos_arm64_cp313"
        for blocker in blockers
    )
    linux_wheelhouse_incomplete = any(
        blocker.get("code") == "offline_wheel_cache_incomplete" and blocker.get("target_profile") == "linux_arm64_cp313"
        for blocker in blockers
    )
    if wheel_cache_unavailable or macos_wheelhouse_incomplete:
        records["wheel"] = {
            "status": "blocked_dependency",
            "reason_code": (
                "offline_wheel_cache_unavailable" if wheel_cache_unavailable else "offline_wheel_cache_incomplete"
            ),
        }
    elif not npm_cache_available:
        records["wheel"] = {
            "status": "blocked_dependency",
            "reason_code": "offline_npm_cache_unavailable",
        }
    if wheel_cache_unavailable or linux_wheelhouse_incomplete:
        records["container"] = {
            "status": "blocked_dependency",
            "reason_code": (
                "offline_wheel_cache_unavailable" if wheel_cache_unavailable else "offline_wheel_cache_incomplete"
            ),
        }
    elif not npm_cache_available:
        records["container"] = {
            "status": "blocked_dependency",
            "reason_code": "offline_npm_cache_unavailable",
        }
    else:
        records["container"] = {
            "status": "not_run",
            "reason_code": "artifact_aware_oci_smoke_not_implemented",
        }
    return records


def _write_new_record(output_dir: Path, record: dict[str, Any]) -> Path:
    if not output_dir.is_dir() or output_dir.is_symlink():
        raise FinalizerError("finalizer output directory is unavailable")
    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if nofollow is None:
        raise FinalizerError("platform lacks safe no-follow record creation")
    try:
        directory_fd = os.open(output_dir, directory_flags | nofollow)
    except OSError as error:
        raise FinalizerError("finalizer output directory is unavailable") from error
    try:
        try:
            record_fd = os.open(
                "finalizer-record.json",
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | nofollow,
                0o600,
                dir_fd=directory_fd,
            )
        except FileExistsError as error:
            raise FinalizerError("finalizer record already exists") from error
        try:
            with os.fdopen(record_fd, "wb") as handle:
                handle.write(_canonical_json_bytes(record))
                handle.flush()
                os.fchmod(handle.fileno(), 0o644)
        except OSError as error:
            raise FinalizerError("unable to write finalizer record") from error
    finally:
        os.close(directory_fd)
    return output_dir / "finalizer-record.json"


def finalize_local_rc(
    *,
    output_dir: Path,
    pip_cache_root: Path | None = None,
    npm_cache_root: Path | None = None,
) -> dict[str, Any]:
    """Write a controlled, always-incomplete local RC preflight record.

    Cache paths are only local, hash-validated dependency inputs.  No artifact,
    test-evidence, comparison, status, source, or policy parameter is accepted.
    """
    repo = _FINALIZER_REPO_ROOT.resolve()
    output = _safe_output_dir(repo, output_dir)
    before_observed = _observed_identity(repo)
    before_exact, source_error = _exact_identity(repo)
    blockers: list[dict[str, Any]] = []
    wheelhouses: dict[str, dict[str, Any]] = {}
    npm_cache: Path | None = None
    npm_status: dict[str, Any]

    interpreter_ok = sys.implementation.name == "cpython" and sys.version_info[:2] == (3, 13)
    if not interpreter_ok:
        blockers.append(
            _blocker(
                code="python_interpreter_not_cpython313",
                dependency="release_interpreter",
                detail=f"observed {sys.implementation.name} {sys.version.split()[0]}",
            )
        )

    if before_exact is None:
        blockers.append(
            _blocker(
                code="source_not_clean_exact_head",
                dependency="exact_committed_source",
                detail=source_error or "source identity is unavailable",
            )
        )
        npm_status = {"status": "not_checked", "reason_code": "source_not_clean_exact_head"}
    else:
        locks: list[Path] = []
        try:
            for relative in _LOCK_RELATIVES:
                locks.append(release_candidate._require_exact_head_file(repo, repo / relative, relative))
        except release_candidate.ReleaseContractError as error:
            blockers.append(
                _blocker(
                    code="lock_not_exact_head",
                    dependency="hash_locked_dependencies",
                    detail=str(error),
                )
            )

        cache, cache_error = _cache_root(
            pip_cache_root,
            command=(sys.executable, "-m", "pip", "cache", "dir"),
            label="pip cache root",
        )
        npm_cache, npm_error = _cache_root(
            npm_cache_root,
            command=("npm", "config", "get", "cache"),
            label="npm cache root",
        )
        npm_status = (
            {
                "status": "path_available_not_coverage_validated",
                "identity": "local_cache_path_not_serialized",
            }
            if npm_cache is not None
            else {"status": "blocked_dependency", "detail": npm_error}
        )
        if cache is None:
            blockers.append(
                _blocker(
                    code="offline_wheel_cache_unavailable",
                    dependency="hash_locked_python_wheels",
                    detail=cache_error or "pip cache root is unavailable",
                )
            )
        if npm_cache is None:
            blockers.append(
                _blocker(
                    code="offline_npm_cache_unavailable",
                    dependency="locked_frontend_packages",
                    detail=npm_error or "npm cache root is unavailable",
                )
            )
        if cache is not None and len(locks) == len(_LOCK_RELATIVES) and interpreter_ok:
            for profile in _WHEELHOUSE_PROFILES:
                wheelhouse = output / "preflight" / f"wheelhouse-{profile}"
                try:
                    manifest = release_candidate.materialize_wheelhouse(
                        lock_paths=tuple(locks),
                        cache_root=cache,
                        output_dir=wheelhouse,
                        source_date_epoch=before_exact["source_date_epoch"],
                        target_profile=profile,
                    )
                except release_candidate.ReleaseContractError as error:
                    detail = str(error)
                    wheelhouses[profile] = {"status": "blocked_dependency", "detail": detail}
                    blockers.append(
                        _blocker(
                            code="offline_wheel_cache_incomplete",
                            dependency="hash_locked_python_wheels",
                            detail=detail,
                            target_profile=profile,
                        )
                    )
                else:
                    manifest_path = wheelhouse / "wheelhouse-manifest.json"
                    wheelhouses[profile] = {
                        "status": "available",
                        "manifest_sha256": release_candidate._sha256_file(manifest_path),
                        "component_count": len(manifest["components"]),
                    }

    after_observed = _observed_identity(repo)
    after_exact, after_error = _exact_identity(repo)
    source_stable = before_exact is not None and before_exact == after_exact
    if before_exact is not None and not source_stable:
        blockers.append(
            _blocker(
                code="source_identity_changed_during_preflight",
                dependency="exact_committed_source",
                detail=after_error or "source HEAD/tree/clean state changed during preflight",
            )
        )

    record = {
        "schema_version": "praxis.local-rc-finalizer-preflight.v1",
        "status": "LOCAL_RC_INCOMPLETE",
        "source": {
            "pre_exact": before_exact,
            "post_exact": after_exact,
            "pre_observed": before_observed,
            "post_observed": after_observed,
            "observed_stable_during_preflight": source_stable,
            "not_attestation": True,
            "future_execution_must_reverify": True,
        },
        "offline_boundary": {
            "network_used": False,
            "pip_install_policy": "no_index_require_hashes_required_for_future_execution",
            "npm_install_policy": "offline_required_for_future_execution",
            "oci_build_policy": "network_none_pull_false_required_for_future_execution",
        },
        "interpreter": {
            "implementation": sys.implementation.name,
            "version": sys.version.split()[0],
            "exact_cpython313": interpreter_ok,
        },
        "dependency_preflight": {
            "python_wheelhouses": wheelhouses,
            "npm_cache": npm_status,
        },
        "blockers": blockers,
        "gates": _gate_records(blockers, npm_cache_available=npm_cache is not None),
        "full_gate_execution": "PRECHECK_ONLY_NOT_EXECUTED",
        "software_rc_gates_passed": False,
        "science_qualified_badge": False,
        "published": False,
        "signed": False,
        "tag_created": False,
        "deployed": False,
    }
    _write_new_record(output, record)
    return record


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pip-cache-root", type=Path)
    parser.add_argument("--npm-cache-root", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        record = finalize_local_rc(
            output_dir=arguments.output,
            pip_cache_root=arguments.pip_cache_root,
            npm_cache_root=arguments.npm_cache_root,
        )
    except FinalizerError as error:
        print(f"release_finalizer_error: {error}", file=sys.stderr)
        return 2
    print(release_candidate._sha256_bytes(_canonical_json_bytes(record)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
