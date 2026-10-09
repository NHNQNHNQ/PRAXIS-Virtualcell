"""P26E host–microbiome contracts remain value-free and fail closed."""

from __future__ import annotations

import hashlib
import json
import shutil

import pytest
from pydantic import ValidationError

from praxis_virtualcell.benchmarks.system import BenchmarkProtocolV1
from praxis_virtualcell.community_packs import (
    CommunityPack,
    VirtualMicrobiomeScopeV1,
    freeze_virtual_microbiome_contract,
    register_community,
    tiny_microbial_pack_roots,
)
from praxis_virtualcell.core.request_v2 import CellContext, VirtualCellRequestV2
from praxis_virtualcell.data_packs.registry import PackRegistry
from praxis_virtualcell.host_microbiome import (
    HostMicrobiomeCompilationV1,
    HostMicrobiomeContractError,
    HostMicrobiomeContractV1,
    HostMicrobiomeDAGV1,
    HostMicrobiomeInterfaceRequirementV1,
    HostReleaseAuditSnapshotV1,
    compile_host_microbiome,
    freeze_host_microbiome_contract,
)
from praxis_virtualcell.model_zoo.curated_registry import CuratedVirtualCellRegistry
from praxis_virtualcell.tests import test_curated_registry as p22
from praxis_virtualcell.tests.test_benchmark_system import _canonical_fp, _protocol_raw
from praxis_virtualcell.tests.test_virtual_microbiome_contract import (
    _community_raw,
)
from praxis_virtualcell.tests.test_virtual_microbiome_contract import (
    _contract as _p25_contract,
)
from praxis_virtualcell.tests.test_virtual_microbiome_contract import (
    _registered as _p25_community,
)


def _host_request(
    *,
    cell_type_name: str = "intestinal epithelial cell",
    tissue_name: str = "intestinal epithelium",
    tissue_id: str = "UBERON:0001277",
    attributes: dict | None = None,
) -> VirtualCellRequestV2:
    return VirtualCellRequestV2.from_dict(
        {
            "schema_version": "vc.request.v2",
            "request_id": "p26e-intestinal-host-fixture",
            "species": {
                "schema_version": "vc.species-ref.v1",
                "taxonomy_id": "NCBITaxon:9606",
                "scientific_name": "Homo sapiens",
                "common_name": "human",
            },
            "cell_context": {
                "schema_version": "vc.cell-context.v1",
                "cell_type_name": cell_type_name,
                "cell_type_id": "CL:0000066",
                "tissue_name": tissue_name,
                "tissue_id": tissue_id,
                "attributes": attributes or {},
            },
            "input_modality": {
                "schema_version": "vc.modality.v1",
                "name": "scRNA",
                "ontology_id": "EFO:0008913",
                "unit": None,
                "feature_namespace": "EnsemblGene",
            },
            "output_modality": {
                "schema_version": "vc.modality.v1",
                "name": "synthetic-delta",
                "ontology_id": None,
                "unit": None,
                "feature_namespace": "EnsemblGene",
            },
            "perturbation": {
                "schema_version": "vc.perturbation.v1",
                "kind": "gene",
                "targets": ["TP53"],
                "dose_value": None,
                "dose_unit": None,
                "timepoint": None,
            },
            "task": {
                "schema_version": "vc.task.v1",
                "task_type": "synthetic_perturbation_delta_prediction",
                "requested_outputs": ["synthetic-delta"],
            },
            "baseline_context": None,
            "metadata": {},
            "constraints": {},
        }
    )


def _intervention(request: VirtualCellRequestV2) -> str:
    return json.dumps(
        request.perturbation.to_dict(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _host_protocol(
    request: VirtualCellRequestV2,
    *,
    cell_type_name: str | None = None,
) -> BenchmarkProtocolV1:
    raw = _protocol_raw()
    raw["scope"] = {
        "schema_version": "vc.benchmark-scope.v1",
        "organism": request.species.scientific_name,
        "cell_type": cell_type_name or request.cell_context.cell_type_name,
        "intervention": _intervention(request),
        "endpoint": request.task.requested_outputs[0],
    }
    raw["external_policy"]["scope_fingerprint"] = _canonical_fp(raw["scope"])
    return BenchmarkProtocolV1.from_dict(raw)


def _synthetic_checkpointed_host_registry(
    tmp_path,
    monkeypatch,
    request,
    *,
    cell_type_name=None,
):
    protocol = _host_protocol(request, cell_type_name=cell_type_name)
    monkeypatch.setattr(p22, "_protocol", lambda: protocol)
    release = p22._positive_release(virtual_cell_id="transient-p26e-host")
    root = (tmp_path / "host-registry").resolve()
    registry = CuratedVirtualCellRegistry.create(root)
    p22._import(registry, release)
    decision = p22._decision(release, "approve_catalog")
    p22._record(registry, decision)
    checkpoint = registry.checkpoint()
    trusted = CuratedVirtualCellRegistry(
        root,
        trust=p22._trust(
            imports=(release,),
            decisions=(decision,),
            checkpoint=checkpoint,
        ),
    )
    return release, trusted


def _p26_contract(
    community,
    p25_contract,
    request,
    *,
    host_pack_fingerprint: str | None = None,
    host_release_fingerprint: str | None = None,
):
    return freeze_host_microbiome_contract(
        host_request=request,
        required_host_pack_fingerprint=host_pack_fingerprint,
        required_host_release_fingerprint=host_release_fingerprint,
        community=community,
        community_contract=p25_contract,
    )


def _resign_compilation(raw: dict) -> dict:
    payload = dict(raw)
    payload.pop("compilation_id", None)
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    raw["compilation_id"] = f"hm_comp_{hashlib.sha256(canonical).hexdigest()[:24]}"
    return raw


def test_p22_context_candidate_cannot_upgrade_full_request_or_p25(tmp_path, monkeypatch):
    request = _host_request()
    release, registry = _synthetic_checkpointed_host_registry(tmp_path, monkeypatch, request)
    community = _p25_community()
    contract = _p26_contract(
        community,
        _p25_contract(),
        request,
        host_pack_fingerprint=release.pack_registration.pack_fingerprint,
        host_release_fingerprint=release.fingerprint(),
    )

    compilation = compile_host_microbiome(community, contract, host_registry=registry)

    assert compilation.host_release_audit.audit_status == "p22_context_matched_request_binding_insufficient"
    assert compilation.host_release_audit.exact_request_match_verified is False
    assert compilation.host_release_audit.scientifically_validated_for_full_request is None
    assert compilation.host_release_audit.production_promoted_for_full_request is None
    assert compilation.community_release_fingerprint is None
    assert compilation.community_scientifically_validated is None
    assert compilation.community_production_promoted is None
    assert compilation.matching_release_fingerprint is None
    assert compilation.matching_release_verified is False
    assert compilation.steps == ()
    assert compilation.executable is False
    assert compilation.prediction is None
    assert compilation.execution_performed is False
    assert compilation.scientifically_validated is False
    assert compilation.promotion_eligible is False
    assert compilation.production_promoted is False
    assert compilation.abstain_reasons == (
        "matching_host_release_unavailable",
        "matching_community_release_unavailable",
        "matching_release_unavailable",
        "cross_domain_interface_unavailable",
        "p26_real_execution_not_authorized",
    )


def test_tissue_drift_cannot_be_hidden_by_same_p22_context(tmp_path, monkeypatch):
    intestinal = _host_request()
    release, registry = _synthetic_checkpointed_host_registry(
        tmp_path,
        monkeypatch,
        intestinal,
    )
    community = _p25_community()
    p25 = _p25_contract()
    liver = _host_request(
        tissue_name="liver",
        tissue_id="UBERON:0002107",
        attributes={"donor_group": "different"},
    )
    intestinal_contract = _p26_contract(
        community,
        p25,
        intestinal,
        host_pack_fingerprint=release.pack_registration.pack_fingerprint,
        host_release_fingerprint=release.fingerprint(),
    )
    liver_contract = _p26_contract(
        community,
        p25,
        liver,
        host_pack_fingerprint=release.pack_registration.pack_fingerprint,
        host_release_fingerprint=release.fingerprint(),
    )

    intestinal_result = compile_host_microbiome(
        community,
        intestinal_contract,
        host_registry=registry,
    )
    liver_result = compile_host_microbiome(
        community,
        liver_contract,
        host_registry=registry,
    )

    assert intestinal_contract.host_request_fingerprint != liver_contract.host_request_fingerprint
    assert intestinal_contract.host_context.benchmark_scope_fingerprint == (
        liver_contract.host_context.benchmark_scope_fingerprint
    )
    assert intestinal_result.host_release_audit.exact_request_match_verified is False
    assert liver_result.host_release_audit.exact_request_match_verified is False
    assert liver_result.host_release_audit.scientifically_validated_for_full_request is None
    assert liver_result.abstain_reasons[0] == "matching_host_release_unavailable"


def test_k562_release_cannot_satisfy_intestinal_host_request(tmp_path, monkeypatch):
    request = _host_request()
    release, registry = _synthetic_checkpointed_host_registry(
        tmp_path,
        monkeypatch,
        request,
        cell_type_name="K562",
    )
    community = _p25_community()
    contract = _p26_contract(
        community,
        _p25_contract(),
        request,
        host_pack_fingerprint=release.pack_registration.pack_fingerprint,
        host_release_fingerprint=release.fingerprint(),
    )

    compilation = compile_host_microbiome(community, contract, host_registry=registry)

    assert compilation.host_release_audit.audit_status == "release_mismatch"
    assert compilation.host_release_audit.exact_request_match_verified is False
    assert compilation.host_release_audit.scientifically_validated_for_full_request is None
    assert compilation.abstain_reasons[0] == "matching_host_release_unavailable"
    assert compilation.steps == ()
    assert compilation.prediction is None


def test_p26_revalidates_p25_member_bytes_after_freeze(tmp_path):
    copied_roots = {}
    for member, source in tiny_microbial_pack_roots().items():
        target = tmp_path / member
        shutil.copytree(source, target)
        copied_roots[member] = target
    registry = PackRegistry()
    for root in copied_roots.values():
        registry.register(root)
    community = register_community(CommunityPack.from_dict(_community_raw(registry)), registry)
    p25 = freeze_virtual_microbiome_contract(community, scientific_gate_threshold="0.1")
    contract = _p26_contract(community, p25, _host_request())
    with (copied_roots["ecoli"] / "tiny.h5ad").open("ab") as handle:
        handle.write(b"p26-stale")

    compilation = compile_host_microbiome(community, contract)

    assert compilation.abstain_reasons[0] == "unsupported_host_microbiome_scope"
    assert compilation.steps == ()
    assert compilation.prediction is None


def test_nested_model_copy_and_authority_injections_are_rejected():
    community = _p25_community()
    p25 = _p25_contract()
    request = _host_request()
    bad_context = request.cell_context.model_copy(update={"cell_type_name": ""})
    bad_request = request.model_copy(update={"cell_context": bad_context})
    with pytest.raises(HostMicrobiomeContractError, match="host request"):
        _p26_contract(community, p25, bad_request)

    class LyingCellContext(CellContext):
        production_promoted: bool
        executable: bool
        prediction: list[float]

    lying_context = LyingCellContext.model_construct(
        _fields_set=set(LyingCellContext.model_fields),
        **{
            **request.cell_context.to_dict(),
            "production_promoted": True,
            "executable": True,
            "prediction": [1.0],
        },
    )
    lying_request = request.model_copy(update={"cell_context": lying_context})
    with pytest.raises(HostMicrobiomeContractError, match="host request"):
        _p26_contract(community, p25, lying_request)

    contract = _p26_contract(community, p25, request)
    bad_scope = p25.scope.model_copy(update={"time_end": "48"})
    bad_p25 = p25.model_copy(update={"scope": bad_scope})
    bad_contract = contract.model_copy(update={"community_contract": bad_p25})
    with pytest.raises(HostMicrobiomeContractError, match="contract"):
        compile_host_microbiome(community, bad_contract)

    class LyingP25Scope(VirtualMicrobiomeScopeV1):
        production_promoted: bool
        prediction: list[float]

        def to_dict(self):
            return p25.scope.to_dict()

    lying_scope = LyingP25Scope.model_construct(
        _fields_set=set(LyingP25Scope.model_fields),
        **{
            **p25.scope.to_dict(),
            "production_promoted": True,
            "prediction": [1.0],
        },
    )
    lying_p25 = p25.model_copy(update={"scope": lying_scope})
    lying_contract = contract.model_copy(update={"community_contract": lying_p25})
    with pytest.raises(HostMicrobiomeContractError, match="contract"):
        compile_host_microbiome(community, lying_contract)

    raw = contract.to_dict()
    raw["llm_verdict"] = "execute"
    with pytest.raises(ValidationError):
        HostMicrobiomeContractV1.model_validate(raw)

    interface = contract.interface_requirement

    class LyingInterface(HostMicrobiomeInterfaceRequirementV1):
        mapping_fingerprint: str | None
        implementation_available: bool
        causal_claim_allowed: bool

        def to_dict(self):
            return interface.to_dict()

    lying_interface = LyingInterface.model_construct(
        _fields_set=set(LyingInterface.model_fields),
        **{
            **interface.to_dict(),
            "mapping_fingerprint": "a" * 64,
            "implementation_available": True,
            "causal_claim_allowed": True,
        },
    )
    raw = contract.to_dict()
    raw["interface_requirement"] = lying_interface
    with pytest.raises(ValidationError, match="non-canonical nested identity"):
        HostMicrobiomeContractV1.model_validate(raw)

    dag = contract.dag

    class LyingDAG(HostMicrobiomeDAGV1):
        execution_steps: tuple[dict[str, str], ...]
        executable: bool

        def to_dict(self):
            return dag.to_dict()

    lying_dag = LyingDAG.model_construct(
        _fields_set=set(LyingDAG.model_fields),
        **{
            **dag.to_dict(),
            "execution_steps": ({"model": "fallback"},),
            "executable": True,
        },
    )
    raw = contract.to_dict()
    raw["dag"] = lying_dag
    with pytest.raises(ValidationError, match="non-canonical nested identity"):
        HostMicrobiomeContractV1.model_validate(raw)

    compilation = compile_host_microbiome(community, contract)
    benign = compilation.host_release_audit

    class LyingAudit(HostReleaseAuditSnapshotV1):
        scientifically_validated_for_full_request: bool
        production_promoted_for_full_request: bool
        exact_request_match_verified: bool

        def to_dict(self):
            return benign.to_dict()

    evil = LyingAudit.model_construct(
        _fields_set=set(LyingAudit.model_fields),
        **{
            **benign.to_dict(),
            "scientifically_validated_for_full_request": True,
            "production_promoted_for_full_request": True,
            "exact_request_match_verified": True,
        },
    )
    raw = compilation.to_dict()
    raw["host_release_audit"] = evil
    with pytest.raises(ValidationError, match="exact HostReleaseAuditSnapshotV1"):
        HostMicrobiomeCompilationV1.model_validate(raw)


def test_interface_and_release_slots_are_fixed_negative_requirements():
    community = _p25_community()
    contract = _p26_contract(community, _p25_contract(), _host_request())
    interface = contract.interface_requirement

    assert contract.required_host_pack_fingerprint is None
    assert contract.required_host_release_fingerprint is None
    assert interface.interface_entity_kinds == ("metabolite", "cytokine", "receptor")
    assert interface.directions == ("microbe_to_mediator_to_host", "host_to_community")
    assert interface.mapping_fingerprint is None
    assert interface.implementation_available is False

    raw = interface.to_dict()
    raw["directions"] = list(reversed(raw["directions"]))
    with pytest.raises(ValidationError, match="directions"):
        HostMicrobiomeInterfaceRequirementV1.model_validate(raw)
    raw = interface.to_dict()
    raw["mapping_fingerprint"] = "8" * 64
    with pytest.raises(ValidationError):
        HostMicrobiomeInterfaceRequirementV1.model_validate(raw)

    raw = contract.to_dict()
    raw["required_community_release_schema_version"] = "vc.virtual-cell-release.v1"
    raw["required_community_release_fingerprint"] = contract.community_scope_fingerprint
    with pytest.raises(ValidationError):
        HostMicrobiomeContractV1.model_validate(raw)
    raw = contract.to_dict()
    raw["required_matching_release_fingerprint"] = contract.community_contract_fingerprint
    with pytest.raises(ValidationError):
        HostMicrobiomeContractV1.model_validate(raw)


def test_registry_checkpoint_and_lifecycle_are_revalidated(tmp_path, monkeypatch):
    request = _host_request()
    release, registry = _synthetic_checkpointed_host_registry(tmp_path, monkeypatch, request)
    community = _p25_community()
    contract = _p26_contract(
        community,
        _p25_contract(),
        request,
        host_pack_fingerprint=release.pack_registration.pack_fingerprint,
        host_release_fingerprint=release.fingerprint(),
    )
    uncheckpointed = CuratedVirtualCellRegistry(
        registry.root,
        trust=p22._trust(
            imports=(release,),
            decisions=(p22._decision(release, "approve_catalog"),),
        ),
    )
    compilation = compile_host_microbiome(
        community,
        contract,
        host_registry=uncheckpointed,
    )
    assert compilation.host_release_audit.audit_status == "registry_checkpoint_unverified"
    assert compilation.host_release_audit.scientifically_validated_for_full_request is None

    revoke = p22._decision(release, "revoke")
    p22._record(registry, revoke)
    revoked = CuratedVirtualCellRegistry(
        registry.root,
        trust=p22._trust(
            imports=(release,),
            decisions=(p22._decision(release, "approve_catalog"), revoke),
            checkpoint=registry.checkpoint(),
        ),
    )
    compilation = compile_host_microbiome(community, contract, host_registry=revoked)
    assert compilation.host_release_audit.audit_status == "release_inactive"
    assert compilation.host_release_audit.production_promoted_for_full_request is None
    assert compilation.steps == ()


def test_candidate_api_is_closed_and_rehashed_payload_cannot_upgrade_result():
    class Bomb:
        def __getattribute__(self, name):
            raise AssertionError(f"candidate was inspected: {name}")

        __iter__ = __len__ = __getitem__ = __repr__ = __getattribute__

    community = _p25_community()
    contract = _p26_contract(community, _p25_contract(), _host_request())
    compilation = compile_host_microbiome(community, contract)

    with pytest.raises(TypeError, match="candidate_dag"):
        compile_host_microbiome(community, contract, candidate_dag=Bomb())  # type: ignore[call-arg]

    assert contract.dag.nodes == (
        "community_state_t0",
        "mediator_state_t1",
        "host_state_t2",
        "community_state_t3",
    )
    assert contract.dag.edges == (
        "community_state_t0|microbe_to_mediator|mediator_state_t1",
        "mediator_state_t1|mediator_to_host|host_state_t2",
        "host_state_t2|host_to_community|community_state_t3",
    )
    assert compilation.steps == ()
    assert compilation.prediction is None

    for field, value in (
        ("steps", [{"model": "fallback"}]),
        ("prediction", [1.0]),
        ("execution_performed", True),
        ("community_release_fingerprint", contract.community_scope_fingerprint),
    ):
        raw = compilation.to_dict()
        raw[field] = value
        _resign_compilation(raw)
        with pytest.raises(ValidationError):
            HostMicrobiomeCompilationV1.model_validate(raw)

    raw = contract.dag.to_dict()
    raw["execution_steps"] = [{"model": "fallback"}]
    with pytest.raises(ValidationError):
        HostMicrobiomeDAGV1.model_validate(raw)
