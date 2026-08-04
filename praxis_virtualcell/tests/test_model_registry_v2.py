"""P12 Model Registry v2 strict identities, migration, and lifecycle gates."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from praxis_virtualcell.model_zoo.capability_registry import (
    CompatibilityReportV2,
    ExecutionPlanV2,
    ExecutionStepV2,
)
from praxis_virtualcell.model_zoo.registry import ModelZooRegistry
from praxis_virtualcell.model_zoo.registry_v2 import (
    AdapterIdentity,
    ArtifactIdentity,
    EnvironmentIdentity,
    LegacyMigrationReceipt,
    ModelRegistryV2,
    ModelReleaseRecord,
    OperatorPolicyRecord,
    RegistryLifecycleEvent,
    ValidationEvidence,
    legacy_migration_report,
)

_ROOT = Path(__file__).resolve().parents[2]
_FIXTURE = Path(__file__).parent / "fixtures" / "model_registry_v2" / "legacy_migration.json"


def _event(
    registry: ModelRegistryV2,
    action: str,
    release_fingerprint: str,
    *,
    target_release_fingerprint: str | None = None,
) -> RegistryLifecycleEvent:
    return RegistryLifecycleEvent.from_dict(
        {
            "schema_version": "vc.model-registry-event.v1",
            "event_id": f"event-{len(registry.lifecycle_events) + 1}",
            "sequence": len(registry.lifecycle_events) + 1,
            "previous_event_fingerprint": (
                registry.lifecycle_events[-1].fingerprint()
                if registry.lifecycle_events
                else None
            ),
            "release_fingerprint": release_fingerprint,
            "action": action,
            "target_release_fingerprint": target_release_fingerprint,
            "recorded_at": "2026-08-02T00:00:00Z",
            "operator_id": "test-only-operator",
            "reason": "contract conformance fixture only",
        }
    )


def _install_release(payload: dict, value: dict) -> ModelReleaseRecord:
    release = ModelReleaseRecord.from_dict(value)
    payload["releases"][0] = release.to_dict()
    payload["lifecycle_events"][0]["release_fingerprint"] = release.fingerprint()
    return release


def _complete_v2_report_payload() -> dict:
    return {
        "schema_version": "vc.compatibility-report.v2",
        "request_id": "test-request",
        "request_fingerprint": "1" * 64,
        "model_name": "test_model",
        "model_version": "1.0.0",
        "model_fingerprint": "2" * 64,
        "release_fingerprint": "3" * 64,
        "capability_fingerprint": "4" * 64,
        "pack_id": "test-pack",
        "pack_version": "1.0.0",
        "pack_fingerprint": "5" * 64,
        "environment_fingerprint": "6" * 64,
        "environment_snapshot_fingerprint": "7" * 64,
        "artifact_fingerprints": ["8" * 64],
        "adapter_fingerprints": ["9" * 64],
        "evidence_fingerprints": ["a" * 64],
        "policy_fingerprint": "b" * 64,
        "cataloged": True,
        "artifact_ready": True,
        "revoked": False,
        "superseded_by": None,
        "pack_valid": True,
        "model_compatible": True,
        "environment_compatible": True,
        "adapter_compatible": True,
        "assets_ready": True,
        "wrapper_ready": True,
        "benchmark_passed": True,
        "scientifically_validated": True,
        "promotion_eligible": True,
        "policy_present": True,
        "production_promoted": True,
        "executable": True,
        "checks": {},
        "reasons": [],
        "asset_paths": {},
    }


def complete_registry_payload(*, promoted: bool = True) -> dict:
    """Return a complete test-only v2 graph; it is not scientific evidence."""
    model_fingerprint = "1" * 64
    pack_fingerprint = "2" * 64
    artifact = ArtifactIdentity.from_dict(
        {
            "schema_version": "vc.model-artifact.v1",
            "artifact_id": "test-model:model.bin",
            "model_fingerprint": model_fingerprint,
            "uri": "https://private.invalid/model.bin",
            "cache_key": "test_model/model.bin",
            "size_bytes": 17,
            "sha256": "3" * 64,
            "media_type": "application/octet-stream",
            "license": "CC0-1.0",
            "source": (
                "/private/source C:\\Users\\secret \\\\server\\share "
                "file:///tmp/secret token=secret"
            ),
            "safe_load_policy": "data_only",
            "legacy_incomplete": False,
        }
    )
    adapter = AdapterIdentity.from_dict(
        {
            "schema_version": "vc.model-adapter.v1",
            "adapter_id": "delta-expression-runtime",
            "version": "1.0.0",
            "implementation": "private.adapter.DeltaExpressionAdapter",
            "task": "predict_delta_expression",
            "outputs": ["delta_expression"],
            "input_contract_fingerprint": "4" * 64,
            "output_contract_fingerprint": "5" * 64,
            "legacy_incomplete": False,
        }
    )
    environment = EnvironmentIdentity.from_dict(
        {
            "schema_version": "vc.model-environment.v1",
            "environment_id": "test-cpu-lock",
            "python_version": "3.13.5",
            "cpu_architecture": "arm64",
            "packages": [{"name": "pydantic", "version": "2.11.7"}],
            "lock_digest": "6" * 64,
            "image_digest": None,
            "resources": ["cpu"],
            "accelerators": [],
            "adapter_fingerprints": [adapter.fingerprint()],
            "legacy_incomplete": False,
        }
    )
    evidence = ValidationEvidence.from_dict(
        {
            "schema_version": "vc.model-validation-evidence.v1",
            "evidence_id": "test-only-positive-evidence",
            "pack_fingerprint": pack_fingerprint,
            "model_fingerprint": model_fingerprint,
            "environment_fingerprint": environment.fingerprint(),
            "adapter_fingerprints": [adapter.fingerprint()],
            "protocol_fingerprint": "7" * 64,
            "baseline_fingerprint": "8" * 64,
            "metric_name": "test_only_loss",
            "metric_direction": "lower_is_better",
            "result_sha256": "9" * 64,
            "benchmark_passed": promoted,
            "scientifically_validated": promoted,
            "promotion_eligible": promoted,
            "legacy_incomplete": False,
            "binding_errors": [],
        }
    )
    release_without_policy = ModelReleaseRecord.from_dict(
        {
            "schema_version": "vc.model-release.v1",
            "release_id": "test-model@1.0.0",
            "model_name": "test_model",
            "model_version": "1.0.0",
            "model_fingerprint": model_fingerprint,
            "pack_fingerprints": [pack_fingerprint],
            "artifact_fingerprints": [artifact.fingerprint()],
            "environment_fingerprint": environment.fingerprint(),
            "adapter_fingerprints": [adapter.fingerprint()],
            "evidence_fingerprints": [evidence.fingerprint()],
            "policy_fingerprint": None,
            "migration_status": "native",
            "legacy_status": None,
            "incomplete_reasons": [],
        }
    )
    policy = OperatorPolicyRecord.from_dict(
        {
            "schema_version": "vc.model-operator-policy.v1",
            "policy_id": "test-only-policy",
            "capability_fingerprint": release_without_policy.capability_fingerprint(),
            "evidence_fingerprints": [evidence.fingerprint()],
            "production_promoted": promoted,
            "decision_kind": "operator_decision",
            "operator_id": "test-only-operator",
            "decided_at": "2026-08-02T00:00:00Z",
            "reason": "contract conformance fixture only",
        }
    )
    release = ModelReleaseRecord.from_dict(
        {
            **release_without_policy.to_dict(),
            "policy_fingerprint": policy.fingerprint(),
        }
    )
    event = RegistryLifecycleEvent.from_dict(
        {
            "schema_version": "vc.model-registry-event.v1",
            "event_id": "event-1",
            "sequence": 1,
            "previous_event_fingerprint": None,
            "release_fingerprint": release.fingerprint(),
            "action": "cataloged",
            "target_release_fingerprint": None,
            "recorded_at": "2026-08-02T00:00:00Z",
            "operator_id": "test-only-operator",
            "reason": "contract conformance fixture only",
        }
    )
    return {
        "schema_version": "vc.model-registry.v2",
        "artifacts": [artifact.to_dict()],
        "environments": [environment.to_dict()],
        "adapters": [adapter.to_dict()],
        "evidence_records": [evidence.to_dict()],
        "policy_records": [policy.to_dict()],
        "releases": [release.to_dict()],
        "lifecycle_events": [event.to_dict()],
    }


def test_complete_graph_roundtrips_is_frozen_and_fingerprinted():
    registry = ModelRegistryV2.from_dict(complete_registry_payload())

    assert registry == ModelRegistryV2.from_dict(registry.to_dict())
    assert registry.fingerprint() == ModelRegistryV2.from_dict(registry.to_dict()).fingerprint()
    assert len(registry.release(registry.releases[0].fingerprint()).fingerprint()) == 64
    assert registry.policy(registry.policy_records[0].fingerprint()).production_promoted is True
    with pytest.raises(ValidationError):
        registry.schema_version = "changed"  # type: ignore[misc]


def test_v2_report_rejects_promoted_state_without_bound_passing_evidence():
    unavailable = _complete_v2_report_payload()
    unavailable.update(
        {
            "evidence_fingerprints": [],
            "benchmark_passed": None,
            "scientifically_validated": None,
            "promotion_eligible": None,
        }
    )
    with pytest.raises(ValueError, match="bound passing scientific evidence"):
        CompatibilityReportV2.from_dict(unavailable)

    failed = _complete_v2_report_payload()
    failed.update(
        {
            "benchmark_passed": False,
            "scientifically_validated": False,
            "promotion_eligible": False,
        }
    )
    with pytest.raises(ValueError, match="bound passing scientific evidence"):
        CompatibilityReportV2.from_dict(failed)

    mismatched = _complete_v2_report_payload()
    mismatched.update(
        {
            "evidence_fingerprints": [],
            "benchmark_passed": None,
            "scientifically_validated": None,
            "promotion_eligible": None,
            "production_promoted": False,
            "executable": False,
        }
    )
    assert CompatibilityReportV2.from_dict(mismatched).evidence_fingerprints == ()

    mismatched["evidence_fingerprints"] = ["a" * 64]
    with pytest.raises(ValueError, match="evidence refs and states"):
        CompatibilityReportV2.from_dict(mismatched)


def test_v2_execution_plan_rebuilds_canonical_identity():
    report = CompatibilityReportV2.from_dict(_complete_v2_report_payload())
    step = ExecutionStepV2.from_dict(
        {
            "schema_version": "vc.execution-step.v2",
            "model_name": report.model_name,
            "model_version": report.model_version,
            "model_fingerprint": report.model_fingerprint,
            "release_fingerprint": report.release_fingerprint,
            "capability_fingerprint": report.capability_fingerprint,
            "artifact_fingerprints": report.artifact_fingerprints,
            "environment_fingerprint": report.environment_fingerprint,
            "adapter_fingerprints": report.adapter_fingerprints,
            "evidence_fingerprints": report.evidence_fingerprints,
            "policy_fingerprint": report.policy_fingerprint,
            "compatibility_fingerprint": report.fingerprint(),
            "wrapper": "test.module.Adapter",
            "agent_name": report.model_name,
            "asset_paths": report.asset_paths,
        }
    )
    plan = ExecutionPlanV2.build(
        request_id=report.request_id,
        request_fingerprint=report.request_fingerprint,
        pack_id=report.pack_id,
        pack_version=report.pack_version,
        pack_fingerprint=report.pack_fingerprint,
        environment_snapshot_fingerprint=report.environment_snapshot_fingerprint,
        reports=(report,),
        steps=(step,),
    )
    failed = report.to_dict()
    failed.update(
        {
            "wrapper_ready": False,
            "environment_compatible": False,
            "executable": False,
        }
    )
    rebuilt = plan.rebuild(
        reports=(CompatibilityReportV2.from_dict(failed),),
        steps=(),
    )

    assert rebuilt.plan_id != plan.plan_id
    assert rebuilt.executable is False
    assert rebuilt.steps == ()
    assert ExecutionPlanV2.from_dict(rebuilt.to_dict()) == rebuilt


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value.update({"unknown": True}),
        lambda value: value.update({"sha256": "bad"}),
        lambda value: value.update({"cache_key": "../escape/model.bin"}),
        lambda value: value.update({"cache_key": "/absolute/model.bin"}),
        lambda value: value.update({"size_bytes": 0}),
        lambda value: value.update({"uri": "file:///private/model.bin"}),
        lambda value: value.update({"uri": "javascript:alert(1)"}),
        lambda value: value.update({"uri": "data:text/plain,model"}),
        lambda value: value.update({"uri": "https:"}),
        lambda value: value.update(
            {"uri": "https://private.invalid/model.bin?token=secret"}
        ),
        lambda value: value.update(
            {"uri": "https://private.invalid/model.bin#credential"}
        ),
    ],
)
def test_artifact_identity_rejects_unknown_bad_hash_and_unsafe_paths(mutate):
    value = complete_registry_payload()["artifacts"][0]
    mutate(value)
    with pytest.raises(ValueError):
        ArtifactIdentity.from_dict(value)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("release_id", "/Volumes/T7/secret/model"),
        ("release_id", r"C:\Users\secret\model"),
        ("release_id", r"\\server\share\model"),
        ("release_id", "file:///private/model"),
        ("model_version", "/Volumes/T7/secret/model-version"),
    ],
)
def test_public_release_identifiers_reject_path_shaped_values(field, value):
    release = complete_registry_payload()["releases"][0]
    release[field] = value
    with pytest.raises(ValueError, match="path-safe") as error:
        ModelReleaseRecord.from_dict(release)
    assert value not in str(error.value)


def test_contract_text_rejects_non_utf8_surrogates_as_validation_error():
    artifact = complete_registry_payload()["artifacts"][0]
    artifact["artifact_id"] = "invalid-\ud800-text"
    with pytest.raises(ValueError, match="UTF-8"):
        ArtifactIdentity.from_dict(artifact)


@pytest.mark.parametrize(
    "secret_field",
    ["/Volumes/T7/private-field", "api_key_ABC123", "secretToken123"],
)
def test_validation_error_redacts_every_unknown_field_name(secret_field):
    artifact = complete_registry_payload()["artifacts"][0]
    artifact[secret_field] = True
    with pytest.raises(ValueError) as error:
        ArtifactIdentity.from_dict(artifact)
    assert secret_field not in str(error.value)


def test_any_artifact_or_evidence_byte_identity_change_yields_new_fingerprint():
    payload = complete_registry_payload()
    artifact = ArtifactIdentity.from_dict(payload["artifacts"][0])
    changed_artifact = {**artifact.to_dict(), "sha256": "a" * 64}
    evidence = ValidationEvidence.from_dict(payload["evidence_records"][0])
    changed_evidence = {**evidence.to_dict(), "result_sha256": "b" * 64}

    assert artifact.fingerprint() != ArtifactIdentity.from_dict(changed_artifact).fingerprint()
    assert evidence.fingerprint() != ValidationEvidence.from_dict(changed_evidence).fingerprint()


def test_native_environment_requires_cpu_identity_and_unique_packages():
    environment = complete_registry_payload()["environments"][0]
    environment["cpu_architecture"] = None
    with pytest.raises(ValueError, match="cpu_architecture"):
        EnvironmentIdentity.from_dict(environment)

    environment["cpu_architecture"] = "arm64"
    environment["packages"].append(copy.deepcopy(environment["packages"][0]))
    with pytest.raises(ValueError, match="unique"):
        EnvironmentIdentity.from_dict(environment)

    environment["legacy_incomplete"] = True
    environment["packages"] = [
        {"name": "my_package", "version": None},
        {"name": "my-package", "version": None},
    ]
    legacy = EnvironmentIdentity.from_dict(environment)
    assert tuple(package.name for package in legacy.packages) == (
        "my_package",
        "my-package",
    )

    environment["legacy_incomplete"] = False
    environment["packages"] = [{"name": "My_Package", "version": "1.0.0"}]
    with pytest.raises(ValueError, match="PEP 503"):
        EnvironmentIdentity.from_dict(environment)


def test_registry_rejects_cache_key_aliasing_between_artifacts():
    payload = complete_registry_payload()
    alias = copy.deepcopy(payload["artifacts"][0])
    alias["artifact_id"] = "different-artifact"
    alias["sha256"] = "a" * 64
    alias["cache_key"] = alias["cache_key"].upper()
    payload["artifacts"].append(alias)
    with pytest.raises(ValueError, match="cache_key"):
        ModelRegistryV2.from_dict(payload)


def test_every_operator_decision_requires_exact_evidence_refs():
    policy = complete_registry_payload()["policy_records"][0]
    policy["production_promoted"] = False
    policy["evidence_fingerprints"] = []
    with pytest.raises(ValueError, match="evidence"):
        OperatorPolicyRecord.from_dict(policy)


def test_registry_rejects_artifact_model_misbinding_after_ref_rebuild():
    payload = complete_registry_payload()
    artifact = payload["artifacts"][0]
    artifact["model_fingerprint"] = "a" * 64
    changed = ArtifactIdentity.from_dict(artifact)
    payload["artifacts"][0] = changed.to_dict()
    payload["policy_records"] = []
    release = payload["releases"][0]
    release["artifact_fingerprints"] = [changed.fingerprint()]
    release["policy_fingerprint"] = None
    _install_release(payload, release)

    with pytest.raises(ValueError, match="artifact is bound to a different model"):
        ModelRegistryV2.from_dict(payload)


def test_registry_rejects_environment_adapter_misbinding_after_ref_rebuild():
    payload = complete_registry_payload()
    environment = payload["environments"][0]
    environment["adapter_fingerprints"] = ["a" * 64]
    changed = EnvironmentIdentity.from_dict(environment)
    payload["environments"][0] = changed.to_dict()
    payload["policy_records"] = []
    release = payload["releases"][0]
    release["environment_fingerprint"] = changed.fingerprint()
    release["policy_fingerprint"] = None
    _install_release(payload, release)

    with pytest.raises(ValueError, match="environment and release adapter bindings differ"):
        ModelRegistryV2.from_dict(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("pack_fingerprint", "a" * 64),
        ("environment_fingerprint", "a" * 64),
        ("adapter_fingerprints", ["a" * 64]),
    ],
)
def test_registry_rejects_evidence_misbinding_after_ref_rebuild(field, value):
    payload = complete_registry_payload()
    evidence = payload["evidence_records"][0]
    evidence[field] = value
    changed = ValidationEvidence.from_dict(evidence)
    payload["evidence_records"][0] = changed.to_dict()
    payload["policy_records"] = []
    release = payload["releases"][0]
    release["evidence_fingerprints"] = [changed.fingerprint()]
    release["policy_fingerprint"] = None
    _install_release(payload, release)

    with pytest.raises(ValueError, match="evidence identity does not match"):
        ModelRegistryV2.from_dict(payload)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("capability_fingerprint", "a" * 64, "different capability"),
        ("evidence_fingerprints", ["a" * 64], "evidence bindings differ"),
    ],
)
def test_registry_rejects_policy_misbinding_after_ref_rebuild(field, value, message):
    payload = complete_registry_payload()
    policy = payload["policy_records"][0]
    policy[field] = value
    changed = OperatorPolicyRecord.from_dict(policy)
    payload["policy_records"][0] = changed.to_dict()
    release = payload["releases"][0]
    release["policy_fingerprint"] = changed.fingerprint()
    _install_release(payload, release)

    with pytest.raises(ValueError, match=message):
        ModelRegistryV2.from_dict(payload)


def test_orphan_environment_cannot_reference_unknown_adapter():
    payload = complete_registry_payload()
    orphan = copy.deepcopy(payload["environments"][0])
    orphan["environment_id"] = "orphan-environment"
    orphan["adapter_fingerprints"] = ["a" * 64]
    payload["environments"].append(orphan)

    with pytest.raises(ValueError, match="environment references unknown adapter"):
        ModelRegistryV2.from_dict(payload)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("environment_fingerprint", "a" * 64, "unknown environment"),
        ("adapter_fingerprints", ["a" * 64], "unknown adapter"),
    ],
)
def test_orphan_evidence_cannot_reference_unknown_components(field, value, message):
    payload = complete_registry_payload()
    orphan = copy.deepcopy(payload["evidence_records"][0])
    orphan["evidence_id"] = "orphan-evidence"
    orphan["result_sha256"] = "a" * 64
    orphan[field] = value
    payload["evidence_records"].append(orphan)

    with pytest.raises(ValueError, match=message):
        ModelRegistryV2.from_dict(payload)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("evidence_fingerprints", ["a" * 64], "unknown evidence"),
        ("capability_fingerprint", "a" * 64, "unknown release capability"),
    ],
)
def test_orphan_policy_cannot_reference_unknown_components(field, value, message):
    payload = complete_registry_payload()
    orphan = copy.deepcopy(payload["policy_records"][0])
    orphan["policy_id"] = "orphan-policy"
    orphan[field] = value
    payload["policy_records"].append(orphan)

    with pytest.raises(ValueError, match=message):
        ModelRegistryV2.from_dict(payload)


@pytest.mark.parametrize("section", ["evidence_records", "policy_records"])
def test_valid_but_unreferenced_science_or_policy_record_is_rejected(section):
    payload = complete_registry_payload()
    orphan = copy.deepcopy(payload[section][0])
    identity_field = "evidence_id" if section == "evidence_records" else "policy_id"
    orphan[identity_field] = f"orphan-{identity_field}"
    payload[section].append(orphan)

    with pytest.raises(ValueError, match=f"{section.split('_')[0]} records must be referenced"):
        ModelRegistryV2.from_dict(payload)


@pytest.mark.parametrize(
    ("section", "updates"),
    [
        ("artifacts", {"artifact_id": "orphan-artifact", "cache_key": "orphan/model.bin"}),
        ("environments", {"environment_id": "orphan-environment"}),
        ("adapters", {"adapter_id": "orphan-adapter"}),
    ],
)
def test_valid_but_unreferenced_component_record_is_rejected(section, updates):
    payload = complete_registry_payload()
    orphan = copy.deepcopy(payload[section][0])
    orphan.update(updates)
    payload[section].append(orphan)

    with pytest.raises(ValueError, match=f"{section[:-1]} records must be referenced"):
        ModelRegistryV2.from_dict(payload)


def test_scientific_and_policy_state_cannot_jump_gates():
    evidence = complete_registry_payload()["evidence_records"][0]
    evidence["benchmark_passed"] = False
    with pytest.raises(ValueError):
        ValidationEvidence.from_dict(evidence)

    payload = complete_registry_payload(promoted=False)
    payload["policy_records"][0]["production_promoted"] = True
    with pytest.raises(ValueError):
        ModelRegistryV2.from_dict(payload)


def test_native_release_rejects_multi_pack_scope_overclaim():
    release = complete_registry_payload()["releases"][0]
    release["pack_fingerprints"].append("a" * 64)

    with pytest.raises(ValueError, match="exactly one Pack"):
        ModelReleaseRecord.from_dict(release)


def test_append_only_lifecycle_returns_new_registry_and_preserves_history():
    initial = ModelRegistryV2.from_dict(complete_registry_payload())
    release_fp = initial.releases[0].fingerprint()
    assert initial.state(release_fp).cataloged is True
    assert initial.state(release_fp).artifact_ready is False

    ready = initial.append(_event(initial, "artifact_ready", release_fp))
    revoked = ready.append(_event(ready, "revoke", release_fp))

    assert initial.state(release_fp).artifact_ready is False
    assert ready.state(release_fp).artifact_ready is True
    assert revoked.state(release_fp).revoked is True
    assert len(initial.lifecycle_events) == 1
    assert len(revoked.lifecycle_events) == 3
    with pytest.raises(ValueError):
        revoked.append(_event(revoked, "artifact_ready", release_fp))


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("sequence", 2, "sequence"),
        ("previous_event_fingerprint", "a" * 64, "hash chain"),
        ("release_fingerprint", "a" * 64, "unknown release"),
    ],
)
def test_lifecycle_rejects_partial_chain_and_unknown_identity(field, value, message):
    payload = complete_registry_payload()
    payload["lifecycle_events"][0][field] = value
    with pytest.raises(ValueError, match=message):
        ModelRegistryV2.from_dict(payload)


def test_registry_rejects_duplicate_release_identity():
    payload = complete_registry_payload()
    payload["releases"].append(copy.deepcopy(payload["releases"][0]))
    with pytest.raises(ValueError, match="duplicate release fingerprint"):
        ModelRegistryV2.from_dict(payload)


def test_legacy_incomplete_release_cannot_become_artifact_ready():
    zoo = ModelZooRegistry()
    migrated = ModelRegistryV2.from_v1_cards(
        tuple(zoo.card(name) for name in zoo.capability_names())
    )
    release_fp = migrated.releases[0].fingerprint()
    with pytest.raises(ValueError, match="complete native artifact"):
        migrated.append(_event(migrated, "artifact_ready", release_fp))


def test_supersede_requires_existing_distinct_target_and_closes_source():
    payload = complete_registry_payload()
    first = ModelRegistryV2.from_dict(payload)
    old = first.releases[0]
    replacement_raw = copy.deepcopy(old.to_dict())
    replacement_raw["release_id"] = "test-model@1.0.1"
    replacement = ModelReleaseRecord.from_dict(replacement_raw)
    payload["releases"].append(replacement.to_dict())
    second_catalog = RegistryLifecycleEvent.from_dict(
        {
            "schema_version": "vc.model-registry-event.v1",
            "event_id": "event-2",
            "sequence": 2,
            "previous_event_fingerprint": first.lifecycle_events[-1].fingerprint(),
            "release_fingerprint": replacement.fingerprint(),
            "action": "cataloged",
            "target_release_fingerprint": None,
            "recorded_at": "2026-08-02T00:00:00Z",
            "operator_id": "test-only-operator",
            "reason": "contract conformance fixture only",
        }
    )
    payload["lifecycle_events"].append(second_catalog.to_dict())
    registry = ModelRegistryV2.from_dict(payload)

    superseded = registry.append(
        _event(
            registry,
            "supersede",
            old.fingerprint(),
            target_release_fingerprint=replacement.fingerprint(),
        )
    )
    assert superseded.state(old.fingerprint()).superseded_by == replacement.fingerprint()
    with pytest.raises(ValueError):
        registry.append(
            _event(
                registry,
                "supersede",
                old.fingerprint(),
                target_release_fingerprint="f" * 64,
            )
        )

    revoked_target = registry.append(
        _event(registry, "revoke", replacement.fingerprint())
    )
    with pytest.raises(ValueError, match="target"):
        revoked_target.append(
            _event(
                revoked_target,
                "supersede",
                old.fingerprint(),
                target_release_fingerprint=replacement.fingerprint(),
            )
        )


def test_public_catalog_is_an_explicit_path_safe_whitelist():
    registry = ModelRegistryV2.from_dict(complete_registry_payload())
    public = registry.public_catalog()
    rendered = json.dumps(public, sort_keys=True)

    assert public["schema_version"] == "vc.model-registry-catalog.v2"
    assert public["releases"][0]["production_promoted"] is True
    assert public["releases"][0]["policy_present"] is True
    assert public["releases"][0]["legacy_status"] is None
    for forbidden in (
        "private.invalid",
        "token=secret",
        "/private/source",
        r"C:\Users\secret",
        r"\\server\share",
        "file:///tmp/secret",
        "cache_key",
        "uri",
        "source",
        "safe_load_policy",
        "implementation",
        "packages",
    ):
        assert forbidden not in rendered


def test_default_v1_cards_migrate_cataloged_only_without_evidence_or_policy():
    zoo = ModelZooRegistry()
    cards = tuple(zoo.card(name) for name in zoo.capability_names())
    migrated = ModelRegistryV2.from_v1_cards(cards)

    assert {release.model_name for release in migrated.releases} == set(zoo.capability_names())
    assert migrated.evidence_records == ()
    assert migrated.policy_records == ()
    assert all(release.policy_fingerprint is None for release in migrated.releases)
    assert all(release.migration_status == "legacy_incomplete" for release in migrated.releases)
    expected_statuses = json.loads(_FIXTURE.read_text(encoding="utf-8"))["model_registry"][
        "expected_models"
    ]
    assert {
        release.model_name: release.legacy_status for release in migrated.releases
    } == expected_statuses
    assert {
        item["model_name"]: item["legacy_status"]
        for item in migrated.public_catalog()["releases"]
    } == expected_statuses
    assert all(migrated.state(release.fingerprint()).cataloged for release in migrated.releases)
    assert not any(migrated.state(release.fingerprint()).artifact_ready for release in migrated.releases)
    assert not any(item["production_promoted"] for item in migrated.public_catalog()["releases"])
    assert not any(item["policy_present"] for item in migrated.public_catalog()["releases"])
    assert all(item["benchmark_passed"] is None for item in migrated.public_catalog()["releases"])
    assert all(
        item["scientifically_validated"] is None
        for item in migrated.public_catalog()["releases"]
    )
    assert all(item["promotion_eligible"] is None for item in migrated.public_catalog()["releases"])
    assert zoo.status("ecoli_gem") == "available"
    assert zoo.status("gears") == "planned"
    assert migrated.fingerprint() == ModelRegistryV2.from_v1_cards(cards).fingerprint()


def test_v1_unsafe_version_is_preserved_in_identity_but_redacted_from_public():
    zoo = ModelZooRegistry()
    source = zoo.card("ecoli_gem")
    unsafe = source.model_copy(update={"version": "release/2026"})

    migrated = ModelRegistryV2.from_v1_cards((unsafe,))
    release = migrated.releases[0]
    public = migrated.public_catalog()["releases"][0]

    assert release.model_version == "release/2026"
    assert release.model_fingerprint == unsafe.fingerprint()
    assert "release/2026" not in release.release_id
    assert public["model_version"] is None
    assert "release/2026" not in json.dumps(public, sort_keys=True)


def test_v1_import_module_dependency_survives_legacy_migration():
    zoo = ModelZooRegistry()
    source = zoo.card("ecoli_gem")
    resources = source.resources.model_copy(
        update={"python_dependencies": ("torch_geometric", "foo_bar", "foo.bar")}
    )
    legacy = source.model_copy(update={"resources": resources})

    migrated = ModelRegistryV2.from_v1_cards((legacy,))
    environment = migrated.environments[0]

    assert environment.legacy_incomplete is True
    assert tuple(package.name for package in environment.packages) == (
        "torch_geometric",
        "foo_bar",
        "foo.bar",
    )


def test_p8_p9_legacy_receipts_remain_unbound_and_are_not_evidence():
    fixture = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    registry_source = _ROOT / fixture["model_registry"]["path"]
    assert registry_source.stat().st_size == fixture["model_registry"]["size_bytes"]
    assert hashlib.sha256(registry_source.read_bytes()).hexdigest() == fixture["model_registry"]["sha256"]

    receipts = tuple(LegacyMigrationReceipt.from_dict(item) for item in fixture["receipts"])
    for receipt in receipts:
        source = _ROOT / receipt.source_path
        assert source.stat().st_size == receipt.size_bytes
        assert hashlib.sha256(source.read_bytes()).hexdigest() == receipt.sha256
        source_doc = json.loads(source.read_text(encoding="utf-8"))
        assert receipt.binding_status == "unbound"
        assert receipt.scientifically_validated is False
        if receipt.receipt_id.startswith("p8-"):
            assert receipt.available is None
            assert receipt.declared_pack_fingerprint == source_doc["pack"]["fingerprint"]
            assert (
                receipt.scientifically_validated
                is source_doc["states"]["scientifically_validated"]
            )
            assert receipt.benchmark_passed is None
            assert receipt.promotion_eligible is None
        else:
            assert receipt.available is source_doc["status"]["available"]
            assert (
                receipt.scientifically_validated
                is source_doc["status"]["scientifically_validated"]
            )
            source_reasons = source_doc["status"]["reason_codes"]
            assert list(receipt.reason_codes[: len(source_reasons)]) == source_reasons
            assert receipt.benchmark_passed is False
            assert receipt.promotion_eligible is False

    zoo = ModelZooRegistry()
    migrated = ModelRegistryV2.from_v1_cards(
        tuple(zoo.card(name) for name in zoo.capability_names())
    )
    report = legacy_migration_report(migrated, receipts)
    assert report.evidence_admitted is False
    assert report.production_promoted is False
    assert report.receipts == receipts
    assert migrated.evidence_records == ()
    assert migrated.policy_records == ()


def test_legacy_report_rejects_any_admitted_evidence_or_policy():
    zoo = ModelZooRegistry()
    migrated = ModelRegistryV2.from_v1_cards(
        tuple(zoo.card(name) for name in zoo.capability_names())
    )
    evidence = ValidationEvidence.from_dict(
        complete_registry_payload()["evidence_records"][0]
    )
    contaminated = migrated.model_copy(update={"evidence_records": (evidence,)})

    with pytest.raises(ValueError, match="evidence or policy"):
        legacy_migration_report(contaminated, ())


def test_legacy_receipt_rejects_unknown_fields_and_positive_state():
    value = json.loads(_FIXTURE.read_text(encoding="utf-8"))["receipts"][0]
    value["unknown"] = True
    with pytest.raises(ValueError):
        LegacyMigrationReceipt.from_dict(value)

    value.pop("unknown")
    value["scientifically_validated"] = True
    with pytest.raises(ValueError):
        LegacyMigrationReceipt.from_dict(value)
