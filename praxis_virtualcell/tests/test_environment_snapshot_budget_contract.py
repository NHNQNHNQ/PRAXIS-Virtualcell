"""Write-new environment snapshot capacity identities."""

from __future__ import annotations

import copy

import pytest

from praxis_virtualcell.model_zoo.capability_registry import EnvironmentSnapshot
from praxis_virtualcell.model_zoo.registry_v2 import (
    ArtifactSnapshotBudgetPolicyV1,
    ComposedModelRegistryV2,
    EnvironmentIdentity,
    EnvironmentIdentityV2,
    ModelRegistryV2,
    ModelReleaseRecord,
    OperatorPolicyRecord,
    ValidationEvidence,
)
from praxis_virtualcell.tests.test_model_registry_v2 import complete_registry_payload


def _v1_identity_payload() -> dict:
    return {
        "schema_version": "vc.model-environment.v1",
        "environment_id": "test-only-budget-environment",
        "python_version": "3.13.5",
        "cpu_architecture": "arm64",
        "packages": [{"name": "pydantic", "version": "2.11.7"}],
        "lock_digest": "6" * 64,
        "image_digest": None,
        "resources": ["cpu"],
        "accelerators": [],
        "adapter_fingerprints": ["a" * 64],
        "legacy_incomplete": False,
    }


def _budget_payload() -> dict:
    return {
        "schema_version": "vc.artifact-snapshot-budget-policy.v1",
        "max_live_snapshot_payload_bytes": 4096,
        "max_snapshot_entries_per_execution": 3,
        "retention_scope": "execution_only",
    }


def _v2_identity(*, adapter_fingerprint: str = "a" * 64) -> EnvironmentIdentityV2:
    value = _v1_identity_payload()
    value["adapter_fingerprints"] = [adapter_fingerprint]
    value.update(
        {
            "schema_version": "vc.model-environment.v2",
            "artifact_snapshot_budget_policy": _budget_payload(),
        }
    )
    return EnvironmentIdentityV2.from_dict(value)


def _registry_with_environment(identity: EnvironmentIdentityV2) -> ModelRegistryV2:
    """Rebind the existing synthetic full graph to one v2 environment."""
    payload = complete_registry_payload()
    payload["environments"] = [identity.to_dict()]

    evidence_value = copy.deepcopy(payload["evidence_records"][0])
    evidence_value["environment_fingerprint"] = identity.fingerprint()
    evidence = ValidationEvidence.from_dict(evidence_value)
    payload["evidence_records"] = [evidence.to_dict()]

    release_value = copy.deepcopy(payload["releases"][0])
    release_value["environment_fingerprint"] = identity.fingerprint()
    release_value["evidence_fingerprints"] = [evidence.fingerprint()]
    release_value["policy_fingerprint"] = None
    release_without_policy = ModelReleaseRecord.from_dict(release_value)

    policy_value = copy.deepcopy(payload["policy_records"][0])
    policy_value["capability_fingerprint"] = release_without_policy.capability_fingerprint()
    policy_value["evidence_fingerprints"] = [evidence.fingerprint()]
    policy = OperatorPolicyRecord.from_dict(policy_value)
    payload["policy_records"] = [policy.to_dict()]

    release_value["policy_fingerprint"] = policy.fingerprint()
    release = ModelReleaseRecord.from_dict(release_value)
    payload["releases"] = [release.to_dict()]
    payload["lifecycle_events"][0]["release_fingerprint"] = release.fingerprint()
    return ModelRegistryV2.from_dict(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("max_live_snapshot_payload_bytes", 0),
        ("max_live_snapshot_payload_bytes", -1),
        ("max_live_snapshot_payload_bytes", 1.0),
        ("max_live_snapshot_payload_bytes", True),
        ("max_live_snapshot_payload_bytes", "1"),
        ("max_snapshot_entries_per_execution", 0),
        ("max_snapshot_entries_per_execution", -1),
        ("max_snapshot_entries_per_execution", 1.0),
        ("max_snapshot_entries_per_execution", True),
        ("max_snapshot_entries_per_execution", "1"),
    ],
)
def test_artifact_snapshot_budget_requires_positive_exact_integers(field, value) -> None:
    payload = _budget_payload()
    payload[field] = value

    with pytest.raises(ValueError, match=field):
        ArtifactSnapshotBudgetPolicyV1.from_dict(payload)


def test_artifact_snapshot_budget_is_execution_only() -> None:
    payload = _budget_payload()
    payload["retention_scope"] = "process_lifetime"

    with pytest.raises(ValueError, match="retention_scope"):
        ArtifactSnapshotBudgetPolicyV1.from_dict(payload)


def test_v1_environment_identity_bytes_and_fingerprint_remain_stable() -> None:
    payload = _v1_identity_payload()
    identity = EnvironmentIdentity.from_dict(payload)

    assert identity.to_dict() == payload
    assert identity.fingerprint() == "2d66a505e716c8e6c104e31d2cbe0ef020d4d812877613d7e8b7e57cdc7a8348"


def test_v2_environment_identity_requires_budget_and_registry_parses_exact_union() -> None:
    missing_budget = _v1_identity_payload()
    missing_budget["schema_version"] = "vc.model-environment.v2"
    with pytest.raises(ValueError, match="artifact_snapshot_budget_policy"):
        EnvironmentIdentityV2.from_dict(missing_budget)

    identity = _v2_identity(
        adapter_fingerprint=complete_registry_payload()["environments"][0]["adapter_fingerprints"][0]
    )
    registry = _registry_with_environment(identity)

    assert type(registry.environments[0]) is EnvironmentIdentityV2
    assert registry.environment(identity.fingerprint()) is registry.environments[0]
    assert registry.to_dict()["environments"] == [identity.to_dict()]

    empty = ModelRegistryV2.from_dict(
        {
            "schema_version": "vc.model-registry.v2",
            "artifacts": [],
            "environments": [],
            "adapters": [],
            "evidence_records": [],
            "policy_records": [],
            "releases": [],
            "lifecycle_events": [],
        }
    )
    composed = ComposedModelRegistryV2.compose(empty, registry)
    assert type(composed.environment(identity.fingerprint())) is EnvironmentIdentityV2


def test_environment_snapshot_v3_requires_exact_v2_identity() -> None:
    v1 = EnvironmentIdentity.from_dict(_v1_identity_payload())
    v2 = _v2_identity()

    legacy_v2_snapshot = EnvironmentSnapshot.from_dict(
        {
            "schema_version": "vc.environment.v2",
            "python_dependencies": [],
            "resources": ["cpu"],
            "runtime_tasks": ["predict_delta_expression"],
            "runtime_outputs": ["delta_expression"],
            "identity": v1.to_dict(),
        }
    )
    assert type(legacy_v2_snapshot.identity) is EnvironmentIdentity
    assert legacy_v2_snapshot.fingerprint() == "7571bba14adf6a754d6858f6f6a95b13f497962265efa5041b3ec1f6fd85894d"

    snapshot_v3 = EnvironmentSnapshot.from_dict(
        {
            "schema_version": "vc.environment.v3",
            "python_dependencies": [],
            "resources": ["cpu"],
            "runtime_tasks": ["predict_delta_expression"],
            "runtime_outputs": ["delta_expression"],
            "identity": v2.to_dict(),
        }
    )
    assert type(snapshot_v3.identity) is EnvironmentIdentityV2
    assert snapshot_v3.identity.artifact_snapshot_budget_policy == ArtifactSnapshotBudgetPolicyV1.from_dict(
        _budget_payload()
    )

    wrong_v2 = legacy_v2_snapshot.to_dict()
    wrong_v2["identity"] = v2.to_dict()
    with pytest.raises(ValueError, match="EnvironmentIdentity"):
        EnvironmentSnapshot.from_dict(wrong_v2)

    wrong_v3 = snapshot_v3.to_dict()
    wrong_v3["identity"] = v1.to_dict()
    with pytest.raises(ValueError, match="EnvironmentIdentityV2"):
        EnvironmentSnapshot.from_dict(wrong_v3)
