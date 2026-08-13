from __future__ import annotations

import importlib.util
import inspect
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS = _ROOT / "scripts"
_SCRIPT = _SCRIPTS / "run_full_local_rc.py"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

_SPEC = importlib.util.spec_from_file_location("praxis_full_local_rc", _SCRIPT)
assert _SPEC and _SPEC.loader
runner = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = runner
_SPEC.loader.exec_module(runner)


def _passed_gates() -> dict[str, dict[str, str]]:
    return {name: {"status": "passed", "command": f"run {name}", "summary": f"{name} passed"} for name in runner._GATES}


def test_interface_accepts_only_local_inputs_and_no_claims() -> None:
    parsed = runner._parser().parse_args(
        [
            "--output",
            "/tmp/rc",
            "--pip-cache-root",
            "/tmp/pip",
            "--npm-cache-root",
            "/tmp/npm",
            "--trivy",
            "/tmp/trivy",
            "--trivy-cache",
            "/tmp/trivy-cache",
        ]
    )

    assert vars(parsed) == {
        "output": Path("/tmp/rc"),
        "pip_cache_root": Path("/tmp/pip"),
        "npm_cache_root": Path("/tmp/npm"),
        "trivy": Path("/tmp/trivy"),
        "trivy_cache": Path("/tmp/trivy-cache"),
    }
    assert set(inspect.signature(runner.run_full_local_rc).parameters) == {
        "output_dir",
        "pip_cache_root",
        "npm_cache_root",
        "trivy_path",
        "trivy_cache_root",
    }
    with pytest.raises(SystemExit):
        runner._parser().parse_args(
            [
                "--output",
                "/tmp/rc",
                "--pip-cache-root",
                "/tmp/pip",
                "--npm-cache-root",
                "/tmp/npm",
                "--trivy",
                "/tmp/trivy",
                "--trivy-cache",
                "/tmp/cache",
                "--status",
                "LOCAL_RC_UNPUBLISHED",
            ]
        )


def test_test_environment_does_not_leak_runner_private_praxis_settings() -> None:
    source = {
        "PATH": "/usr/bin",
        "PRAXIS_RELEASE_OFFLINE": "1",
        "PRAXIS_PIP_CACHE_ROOT": "/cache/pip",
        "PRAXIS_NPM_CACHE_ROOT": "/cache/npm",
    }

    assert runner._test_environment(source) == {"PATH": "/usr/bin"}
    assert source["PRAXIS_RELEASE_OFFLINE"] == "1"


def test_incomplete_record_never_grants_release_or_science_authority() -> None:
    error = runner.FullLocalRcError("wheel", "wheel failed")
    record = runner._incomplete_record(None, {}, error)

    assert record["status"] == "LOCAL_RC_INCOMPLETE"
    assert record["blocker"] == {"stage": "wheel", "detail": "wheel failed"}
    assert set(record["gates"]) == set(runner._GATES)
    assert all(item["status"] == "not_run" for item in record["gates"].values())
    for name in (
        "software_rc_gates_passed",
        "security_supported",
        "science_qualified_badge",
        "published",
        "signed",
        "tag_created",
        "deployed",
    ):
        assert record[name] is False


def test_vulnerability_projection_is_deterministic_and_complete() -> None:
    document = {
        "Results": [
            {
                "Target": "requirements/runtime.lock",
                "Type": "pip",
                "Vulnerabilities": [
                    {
                        "VulnerabilityID": "CVE-2099-0001",
                        "PkgName": "fixture",
                        "InstalledVersion": "1.0",
                        "FixedVersion": "1.1",
                        "Severity": "HIGH",
                    }
                ],
            }
        ]
    }

    findings = runner._vulnerabilities((("source", document),))

    assert findings == [
        {
            "scope": "source",
            "target": "requirements/runtime.lock",
            "type": "pip",
            "vulnerability_id": "CVE-2099-0001",
            "package": "fixture",
            "installed_version": "1.0",
            "fixed_version": "1.1",
            "severity": "HIGH",
            "status": "unknown",
            "data_source": "unknown",
        }
    ]
    assert runner._vulnerabilities((("source", {"Results": []}),)) == []


def test_test_evidence_requires_every_exact_gate_to_pass() -> None:
    identity = {"source_sha": "a" * 40}
    gates = _passed_gates()

    evidence = runner._test_evidence(identity, gates)

    assert evidence["source_sha"] == "a" * 40
    assert list(evidence["gates"]) == list(runner._GATES)
    gates["container"]["status"] = "failed"
    with pytest.raises(runner.FullLocalRcError, match="not every required"):
        runner._test_evidence(identity, gates)


def test_sha256sums_requires_exact_regular_file_coverage(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    artifact = bundle / "artifact.whl"
    artifact.write_bytes(b"wheel")
    digest = runner._sha256_file(artifact)
    (bundle / "SHA256SUMS").write_text(f"{digest}  artifact.whl\n", encoding="ascii")

    runner._verify_sums(bundle)

    extra = bundle / "unlisted.json"
    extra.write_text("{}\n", encoding="ascii")
    with pytest.raises(runner.FullLocalRcError, match="coverage"):
        runner._verify_sums(bundle)


def test_vulnerability_policy_records_unfixed_findings_and_blocks_known_fixes() -> None:
    policy = {
        "policy_id": "no-known-remediation-available-v1",
        "acceptance": {"blocking_rule": "any_finding_with_nonempty_fixed_version"},
    }
    unresolved = [{"fixed_version": ""}]
    result = runner._evaluate_vulnerability_policy(unresolved, policy)
    assert result == {
        "policy_id": "no-known-remediation-available-v1",
        "status": "passed_with_unresolved_unfixed_findings",
        "finding_count": 1,
        "blocking_finding_count": 0,
        "unresolved_unfixed_finding_count": 1,
        "zero_findings": False,
        "passed_does_not_mean_vulnerability_free": True,
        "security_supported": False,
    }
    assert runner._evaluate_vulnerability_policy([{"fixed_version": "1.1"}], policy)["blocking_finding_count"] == 1


def test_trivy_document_rejects_empty_or_wrong_artifact_report(tmp_path: Path) -> None:
    path = tmp_path / "report.json"
    base = {
        "SchemaVersion": 2,
        "Trivy": {"Version": runner._TRIVY_VERSION},
        "ReportID": "report-1",
        "CreatedAt": "2099-01-01T00:00:00Z",
        "ArtifactName": "package-lock.json",
        "ArtifactType": "filesystem",
        "Results": [],
    }
    path.write_text(json.dumps(base), encoding="utf-8")
    with pytest.raises(runner.FullLocalRcError, match="invalid schema"):
        runner._trivy_document(path, artifact_type="filesystem")
    base["Results"] = [{"Target": "package-lock.json", "Type": "npm", "Packages": []}]
    path.write_text(json.dumps(base), encoding="utf-8")
    with pytest.raises(runner.FullLocalRcError, match="requested artifact"):
        runner._trivy_document(path, artifact_type="filesystem", artifact_name="other.json")


def test_success_record_requires_all_executed_evidence(tmp_path: Path) -> None:
    output = tmp_path / "output"
    bundle = output / "release-bundle"
    evidence = output / "evidence"
    bundle.mkdir(parents=True)
    evidence.mkdir()
    for path in (
        bundle / "praxis-virtualcell-1.7.0.tar.gz",
        bundle / "praxis_virtualcell-1.7.0-py3-none-any.whl",
        bundle / "release.oci.tar",
        bundle / "release-manifest.json",
        bundle / "SHA256SUMS",
        evidence / "trivy-npm-lock.json",
        evidence / "python-build-runtime-locks.cdx.json",
        evidence / "trivy-python-locks.json",
        evidence / "trivy-image.json",
    ):
        path.write_bytes(b"fixture")
    manifest = {
        "unverified_supplied_claims_complete": True,
        "artifacts": [
            {"filename": "praxis-virtualcell-1.7.0.tar.gz"},
            {"filename": "praxis_virtualcell-1.7.0-py3-none-any.whl"},
            {"filename": "release.oci.tar"},
        ],
        "status": "LOCAL_RC_INCOMPLETE",
    }
    identity = {"source_sha": "a" * 40, "source_tree": "b" * 40, "source_date_epoch": 1}
    comparison = {"identical": True}
    vulnerability = {
        "status": "passed",
        "database_sha256": "c" * 64,
        "database_as_of": "2099-01-01T00:00:00Z",
        "policy_result": {
            "status": "passed_with_unresolved_unfixed_findings",
            "finding_count": 1,
            "blocking_finding_count": 0,
            "security_supported": False,
        },
    }
    trivy = {"binary_sha256": "d" * 64, "database_metadata_sha256": "e" * 64}
    policy_record = {"path": runner._VULNERABILITY_POLICY, "size": 1, "sha256": "f" * 64}

    record = runner._success_record(
        output,
        identity,
        _passed_gates(),
        manifest,
        runner._file_record(bundle / "release-manifest.json", output),
        comparison,
        comparison,
        comparison,
        vulnerability,
        trivy,
        policy_record,
    )

    assert record["status"] == "LOCAL_RC_UNPUBLISHED"
    assert record["software_rc_gates_passed"] is True
    assert record["release_bundle"]["metadata_generator_status"] == "LOCAL_RC_INCOMPLETE"
    for name in (
        "security_supported",
        "science_qualified_badge",
        "published",
        "signed",
        "tag_created",
        "deployed",
    ):
        assert record[name] is False

    failed = _passed_gates()
    failed["core"]["status"] = "failed"
    with pytest.raises(runner.FullLocalRcError, match="prerequisites"):
        runner._success_record(
            output,
            identity,
            failed,
            manifest,
            runner._file_record(bundle / "release-manifest.json", output),
            comparison,
            comparison,
            comparison,
            vulnerability,
            trivy,
            policy_record,
        )


def test_success_record_binds_release_bundle_sha256sums(tmp_path: Path) -> None:
    sums = tmp_path / "SHA256SUMS"
    sums.write_bytes(b"first\n")
    first = runner._file_record(sums, tmp_path)
    sums.write_bytes(b"second\n")
    second = runner._file_record(sums, tmp_path)
    assert first["sha256"] != second["sha256"]


def test_input_guards_reject_symlinked_scanner_and_cache(tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    cache.mkdir()
    cache_link = tmp_path / "cache-link"
    cache_link.symlink_to(cache)
    scanner = tmp_path / "trivy"
    scanner.write_text("#!/bin/sh\n", encoding="utf-8")
    scanner.chmod(0o755)
    scanner_link = tmp_path / "trivy-link"
    scanner_link.symlink_to(scanner)

    with pytest.raises(runner.FullLocalRcError, match="real directory"):
        runner._input_directory(cache_link, "cache")
    with pytest.raises(runner.FullLocalRcError, match="regular file"):
        runner._input_file(scanner_link, "Trivy", executable=True)


def test_write_new_json_never_overwrites(tmp_path: Path) -> None:
    path = tmp_path / "record.json"
    runner._write_new_json(path, {"status": "first"})
    original = path.read_bytes()

    with pytest.raises(runner.FullLocalRcError, match="write-new"):
        runner._write_new_json(path, {"status": "replacement"})
    assert path.read_bytes() == original
    assert json.loads(original) == {"status": "first"}
