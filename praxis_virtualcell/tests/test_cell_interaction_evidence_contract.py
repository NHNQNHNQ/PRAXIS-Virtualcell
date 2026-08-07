"""P23A directed cell-interaction evidence contract-only conformance tests.

Every identity and score in this module is synthetic.  No registry import,
asset read, model execution, scientific validation, or policy action occurs.
"""

from __future__ import annotations

import hashlib
import inspect
import json
from collections import UserDict
from copy import deepcopy
from functools import cache

import pytest
from pydantic import ValidationError

from praxis_virtualcell.core.request_v2 import SpeciesRef, VirtualCellRequestV2
from praxis_virtualcell.model_zoo import cell_interaction_evidence_contract
from praxis_virtualcell.model_zoo.adapter_sdk import (
    DEFAULT_ADAPTER_REGISTRY,
    AdapterContractError,
    run_adapter_conformance,
)
from praxis_virtualcell.model_zoo.cell_interaction_evidence_contract import (
    CellInteractionEvidenceAdapter,
    InteractionEndpointV1,
    InteractionEvidenceInputV1,
    InteractionScorerFixtureV1,
    P18EndpointIdentityV1,
    SameExperimentInteractionEvidenceV1,
)
from praxis_virtualcell.model_zoo.curated_registry import (
    VirtualCellContextV1,
    _release_dependencies,
)
from praxis_virtualcell.tests.test_curated_registry import _positive_release


def _fp(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _canonical_fp(value) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@cache
def _release(virtual_cell_id: str):
    return _positive_release(virtual_cell_id=virtual_cell_id)


def _endpoint(role: str, *, virtual_cell_id: str, observation_id: str):
    release = _release(virtual_cell_id)
    p18_identity = P18EndpointIdentityV1(
        schema_version="vc.p23-p18-endpoint-identity.v1",
        model_input_schema_version="vc.multiomics-model-input.v1",
        model_input_fingerprint=_fp(f"p18-{role}"),
        pack_fingerprint=release.pack_registration.pack_fingerprint,
        view_identity_fingerprint=_fp(f"p18-{role}-view"),
        observation_semantics_fingerprint=_fp(f"p18-{role}-semantics"),
        join_fingerprint=_fp(f"p18-{role}-join"),
        modality_key="rna",
        modality_identity_fingerprint=_fp(f"p18-{role}-rna"),
        observation_id=observation_id,
        taxonomy_id="NCBITaxon:32644",
        scientific_name=release.context.organism,
        identity_role="declared_p18_contract_fixture_reference",
        p18_contract_verified=False,
        observation_membership_verified=False,
    )
    return InteractionEndpointV1(
        schema_version="vc.interaction-endpoint.v1",
        role=role,
        release=release,
        release_fingerprint=release.fingerprint(),
        context_fingerprint=release.context.fingerprint(),
        pack_registration_fingerprint=release.pack_registration.fingerprint(),
        pack_fingerprint=release.pack_registration.pack_fingerprint,
        p18_identity=p18_identity,
        p18_identity_fingerprint=p18_identity.fingerprint(),
        registry_state_verified=False,
    )


def _evidence():
    return SameExperimentInteractionEvidenceV1(
        schema_version="vc.same-experiment-interaction-evidence.v1",
        dataset_fingerprint=_fp("paired-dataset"),
        platform_fingerprint=_fp("paired-platform"),
        evidence_asset_fingerprint=_fp("paired-asset"),
        evidence_record_fingerprint=_fp("paired-record"),
        experiment_id="experiment-001",
        donor_id="donor-001",
        sample_id="sample-001",
        well_id="well-A01",
        condition_id="condition-stimulated",
        dose_value=1.0,
        dose_unit="micromolar",
        time_value=6.0,
        time_unit="hour",
        sender_role="sender",
        sender_observation_id="sender-observation",
        receiver_role="receiver",
        receiver_observation_id="receiver-observation",
        ligand_id="UniProtKB:P01375",
        ligand_namespace="UniProtKB",
        ligand_namespace_version="2026_03",
        ligand_namespace_fingerprint=_fp("ligand-namespace"),
        receptor_id="UniProtKB:P19438",
        receptor_namespace="UniProtKB",
        receptor_namespace_version="2026_03",
        receptor_namespace_fingerprint=_fp("receptor-namespace"),
        evidence_namespace="synthetic-paired-assay",
        evidence_namespace_version="1.0.0",
        evidence_namespace_fingerprint=_fp("evidence-namespace"),
        mapping_asset_fingerprint=_fp("ligand-receptor-mapping"),
        evidence_asset_verified=False,
        paired_linkage_verified=False,
    )


def _scorer(adapter: CellInteractionEvidenceAdapter):
    return InteractionScorerFixtureV1(
        schema_version="vc.interaction-scorer-fixture.v1",
        adapter_fingerprint=adapter.fingerprint(),
        model_release_fingerprint=_fp("interaction-model-release"),
        model_artifact_fingerprint=_fp("interaction-model-artifact"),
        benchmark_bundle_fingerprint=_fp("interaction-benchmark-bundle"),
        benchmark_protocol_fingerprint=_fp("interaction-benchmark-protocol"),
        benchmark_run_fingerprint=_fp("interaction-benchmark-run"),
        benchmark_result_fingerprint=_fp("interaction-benchmark-result"),
        p21b_execution_identity_fingerprint=_fp("interaction-p21b-execution"),
        baselines=("no_interaction", "receiver_only", "lr_coexpression"),
        ood_axes=(
            "sender",
            "receiver",
            "ligand",
            "donor",
            "dataset",
            "platform",
            "dose_time",
        ),
        record_role="contract_fixture",
        p20_p21_bindings_verified=False,
        trusted_p21b_execution=False,
        model_artifact_verified=False,
        real_model_execution_authorized=False,
        real_model_execution_performed=False,
    )


@cache
def _cached_interaction():
    adapter = CellInteractionEvidenceAdapter()
    return InteractionEvidenceInputV1(
        schema_version="vc.cell-interaction-evidence-input.v1",
        task="cell_interaction_evidence",
        output="interaction_evidence_score",
        direction="sender_to_receiver",
        score_scale="unit_interval",
        score_semantics="association_evidence_only",
        sender=_endpoint(
            "sender",
            virtual_cell_id="synthetic-sender-cell",
            observation_id="sender-observation",
        ),
        receiver=_endpoint(
            "receiver",
            virtual_cell_id="synthetic-receiver-cell",
            observation_id="receiver-observation",
        ),
        paired_evidence=_evidence(),
        scorer=_scorer(adapter),
        p18_role_semantics="p23_roles_over_p18_identity_state_context",
        real_data_authorized=False,
        scientifically_validated=False,
        promotion_eligible=False,
        production_promoted=False,
    )


def _interaction(adapter: CellInteractionEvidenceAdapter | None = None):
    interaction = _cached_interaction()
    if adapter is not None:
        assert interaction.scorer.adapter_fingerprint == adapter.fingerprint()
    return interaction


def _request(interaction: InteractionEvidenceInputV1):
    sender_release = interaction.sender.release
    return VirtualCellRequestV2.from_dict(
        {
            "schema_version": "vc.request.v2",
            "request_id": "synthetic-p23a-conformance",
            "species": {
                "schema_version": "vc.species-ref.v1",
                "taxonomy_id": "NCBITaxon:32644",
                "scientific_name": sender_release.context.organism,
                "common_name": None,
            },
            "cell_context": {
                "schema_version": "vc.cell-context.v1",
                "cell_type_name": "directed_sender_receiver_pair",
                "cell_type_id": None,
                "tissue_name": None,
                "tissue_id": None,
                "attributes": {
                    "interaction_input_fingerprint": interaction.fingerprint(),
                    "receiver_release_fingerprint": interaction.receiver.release_fingerprint,
                    "sender_release_fingerprint": interaction.sender.release_fingerprint,
                },
            },
            "input_modality": {
                "schema_version": "vc.modality.v1",
                "name": "paired_cell_interaction_evidence",
                "ontology_id": None,
                "unit": None,
                "feature_namespace": None,
            },
            "output_modality": {
                "schema_version": "vc.modality.v1",
                "name": "interaction_evidence_score",
                "ontology_id": None,
                "unit": "dimensionless",
                "feature_namespace": None,
            },
            "perturbation": {
                "schema_version": "vc.perturbation.v1",
                "kind": "medium",
                "targets": [],
                "dose_value": None,
                "dose_unit": None,
                "timepoint": None,
            },
            "task": {
                "schema_version": "vc.task.v1",
                "task_type": "cell_interaction_evidence",
                "requested_outputs": ["interaction_evidence_score"],
            },
            "baseline_context": {"baselines": ["no_interaction", "receiver_only", "lr_coexpression"]},
            "metadata": {},
            "constraints": {
                "direction": "sender_to_receiver",
                "interaction_input_fingerprint": interaction.fingerprint(),
                "score_scale": "unit_interval",
            },
        }
    )


@cache
def _prepared():
    adapter = CellInteractionEvidenceAdapter()
    interaction = _interaction(adapter)
    request = _request(interaction)
    prepared = adapter.prepare_input(request, interaction_input=interaction)
    return adapter, interaction, request, prepared


def _raw(
    *,
    score=0.625,
    status="synthetic_conformance",
    abstain=False,
    reasons=(),
    ood_dimensions=(),
    ood_reason=None,
):
    return {
        "prediction": (
            None
            if abstain
            else {
                "interaction_evidence_score": score,
                "score_scale": "unit_interval",
                "score_semantics": "association_evidence_only",
            }
        ),
        "prediction_status": status,
        "interaction_input_fingerprint": _interaction().fingerprint(),
        "uncertainty": {
            "available": False,
            "method": "not_available",
            "calibrated": False,
            "value": None,
            "sigma": None,
            "reason": "p23a_contract_fixture_no_calibrated_uncertainty",
        },
        "ood": {
            "detected": bool(ood_dimensions),
            "dimensions": list(ood_dimensions),
            "reason": ood_reason,
        },
        "abstain": abstain,
        "abstain_reasons": list(reasons),
        "record_role": "synthetic_conformance_not_evidence",
    }


def _bound_raw(interaction: InteractionEvidenceInputV1, **kwargs):
    raw = _raw(**kwargs)
    raw["interaction_input_fingerprint"] = interaction.fingerprint()
    return raw


def test_input_contract_is_frozen_canonical_and_direction_sensitive():
    adapter = CellInteractionEvidenceAdapter()
    interaction = _interaction(adapter)
    clone = InteractionEvidenceInputV1.model_validate(interaction.to_dict())
    assert clone.to_dict() == interaction.to_dict()
    assert clone.fingerprint() == interaction.fingerprint()

    with pytest.raises(ValidationError, match="frozen"):
        interaction.direction = "receiver_to_sender"
    with pytest.raises(ValidationError, match="extra"):
        InteractionEvidenceInputV1.model_validate({**interaction.to_dict(), "receiver_response": 1.0})

    swapped = InteractionEvidenceInputV1.model_validate(
        {
            **interaction.to_dict(),
            "sender": {
                **interaction.receiver.to_dict(),
                "role": "sender",
            },
            "receiver": {
                **interaction.sender.to_dict(),
                "role": "receiver",
            },
            "paired_evidence": {
                **interaction.paired_evidence.to_dict(),
                "sender_observation_id": interaction.receiver.p18_identity.observation_id,
                "receiver_observation_id": interaction.sender.p18_identity.observation_id,
            },
        }
    )
    assert swapped.fingerprint() != interaction.fingerprint()


@pytest.mark.parametrize(
    "field",
    [
        "release_fingerprint",
        "context_fingerprint",
        "pack_registration_fingerprint",
        "pack_fingerprint",
    ],
)
def test_endpoint_rejects_stale_release_closure_fingerprints(field):
    endpoint = _interaction().sender
    with pytest.raises(ValidationError, match="stale|does not match"):
        InteractionEndpointV1.model_validate({**endpoint.to_dict(), field: _fp(field)})


def test_endpoint_revalidates_nested_release_and_role_order():
    interaction = _interaction()
    forged_release = interaction.sender.release.model_copy(update={"virtual_cell_id": "forged-cell"})
    with pytest.raises(ValidationError, match="release"):
        InteractionEndpointV1.model_validate({**interaction.sender.to_dict(), "release": forged_release})
    with pytest.raises(ValidationError, match="sender role"):
        InteractionEvidenceInputV1.model_validate(
            {
                **interaction.to_dict(),
                "sender": {**interaction.sender.to_dict(), "role": "receiver"},
            }
        )


def test_endpoint_rejects_undeclared_fields_in_nested_release_models_and_mappings():
    endpoint = _interaction().sender
    release = endpoint.release
    forged_release = release.model_copy(update={"causal_claim": "forged"})
    forged_context = release.context.model_copy(update={"receiver_response": 1.0})
    for candidate in (
        forged_release,
        {**release.to_dict(), "context": forged_context},
        UserDict({**release.to_dict(), "context": forged_context}),
    ):
        with pytest.raises(ValidationError, match="release"):
            InteractionEndpointV1.model_validate({**endpoint.to_dict(), "release": candidate})


def test_endpoint_cross_binds_typed_p18_identity_to_release_pack():
    endpoint = _interaction().sender
    assert endpoint.p18_identity.model_input_schema_version == "vc.multiomics-model-input.v1"
    assert endpoint.p18_identity.pack_fingerprint == endpoint.pack_fingerprint
    assert endpoint.p18_identity.p18_contract_verified is False
    assert endpoint.p18_identity.observation_membership_verified is False
    other_pack_identity = P18EndpointIdentityV1.model_validate(
        {
            **endpoint.p18_identity.to_dict(),
            "pack_fingerprint": _fp("other-pack"),
        }
    )
    with pytest.raises(ValidationError, match="P18 Pack"):
        InteractionEndpointV1.model_validate(
            {
                **endpoint.to_dict(),
                "p18_identity": other_pack_identity.to_dict(),
                "p18_identity_fingerprint": other_pack_identity.fingerprint(),
            }
        )
    with pytest.raises(ValidationError, match="p18_identity_fingerprint"):
        InteractionEndpointV1.model_validate({**endpoint.to_dict(), "p18_identity_fingerprint": _fp("stale-p18")})
    with pytest.raises(ValidationError):
        P18EndpointIdentityV1.model_validate({**endpoint.p18_identity.to_dict(), "p18_contract_verified": True})


def test_directed_pair_rejects_sender_receiver_p18_taxonomy_drift():
    interaction = _interaction()
    receiver = interaction.receiver
    other_taxonomy = P18EndpointIdentityV1.model_validate(
        {**receiver.p18_identity.to_dict(), "taxonomy_id": "NCBITaxon:9606"}
    )
    changed_receiver = InteractionEndpointV1.model_validate(
        {
            **receiver.to_dict(),
            "p18_identity": other_taxonomy.to_dict(),
            "p18_identity_fingerprint": other_taxonomy.fingerprint(),
        }
    )
    with pytest.raises(ValidationError, match="P18 taxonomy"):
        InteractionEvidenceInputV1.model_validate({**interaction.to_dict(), "receiver": changed_receiver.to_dict()})


def test_contract_fixture_false_gates_cannot_be_self_promoted():
    interaction = _interaction()
    for value, contract, fields in (
        (interaction.sender, InteractionEndpointV1, ("registry_state_verified",)),
        (
            interaction.sender.p18_identity,
            P18EndpointIdentityV1,
            ("p18_contract_verified", "observation_membership_verified"),
        ),
        (
            interaction.paired_evidence,
            SameExperimentInteractionEvidenceV1,
            ("evidence_asset_verified", "paired_linkage_verified"),
        ),
        (
            interaction,
            InteractionEvidenceInputV1,
            (
                "real_data_authorized",
                "scientifically_validated",
                "promotion_eligible",
                "production_promoted",
            ),
        ),
    ):
        for field in fields:
            with pytest.raises(ValidationError, match=field):
                contract.model_validate({**value.to_dict(), field: True})


@pytest.mark.parametrize(
    "field",
    [
        "dataset_fingerprint",
        "platform_fingerprint",
        "evidence_asset_fingerprint",
        "evidence_record_fingerprint",
        "experiment_id",
        "donor_id",
        "sample_id",
        "well_id",
        "condition_id",
        "dose_value",
        "dose_unit",
        "time_value",
        "time_unit",
        "sender_observation_id",
        "receiver_observation_id",
        "ligand_id",
        "ligand_namespace",
        "ligand_namespace_version",
        "ligand_namespace_fingerprint",
        "receptor_id",
        "receptor_namespace",
        "receptor_namespace_version",
        "receptor_namespace_fingerprint",
        "evidence_namespace",
        "evidence_namespace_version",
        "evidence_namespace_fingerprint",
        "mapping_asset_fingerprint",
    ],
)
def test_same_experiment_binding_requires_every_declared_identity(field):
    raw = _evidence().to_dict()
    raw.pop(field)
    with pytest.raises(ValidationError, match=field):
        SameExperimentInteractionEvidenceV1.model_validate(raw)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("dataset_fingerprint", "A" * 64),
        ("ligand_id", "TNF"),
        ("receptor_id", " TNFRSF1A"),
        ("dose_value", -0.1),
        ("dose_value", float("nan")),
        ("time_value", float("inf")),
        ("time_value", True),
    ],
)
def test_same_experiment_binding_rejects_bad_hash_id_and_quantity(field, value):
    with pytest.raises(ValidationError):
        SameExperimentInteractionEvidenceV1.model_validate({**_evidence().to_dict(), field: value})


def test_same_experiment_binding_cannot_grow_a_second_dataset_or_drift_observations():
    evidence = _evidence()
    with pytest.raises(ValidationError, match="extra"):
        SameExperimentInteractionEvidenceV1.model_validate(
            {**evidence.to_dict(), "receiver_dataset_fingerprint": _fp("other-dataset")}
        )
    interaction = _interaction()
    with pytest.raises(ValidationError, match="observation"):
        InteractionEvidenceInputV1.model_validate(
            {
                **interaction.to_dict(),
                "paired_evidence": {
                    **interaction.paired_evidence.to_dict(),
                    "receiver_observation_id": "different-receiver",
                },
            }
        )


def test_endpoint_rejects_declared_pydantic_subclass_fields_before_p22_normalization():
    endpoint = _interaction().sender
    release = endpoint.release

    class ExtendedContext(VirtualCellContextV1):
        causal_claim: str

    context = ExtendedContext(
        **release.context.to_dict(),
        causal_claim="sender causes receiver activation",
    )
    dependencies = _release_dependencies(
        context=context,
        pack_registration=release.pack_registration,
        source_registry=release.source_registry,
        model_release_fingerprint=release.model_release_fingerprint,
        benchmark_bundle=release.benchmark_bundle,
        p21b_execution_identity_fingerprint=release.p21b_execution_identity_fingerprint,
        wrapper_approvals=release.wrapper_approvals,
    )
    with pytest.raises(ValueError, match="invalid Virtual Cell release"):
        cell_interaction_evidence_contract._release(
            {
                **release.to_dict(),
                "context": context,
                "dependency_fingerprints": dependencies,
            }
        )


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("ligand_namespace", "HGNC", "ligand CURIE prefix"),
        ("receptor_namespace", "HGNC", "receptor CURIE prefix"),
    ],
)
def test_ligand_and_receptor_curie_prefixes_match_declared_namespaces(field, value, match):
    with pytest.raises(ValidationError, match=match):
        SameExperimentInteractionEvidenceV1.model_validate({**_evidence().to_dict(), field: value})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("baselines", ("receiver_only", "no_interaction", "lr_coexpression")),
        ("baselines", ("no_interaction", "receiver_only", "legacy_proxy")),
        (
            "ood_axes",
            ("receiver", "sender", "ligand", "donor", "dataset", "platform", "dose_time"),
        ),
        ("p20_p21_bindings_verified", True),
        ("trusted_p21b_execution", True),
        ("model_artifact_verified", True),
        ("real_model_execution_authorized", True),
        ("real_model_execution_performed", True),
        ("record_role", "authorized_candidate"),
    ],
)
def test_scorer_fixture_freezes_baselines_ood_and_untrusted_execution(field, value):
    adapter = CellInteractionEvidenceAdapter()
    scorer = _scorer(adapter)
    with pytest.raises(ValidationError):
        InteractionScorerFixtureV1.model_validate({**scorer.to_dict(), field: value})


def test_prepare_input_binds_request_pair_and_adapter_without_pack_data():
    adapter, interaction, request, prepared = _prepared()
    assert prepared.adapter_fingerprint == adapter.fingerprint()
    assert prepared.request_fingerprint == _canonical_fp(request.to_dict())
    assert prepared.pack_fingerprint is None
    assert prepared.compatibility_fingerprint == interaction.fingerprint()
    assert prepared.values is None
    assert prepared.shape is None
    assert prepared.model_input["direction"] == "sender_to_receiver"
    assert prepared.model_input["real_data_authorized"] is False
    assert prepared.model_input["scientifically_validated"] is False
    assert prepared.model_input["scorer"]["p20_p21_bindings_verified"] is False


@pytest.mark.parametrize(
    ("path", "value", "match"),
    [
        (("task", "task_type"), "receiver_response_prediction", "task"),
        (("task", "requested_outputs"), ["receiver_response_delta"], "output"),
        (("species", "taxonomy_id"), "NCBITaxon:9606", "organism"),
        (("species", "scientific_name"), "Other organism", "organism"),
        (("species", "common_name"), "synthetic", "organism"),
        (("cell_context", "cell_type_name"), "receiver_only", "cell context"),
        (("input_modality", "name"), "legacy_lr_proxy", "input modality"),
        (("output_modality", "name"), "receiver_response_delta", "output modality"),
        (("baseline_context", "baselines"), ["lr_coexpression"], "baseline"),
        (("constraints", "direction"), "receiver_to_sender", "constraints"),
        (("metadata",), {"causal_claim": "sender causes receiver"}, "metadata"),
    ],
)
def test_prepare_input_rejects_request_scope_drift(path, value, match):
    adapter = CellInteractionEvidenceAdapter()
    interaction = _interaction(adapter)
    raw = _request(interaction).to_dict()
    cursor = raw
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = value
    request = VirtualCellRequestV2.from_dict(raw)
    with pytest.raises(AdapterContractError, match=match):
        adapter.prepare_input(request, interaction_input=interaction)


def test_prepare_input_rejects_undeclared_nested_request_fields():
    adapter = CellInteractionEvidenceAdapter()
    interaction = _interaction(adapter)
    request = _request(interaction)
    forged_species = request.species.model_copy(update={"causal_claim": "forged"})

    class ExtendedSpecies(SpeciesRef):
        causal_claim: str

    extended_species = ExtendedSpecies(
        **request.species.to_dict(),
        causal_claim="sender causes receiver activation",
    )
    for species in (forged_species, extended_species):
        forged_request = request.model_copy(update={"species": species})
        with pytest.raises(AdapterContractError, match="invalid request"):
            adapter.prepare_input(forged_request, interaction_input=interaction)

    cyclic_metadata = {}
    cyclic_metadata["self"] = cyclic_metadata
    cyclic_request = request.model_copy(update={"metadata": cyclic_metadata})
    with pytest.raises(AdapterContractError, match="invalid request"):
        adapter.prepare_input(cyclic_request, interaction_input=interaction)


@pytest.mark.parametrize("score", [0.0, 0.25, 1.0])
def test_synthetic_score_projects_only_interaction_evidence(score):
    adapter, interaction, _, prepared = _prepared()
    raw = _bound_raw(interaction, score=score)
    envelope = adapter.adapt_output(prepared, raw)
    assert envelope.values == (score,)
    assert envelope.shape == (1,)
    assert envelope.unit == "dimensionless"
    assert envelope.uncertainty.available is False
    assert envelope.ood.detected is False
    assert envelope.projection_metadata == {
        "baseline_comparison_performed": False,
        "causal_claim_included": False,
        "evidence_asset_verified": False,
        "interaction_input_fingerprint": interaction.fingerprint(),
        "p20_p21_bindings_verified": False,
        "paired_ci_performed": False,
        "paired_linkage_verified": False,
        "real_data_authorized": False,
        "real_model_execution_performed": False,
        "receiver_registry_state_verified": False,
        "receiver_response_included": False,
        "record_role": "synthetic_conformance_not_evidence",
        "score_scale": "unit_interval",
        "score_semantics": "association_evidence_only",
        "score_source": "supplied_contract_fixture_not_model_output",
        "sender_registry_state_verified": False,
    }
    projection = adapter.project_prepared_output(prepared, envelope)
    assert projection == {"interaction_evidence_score": [score]}
    assert set(projection) == {"interaction_evidence_score"}

    second = adapter.adapt_output(prepared, deepcopy(raw))
    assert second.to_dict() == envelope.to_dict()
    assert second.fingerprint() == envelope.fingerprint()
    report = run_adapter_conformance(adapter, prepared, raw)
    assert report.adapter_fingerprint == adapter.fingerprint()
    assert report.deterministic is True


def test_generic_success_status_is_not_a_real_gate_bypass():
    adapter, interaction, _, prepared = _prepared()
    with pytest.raises(AdapterContractError, match="status"):
        adapter.adapt_output(
            prepared,
            _bound_raw(interaction, status="success"),
        )


@pytest.mark.parametrize(
    "score",
    [True, "0.5", float("nan"), float("inf"), -(2**53), 2**53, -0.001, 1.001],
)
def test_score_rejects_nonfinite_unsafe_or_out_of_scale_values(score):
    adapter, interaction, _, prepared = _prepared()
    with pytest.raises(AdapterContractError, match="score"):
        adapter.adapt_output(prepared, _bound_raw(interaction, score=score))


@pytest.mark.parametrize(
    "field",
    [
        "receiver_response",
        "receiver_response_delta",
        "effect_size",
        "treatment_effect",
        "causal_claim",
        "activated",
        "chain_complete",
        "ctrl",
        "stim",
        "fold_change",
    ],
)
def test_output_rejects_response_causal_and_legacy_fields_at_every_layer(field):
    adapter, interaction, _, prepared = _prepared()
    top = _bound_raw(interaction)
    top[field] = 1.0
    with pytest.raises(AdapterContractError, match="unknown wrapper output"):
        adapter.adapt_output(prepared, top)

    nested = _bound_raw(interaction)
    nested["prediction"][field] = 1.0
    with pytest.raises(AdapterContractError, match="unknown prediction"):
        adapter.adapt_output(prepared, nested)

    with pytest.raises(AdapterContractError, match="only interaction_evidence_score"):
        adapter.validate_projection({"interaction_evidence_score": [0.5], field: [1.0]})


@pytest.mark.parametrize(
    ("path", "value", "match"),
    [
        (("abstain_reasons",), ["sender causes receiver activation"], "reason"),
        (("ood", "reason"), "sender causes receiver activation", "OOD"),
        (("uncertainty", "reason"), "sender causes receiver activation", "uncertainty"),
        (("record_role",), "scientific_evidence", "record role"),
    ],
)
def test_output_free_text_slots_cannot_carry_causal_claims(path, value, match):
    adapter, interaction, _, prepared = _prepared()
    raw = _bound_raw(
        interaction,
        status="unsupported_scope",
        abstain=True,
        reasons=("unsupported_interaction_scope",),
        ood_dimensions=("sender",),
        ood_reason="unsupported_interaction_scope",
    )
    cursor = raw
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = value
    with pytest.raises(AdapterContractError, match=match):
        adapter.adapt_output(prepared, raw)


@pytest.mark.parametrize(
    ("status", "reason", "ood_dimensions", "ood_reason"),
    [
        ("missing_paired_evidence", "missing_paired_evidence", (), None),
        ("baseline_gate_failed", "baseline_gate_not_met", (), None),
        (
            "unsupported_scope",
            "unsupported_interaction_scope",
            ("sender", "dataset"),
            "unsupported_interaction_scope",
        ),
        (
            "execution_not_authorized",
            "p23a_real_execution_not_authorized",
            (),
            None,
        ),
        (
            "registry_state_unverified",
            "curated_release_state_unverified",
            (),
            None,
        ),
    ],
)
def test_gate_failures_are_value_free_abstentions(status, reason, ood_dimensions, ood_reason):
    adapter, interaction, _, prepared = _prepared()
    envelope = adapter.adapt_output(
        prepared,
        _bound_raw(
            interaction,
            status=status,
            abstain=True,
            reasons=(reason,),
            ood_dimensions=ood_dimensions,
            ood_reason=ood_reason,
        ),
    )
    assert envelope.abstain is True
    assert envelope.values is None
    assert envelope.shape is None
    assert envelope.projection_metadata == {}
    with pytest.raises(AdapterContractError, match="cannot project"):
        adapter.project_prepared_output(prepared, envelope)


@pytest.mark.parametrize(
    ("dimensions", "reason"),
    [
        (("invented_axis",), "unsupported_interaction_scope"),
        (("receiver", "sender"), "unsupported_interaction_scope"),
        (("sender",), None),
    ],
)
def test_ood_rejects_unknown_reordered_or_unexplained_dimensions(dimensions, reason):
    adapter, interaction, _, prepared = _prepared()
    with pytest.raises(AdapterContractError, match="OOD"):
        adapter.adapt_output(
            prepared,
            _bound_raw(
                interaction,
                status="unsupported_scope",
                abstain=True,
                reasons=("unsupported_interaction_scope",),
                ood_dimensions=dimensions,
                ood_reason=reason,
            ),
        )


def test_output_rejects_identity_drift_and_forged_provenance():
    adapter, interaction, _, prepared = _prepared()
    stale = _bound_raw(interaction)
    stale["interaction_input_fingerprint"] = _fp("stale-input")
    with pytest.raises(AdapterContractError, match="prepared input"):
        adapter.adapt_output(prepared, stale)

    envelope = adapter.adapt_output(prepared, _bound_raw(interaction))
    forged = envelope.model_copy(
        update={"provenance": envelope.provenance.model_copy(update={"input_fingerprints": (_fp("other-input"),)})}
    )
    with pytest.raises(AdapterContractError, match="provenance"):
        adapter.validate_prepared_envelope(prepared, forged)


def test_standalone_output_paths_and_legacy_payloads_fail_closed():
    adapter, interaction, _, prepared = _prepared()
    envelope = adapter.adapt_output(prepared, _bound_raw(interaction))
    for operation, match in (
        (lambda: adapter.validate_envelope(envelope), "prepared input"),
        (lambda: adapter.project_output(envelope), "prepared input"),
        (lambda: adapter.aggregate((envelope,)), "aggregation"),
    ):
        with pytest.raises(AdapterContractError, match=match):
            operation()

    legacy = {
        "step1_communication": {"ligand": "TNF", "receptor": "TNFRSF1A"},
        "step2_receiver_response": {"effect_size": 1.2},
        "chain_complete": True,
    }
    with pytest.raises(AdapterContractError, match="unknown wrapper output"):
        adapter.adapt_output(prepared, legacy)


def test_contract_has_no_runtime_io_legacy_runner_or_default_registration():
    source = inspect.getsource(cell_interaction_evidence_contract)
    for forbidden in (
        "predictors.communication",
        "LRCommDB",
        "CellStateDB",
        "run_communication_case",
        "run_coculture_case",
        "anndata",
        "scanpy",
        "requests.",
        "urllib",
        "Path(",
        "open(",
    ):
        assert forbidden not in source
    assert (
        "cell_interaction_evidence",
        "interaction_evidence_score",
    ) not in DEFAULT_ADAPTER_REGISTRY.keys()
