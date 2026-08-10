#!/usr/bin/env python3
"""Build the independently verifiable local portion of a P30A RC record.

This runner deliberately stops before any wheel install, OCI build, publication,
signature, tag, deployment, or scientific-policy decision.  It re-runs the
controlled E2a preflight, then independently builds and inspects two source
archives from the same exact committed source.  Its output is therefore useful
negative engineering evidence, never a formal release-candidate attestation.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tomllib
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import finalize_local_rc as preflight
import release_candidate

_SCRIPT_DIR = Path(__file__).resolve().parent
_RUNNER_REPO_ROOT = _SCRIPT_DIR.parent
_SOURCE_ARCHIVE_SCRIPT = "scripts/build_release_source_archive.sh"
_RUNNER_RECORD = "local-rc-runner-record.json"
_PREFLIGHT_KEYS = frozenset(
    {
        "schema_version",
        "status",
        "source",
        "offline_boundary",
        "interpreter",
        "dependency_preflight",
        "blockers",
        "gates",
        "full_gate_execution",
        "software_rc_gates_passed",
        "science_qualified_badge",
        "published",
        "signed",
        "tag_created",
        "deployed",
    }
)


class LocalRcRunnerError(ValueError):
    """Stable fail-closed error for artifact-aware local-RC inputs."""


def _canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()


def _exact_identity(repo: Path) -> tuple[dict[str, Any] | None, str | None]:
    return preflight._exact_identity(repo)


@contextmanager
def _controlled_environment() -> Any:
    """Keep Git and the builder independent of caller-controlled process vars."""
    original = dict(os.environ)
    os.environ.clear()
    os.environ.update({"PATH": os.defpath, "LC_ALL": "C", "LANG": "C", "TZ": "UTC"})
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(original)


def _product_version(repo: Path) -> str:
    try:
        source = release_candidate._head_blob_bytes(repo, "pyproject.toml")
        value = tomllib.loads(source.decode("utf-8"))["project"]["version"]
    except (KeyError, UnicodeError, tomllib.TOMLDecodeError, release_candidate.ReleaseContractError) as error:
        raise LocalRcRunnerError("exact HEAD product version is unavailable") from error
    if type(value) is not str or not value:
        raise LocalRcRunnerError("exact HEAD product version is unavailable")
    return value


def _load_preflight_record(
    path: Path,
    *,
    expected_pre_exact: dict[str, Any] | None,
    expected_post_exact: dict[str, Any] | None,
) -> dict[str, Any]:
    try:
        raw = release_candidate._load_json(path)
    except release_candidate.ReleaseContractError as error:
        raise LocalRcRunnerError("controlled preflight record is unreadable") from error
    if (
        type(raw) is not dict
        or set(raw) != _PREFLIGHT_KEYS
        or raw.get("schema_version") != "praxis.local-rc-finalizer-preflight.v1"
        or raw.get("status") != "LOCAL_RC_INCOMPLETE"
        or type(raw.get("blockers")) is not list
    ):
        raise LocalRcRunnerError("controlled preflight record is invalid")
    source = raw["source"]
    offline = raw["offline_boundary"]
    dependency = raw["dependency_preflight"]
    gates = raw["gates"]
    if (
        type(source) is not dict
        or set(source)
        != {
            "pre_exact",
            "post_exact",
            "pre_observed",
            "post_observed",
            "observed_stable_during_preflight",
            "not_attestation",
            "future_execution_must_reverify",
        }
        or source["pre_exact"] != expected_pre_exact
        or source["post_exact"] != expected_post_exact
        or source["observed_stable_during_preflight"]
        is not (expected_pre_exact is not None and expected_pre_exact == expected_post_exact)
        or source["not_attestation"] is not True
        or source["future_execution_must_reverify"] is not True
        or type(offline) is not dict
        or set(offline)
        != {
            "network_used",
            "pip_install_policy",
            "npm_install_policy",
            "oci_build_policy",
        }
        or offline["network_used"] is not False
        or offline["pip_install_policy"] != "no_index_require_hashes_required_for_future_execution"
        or offline["npm_install_policy"] != "offline_required_for_future_execution"
        or offline["oci_build_policy"] != "network_none_pull_false_required_for_future_execution"
        or type(dependency) is not dict
        or set(dependency) != {"python_wheelhouses", "npm_cache"}
        or raw["full_gate_execution"] != "PRECHECK_ONLY_NOT_EXECUTED"
        or any(
            raw[name] is not False
            for name in (
                "software_rc_gates_passed",
                "science_qualified_badge",
                "published",
                "signed",
                "tag_created",
                "deployed",
            )
        )
        or type(gates) is not dict
        or set(gates) != set(preflight._GATE_NAMES)
        or any(
            type(gate) is not dict or gate.get("status") not in {"not_run", "blocked_dependency"}
            for gate in gates.values()
        )
        or any(type(item) is not dict or type(item.get("code")) is not str for item in raw["blockers"])
    ):
        raise LocalRcRunnerError("controlled preflight record violates negative invariants")
    return raw


def _write_new_runner_record(output: Path, record: dict[str, Any]) -> Path:
    if not output.is_dir() or output.is_symlink():
        raise LocalRcRunnerError("local RC output directory is unavailable")
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if nofollow is None:
        raise LocalRcRunnerError("platform lacks safe no-follow record creation")
    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | nofollow
    try:
        directory_fd = os.open(output, directory_flags)
    except OSError as error:
        raise LocalRcRunnerError("local RC output directory is unavailable") from error
    try:
        try:
            record_fd = os.open(
                _RUNNER_RECORD,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | nofollow,
                0o600,
                dir_fd=directory_fd,
            )
        except FileExistsError as error:
            raise LocalRcRunnerError("local RC runner record already exists") from error
        try:
            with os.fdopen(record_fd, "wb") as stream:
                stream.write(_canonical_json_bytes(record))
                stream.flush()
                os.fchmod(stream.fileno(), 0o644)
        except OSError as error:
            raise LocalRcRunnerError("unable to write local RC runner record") from error
    finally:
        os.close(directory_fd)
    return output / _RUNNER_RECORD


def _new_controlled_directory(parent: Path, name: str) -> Path:
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if nofollow is None:
        raise LocalRcRunnerError("platform lacks safe no-follow artifact directory creation")
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | nofollow
    try:
        parent_fd = os.open(parent, flags)
    except OSError as error:
        raise LocalRcRunnerError("controlled artifact parent is unavailable") from error
    try:
        try:
            os.mkdir(name, 0o700, dir_fd=parent_fd)
        except FileExistsError as error:
            raise LocalRcRunnerError("controlled artifact directory already exists") from error
        try:
            child_fd = os.open(name, flags, dir_fd=parent_fd)
        except OSError as error:
            raise LocalRcRunnerError("controlled artifact directory is unavailable") from error
        else:
            os.close(child_fd)
    finally:
        os.close(parent_fd)
    return parent / name


def _snapshot_builder(repo: Path) -> tuple[bytes, str]:
    try:
        release_candidate._require_exact_head_file(repo, repo / _SOURCE_ARCHIVE_SCRIPT, _SOURCE_ARCHIVE_SCRIPT)
        content = release_candidate._head_blob_bytes(repo, _SOURCE_ARCHIVE_SCRIPT)
    except release_candidate.ReleaseContractError as error:
        raise LocalRcRunnerError("source archive builder is not an exact HEAD input") from error
    return content, release_candidate._sha256_bytes(content)


def _build_source_archive(
    *,
    repo: Path,
    destination: Path,
    source_sha: str,
    product_version: str,
    builder_snapshot: bytes,
    builder_sha256: str,
) -> dict[str, Any]:
    result = subprocess.run(
        ["/bin/bash", "-s", "--", str(destination)],
        cwd=repo,
        env={
            "PATH": os.defpath,
            "LC_ALL": "C",
            "LANG": "C",
            "TZ": "UTC",
            "PYTHON_BIN": sys.executable,
            "PRAXIS_SOURCE_ARCHIVE_ROOT": str(repo),
            "PRAXIS_SOURCE_ARCHIVE_REF": source_sha,
        },
        capture_output=True,
        check=False,
        input=builder_snapshot,
    )
    command_identity = {
        "exit_code": result.returncode,
        "stdout_sha256": release_candidate._sha256_bytes(result.stdout),
        "stderr_sha256": release_candidate._sha256_bytes(result.stderr),
    }
    if result.returncode != 0:
        return {"status": "failed", "reason_code": "source_archive_build_failed", "command": command_identity}
    try:
        inspected = release_candidate._inspect_release_artifact(
            destination,
            product_version,
            repo=repo,
            source_sha=source_sha,
        )
    except release_candidate.ReleaseContractError:
        return {
            "status": "failed",
            "reason_code": "source_archive_inspection_failed",
            "command": command_identity,
        }
    return {
        "status": "passed_engineering_evidence_only",
        "builder_sha256": builder_sha256,
        "command": command_identity,
        "size": destination.stat().st_size,
        "sha256": release_candidate._sha256_file(destination),
        **inspected,
    }


def _source_archive_record(
    *,
    repo: Path,
    output: Path,
    source: dict[str, Any] | None,
) -> dict[str, Any]:
    if source is None:
        return {"status": "blocked_dependency", "reason_code": "source_not_clean_exact_head"}
    try:
        version = _product_version(repo)
    except LocalRcRunnerError:
        return {"status": "blocked_dependency", "reason_code": "product_version_unavailable"}
    name = f"praxis-virtualcell-{version}.tar.gz"
    try:
        artifacts = _new_controlled_directory(output, "artifacts")
        first_path = _new_controlled_directory(artifacts, "source-one") / name
        second_path = _new_controlled_directory(artifacts, "source-two") / name
    except LocalRcRunnerError:
        return {"status": "blocked_dependency", "reason_code": "controlled_artifact_directory_unavailable"}
    try:
        builder_snapshot, builder_sha256 = _snapshot_builder(repo)
    except LocalRcRunnerError:
        return {
            "status": "blocked_dependency",
            "reason_code": "source_archive_builder_snapshot_unavailable",
        }
    first = _build_source_archive(
        repo=repo,
        destination=first_path,
        source_sha=source["source_sha"],
        product_version=version,
        builder_snapshot=builder_snapshot,
        builder_sha256=builder_sha256,
    )
    second = _build_source_archive(
        repo=repo,
        destination=second_path,
        source_sha=source["source_sha"],
        product_version=version,
        builder_snapshot=builder_snapshot,
        builder_sha256=builder_sha256,
    )
    for item, path in ((first, first_path), (second, second_path)):
        if item.get("status") == "passed_engineering_evidence_only":
            item["relative_path"] = str(path.relative_to(output))
    if (
        first.get("status") != "passed_engineering_evidence_only"
        or second.get("status") != "passed_engineering_evidence_only"
    ):
        return {"status": "failed", "first": first, "second": second}
    identical = first["sha256"] == second["sha256"] and first["size"] == second["size"]
    return {
        "status": "passed_engineering_evidence_only" if identical else "failed",
        "reason_code": "byte_identical" if identical else "byte_drift_detected",
        "product_version": version,
        "first": first,
        "second": second,
    }


def _preflight_summary(record: dict[str, Any], path: Path) -> dict[str, Any]:
    codes = sorted(
        str(item["code"]) for item in record["blockers"] if type(item) is dict and type(item.get("code")) is str
    )
    return {
        "schema_version": record["schema_version"],
        "status": record["status"],
        "record_sha256": release_candidate._sha256_file(path),
        "blocker_codes": codes,
    }


def run_local_rc(
    *,
    output_dir: Path,
    pip_cache_root: Path | None = None,
    npm_cache_root: Path | None = None,
) -> dict[str, Any]:
    """Create an artifact-aware but always-incomplete local RC record.

    The closed interface intentionally has no artifact, evidence, result,
    status, release, or policy inputs.  A later full runner must independently
    revalidate this source and execute all required gates in one controlled
    window before it can ever form a formal local RC.
    """
    repo = _RUNNER_REPO_ROOT.resolve()
    with _controlled_environment():
        output = preflight._safe_output_dir(repo, output_dir)
        before_exact, _ = _exact_identity(repo)
        preflight_path = output / "preflight" / "finalizer-record.json"
        preflight.finalize_local_rc(
            output_dir=output / "preflight",
            pip_cache_root=pip_cache_root,
            npm_cache_root=npm_cache_root,
        )
        after_preflight_exact, _ = _exact_identity(repo)
        preflight_record = _load_preflight_record(
            preflight_path,
            expected_pre_exact=before_exact,
            expected_post_exact=after_preflight_exact,
        )
        source_before_archive = before_exact if before_exact == after_preflight_exact else None
        archive = _source_archive_record(repo=repo, output=output, source=source_before_archive)
        after_exact, _ = _exact_identity(repo)
    source_stable = before_exact is not None and before_exact == after_preflight_exact and before_exact == after_exact
    if before_exact is not None and not source_stable:
        archive = {
            "status": "invalidated_source_drift",
            "reason_code": "source_identity_changed_during_runner",
            "built_artifacts": archive,
        }
    record = {
        "schema_version": "praxis.local-rc-artifact-aware-runner.v1",
        "status": "LOCAL_RC_INCOMPLETE",
        "source": {
            "pre_exact": before_exact,
            "post_exact": after_exact,
            "observed_stable_during_runner": source_stable,
            "future_full_runner_must_reverify": True,
        },
        "preflight": _preflight_summary(preflight_record, preflight_path),
        "artifacts": {"source_archive": archive},
        "full_gate_execution": "SOURCE_ARCHIVE_ONLY_NOT_FULL_RC",
        "software_rc_gates_passed": False,
        "science_qualified_badge": False,
        "published": False,
        "signed": False,
        "tag_created": False,
        "deployed": False,
        "policy_decision_created": False,
    }
    _write_new_runner_record(output, record)
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
        record = run_local_rc(
            output_dir=arguments.output,
            pip_cache_root=arguments.pip_cache_root,
            npm_cache_root=arguments.npm_cache_root,
        )
    except (LocalRcRunnerError, preflight.FinalizerError) as error:
        print(f"local_rc_runner_error: {error}", file=sys.stderr)
        return 2
    print(release_candidate._sha256_bytes(_canonical_json_bytes(record)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
