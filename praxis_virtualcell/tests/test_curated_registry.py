"""P22 curated Virtual Cell Registry contract-only conformance tests."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from praxis_virtualcell.benchmarks.system import (
    BenchmarkRunV1,
    compute_p21b_execution_fingerprint,
)
from praxis_virtualcell.model_zoo.curated_registry import (
    CuratedRegistryDecisionV1,
    CuratedRegistryError,
    CuratedRegistryHeadV1,
    CuratedRegistryTrustV1,
    CuratedVirtualCellRegistry,
    VirtualCellContextV1,
    VirtualCellReleaseV1,
    WrapperApprovalV1,
    build_virtual_cell_release,
    compute_curated_import_fingerprint,
)
from praxis_virtualcell.model_zoo.registry_v2 import (
    AdapterIdentity,
    ArtifactIdentity,
    EnvironmentIdentity,
    ModelRegistryV2,
    ModelReleaseRecord,
    OperatorPolicyRecord,
    ValidationEvidence,
)
from praxis_virtualcell.pack_factory import FactoryRegisteredPackV1
from praxis_virtualcell.tests.test_benchmark_system import (
    _bundle,
    _canonical_fp,
    _fp,
    _protocol,
    _rebind_run_authorization,
    _result,
    _run_raw,
)


def _candidate_provenance(raw: dict) -> str:
    fields = (
        "training_job_fingerprint",
        "training_result_fingerprint",
        "checkpoint_fingerprint",
        "artifact_fingerprint",
        "model_card_fingerprint",
        "candidate_model_fingerprint",
        "model_identity_fingerprint",
        "factory_registration_fingerprint",
        "pack_fingerprint",
        "feature_contract_fingerprint",
        "output_contract_fingerprint",
        "trainer_revision",
        "trainer_source_sha256",
        "training_environment_fingerprint",
    )
    return _canonical_fp({field: raw[field] for field in fields})


def _positive_release(
    *,
    release_version: str = "1.0.0",
    virtual_cell_id: str = "synthetic-cell",
) -> VirtualCellReleaseV1:
    """Build a transient positive conformance closure, never real evidence."""

    protocol = _protocol()
    model_fingerprint = _fp("model")
    adapter = AdapterIdentity.from_dict(
        {
            "schema_version": "vc.model-adapter.v1",
            "adapter_id": "synthetic-delta-adapter",
            "version": "1.0.0",
            "implementation": "synthetic.adapter.DeltaAdapter",
            "task": "synthetic_perturbation_delta_prediction",
            "outputs": ["synthetic-delta"],
            "input_contract_fingerprint": protocol.feature_contract_fingerprint,
            "output_contract_fingerprint": protocol.output_contract_fingerprint,
            "legacy_incomplete": False,
        }
    )
    environment = EnvironmentIdentity.from_dict(
        {
            "schema_version": "vc.model-environment.v1",
            "environment_id": "synthetic-cpu-lock",
            "python_version": "3.13.12",
            "cpu_architecture": "arm64",
            "packages": [{"name": "pydantic", "version": "2.11.7"}],
            "lock_digest": _fp("environment-lock"),
            "image_digest": None,
            "resources": ["cpu"],
            "accelerators": [],
            "adapter_fingerprints": [adapter.fingerprint()],
            "legacy_incomplete": False,
        }
    )
    artifact = ArtifactIdentity.from_dict(
        {
            "schema_version": "vc.model-artifact.v1",
            "artifact_id": "synthetic-model:model.json",
            "model_fingerprint": model_fingerprint,
            "uri": "https://private.invalid/synthetic-model.json",
            "cache_key": "private/synthetic-model.json",
            "size_bytes": 17,
            "sha256": _fp("artifact-bytes"),
            "media_type": "application/json",
            "license": "CC0-1.0",
            "source": "/private/source token=secret",
            "safe_load_policy": "data_only",
            "legacy_incomplete": False,
        }
    )
    registration = FactoryRegisteredPackV1.from_dict(
        {
            "schema_version": "vc.factory-registered-pack.v1",
            "receipt_fingerprint": _fp("receipt"),
            "candidate_fingerprint": _fp("pack-candidate"),
            "metadata_review_fingerprint": _fp("pack-review"),
            "validation_report_fingerprint": _fp("pack-validation"),
            "operator_decision_fingerprint": _fp("pack-decision"),
            "pack_id": "synthetic-pack",
            "pack_version": "1.0.0",
            "pack_fingerprint": protocol.pack_fingerprint,
            "operator_id": "synthetic-pack-operator",
            "registered_at": "2026-08-07T00:00:00Z",
            "registration_method": "controlled_pack_factory_v1",
            "factory_registered": True,
            "cataloged": True,
            "pack_valid": True,
            "model_compatible": None,
            "environment_compatible": None,
            "adapter_compatible": None,
            "executable": False,
            "training_performed": False,
            "checkpoint_created": False,
            "model_card_created": False,
            "benchmark_performed": False,
            "evidence_created": False,
            "scientifically_validated": False,
            "promotion_eligible": False,
            "production_promoted": False,
        }
    )

    run_raw = _run_raw(protocol)
    run_raw.update(
        {
            "artifact_fingerprint": artifact.fingerprint(),
            "factory_registration_fingerprint": registration.fingerprint(),
            "adapter_fingerprints": [adapter.fingerprint()],
            "evaluation_environment_fingerprint": environment.fingerprint(),
        }
    )
    run_raw["candidate_provenance_fingerprint"] = _candidate_provenance(run_raw)
    run = BenchmarkRunV1.from_dict(_rebind_run_authorization(run_raw))
    result = _result(protocol, run)
    bundle = _bundle(protocol, run, result)
    execution_identity = compute_p21b_execution_fingerprint(run, result)
    evidence = bundle.derive_with_p21b_execution(
        trusted_p21b_execution_fingerprint=execution_identity
    ).validation_evidence

    release_without_policy = ModelReleaseRecord.from_dict(
        {
            "schema_version": "vc.model-release.v1",
            "release_id": "synthetic-model@1.0.0",
            "model_name": "synthetic_model",
            "model_version": "1.0.0",
            "model_fingerprint": model_fingerprint,
            "pack_fingerprints": [registration.pack_fingerprint],
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
            "policy_id": "synthetic-p21c-policy",
            "capability_fingerprint": release_without_policy.capability_fingerprint(),
            "evidence_fingerprints": [evidence.fingerprint()],
            "production_promoted": True,
            "decision_kind": "operator_decision",
            "operator_id": "synthetic-policy-operator",
            "decided_at": "2026-08-07T00:00:00Z",
            "reason": "transient contract conformance only",
        }
    )
    model_release = ModelReleaseRecord.from_dict(
        {
            **release_without_policy.to_dict(),
            "policy_fingerprint": policy.fingerprint(),
        }
    )
    source_registry = ModelRegistryV2.from_dict(
        {
            "schema_version": "vc.model-registry.v2",
            "artifacts": [artifact.to_dict()],
            "environments": [environment.to_dict()],
            "adapters": [adapter.to_dict()],
            "evidence_records": [evidence.to_dict()],
            "policy_records": [policy.to_dict()],
            "releases": [model_release.to_dict()],
            "lifecycle_events": [],
        }
    )
    wrapper = WrapperApprovalV1.from_dict(
        {
            "schema_version": "vc.virtual-cell-wrapper-approval.v1",
            "approval_id": "synthetic-wrapper-review",
            "adapter_fingerprint": adapter.fingerprint(),
            "entrypoint": adapter.implementation,
            "wrapper_source_sha256": _fp("wrapper-source"),
            "model_card_fingerprint": run.model_card_fingerprint,
            "reviewer_id": "synthetic-release-reviewer",
            "reviewed_at": "2026-08-07T00:00:00Z",
            "reason": "transient contract conformance only",
            "approved": True,
        }
    )
    scope = protocol.scope
    context = VirtualCellContextV1.from_dict(
        {
            "schema_version": "vc.virtual-cell-context.v1",
            "context_id": "synthetic-context",
            "organism": scope.organism,
            "cell_type": scope.cell_type,
            "intervention": scope.intervention,
            "endpoint": scope.endpoint,
            "benchmark_scope_fingerprint": scope.fingerprint(),
        }
    )
    return build_virtual_cell_release(
        virtual_cell_id=virtual_cell_id,
        release_version=release_version,
        context=context,
        pack_registration=registration,
        source_registry=source_registry,
        benchmark_bundle=bundle,
        p21b_execution_identity_fingerprint=execution_identity,
        wrapper_approvals=(wrapper,),
        publisher_id="synthetic-publisher",
        reviewer_id="synthetic-release-reviewer",
        reviewed_at="2026-08-07T00:00:00Z",
        release_license="CC0-1.0",
        source_name="synthetic-conformance",
        source_uri="https://example.invalid/synthetic-conformance",
    )


def _trust(
    *,
    imports: tuple[VirtualCellReleaseV1, ...] = (),
    decisions: tuple[CuratedRegistryDecisionV1, ...] = (),
    checkpoint: CuratedRegistryHeadV1 | None = None,
) -> CuratedRegistryTrustV1:
    """Act as the external operator trust source for transient conformance only."""

    return CuratedRegistryTrustV1.from_dict(
        {
            "schema_version": "vc.curated-registry-trust.v1",
            "authority_id": "synthetic-conformance-authority",
            "authorized_import_fingerprints": sorted(compute_curated_import_fingerprint(item) for item in imports),
            "authorized_decision_fingerprints": sorted(item.fingerprint() for item in decisions),
            "checkpoint": (
                checkpoint
                or CuratedRegistryHeadV1(
                    schema_version="vc.curated-registry-head.v1",
                    entry_count=0,
                    last_entry_fingerprint=None,
                )
            ).to_dict(),
        }
    )


def _import(
    registry: CuratedVirtualCellRegistry,
    release: VirtualCellReleaseV1,
):
    current = registry._trust
    registry._trust = CuratedRegistryTrustV1.from_dict(
        {
            **_trust(imports=(release,), checkpoint=current.checkpoint).to_dict(),
            "authorized_import_fingerprints": sorted(
                {
                    *current.authorized_import_fingerprints,
                    compute_curated_import_fingerprint(release),
                }
            ),
            "authorized_decision_fingerprints": list(current.authorized_decision_fingerprints),
        }
    )
    return registry.import_release(release)


def _decision(
    release: VirtualCellReleaseV1,
    action: str,
    *,
    decision_id: str | None = None,
    target: VirtualCellReleaseV1 | None = None,
) -> CuratedRegistryDecisionV1:
    return CuratedRegistryDecisionV1.from_dict(
        {
            "schema_version": "vc.curated-registry-decision.v1",
            "decision_id": decision_id or f"{action}-{release.release_version}",
            "action": action,
            "release_fingerprint": release.fingerprint(),
            "target_release_fingerprint": target.fingerprint() if target else None,
            "curator_id": "synthetic-registry-curator",
            "recorded_at": "2026-08-07T00:00:00Z",
            "reason": "transient catalog conformance only",
            "effect": "catalog_metadata_only",
            "scientific_state_changed": False,
            "policy_state_changed": False,
            "assets_installed": False,
            "execution_performed": False,
        }
    )


def _record(
    registry: CuratedVirtualCellRegistry,
    decision: CuratedRegistryDecisionV1,
):
    current = registry._trust
    registry._trust = CuratedRegistryTrustV1.from_dict(
        {
            **_trust(decisions=(decision,), checkpoint=current.checkpoint).to_dict(),
            "authorized_import_fingerprints": list(current.authorized_import_fingerprints),
            "authorized_decision_fingerprints": sorted(
                {
                    *current.authorized_decision_fingerprints,
                    decision.fingerprint(),
                }
            ),
        }
    )
    return registry.record_decision(decision)


def test_release_is_strict_frozen_reproducible_and_bundle_stays_untrusted():
    release = _positive_release()
    assert release == VirtualCellReleaseV1.from_dict(release.to_dict())
    assert release.fingerprint() == VirtualCellReleaseV1.from_dict(release.to_dict()).fingerprint()
    assert release.benchmark_bundle.evidence.validation_evidence.promotion_eligible is False
    assert release.source_registry.evidence(release.validation_evidence_fingerprint).promotion_eligible is True
    assert len(compute_curated_import_fingerprint(release)) == 64
    with pytest.raises(ValidationError):
        release.release_version = "changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda raw: raw.__setitem__("source_registry_fingerprint", "f" * 64),
            "source registry fingerprint",
        ),
        (
            lambda raw: raw.__setitem__("p21b_execution_identity_fingerprint", "f" * 64),
            "P21B execution identity",
        ),
        (
            lambda raw: raw["context"].__setitem__("cell_type", "wrong-cell"),
            "context",
        ),
        (
            lambda raw: raw["wrapper_approvals"][0].__setitem__("entrypoint", "wrong.adapter.Entrypoint"),
            "wrapper approval",
        ),
        (
            lambda raw: raw["wrapper_approvals"][0].__setitem__("model_card_fingerprint", "f" * 64),
            "wrapper approval",
        ),
        (
            lambda raw: raw.__setitem__("dependency_fingerprints", ["f" * 64]),
            "dependency closure",
        ),
        (
            lambda raw: raw.__setitem__("policy_fingerprint", "f" * 64),
            "policy",
        ),
    ],
)
def test_release_rejects_stale_or_mixed_closure(mutation, message):
    raw = _positive_release().to_dict()
    mutation(raw)
    with pytest.raises(ValueError, match=message):
        VirtualCellReleaseV1.from_dict(raw)


def test_release_rejects_unknown_fields_and_credential_bearing_source_uri():
    raw = _positive_release().to_dict()
    raw["unknown"] = True
    with pytest.raises(ValueError):
        VirtualCellReleaseV1.from_dict(raw)
    raw.pop("unknown")
    raw["source_uri"] = "https://user:secret@example.invalid/source?token=secret"
    with pytest.raises(ValueError, match="source_uri"):
        VirtualCellReleaseV1.from_dict(raw)


def test_default_or_negative_p12_registry_cannot_form_a_curated_release():
    base = _positive_release()
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
    arguments = {
        "virtual_cell_id": base.virtual_cell_id,
        "release_version": base.release_version,
        "context": base.context,
        "pack_registration": base.pack_registration,
        "benchmark_bundle": base.benchmark_bundle,
        "p21b_execution_identity_fingerprint": (base.p21b_execution_identity_fingerprint),
        "wrapper_approvals": base.wrapper_approvals,
        "publisher_id": base.publisher_id,
        "reviewer_id": base.reviewer_id,
        "reviewed_at": base.reviewed_at,
        "release_license": base.release_license,
        "source_name": base.source_name,
        "source_uri": base.source_uri,
    }
    with pytest.raises(CuratedRegistryError, match="exactly one release"):
        build_virtual_cell_release(source_registry=empty, **arguments)

    evidence_raw = base.source_registry.evidence_records[0].to_dict()
    evidence_raw.update(
        {
            "benchmark_passed": False,
            "scientifically_validated": False,
            "promotion_eligible": False,
        }
    )
    evidence = ValidationEvidence.from_dict(evidence_raw)
    release_raw = base.source_registry.releases[0].to_dict()
    release_raw.update(
        {
            "evidence_fingerprints": [evidence.fingerprint()],
            "policy_fingerprint": None,
        }
    )
    release_without_policy = ModelReleaseRecord.from_dict(release_raw)
    policy_raw = base.source_registry.policy_records[0].to_dict()
    policy_raw.update(
        {
            "capability_fingerprint": (release_without_policy.capability_fingerprint()),
            "evidence_fingerprints": [evidence.fingerprint()],
            "production_promoted": False,
        }
    )
    policy = OperatorPolicyRecord.from_dict(policy_raw)
    model_release = ModelReleaseRecord.from_dict(
        {
            **release_without_policy.to_dict(),
            "policy_fingerprint": policy.fingerprint(),
        }
    )
    source_raw = base.source_registry.to_dict()
    source_raw.update(
        {
            "evidence_records": [evidence.to_dict()],
            "policy_records": [policy.to_dict()],
            "releases": [model_release.to_dict()],
        }
    )
    negative = ModelRegistryV2.from_dict(source_raw)
    with pytest.raises(ValueError, match="pre-existing positive scientific evidence"):
        build_virtual_cell_release(source_registry=negative, **arguments)


def test_empty_registry_is_honest_write_disabled_and_non_executable(tmp_path):
    registry = CuratedVirtualCellRegistry.create((tmp_path / "registry").resolve())
    assert registry.verify() == ()
    assert registry.query() == ()
    assert registry.public_catalog() == {
        "schema_version": "vc.curated-virtual-cell-catalog.v1",
        "registry_fingerprint": hashlib.sha256(b"[]").hexdigest(),
        "revocation_checkpointed": False,
        "write_api_enabled": False,
        "releases": [],
    }


def test_candidate_hashes_cannot_bypass_default_deny_operator_allowlist(tmp_path):
    release = _positive_release()
    registry = CuratedVirtualCellRegistry.create((tmp_path / "registry").resolve())
    assert len(compute_curated_import_fingerprint(release)) == 64
    with pytest.raises(CuratedRegistryError, match="authority does not allow"):
        registry.import_release(release)

    unrelated = CuratedRegistryTrustV1.from_dict(
        {
            **_trust().to_dict(),
            "authorized_import_fingerprints": ["f" * 64],
        }
    )
    wrong_authority = CuratedVirtualCellRegistry.open(
        registry.root,
        trust=unrelated,
    )
    with pytest.raises(CuratedRegistryError, match="authority does not allow"):
        wrong_authority.import_release(release)
    assert registry.verify() == ()


def test_import_is_quarantine_first_idempotent_and_does_not_create_science(tmp_path):
    release = _positive_release()
    registry = CuratedVirtualCellRegistry.create((tmp_path / "registry").resolve())
    stored = _import(registry, release)
    assert _import(registry, release).entry_fingerprint == stored.entry_fingerprint
    assert len(registry.verify()) == 1
    state = registry.state(release.fingerprint())
    assert state.quarantined is True
    assert state.cataloged is state.revoked is False
    assert registry.query() == ()

    assert registry.public_catalog()["releases"] == []
    public = registry.public_catalog(include_inactive=True)["releases"][0]
    assert public["benchmark_passed"] is True
    assert public["scientifically_validated"] is True
    assert public["promotion_eligible"] is True
    assert public["production_promoted"] is True
    assert public["cataloged"] is False
    assert public["installed"] is None
    assert public["model_compatible"] is None
    assert public["environment_compatible"] is None
    assert public["adapter_compatible"] is None
    assert public["executable"] is False


def test_catalog_approval_quarantine_and_reapproval_change_only_lifecycle(tmp_path):
    release = _positive_release()
    registry = CuratedVirtualCellRegistry.create((tmp_path / "registry").resolve())
    _import(registry, release)
    evidence_before = registry.release(release.fingerprint()).validation_evidence_fingerprint
    policy_before = registry.release(release.fingerprint()).policy_fingerprint

    approve = _decision(release, "approve_catalog")
    assert _record(registry, approve).record_fingerprint == approve.fingerprint()
    assert registry.state(release.fingerprint()).cataloged is True
    assert len(registry.query()) == 1

    quarantine = _decision(release, "quarantine", decision_id="quarantine-1")
    _record(registry, quarantine)
    assert registry.state(release.fingerprint()).quarantined is True
    assert registry.query() == ()

    reapprove = _decision(release, "approve_catalog", decision_id="approve-2")
    _record(registry, reapprove)
    assert registry.state(release.fingerprint()).cataloged is True
    current = registry.release(release.fingerprint())
    assert current.fingerprint() == release.fingerprint()
    assert current.validation_evidence_fingerprint == evidence_before
    assert current.policy_fingerprint == policy_before


def test_revocation_is_terminal_and_historical_release_is_unchanged(tmp_path):
    release = _positive_release()
    registry = CuratedVirtualCellRegistry.create((tmp_path / "registry").resolve())
    _import(registry, release)
    _record(registry, _decision(release, "approve_catalog"))
    _record(registry, _decision(release, "revoke"))
    state = registry.state(release.fingerprint())
    assert state.revoked is True
    assert registry.query() == ()
    assert registry.release(release.fingerprint()).fingerprint() == release.fingerprint()
    with pytest.raises(CuratedRegistryError, match="closed releases"):
        _record(
            registry,
            _decision(release, "approve_catalog", decision_id="illegal-reopen"),
        )


def test_supersession_requires_active_same_id_different_version(tmp_path):
    first = _positive_release(release_version="1.0.0")
    second_raw = first.to_dict()
    second_raw["release_version"] = "1.1.0"
    second = VirtualCellReleaseV1.from_dict(second_raw)
    registry = CuratedVirtualCellRegistry.create((tmp_path / "registry").resolve())
    for release in (first, second):
        _import(registry, release)
        _record(registry, _decision(release, "approve_catalog"))
    supersede = _decision(first, "supersede", target=second)
    _record(registry, supersede)
    assert registry.state(first.fingerprint()).superseded_by == second.fingerprint()
    assert registry.state(second.fingerprint()).cataloged is True
    assert tuple(item["release_version"] for item in registry.query()) == ("1.1.0",)

    other = _positive_release(
        release_version="2.0.0",
        virtual_cell_id="other-cell",
    )
    _import(registry, other)
    _record(registry, _decision(other, "approve_catalog"))
    with pytest.raises(CuratedRegistryError, match="same Virtual Cell"):
        _record(
            registry,
            _decision(
                second,
                "supersede",
                decision_id="wrong-target",
                target=other,
            ),
        )


def test_same_id_version_conflict_is_permanent_even_after_revoke(tmp_path):
    release = _positive_release()
    conflicting = release.to_dict()
    conflicting["source_name"] = "different-source"
    conflicting_release = VirtualCellReleaseV1.from_dict(conflicting)
    registry = CuratedVirtualCellRegistry.create((tmp_path / "registry").resolve())
    _import(registry, release)
    _record(registry, _decision(release, "revoke"))
    with pytest.raises(CuratedRegistryError, match="ID/version"):
        _import(registry, conflicting_release)


def test_decision_contract_cannot_claim_science_policy_install_or_execution():
    release = _positive_release()
    raw = _decision(release, "approve_catalog").to_dict()
    for field, value in (
        ("scientific_state_changed", True),
        ("policy_state_changed", True),
        ("assets_installed", True),
        ("execution_performed", True),
    ):
        changed = dict(raw)
        changed[field] = value
        with pytest.raises(ValueError):
            CuratedRegistryDecisionV1.from_dict(changed)


def test_unknown_release_and_reused_decision_identity_fail_before_append(tmp_path):
    release = _positive_release()
    registry = CuratedVirtualCellRegistry.create((tmp_path / "registry").resolve())
    decision = _decision(release, "approve_catalog")
    with pytest.raises(CuratedRegistryError, match="unknown release"):
        _record(registry, decision)
    assert registry.verify() == ()

    _import(registry, release)
    _record(registry, decision)
    conflicting = CuratedRegistryDecisionV1.from_dict(
        {
            **decision.to_dict(),
            "reason": "different immutable decision bytes",
        }
    )
    with pytest.raises(CuratedRegistryError, match="decision ID"):
        _record(registry, conflicting)
    assert len(registry.verify()) == 2


def test_public_catalog_is_path_wrapper_uri_operator_and_reason_redacted(tmp_path):
    raw = _positive_release().to_dict()
    raw["source_name"] = "/private/registry/source token=secret"
    raw["release_license"] = "/private/license token=secret"
    release = VirtualCellReleaseV1.from_dict(raw)
    registry = CuratedVirtualCellRegistry.create((tmp_path / "registry").resolve())
    _import(registry, release)
    payload = registry.public_catalog(include_inactive=True)
    encoded = json.dumps(payload, sort_keys=True)
    for forbidden in (
        str(tmp_path),
        "/private/source",
        "/private/registry/source",
        "/private/license",
        "token=secret",
        "private.invalid",
        "synthetic.adapter.DeltaAdapter",
        "synthetic-policy-operator",
        "synthetic-release-reviewer",
        "transient contract conformance only",
        "cache_key",
        "source_uri",
        "entrypoint",
        "operator_id",
        "reason",
    ):
        assert forbidden not in encoded


def test_query_and_dependency_graph_are_read_only_fingerprint_surfaces(tmp_path):
    release = _positive_release()
    registry = CuratedVirtualCellRegistry.create((tmp_path / "registry").resolve())
    _import(registry, release)
    _record(registry, _decision(release, "approve_catalog"))
    assert len(registry.query(organism=release.context.organism)) == 1
    assert len(registry.query(cell_type=release.context.cell_type)) == 1
    assert registry.query(organism="different-organism") == ()
    graph = registry.dependency_graph(release.fingerprint())
    assert graph["release_fingerprint"] == release.fingerprint()
    assert tuple(graph["dependencies"]) == release.dependency_fingerprints
    assert not any("/" in item for item in graph["dependencies"])


def test_store_requires_canonical_write_new_root_and_rejects_symlinks(tmp_path):
    root = (tmp_path / "registry").resolve()
    CuratedVirtualCellRegistry.create(root)
    with pytest.raises(CuratedRegistryError, match="write-new"):
        CuratedVirtualCellRegistry.create(root)
    with pytest.raises(CuratedRegistryError, match="absolute"):
        CuratedVirtualCellRegistry.create(Path("relative-registry"))
    link = tmp_path / "registry-link"
    link.symlink_to(root, target_is_directory=True)
    with pytest.raises(CuratedRegistryError, match="non-symlink"):
        CuratedVirtualCellRegistry.open(link.absolute())


def test_noncanonical_duplicate_key_tamper_and_tail_truncation_fail_closed(tmp_path):
    release = _positive_release()
    root = (tmp_path / "registry").resolve()
    registry = CuratedVirtualCellRegistry.create(root)
    stored = _import(registry, release)
    original = stored.path.read_bytes()

    stored.path.write_bytes(b" " + original)
    with pytest.raises(CuratedRegistryError, match="canonical"):
        registry.verify()
    stored.path.write_bytes(original)

    raw = json.loads(original)
    duplicate = original.rstrip()[:-1] + b',"sequence":1}\n'
    stored.path.write_bytes(duplicate)
    with pytest.raises(CuratedRegistryError, match="strict JSON"):
        registry.verify()
    stored.path.write_bytes(original)
    assert raw["sequence"] == 1

    stored.path.unlink()
    with pytest.raises(CuratedRegistryError, match="truncation"):
        registry.verify()


def test_unexpected_entry_and_entry_symlink_fail_closed(tmp_path):
    registry = CuratedVirtualCellRegistry.create((tmp_path / "registry").resolve())
    unexpected = registry.root / "entries" / "unexpected.txt"
    unexpected.write_text("unexpected", encoding="utf-8")
    with pytest.raises(CuratedRegistryError, match="unexpected"):
        registry.verify()
    unexpected.unlink()
    target = tmp_path / "outside.json"
    target.write_text("{}", encoding="utf-8")
    link = registry.root / "entries" / f"00000001-{'f' * 64}.json"
    link.symlink_to(target)
    with pytest.raises(CuratedRegistryError, match="unexpected|regular|safely"):
        registry.verify()


def test_registry_reopens_and_revalidates_every_read(tmp_path):
    release = _positive_release()
    root = (tmp_path / "registry").resolve()
    registry = CuratedVirtualCellRegistry.create(root)
    _import(registry, release)
    reopened = CuratedVirtualCellRegistry.open(root, trust=registry._trust)
    assert reopened.release(release.fingerprint()).fingerprint() == release.fingerprint()
    marker = root / ".curated-registry.json"
    marker.write_text("{}\n", encoding="utf-8")
    with pytest.raises(CuratedRegistryError, match="marker"):
        reopened.verify()


def test_verified_external_checkpoint_detects_coherent_revocation_rollback(tmp_path):
    release = _positive_release()
    root = (tmp_path / "registry").resolve()
    registry = CuratedVirtualCellRegistry.create(root)
    _import(registry, release)
    _record(registry, _decision(release, "approve_catalog"))
    approved_checkpoint = registry.checkpoint()
    _record(registry, _decision(release, "revoke"))
    revoked_checkpoint = registry.checkpoint()

    checkpointed = CuratedVirtualCellRegistry.open(
        root,
        trust=_trust(checkpoint=revoked_checkpoint),
    )
    assert checkpointed.public_catalog()["revocation_checkpointed"] is True

    entries = registry.verify()
    entries[-1].path.unlink()
    (root / ".registry.head").write_bytes(
        json.dumps(
            approved_checkpoint.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )
    rolled_back = CuratedVirtualCellRegistry.open(
        root,
        trust=_trust(checkpoint=revoked_checkpoint),
    )
    with pytest.raises(CuratedRegistryError, match="monotonic checkpoint"):
        rolled_back.verify()


def test_checkpointed_reader_rejects_suffix_from_a_different_authority(tmp_path):
    release = _positive_release()
    root = (tmp_path / "registry").resolve()
    registry = CuratedVirtualCellRegistry.create(root)
    _import(registry, release)
    prefix = registry.checkpoint()
    decision = _decision(release, "approve_catalog")

    with pytest.raises(CuratedRegistryError, match="authority does not allow"):
        CuratedVirtualCellRegistry.open(root).verify()

    attacker_raw = _trust(
        decisions=(decision,),
        checkpoint=prefix,
    ).to_dict()
    attacker_raw["authority_id"] = "attacker-authority"
    attacker = CuratedVirtualCellRegistry.open(
        root,
        trust=CuratedRegistryTrustV1.from_dict(attacker_raw),
    )
    attacker.record_decision(decision)

    genuine = CuratedVirtualCellRegistry.open(
        root,
        trust=_trust(decisions=(decision,), checkpoint=prefix),
    )
    with pytest.raises(CuratedRegistryError, match="authorization provenance"):
        genuine.verify()
    with pytest.raises(CuratedRegistryError, match="authorization provenance"):
        genuine.public_catalog()


def test_read_rejects_pathname_rebind_and_verify_takes_shared_lock(tmp_path, monkeypatch):
    root = (tmp_path / "registry").resolve()
    registry = CuratedVirtualCellRegistry.create(root)
    lock_modes = []
    original_flock = fcntl.flock

    def observe_lock(descriptor, operation):
        lock_modes.append(operation)
        return original_flock(descriptor, operation)

    monkeypatch.setattr(fcntl, "flock", observe_lock)
    assert registry.verify() == ()
    assert fcntl.LOCK_SH in lock_modes

    marker = root / ".curated-registry.json"
    original_marker = root / ".original-marker"
    outside = tmp_path / "outside-marker"
    outside.write_bytes(marker.read_bytes())
    original_read = os.read
    swapped = False

    def rebind_after_read(descriptor, size):
        nonlocal swapped
        payload = original_read(descriptor, size)
        if payload and not swapped:
            swapped = True
            marker.rename(original_marker)
            marker.symlink_to(outside)
        return payload

    monkeypatch.setattr(os, "read", rebind_after_read)
    with pytest.raises(CuratedRegistryError, match="changed|regular"):
        registry.verify()


def test_unanchored_tail_is_recovered_only_by_retrying_the_exact_trusted_record(
    tmp_path,
):
    release = _positive_release()
    registry = CuratedVirtualCellRegistry.create((tmp_path / "registry").resolve())
    head = registry.root / ".registry.head"
    empty_head = head.read_bytes()
    _import(registry, release)
    head.write_bytes(empty_head)

    with pytest.raises(CuratedRegistryError, match="unanchored tail"):
        registry.verify()

    decision = _decision(release, "approve_catalog")
    with pytest.raises(CuratedRegistryError, match="unanchored tail"):
        _record(registry, decision)
    assert head.read_bytes() == empty_head

    assert _import(registry, release).record_fingerprint == release.fingerprint()
    _record(registry, decision)
    assert len(registry.verify()) == 2
    assert registry.state(release.fingerprint()).cataloged is True


def test_tail_recovery_also_requires_the_original_authorization_provenance(tmp_path):
    release = _positive_release()
    registry = CuratedVirtualCellRegistry.create((tmp_path / "registry").resolve())
    head = registry.root / ".registry.head"
    empty_head = head.read_bytes()
    stored = _import(registry, release)
    raw = json.loads(stored.path.read_bytes())
    raw["authorization_fingerprint"] = "f" * 64
    payload = json.dumps(raw, sort_keys=True, separators=(",", ":")).encode("utf-8")
    replacement = stored.path.with_name(f"00000001-{hashlib.sha256(payload).hexdigest()}.json")
    stored.path.unlink()
    replacement.write_bytes(payload + b"\n")
    head.write_bytes(empty_head)

    with pytest.raises(CuratedRegistryError, match="authorization provenance"):
        _import(registry, release)
    assert head.read_bytes() == empty_head


def test_publish_collision_and_partial_failure_never_overwrite(tmp_path, monkeypatch):
    release = _positive_release()
    collision_registry = CuratedVirtualCellRegistry.create((tmp_path / "collision").resolve())
    original_link = os.link
    competing = b"competing-entry\n"

    def collide(source, destination, **kwargs):
        (collision_registry.root / "entries" / destination).write_bytes(competing)
        return original_link(source, destination, **kwargs)

    monkeypatch.setattr(os, "link", collide)
    with pytest.raises(CuratedRegistryError, match="collision"):
        _import(collision_registry, release)
    visible = tuple(path for path in (collision_registry.root / "entries").iterdir() if not path.name.startswith("."))
    assert len(visible) == 1
    assert visible[0].read_bytes() == competing

    def fail_link(*_args, **_kwargs):
        raise OSError("injected")

    monkeypatch.setattr(os, "link", fail_link)
    partial_registry = CuratedVirtualCellRegistry.create((tmp_path / "partial").resolve())
    with pytest.raises(CuratedRegistryError, match="cannot append"):
        _import(partial_registry, release)
    assert tuple((partial_registry.root / "entries").iterdir()) == ()


def test_registry_holds_entries_and_lock_identities(tmp_path):
    root = (tmp_path / "registry").resolve()
    registry = CuratedVirtualCellRegistry.create(root)
    original_entries = tmp_path / "original-entries"
    (root / "entries").rename(original_entries)
    (root / "entries").mkdir()
    with pytest.raises(CuratedRegistryError, match="entries identity"):
        registry.verify()

    lock_root = (tmp_path / "lock-registry").resolve()
    lock_registry = CuratedVirtualCellRegistry.create(lock_root)
    (lock_root / ".registry.lock").rename(lock_root / ".original-lock")
    (lock_root / ".registry.lock").write_bytes(b"")
    with pytest.raises(CuratedRegistryError, match="lock identity"):
        lock_registry.verify()


def test_partial_registry_initialization_keeps_final_target_absent(tmp_path, monkeypatch):
    root = (tmp_path / "partial-create").resolve()
    original_open = os.open

    def fail_lock(path, flags, mode=0o777, *, dir_fd=None):
        if Path(path).name == ".registry.lock":
            raise OSError("injected")
        return original_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "open", fail_lock)
    with pytest.raises(CuratedRegistryError, match="initialize"):
        CuratedVirtualCellRegistry.create(root)
    assert not root.exists()


def test_import_and_lifecycle_never_touch_network_or_import_wrapper(tmp_path, monkeypatch):
    release = _positive_release()
    registry = CuratedVirtualCellRegistry.create((tmp_path / "registry").resolve())

    def forbidden(*_args, **_kwargs):
        raise AssertionError("network or dynamic wrapper import attempted")

    monkeypatch.setattr("urllib.request.urlopen", forbidden)
    monkeypatch.setattr("importlib.import_module", forbidden)
    monkeypatch.setattr(
        type(release.benchmark_bundle),
        "derive_with_p21b_execution",
        forbidden,
    )
    _import(registry, release)
    _record(registry, _decision(release, "approve_catalog"))
    assert registry.public_catalog()["releases"][0]["executable"] is False


def test_log_bytes_and_fingerprint_are_deterministic_across_two_stores(tmp_path):
    release = _positive_release()
    roots = ((tmp_path / "one").resolve(), (tmp_path / "two").resolve())
    stores = tuple(CuratedVirtualCellRegistry.create(root) for root in roots)
    for store in stores:
        _import(store, release)
        _record(store, _decision(release, "approve_catalog"))
    entries = [tuple(item.path.read_bytes() for item in store.verify()) for store in stores]
    assert entries[0] == entries[1]
    assert stores[0].public_catalog()["registry_fingerprint"] == stores[1].public_catalog()["registry_fingerprint"]
