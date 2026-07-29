"""P10 CommunityPack pre-interface: strict references and fail-closed planning."""

from __future__ import annotations

import inspect
import shutil
from copy import deepcopy

import pytest
from pydantic import ValidationError

from praxis_virtualcell.community_packs import (
    CommunityContractError,
    CommunityExecutionPlan,
    CommunityModelAdapter,
    CommunityPack,
    CommunityRunResult,
    ToyExchangeLedger,
    plan_community,
    register_community,
    run_community,
    single_member_equivalent,
    tiny_microbial_pack_roots,
    validate_toy_exchange,
)
from praxis_virtualcell.data_packs.registry import PackRegistry, RegisteredPack
from praxis_virtualcell.pack_product import builtin_pack_roots


def _pack_registry() -> PackRegistry:
    registry = PackRegistry()
    for root in tiny_microbial_pack_roots().values():
        registry.register(root)
    return registry


def _community_raw(registry: PackRegistry) -> dict:
    bacteria = registry.record("p8-bacteria-tiny", "1.0.0")
    yeast = registry.record("p10-yeast-tiny", "1.0.0")
    return {
        "schema_version": "vc.community-pack.v1",
        "community_id": "p10-microbial-toy",
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
                    "metabolite_ids": [
                        "PRAXISMET:toy-carbon",
                        "PRAXISMET:toy-byproduct",
                    ],
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
                    "metabolite_ids": [
                        "PRAXISMET:toy-carbon",
                        "PRAXISMET:toy-byproduct",
                    ],
                    "amount_unit": "mmol",
                },
            },
        ],
        "medium": {
            "medium_id": "toy-minimal",
            "compartment_id": "culture",
            "components": [
                {
                    "metabolite_id": "PRAXISMET:toy-carbon",
                    "concentration": {"value": "10", "unit": "mmol/L"},
                }
            ],
        },
        "compartments": [{"id": "culture", "role": "shared_medium"}],
        "time": {"start": "0", "end": "24", "unit": "h"},
        "space": {"representation": "well_mixed"},
        "shared_metabolite_namespace": {
            "name": "PRAXISMET",
            "version": "p10-toy-v1",
            "id_format": "curie",
            "amount_unit": "mmol",
            "metabolites": [
                {
                    "id": "PRAXISMET:toy-carbon",
                    "label": "synthetic toy carbon pool",
                },
                {
                    "id": "PRAXISMET:toy-byproduct",
                    "label": "synthetic toy byproduct pool",
                },
            ],
        },
        "interaction_evidence": [
            {
                "evidence_id": "toy-byproduct-transfer",
                "source_member_id": "ecoli",
                "target_member_id": "yeast",
                "metabolite_id": "PRAXISMET:toy-byproduct",
                "evidence_type": "contract_fixture",
                "reference": "synthetic P10 contract fixture; not experimental evidence",
            }
        ],
        "scientifically_validated": False,
    }


def _registered_community():
    registry = _pack_registry()
    manifest = CommunityPack.from_dict(_community_raw(registry))
    return registry, register_community(manifest, registry)


def _ledger_raw(community_fingerprint: str) -> dict:
    return {
        "schema_version": "vc.community-exchange-ledger.v1",
        "community_fingerprint": community_fingerprint,
        "entries": [
            {
                "participant_type": "medium",
                "participant_id": "toy-minimal",
                "compartment_id": "culture",
                "metabolite_id": "PRAXISMET:toy-carbon",
                "amount": {"value": "-2", "unit": "mmol"},
            },
            {
                "participant_type": "member",
                "participant_id": "ecoli",
                "compartment_id": "culture",
                "metabolite_id": "PRAXISMET:toy-carbon",
                "amount": {"value": "1", "unit": "mmol"},
            },
            {
                "participant_type": "member",
                "participant_id": "yeast",
                "compartment_id": "culture",
                "metabolite_id": "PRAXISMET:toy-carbon",
                "amount": {"value": "1", "unit": "mmol"},
            },
            {
                "participant_type": "member",
                "participant_id": "ecoli",
                "compartment_id": "culture",
                "metabolite_id": "PRAXISMET:toy-byproduct",
                "amount": {"value": "-1", "unit": "mmol"},
            },
            {
                "participant_type": "member",
                "participant_id": "yeast",
                "compartment_id": "culture",
                "metabolite_id": "PRAXISMET:toy-byproduct",
                "amount": {"value": "1", "unit": "mmol"},
            },
        ],
        "scientifically_validated": False,
    }


def test_two_tiny_microbial_packs_are_standard_auditable_packs():
    roots = tiny_microbial_pack_roots()
    assert set(roots) == {"ecoli", "yeast"}
    assert set(builtin_pack_roots()) == {"human", "mouse", "bacteria"}

    registry = _pack_registry()
    bacteria = registry.record("p8-bacteria-tiny", "1.0.0")
    yeast = registry.record("p10-yeast-tiny", "1.0.0")

    assert isinstance(bacteria, RegisteredPack)
    assert isinstance(yeast, RegisteredPack)
    assert bacteria.manifest.taxon.ontology_id == "NCBITaxon:562"
    assert yeast.manifest.taxon.ontology_id == "NCBITaxon:4932"
    assert yeast.manifest.assembly.accession == "GCF_000146045.2"
    assert all((root / "tiny.h5ad").stat().st_size < 100_000 for root in roots.values())
    assert all(len(registry.record(*key).fingerprint) == 64 for key in registry.keys())


def test_community_contract_is_immutable_canonical_and_not_scientific():
    registry = _pack_registry()
    raw = _community_raw(registry)
    original = deepcopy(raw)

    manifest = CommunityPack.from_dict(raw)

    assert raw == original
    assert manifest.to_dict() == raw
    assert manifest.scientifically_validated is False
    assert len(manifest.fingerprint()) == 64
    assert CommunityPack.from_dict(dict(reversed(raw.items()))).fingerprint() == manifest.fingerprint()
    with pytest.raises(CommunityContractError):
        CommunityPack.from_dict({**raw, "scientifically_validated": True})


@pytest.mark.parametrize("bad_value", [0.5, "5e-1", " 0.5", "0.5 ", "NaN"])
def test_abundance_rejects_non_explicit_decimal_strings(bad_value):
    registry = _pack_registry()
    raw = _community_raw(registry)
    raw["members"][0]["abundance"]["value"] = bad_value

    with pytest.raises(CommunityContractError, match="abundance"):
        CommunityPack.from_dict(raw)


def test_abundance_is_not_normalized_or_zero_filled():
    registry = _pack_registry()
    raw = _community_raw(registry)
    raw["members"][0]["abundance"]["value"] = "0.4"

    with pytest.raises(CommunityContractError, match="sum exactly"):
        CommunityPack.from_dict(raw)

    raw = _community_raw(registry)
    raw["members"][1].pop("abundance")
    with pytest.raises(CommunityContractError, match="abundance"):
        CommunityPack.from_dict(raw)


@pytest.mark.parametrize(
    "mutation,reason",
    [
        (lambda raw: raw["time"].update(end="0"), "time.end"),
        (
            lambda raw: raw["space"].update(representation="spatial_grid"),
            "space.representation",
        ),
        (
            lambda raw: raw["medium"]["components"][0]["concentration"].update(value=10.0),
            "concentration",
        ),
    ],
)
def test_time_space_and_medium_are_explicit_not_inferred(mutation, reason):
    registry = _pack_registry()
    raw = _community_raw(registry)
    mutation(raw)

    with pytest.raises(CommunityContractError, match=reason):
        CommunityPack.from_dict(raw)


@pytest.mark.parametrize(
    "mutation,reason",
    [
        (
            lambda raw: raw["members"][1].update(member_id=raw["members"][0]["member_id"]),
            "duplicate member",
        ),
        (
            lambda raw: raw["members"].append(
                {
                    **deepcopy(raw["members"][0]),
                    "member_id": "ecoli-copy",
                }
            ),
            "duplicate Pack",
        ),
        (
            lambda raw: raw["shared_metabolite_namespace"]["metabolites"].append(
                {
                    "id": "PRAXISMET:toy-carbon",
                    "label": "conflicting duplicate",
                }
            ),
            "duplicate metabolite",
        ),
    ],
)
def test_declared_identity_duplicates_are_rejected_not_deduplicated(mutation, reason):
    registry = _pack_registry()
    raw = _community_raw(registry)
    mutation(raw)

    with pytest.raises(CommunityContractError, match=reason):
        CommunityPack.from_dict(raw)


@pytest.mark.parametrize(
    "mutation,reason",
    [
        (
            lambda raw: raw["members"][0]["exchange"]["metabolite_ids"].append("PRAXISMET:not-declared"),
            "metabolite",
        ),
        (
            lambda raw: raw["medium"]["components"][0].update(metabolite_id="PRAXISMET:not-declared"),
            "metabolite",
        ),
        (
            lambda raw: raw["interaction_evidence"][0].update(target_member_id="not-declared"),
            "member",
        ),
        (
            lambda raw: raw["members"][0].update(compartment_id="not-declared"),
            "compartment",
        ),
        (
            lambda raw: raw["members"][0]["exchange"].update(amount_unit="umol"),
            "unit",
        ),
    ],
)
def test_id_and_unit_conflicts_fail_closed(mutation, reason):
    registry = _pack_registry()
    raw = _community_raw(registry)
    mutation(raw)

    with pytest.raises(CommunityContractError, match=reason):
        CommunityPack.from_dict(raw)


def test_shared_metabolite_ids_must_match_the_declared_namespace():
    registry = _pack_registry()
    raw = _community_raw(registry)
    raw["shared_metabolite_namespace"]["metabolites"][0]["id"] = "OTHER:toy-carbon"
    raw["medium"]["components"][0]["metabolite_id"] = "OTHER:toy-carbon"
    for member in raw["members"]:
        member["exchange"]["metabolite_ids"][0] = "OTHER:toy-carbon"

    with pytest.raises(CommunityContractError, match="namespace"):
        CommunityPack.from_dict(raw)


def test_interaction_evidence_requires_both_members_to_declare_exchange():
    registry = _pack_registry()
    raw = _community_raw(registry)
    raw["members"][1]["exchange"]["metabolite_ids"].remove("PRAXISMET:toy-byproduct")

    with pytest.raises(CommunityContractError, match="interaction.*exchange"):
        CommunityPack.from_dict(raw)


def test_member_pack_references_require_exact_registered_fingerprints():
    registry = _pack_registry()
    manifest = CommunityPack.from_dict(_community_raw(registry))
    registered = register_community(manifest, registry)

    assert registered.manifest is manifest
    assert registered.fingerprint == manifest.fingerprint()
    assert [record.fingerprint for record in registered.members] == [
        member.pack_fingerprint for member in manifest.members
    ]

    raw = _community_raw(registry)
    raw["members"][0]["pack_fingerprint"] = "0" * 64
    with pytest.raises(CommunityContractError, match="fingerprint"):
        register_community(CommunityPack.from_dict(raw), registry)

    raw = _community_raw(registry)
    raw["members"][0]["pack_id"] = "not-registered"
    with pytest.raises(CommunityContractError, match="unregistered"):
        register_community(CommunityPack.from_dict(raw), registry)


def test_community_registration_revalidates_current_member_pack_bytes(tmp_path):
    registry = PackRegistry()
    copied_roots = {}
    for species, source in tiny_microbial_pack_roots().items():
        copied_roots[species] = tmp_path / species
        shutil.copytree(source, copied_roots[species])
        registry.register(copied_roots[species])
    manifest = CommunityPack.from_dict(_community_raw(registry))

    with (copied_roots["ecoli"] / "tiny.h5ad").open("ab") as stream:
        stream.write(b"tampered")

    with pytest.raises(CommunityContractError, match="no longer validates"):
        register_community(manifest, registry)


def test_single_member_equivalence_returns_the_original_registered_pack():
    registry = _pack_registry()
    bacteria = registry.record("p8-bacteria-tiny", "1.0.0")
    raw = _community_raw(registry)
    raw["members"] = [deepcopy(raw["members"][0])]
    raw["members"][0]["abundance"]["value"] = "1"
    raw["interaction_evidence"] = []

    community = register_community(CommunityPack.from_dict(raw), registry)
    equivalent = single_member_equivalent(community)

    assert equivalent == bacteria
    assert equivalent.root == bacteria.root
    assert equivalent.fingerprint == raw["members"][0]["pack_fingerprint"]


def test_multi_member_community_has_no_single_member_equivalence():
    _, community = _registered_community()

    with pytest.raises(CommunityContractError, match="exactly one"):
        single_member_equivalent(community)


def test_toy_exchange_uses_exact_mass_conservation():
    _, community = _registered_community()
    ledger = ToyExchangeLedger.from_dict(_ledger_raw(community.fingerprint))

    validation = validate_toy_exchange(community, ledger)

    assert validation.to_dict() == {
        "schema_version": "vc.community-exchange-validation.v1",
        "community_fingerprint": community.fingerprint,
        "mass_conserved": True,
        "balances": [
            {
                "metabolite_id": "PRAXISMET:toy-byproduct",
                "value": "0",
                "unit": "mmol",
            },
            {
                "metabolite_id": "PRAXISMET:toy-carbon",
                "value": "0",
                "unit": "mmol",
            },
        ],
        "scientifically_validated": False,
    }


def test_toy_exchange_rejects_any_residual_without_tolerance():
    _, community = _registered_community()
    raw = _ledger_raw(community.fingerprint)
    raw["entries"][2]["amount"]["value"] = "1.000000000000000000000000000001"

    with pytest.raises(CommunityContractError, match="mass is not conserved"):
        validate_toy_exchange(community, ToyExchangeLedger.from_dict(raw))


def test_toy_exchange_respects_each_members_declared_exchange_ids():
    registry = _pack_registry()
    raw = _community_raw(registry)
    raw["interaction_evidence"] = []
    raw["members"][1]["exchange"]["metabolite_ids"].remove("PRAXISMET:toy-byproduct")
    community = register_community(CommunityPack.from_dict(raw), registry)
    ledger = ToyExchangeLedger.from_dict(_ledger_raw(community.fingerprint))

    with pytest.raises(CommunityContractError, match="member exchange contract"):
        validate_toy_exchange(community, ledger)


@pytest.mark.parametrize(
    "mutation,reason",
    [
        (
            lambda raw: raw["entries"][0]["amount"].update(unit="umol"),
            "unit",
        ),
        (
            lambda raw: raw["entries"][0].update(metabolite_id="PRAXISMET:not-declared"),
            "metabolite",
        ),
        (
            lambda raw: raw["entries"][1].update(participant_id="not-declared"),
            "participant",
        ),
        (
            lambda raw: raw.update(community_fingerprint="0" * 64),
            "fingerprint",
        ),
    ],
)
def test_toy_exchange_rejects_identity_and_unit_conflicts(mutation, reason):
    _, community = _registered_community()
    raw = _ledger_raw(community.fingerprint)
    mutation(raw)

    with pytest.raises(CommunityContractError, match=reason):
        validate_toy_exchange(community, ToyExchangeLedger.from_dict(raw))


def test_no_community_model_only_plans_or_abstains():
    _, community = _registered_community()

    plan = plan_community(community)
    result = run_community(community)

    assert plan.schema_version == "vc.community-execution-plan.v1"
    assert plan.executable is False
    assert plan.steps == ()
    assert plan.reasons == ("community_model_unavailable",)
    assert plan.scientifically_validated is False
    assert result.schema_version == "vc.community-run-result.v1"
    assert result.abstain is True
    assert result.prediction is None
    assert result.models_used == ()
    assert result.abstain_reasons == ("community_model_unavailable",)
    assert result.execution_plan == plan
    assert result.scientifically_validated is False
    assert "Mock" not in str(result.to_dict())


@pytest.mark.parametrize(
    "contract,field,value",
    [
        (CommunityExecutionPlan, "steps", [{"model_name": "forbidden"}]),
        (CommunityExecutionPlan, "reasons", []),
        (CommunityRunResult, "models_used", ["MockCommunity"]),
        (CommunityRunResult, "abstain_reasons", []),
    ],
)
def test_no_model_contracts_cannot_be_forged_with_execution_content(
    contract,
    field,
    value,
):
    _, community = _registered_community()
    instance = plan_community(community) if contract is CommunityExecutionPlan else run_community(community)
    raw = instance.to_dict()
    raw[field] = value

    with pytest.raises(ValidationError):
        contract.model_validate(raw)


def test_community_model_adapter_is_an_unimplemented_abstract_boundary():
    assert inspect.isabstract(CommunityModelAdapter)
    assert CommunityModelAdapter.__subclasses__() == []
    with pytest.raises(TypeError):
        CommunityModelAdapter()
