"""P25E fixed-scope virtual microbiome contracts remain fail-closed."""

from __future__ import annotations

import hashlib
import json
import shutil
from copy import deepcopy

import pytest
import yaml
from pydantic import ValidationError

from praxis_virtualcell.community_packs import (
    CommunityPack,
    VirtualMicrobiomeAdapterRequirementV1,
    VirtualMicrobiomeContractError,
    VirtualMicrobiomeContractV1,
    VirtualMicrobiomePlanV1,
    VirtualMicrobiomePrimaryEndpointV1,
    VirtualMicrobiomeRequestV1,
    VirtualMicrobiomeResultV1,
    VirtualMicrobiomeScopeV1,
    freeze_virtual_microbiome_contract,
    plan_virtual_microbiome,
    register_community,
    run_virtual_microbiome,
    tiny_microbial_pack_roots,
)
from praxis_virtualcell.data_packs.registry import PackRegistry
from praxis_virtualcell.pack_product import builtin_pack_roots


def _registry() -> PackRegistry:
    registry = PackRegistry()
    for root in tiny_microbial_pack_roots().values():
        registry.register(root)
    return registry


def _community_raw(registry: PackRegistry) -> dict:
    bacteria = registry.record("p8-bacteria-tiny", "1.0.0")
    yeast = registry.record("p10-yeast-tiny", "1.0.0")
    return {
        "schema_version": "vc.community-pack.v1",
        "community_id": "p25e-contract-fixture",
        "community_version": "1.0.0",
        "members": [
            {
                "member_id": "ecoli",
                "pack_id": bacteria.manifest.pack_id,
                "pack_version": bacteria.manifest.pack_version,
                "pack_fingerprint": bacteria.fingerprint,
                "abundance": {"value": "0.5", "unit": "fraction"},
                "compartment_id": "culture",
                "exchange": {
                    "metabolite_ids": ["PRAXISMET:carbon"],
                    "amount_unit": "mmol",
                },
            },
            {
                "member_id": "yeast",
                "pack_id": yeast.manifest.pack_id,
                "pack_version": yeast.manifest.pack_version,
                "pack_fingerprint": yeast.fingerprint,
                "abundance": {"value": "0.5", "unit": "fraction"},
                "compartment_id": "culture",
                "exchange": {
                    "metabolite_ids": ["PRAXISMET:carbon"],
                    "amount_unit": "mmol",
                },
            },
        ],
        "medium": {
            "medium_id": "defined-medium",
            "compartment_id": "culture",
            "components": [
                {
                    "metabolite_id": "PRAXISMET:carbon",
                    "concentration": {"value": "10", "unit": "mmol/L"},
                }
            ],
        },
        "compartments": [{"id": "culture", "role": "shared_medium"}],
        "time": {"start": "0", "end": "24", "unit": "h"},
        "space": {"representation": "well_mixed"},
        "shared_metabolite_namespace": {
            "name": "PRAXISMET",
            "version": "p25e-contract-only",
            "id_format": "curie",
            "amount_unit": "mmol",
            "metabolites": [{"id": "PRAXISMET:carbon", "label": "contract fixture"}],
        },
        "interaction_evidence": [],
        "scientifically_validated": False,
    }


def _registered():
    registry = _registry()
    manifest = CommunityPack.from_dict(_community_raw(registry))
    return register_community(manifest, registry)


def _contract():
    return freeze_virtual_microbiome_contract(
        _registered(),
        scientific_gate_threshold="0.1",
    )


def test_contract_freezes_exact_two_member_medium_time_and_one_primary_endpoint():
    community = _registered()
    contract = freeze_virtual_microbiome_contract(
        community,
        scientific_gate_threshold="0.1",
    )

    assert contract.schema_version == "vc.virtual-microbiome-contract.v1"
    assert contract.scope.member_ids == ("ecoli", "yeast")
    assert contract.scope.member_pack_fingerprints == tuple(member.fingerprint for member in community.members)
    assert contract.scope.medium_fingerprint == community.manifest.medium.fingerprint()
    assert contract.scope.time_fingerprint == community.manifest.time.fingerprint()
    assert len(contract.scope.member_ids) in (2, 3)
    assert contract.scope.member_taxonomy_ids == ("NCBITaxon:562", "NCBITaxon:4932")
    assert contract.scope.member_strain_identity_term_ids == (
        "PRAXISCELL:ecoli_k12",
        "PRAXISCELL:yeast_s288c",
    )
    assert contract.endpoint.endpoint_role == "primary"
    assert contract.endpoint.member_ids == contract.scope.member_ids
    assert contract.endpoint.time_fingerprint == contract.scope.time_fingerprint
    assert contract.endpoint.secondary_may_override_primary is False
    assert contract.endpoint.scientific_gate_threshold == "0.1"
    assert contract.adapter_requirement.implementation_available is False
    assert contract.adapter_requirement.p24_adapter_fingerprint is None
    assert contract.adapter_requirement.benchmark_protocol_fingerprint is None
    assert contract.record_role == "p25e_contract_only"


def test_scope_allows_only_two_or_three_ordered_unique_members():
    raw = _contract().scope.to_dict()
    for field in (
        "member_ids",
        "member_pack_fingerprints",
        "member_taxonomy_ids",
        "member_scientific_names",
        "member_assembly_accessions",
        "member_strain_identity_term_ids",
        "initial_abundances",
    ):
        raw[field] = raw[field][:1]
    raw["initial_abundances"] = ["1"]
    with pytest.raises(ValidationError, match="2 or 3"):
        VirtualMicrobiomeScopeV1.model_validate(raw)

    raw = _contract().scope.to_dict()
    raw["member_ids"] = ["a", "b", "c", "d"]
    raw["member_pack_fingerprints"] = [str(index) * 64 for index in range(1, 5)]
    raw["member_taxonomy_ids"] = [f"NCBITaxon:{index}" for index in range(1, 5)]
    raw["member_scientific_names"] = [f"member {index}" for index in range(1, 5)]
    raw["member_assembly_accessions"] = [f"GCF_00000000{index}.1" for index in range(1, 5)]
    raw["member_strain_identity_term_ids"] = [f"STRAIN:member-{index}" for index in range(1, 5)]
    raw["initial_abundances"] = ["0.25"] * 4
    with pytest.raises(ValidationError, match="2 or 3"):
        VirtualMicrobiomeScopeV1.model_validate(raw)

    raw = _contract().scope.to_dict()
    raw["member_ids"] = ["ecoli", "ecoli"]
    with pytest.raises(ValidationError, match="unique"):
        VirtualMicrobiomeScopeV1.model_validate(raw)


def test_bad_hashes_and_stale_nested_fingerprints_are_rejected():
    raw = _contract().to_dict()
    raw["scope_fingerprint"] = "0" * 64
    with pytest.raises(ValidationError, match="scope_fingerprint is stale"):
        VirtualMicrobiomeContractV1.model_validate(raw)

    raw = _contract().adapter_requirement.to_dict()
    raw["scope_fingerprint"] = "not-a-hash"
    with pytest.raises(ValidationError, match="fingerprint"):
        VirtualMicrobiomeAdapterRequirementV1.model_validate(raw)

    for field in ("endpoint_fingerprint", "adapter_requirement_fingerprint"):
        raw = _contract().to_dict()
        raw[field] = "0" * 64
        with pytest.raises(ValidationError, match="stale"):
            VirtualMicrobiomeContractV1.model_validate(raw)

    community = _registered()
    contract = freeze_virtual_microbiome_contract(
        community,
        scientific_gate_threshold="0.1",
    )
    request = VirtualMicrobiomeRequestV1.for_contract(contract)
    plan_raw = plan_virtual_microbiome(community, contract, request).to_dict()
    plan_raw["plan_id"] = "vm_plan_" + "0" * 24
    with pytest.raises(ValidationError, match="plan_id is stale"):
        VirtualMicrobiomePlanV1.model_validate(plan_raw)

    plan_raw = plan_virtual_microbiome(community, contract, request).to_dict()
    plan_raw["abstain_reasons"] = [{}]
    with pytest.raises(ValidationError, match="string JSON array"):
        VirtualMicrobiomePlanV1.model_validate(plan_raw)

    result_raw = run_virtual_microbiome(community, contract, request).to_dict()
    result_raw["execution_plan_fingerprint"] = "0" * 64
    with pytest.raises(ValidationError, match="execution_plan_fingerprint is stale"):
        VirtualMicrobiomeResultV1.model_validate(result_raw)


def test_endpoint_cannot_change_member_order_time_or_primary_policy():
    contract = _contract()
    raw = contract.endpoint.to_dict()
    raw["member_ids"] = list(reversed(raw["member_ids"]))
    endpoint = VirtualMicrobiomePrimaryEndpointV1.model_validate(raw)
    bundle = contract.to_dict()
    bundle["endpoint"] = endpoint.to_dict()
    bundle["endpoint_fingerprint"] = endpoint.fingerprint()
    with pytest.raises(ValidationError, match="endpoint member order"):
        VirtualMicrobiomeContractV1.model_validate(bundle)

    raw = contract.endpoint.to_dict()
    raw["secondary_may_override_primary"] = True
    with pytest.raises(ValidationError):
        VirtualMicrobiomePrimaryEndpointV1.model_validate(raw)


def test_negative_adapter_binding_and_ood_axes_cannot_be_forged():
    adapter = _contract().adapter_requirement
    assert adapter.required_ood_axes == (
        "member",
        "medium",
        "initial_abundance",
        "time",
        "condition",
        "batch",
    )
    for axes in (
        list(adapter.required_ood_axes[:-1]),
        list(reversed(adapter.required_ood_axes)),
        [*adapter.required_ood_axes, "dataset"],
    ):
        raw = adapter.to_dict()
        raw["required_ood_axes"] = axes
        with pytest.raises(ValidationError, match="required_ood_axes"):
            VirtualMicrobiomeAdapterRequirementV1.model_validate(raw)

    for field in (
        "p24_adapter_fingerprint",
        "model_fingerprint",
        "environment_fingerprint",
        "metabolite_mapping_fingerprint",
        "benchmark_protocol_fingerprint",
        "evidence_fingerprint",
        "policy_fingerprint",
    ):
        raw = adapter.to_dict()
        raw[field] = "0" * 64
        with pytest.raises(ValidationError):
            VirtualMicrobiomeAdapterRequirementV1.model_validate(raw)


def test_contract_is_canonical_immutable_and_rejects_injected_fields():
    contract = _contract()
    assert (
        VirtualMicrobiomeContractV1.model_validate(dict(reversed(contract.to_dict().items()))).fingerprint()
        == contract.fingerprint()
    )
    with pytest.raises(ValidationError):
        contract.scope.member_ids = ("changed",)  # type: ignore[misc]

    raw = contract.to_dict()
    raw["llm_verdict"] = "execute"
    with pytest.raises(ValidationError, match="extra"):
        VirtualMicrobiomeContractV1.model_validate(raw)

    raw = contract.adapter_requirement.to_dict()
    raw["implementation_available"] = 0
    with pytest.raises(ValidationError):
        VirtualMicrobiomeAdapterRequirementV1.model_validate(raw)


def test_exact_request_still_abstains_when_p24_and_science_policy_are_missing():
    community = _registered()
    contract = freeze_virtual_microbiome_contract(
        community,
        scientific_gate_threshold="0.1",
    )
    request = VirtualMicrobiomeRequestV1.for_contract(contract)

    plan = plan_virtual_microbiome(community, contract, request)
    result = run_virtual_microbiome(community, contract, request)

    assert plan.schema_version == "vc.virtual-microbiome-plan.v1"
    assert plan.executable is False
    assert plan.steps == ()
    assert plan.abstain_reasons == (
        "p24_adapter_unavailable",
        "model_identity_unavailable",
        "environment_identity_unavailable",
        "metabolite_mapping_identity_unavailable",
        "benchmark_protocol_unavailable",
        "real_execution_binding_unavailable",
        "scientific_evidence_unavailable",
        "production_policy_unavailable",
    )
    assert result.schema_version == "vc.virtual-microbiome-result.v1"
    assert result.abstain is True
    assert result.prediction is None
    assert result.secondary_predictions is None
    assert result.execution_plan == plan
    assert result.scientifically_validated is False
    assert result.production_promoted is False


def test_wrong_scope_and_stale_community_identity_fail_closed():
    community = _registered()
    contract = freeze_virtual_microbiome_contract(
        community,
        scientific_gate_threshold="0.1",
    )
    request_raw = VirtualMicrobiomeRequestV1.for_contract(contract).to_dict()
    request_raw["medium_fingerprint"] = "0" * 64
    request = VirtualMicrobiomeRequestV1.model_validate(request_raw)

    plan = plan_virtual_microbiome(community, contract, request)
    assert plan.executable is False
    assert plan.abstain_reasons[0] == "unsupported_virtual_microbiome_scope"

    registry = _registry()
    changed = _community_raw(registry)
    changed["time"]["end"] = "48"
    other = register_community(CommunityPack.from_dict(changed), registry)
    plan = plan_virtual_microbiome(other, contract, VirtualMicrobiomeRequestV1.for_contract(contract))
    assert plan.executable is False
    assert plan.abstain_reasons[0] == "stale_community_identity"

    raw = contract.to_dict()
    scope_raw = raw["scope"]
    scope_raw["time_end"] = "48"
    resigned_scope = VirtualMicrobiomeScopeV1.model_validate(scope_raw)
    raw["scope"] = resigned_scope.to_dict()
    raw["scope_fingerprint"] = resigned_scope.fingerprint()
    adapter_raw = raw["adapter_requirement"]
    adapter_raw["scope_fingerprint"] = resigned_scope.fingerprint()
    resigned_adapter = VirtualMicrobiomeAdapterRequirementV1.model_validate(adapter_raw)
    raw["adapter_requirement"] = resigned_adapter.to_dict()
    raw["adapter_requirement_fingerprint"] = resigned_adapter.fingerprint()
    resigned_contract = VirtualMicrobiomeContractV1.model_validate(raw)
    plan = plan_virtual_microbiome(
        community,
        resigned_contract,
        VirtualMicrobiomeRequestV1.for_contract(resigned_contract),
    )
    assert plan.abstain_reasons[0] == "stale_community_identity"


def test_member_pack_byte_drift_is_revalidated_before_planning(tmp_path):
    copied_registry = PackRegistry()
    copied_roots = []
    for name, source in tiny_microbial_pack_roots().items():
        root = tmp_path / name
        shutil.copytree(source, root)
        copied_roots.append(root)
        copied_registry.register(root)
    community = register_community(CommunityPack.from_dict(_community_raw(copied_registry)), copied_registry)
    contract = freeze_virtual_microbiome_contract(
        community,
        scientific_gate_threshold="0.1",
    )

    with (copied_roots[0] / "tiny.h5ad").open("ab") as stream:
        stream.write(b"tampered-after-freeze")

    request = VirtualMicrobiomeRequestV1.for_contract(contract)
    plan = plan_virtual_microbiome(community, contract, request)
    result = run_virtual_microbiome(community, contract, request)
    assert plan.abstain_reasons[0] == "member_pack_revalidation_failed"
    assert plan.executable is False
    assert result.prediction is None


def test_member_pack_byte_drift_is_rejected_before_freeze(tmp_path):
    registry = PackRegistry()
    copied_roots = []
    for name, source in tiny_microbial_pack_roots().items():
        root = tmp_path / name
        shutil.copytree(source, root)
        copied_roots.append(root)
        registry.register(root)
    community = register_community(CommunityPack.from_dict(_community_raw(registry)), registry)
    with (copied_roots[0] / "tiny.h5ad").open("ab") as stream:
        stream.write(b"tampered-before-freeze")

    with pytest.raises(VirtualMicrobiomeContractError, match="cannot freeze"):
        freeze_virtual_microbiome_contract(
            community,
            scientific_gate_threshold="0.1",
        )


def test_human_pack_with_injected_identity_term_cannot_be_labeled_microbiome(tmp_path):
    registry = _registry()
    human_root = tmp_path / "human-with-injected-identity"
    shutil.copytree(builtin_pack_roots()["human"], human_root)
    manifest_path = human_root / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["pack_id"] = "p25e-human-injected-identity"
    manifest["cell_semantics"]["local_terms"].append(
        {
            "id": "PRAXISCELL:human_injected",
            "role": "identity",
            "label": "injected human identity",
            "definition": "Adversarial unused identity term; not a microbial strain.",
        }
    )
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    registry.register(human_root)
    raw = _community_raw(registry)
    records = (
        registry.record("p25e-human-injected-identity", "1.0.0"),
        registry.record("p10-yeast-tiny", "1.0.0"),
    )
    for member, record, member_id in zip(raw["members"], records, ("human", "yeast"), strict=True):
        member.update(
            member_id=member_id,
            pack_id=record.manifest.pack_id,
            pack_version=record.manifest.pack_version,
            pack_fingerprint=record.fingerprint,
        )
    community = register_community(CommunityPack.from_dict(raw), registry)

    with pytest.raises(VirtualMicrobiomeContractError, match="audited synthetic microbial"):
        freeze_virtual_microbiome_contract(
            community,
            scientific_gate_threshold="0.1",
        )


@pytest.mark.parametrize(
    "mutation",
    [
        lambda raw: raw.update(community_fingerprint="0" * 64),
        lambda raw: raw.update(member_pack_fingerprints=list(reversed(raw["member_pack_fingerprints"]))),
        lambda raw: raw.update(medium_fingerprint="0" * 64),
        lambda raw: raw.update(time_fingerprint="0" * 64),
        lambda raw: raw.update(scope_fingerprint="0" * 64),
        lambda raw: raw.update(primary_endpoint_fingerprint="0" * 64),
        lambda raw: raw.update(adapter_requirement_fingerprint="0" * 64),
    ],
)
def test_each_request_identity_drift_abstains_without_steps(mutation):
    community = _registered()
    contract = freeze_virtual_microbiome_contract(
        community,
        scientific_gate_threshold="0.1",
    )
    raw = VirtualMicrobiomeRequestV1.for_contract(contract).to_dict()
    mutation(raw)
    request = VirtualMicrobiomeRequestV1.model_validate(raw)

    plan = plan_virtual_microbiome(community, contract, request)
    result = run_virtual_microbiome(community, contract, request)
    assert plan.abstain_reasons[0] == "unsupported_virtual_microbiome_scope"
    assert plan.steps == ()
    assert result.prediction is None


def test_in_memory_nested_model_bypasses_are_revalidated():
    community = _registered()
    contract = freeze_virtual_microbiome_contract(
        community,
        scientific_gate_threshold="0.1",
    )
    forged_adapter = contract.adapter_requirement.model_copy(update={"implementation_available": True})
    with pytest.raises(ValidationError, match="implementation_available"):
        VirtualMicrobiomeContractV1(
            schema_version=contract.schema_version,
            scope=contract.scope,
            scope_fingerprint=contract.scope_fingerprint,
            endpoint=contract.endpoint,
            endpoint_fingerprint=contract.endpoint_fingerprint,
            adapter_requirement=forged_adapter,
            adapter_requirement_fingerprint=forged_adapter.fingerprint(),
            record_role=contract.record_role,
        )

    request = VirtualMicrobiomeRequestV1.for_contract(contract)
    plan = plan_virtual_microbiome(community, contract, request)
    forged_plan = plan.model_copy(update={"executable": True})
    identity = forged_plan.model_dump(mode="json", exclude={"plan_id"})
    encoded = json.dumps(
        identity,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    forged_plan = forged_plan.model_copy(update={"plan_id": f"vm_plan_{hashlib.sha256(encoded).hexdigest()[:24]}"})
    with pytest.raises(ValidationError, match="executable"):
        VirtualMicrobiomeResultV1(
            schema_version="vc.virtual-microbiome-result.v1",
            contract_fingerprint=contract.fingerprint(),
            request_fingerprint=request.fingerprint(),
            execution_plan=forged_plan,
            execution_plan_fingerprint=forged_plan.fingerprint(),
            abstain=True,
            prediction=None,
            secondary_predictions=None,
            abstain_reasons=list(forged_plan.abstain_reasons),
            scientifically_validated=False,
            promotion_eligible=False,
            production_promoted=False,
        )


def test_run_result_cannot_be_forged_with_primary_or_secondary_predictions():
    community = _registered()
    contract = freeze_virtual_microbiome_contract(
        community,
        scientific_gate_threshold="0.1",
    )
    request = VirtualMicrobiomeRequestV1.for_contract(contract)
    raw = run_virtual_microbiome(community, contract, request).to_dict()

    for field, value in (
        ("prediction", [0.5, 0.5]),
        ("secondary_predictions", {"SCFA:butyrate": 1.0}),
        ("scientifically_validated", True),
        ("production_promoted", True),
    ):
        forged = deepcopy(raw)
        forged[field] = value
        with pytest.raises(ValidationError):
            type(run_virtual_microbiome(community, contract, request)).model_validate(forged)


def test_freeze_rejects_single_member_and_invalid_threshold():
    registry = _registry()
    raw = _community_raw(registry)
    raw["members"] = [raw["members"][0]]
    raw["members"][0]["abundance"]["value"] = "1"
    community = register_community(CommunityPack.from_dict(raw), registry)

    with pytest.raises(VirtualMicrobiomeContractError, match="2 or 3"):
        freeze_virtual_microbiome_contract(
            community,
            scientific_gate_threshold="0.1",
        )
    with pytest.raises(VirtualMicrobiomeContractError, match="scientific_gate_threshold"):
        freeze_virtual_microbiome_contract(
            _registered(),
            scientific_gate_threshold="NaN",
        )
