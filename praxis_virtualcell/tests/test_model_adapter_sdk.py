"""P13.1: strict, deterministic model-adapter SDK contracts."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

import pytest
from pydantic import Field, ValidationError

from praxis_virtualcell.core.request_v2 import SpeciesRef, VirtualCellRequestV2
from praxis_virtualcell.data_packs.feature_alignment import (
    AlignmentReport,
    ModelFeatureContract,
)
from praxis_virtualcell.model_zoo.adapter_sdk import (
    DEFAULT_ADAPTER_REGISTRY,
    AdapterContractError,
    AdapterInputContract,
    AdapterOutputContract,
    AdapterOutputEnvelope,
    AdapterRegistry,
    AdapterUncertainty,
    DeltaExpressionReferenceAdapter,
    PreparedAdapterInput,
    VirtualCellModelAdapter,
    run_adapter_conformance,
)
from praxis_virtualcell.model_zoo.registry_v2 import AdapterIdentity


def _request(
    *,
    task: str = "predict_delta_expression",
    output: str = "delta_expression",
) -> VirtualCellRequestV2:
    return VirtualCellRequestV2.from_dict(
        {
            "schema_version": "vc.request.v2",
            "request_id": "p13-reference",
            "species": {
                "schema_version": "vc.species-ref.v1",
                "taxonomy_id": "NCBITaxon:9606",
                "scientific_name": "Homo sapiens",
                "common_name": "human",
            },
            "cell_context": {
                "schema_version": "vc.cell-context.v1",
                "cell_type_name": "K562",
                "cell_type_id": None,
                "tissue_name": None,
                "tissue_id": None,
                "attributes": {},
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
                "name": output,
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
                "task_type": task,
                "requested_outputs": [output],
            },
            "baseline_context": None,
            "metadata": {},
            "constraints": {},
        }
    )


def _feature_contract(*, mapping_asset=None) -> ModelFeatureContract:
    return ModelFeatureContract.from_dict(
        {
            "schema_version": "vc.model-feature-contract.v1",
            "model_id": "p13-reference-model",
            "model_version": "1.0.0",
            "taxonomy_id": "NCBITaxon:9606",
            "assembly_accession": "GCA_000001405.29",
            "modality": "rna",
            "feature_namespace": {"name": "EnsemblGene", "version": "GRCh38"},
            "feature_id_format": "ensembl_gene",
            "feature_ids": ["ENSG00000141510", "ENSG00000146648"],
            "reorder": False,
            "drop": [],
            "fill": [],
            "mapping_asset": mapping_asset,
        }
    )


def _alignment(contract: ModelFeatureContract | None = None) -> AlignmentReport:
    contract = contract or _feature_contract()
    return AlignmentReport(
        schema_version="vc.alignment-report.v1",
        contract_fingerprint=contract.fingerprint(),
        source_feature_ids=contract.feature_ids,
        target_feature_ids=contract.feature_ids,
        source_shape=(1, 2),
        target_shape=(1, 2),
        steps=(),
        mapping_asset=contract.mapping_asset,
    )


def _raw(*, values=(0.25, -0.5)) -> dict:
    return {
        "prediction": {"delta": list(values)},
        "uncertainty": {
            "available": False,
            "method": "point_estimate",
            "calibrated": False,
            "reason": "reference wrapper has no calibrated uncertainty",
        },
        "ood": {"detected": False, "dimensions": [], "reason": None},
    }


def _prepared(adapter: DeltaExpressionReferenceAdapter | None = None) -> PreparedAdapterInput:
    adapter = adapter or DeltaExpressionReferenceAdapter()
    return adapter.prepare_input(_request())


def _contains_reserved_key(value) -> bool:
    if isinstance(value, dict):
        return any(
            key in {"evidence", "scientific_evidence", "policy", "operator_policy"} or _contains_reserved_key(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_reserved_key(item) for item in value)
    return False


def test_default_registry_contains_only_the_production_delta_reference():
    assert DEFAULT_ADAPTER_REGISTRY.keys() == (("predict_delta_expression", "delta_expression"),)
    adapter = DEFAULT_ADAPTER_REGISTRY.resolve("predict_delta_expression", "delta_expression")
    assert isinstance(adapter, DeltaExpressionReferenceAdapter)
    assert DEFAULT_ADAPTER_REGISTRY.resolve_identity(adapter.identity()) is adapter


def test_contracts_are_strict_versioned_canonical_and_unknown_fields_fail():
    adapter = DeltaExpressionReferenceAdapter()
    assert adapter.input_contract.schema_version == "vc.adapter-input-contract.v1"
    assert adapter.output_contract.schema_version == "vc.adapter-output-contract.v1"
    assert len(adapter.input_contract.fingerprint()) == 64
    assert len(adapter.output_contract.fingerprint()) == 64
    assert adapter.identity().input_contract_fingerprint == adapter.input_contract.fingerprint()
    assert adapter.identity().output_contract_fingerprint == adapter.output_contract.fingerprint()
    with pytest.raises(ValidationError, match="extra"):
        AdapterInputContract.model_validate({**adapter.input_contract.to_dict(), "scientific_evidence": {}})
    with pytest.raises(ValidationError, match="literal"):
        AdapterOutputContract.model_validate({**adapter.output_contract.to_dict(), "schema_version": "unknown"})


def test_registry_fails_closed_for_unknown_pairs_duplicate_pairs_and_ambiguous_outputs():
    registry = AdapterRegistry([DeltaExpressionReferenceAdapter()])
    with pytest.raises(AdapterContractError, match="unregistered"):
        registry.resolve("predict_growth", "growth")
    with pytest.raises(AdapterContractError, match="unregistered"):
        registry.resolve("predict_delta_expression", "fitness")
    with pytest.raises(AdapterContractError, match="duplicate task/output"):
        registry.register(DeltaExpressionReferenceAdapter())

    registry.register(_ScalarDummyAdapter("growth"))
    with pytest.raises(AdapterContractError, match="ambiguous"):
        registry.resolve_requested("predict_delta_expression", ["delta_expression", "growth"])


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("implementation", "tests.OtherAdapter"),
        ("task", "predict_growth"),
        ("outputs", ["fitness"]),
        ("input_contract_fingerprint", "0" * 64),
        ("output_contract_fingerprint", "1" * 64),
    ],
)
def test_registry_resolve_identity_requires_exact_p12_identity(field, replacement):
    registry = AdapterRegistry([DeltaExpressionReferenceAdapter()])
    raw = registry.resolve("predict_delta_expression", "delta_expression").identity().to_dict()
    raw[field] = replacement
    drifted = AdapterIdentity.from_dict(raw)
    with pytest.raises(AdapterContractError, match="identity"):
        registry.resolve_identity(drifted)


def test_prepare_input_binds_request_pack_report_and_exact_feature_alignment():
    adapter = DeltaExpressionReferenceAdapter()
    contract = _feature_contract()
    report = _alignment(contract)
    prepared = adapter.prepare_input(
        _request(),
        pack={"pack_id": "p13-pack", "pack_version": "1.0.0", "fingerprint": "2" * 64},
        compatibility_report={"schema_version": "test.compatibility.v1", "executable": True},
        values=[[1.0, 2.0]],
        unit=None,
        feature_contract=contract,
        alignment_report=report,
    )
    assert prepared.shape == (1, 2)
    assert prepared.feature_contract_fingerprint == contract.fingerprint()
    assert prepared.alignment_report is report
    assert prepared.model_input["targets"] == ("TP53",)
    assert len(prepared.fingerprint()) == 64


def test_prepare_input_rejects_nested_request_subclass_fields():
    class PromotedSpeciesRef(SpeciesRef):
        production_promoted: bool = Field(exclude=True)

    adapter = DeltaExpressionReferenceAdapter()
    request = _request()
    species = PromotedSpeciesRef(
        **request.species.model_dump(mode="python"),
        production_promoted=True,
    )
    forged = request.model_copy(update={"species": species})
    with pytest.raises(AdapterContractError, match="invalid request"):
        adapter.prepare_input(forged)


@pytest.mark.parametrize(
    ("values", "match"),
    [
        ([[True, 2.0]], "finite numbers"),
        ([[float("nan"), 2.0]], "finite numbers"),
        ([[float("inf"), 2.0]], "finite numbers"),
        ([[10**10000, 2.0]], "finite numbers"),
        ([["1.0", 2.0]], "finite numbers"),
        ([[1.0], [2.0, 3.0]], "rectangular"),
    ],
)
def test_prepare_input_rejects_nonfinite_wrong_type_huge_and_ragged_values(values, match):
    adapter = DeltaExpressionReferenceAdapter()
    with pytest.raises((AdapterContractError, ValidationError), match=match):
        adapter.prepare_input(
            _request(),
            values=values,
            feature_contract=_feature_contract(),
            alignment_report=_alignment(),
        )


def test_prepare_input_rejects_unit_shape_and_alignment_contract_drift():
    adapter = DeltaExpressionReferenceAdapter()
    contract = _feature_contract()
    with pytest.raises(AdapterContractError, match="unit"):
        adapter.prepare_input(_request(), values=[[1.0, 2.0]], unit="count")
    with pytest.raises(AdapterContractError, match="shape"):
        adapter.prepare_input(
            _request(),
            values=[[1.0]],
            feature_contract=contract,
            alignment_report=_alignment(contract),
        )
    changed = contract.model_copy(update={"model_version": "2.0.0"})
    with pytest.raises(AdapterContractError, match="contract fingerprint"):
        adapter.prepare_input(
            _request(),
            values=[[1.0, 2.0]],
            feature_contract=changed,
            alignment_report=_alignment(contract),
        )
    with pytest.raises(AdapterContractError, match="together"):
        adapter.prepare_input(_request(), feature_contract=contract)


def test_prepare_input_rejects_feature_order_and_mapping_hash_drift():
    adapter = DeltaExpressionReferenceAdapter()
    contract = _feature_contract()
    wrong_order = replace(
        _alignment(contract),
        target_feature_ids=tuple(reversed(contract.feature_ids)),
    )
    with pytest.raises(AdapterContractError, match="feature order"):
        adapter.prepare_input(
            _request(),
            values=[[1.0, 2.0]],
            feature_contract=contract,
            alignment_report=wrong_order,
        )

    mapped = _feature_contract(
        mapping_asset={
            "asset_id": "p13-test-mapping",
            "path": "mappings/p13.json",
            "version": "1.0.0",
            "sha256": "3" * 64,
        }
    )
    wrong_hash = replace(
        _alignment(mapped),
        mapping_asset=mapped.mapping_asset.model_copy(update={"sha256": "4" * 64}),
    )
    with pytest.raises(AdapterContractError, match="mapping asset hash drift"):
        adapter.prepare_input(
            _request(),
            values=[[1.0, 2.0]],
            feature_contract=mapped,
            alignment_report=wrong_hash,
        )


def test_prepared_model_input_is_defensively_copied_and_immutable():
    original = _prepared()
    source = {"targets": ["TP53"], "nested": {"flags": [True]}}
    prepared = PreparedAdapterInput(**{**original.model_dump(mode="python"), "model_input": source})
    fingerprint = prepared.fingerprint()

    source["nested"]["flags"].append(False)
    assert prepared.model_input["nested"]["flags"] == (True,)
    with pytest.raises(TypeError, match="immutable"):
        prepared.model_input["nested"]["new"] = True
    assert prepared.fingerprint() == fingerprint


@pytest.mark.parametrize(
    "update",
    [
        {"unit": "count"},
        {"values": (1.0,), "shape": (2,)},
        {"shape": (1,)},
    ],
)
def test_conformance_rejects_tampered_prepared_input(update):
    adapter = DeltaExpressionReferenceAdapter()
    prepared = _prepared(adapter).model_copy(update=update)
    with pytest.raises(AdapterContractError):
        run_adapter_conformance(adapter, prepared, _raw())


def test_prepared_validation_refreezes_model_copy_and_rejects_unknown_fields():
    adapter = DeltaExpressionReferenceAdapter()
    source = {"request_id": "p13-reference", "nested": {"flags": [True]}}
    copied = _prepared(adapter).model_copy(update={"model_input": source})
    normalized = adapter.validate_prepared_input(copied)
    fingerprint = normalized.fingerprint()
    source["nested"]["flags"].append(False)
    assert normalized.model_input["nested"]["flags"] == (True,)
    assert normalized.fingerprint() == fingerprint

    unknown = _prepared(adapter).model_copy(update={"scientific_evidence": {"validated": True}})
    with pytest.raises(AdapterContractError, match="unknown fields"):
        adapter.validate_prepared_input(unknown)

    row = [1.0, 2.0]
    nested = _prepared(adapter).model_copy(update={"values": (row,), "shape": (1, 2)})
    normalized_nested = adapter.validate_prepared_input(nested)
    row.append(3.0)
    assert normalized_nested.values == ((1.0, 2.0),)


@pytest.mark.parametrize(
    "update",
    [
        {"request_fingerprint": "bad"},
        {"pack_fingerprint": "bad"},
    ],
)
def test_prepared_validation_wraps_invalid_fingerprints(update):
    adapter = DeltaExpressionReferenceAdapter()
    copied = _prepared(adapter).model_copy(update=update)
    with pytest.raises(AdapterContractError, match="fingerprint"):
        adapter.validate_prepared_input(copied)


@pytest.mark.parametrize(
    ("values", "match"),
    [
        ([True, 0.1], "finite numbers"),
        ([float("nan"), 0.1], "finite numbers"),
        ([float("-inf"), 0.1], "finite numbers"),
        ([10**10000, 0.1], "finite numbers"),
        (["0.1", 0.1], "finite numbers"),
        ([[0.1, 0.2]], "shape"),
    ],
)
def test_output_rejects_wrong_type_nonfinite_huge_and_shape(values, match):
    with pytest.raises((AdapterContractError, ValidationError), match=match):
        DeltaExpressionReferenceAdapter().adapt_output(_prepared(), _raw(values=values))


def test_output_rejects_unknown_raw_field():
    raw = _raw()
    raw["debug_payload"] = {"unchecked": True}
    with pytest.raises(AdapterContractError, match="unknown wrapper output fields"):
        DeltaExpressionReferenceAdapter().adapt_output(_prepared(), raw)


def test_output_enforces_unit_uncertainty_ood_and_abstain_invariants():
    adapter = DeltaExpressionReferenceAdapter()
    prepared = _prepared(adapter)

    wrong_unit = _raw()
    wrong_unit["prediction"]["unit"] = "count"
    with pytest.raises(AdapterContractError, match="unit"):
        adapter.adapt_output(prepared, wrong_unit)

    missing_uncertainty = _raw()
    del missing_uncertainty["uncertainty"]
    with pytest.raises(AdapterContractError, match="uncertainty"):
        adapter.adapt_output(prepared, missing_uncertainty)

    nonfinite_uncertainty = _raw()
    nonfinite_uncertainty["uncertainty"].update(available=True, value=float("nan"))
    with pytest.raises(AdapterContractError, match="finite"):
        adapter.adapt_output(prepared, nonfinite_uncertainty)

    unavailable_with_sigma = _raw()
    unavailable_with_sigma["uncertainty"]["sigma"] = 0.1
    with pytest.raises(AdapterContractError, match="unavailable uncertainty"):
        adapter.adapt_output(prepared, unavailable_with_sigma)

    ood_without_abstain = _raw()
    ood_without_abstain["ood"] = {
        "detected": True,
        "dimensions": ["taxon"],
        "reason": "outside training taxon",
    }
    with pytest.raises(AdapterContractError, match="OOD.*abstain"):
        adapter.adapt_output(prepared, ood_without_abstain)

    detail_free_ood = _raw()
    detail_free_ood.update(
        prediction=None,
        abstain=True,
        abstain_reasons=["OOD"],
        ood={"detected": True, "dimensions": [], "reason": None},
    )
    with pytest.raises(AdapterContractError, match="detected OOD"):
        adapter.adapt_output(prepared, detail_free_ood)

    abstain_with_values = _raw()
    abstain_with_values.update(abstain=True, abstain_reasons=["test-only"])
    with pytest.raises(AdapterContractError, match="abstain.*values"):
        adapter.adapt_output(prepared, abstain_with_values)

    abstain_without_reasons = _raw()
    abstain_without_reasons["prediction"] = None
    abstain_without_reasons["abstain"] = True
    with pytest.raises(AdapterContractError, match="reasons"):
        adapter.adapt_output(prepared, abstain_without_reasons)


def test_adapter_rejects_prepared_input_contract_fingerprint_drift():
    adapter = DeltaExpressionReferenceAdapter()
    drifted = _prepared(adapter).model_copy(update={"input_contract_fingerprint": "0" * 64})
    with pytest.raises(AdapterContractError, match="input contract fingerprint"):
        adapter.adapt_output(drifted, _raw())


def test_output_envelope_is_canonical_deterministic_and_does_not_touch_science_policy():
    adapter = DeltaExpressionReferenceAdapter()
    prepared = _prepared(adapter)
    raw = _raw()
    raw["evidence"] = {"scientifically_validated": False, "records": ["untouched"]}
    raw["policy"] = {"production_promoted": False, "operator": None}
    before = deepcopy(raw)

    first = adapter.adapt_output(prepared, raw)
    second = adapter.adapt_output(prepared, raw)
    assert raw == before
    assert first.to_dict() == second.to_dict()
    assert first.fingerprint() == second.fingerprint()
    assert not _contains_reserved_key(first.to_dict())
    assert first.provenance.adapter_fingerprint == adapter.fingerprint()

    report = run_adapter_conformance(adapter, prepared, raw)
    assert report.deterministic is True
    assert report.output_fingerprint == first.fingerprint()
    assert len(report.fingerprint()) == 64


def test_conformance_uses_prepared_bound_projection_hook(monkeypatch):
    adapter = DeltaExpressionReferenceAdapter()
    prepared = _prepared(adapter)
    calls = []

    def prepared_projection(bound, envelope):
        calls.append(bound.fingerprint())
        return VirtualCellModelAdapter.project_output(adapter, envelope)

    def reject_standalone(_envelope):
        raise AssertionError("conformance must not call standalone projection")

    monkeypatch.setattr(adapter, "project_prepared_output", prepared_projection)
    monkeypatch.setattr(adapter, "project_output", reject_standalone)

    assert run_adapter_conformance(adapter, prepared, _raw()).deterministic is True
    assert calls == [prepared.fingerprint(), prepared.fingerprint()]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("shape", (1,)),
        ("values", (float("nan"), -0.5)),
    ],
)
def test_output_envelope_itself_rejects_shape_and_nonfinite_values(field, value):
    envelope = DeltaExpressionReferenceAdapter().adapt_output(_prepared(), _raw())
    raw = envelope.model_dump(mode="python")
    raw[field] = value
    with pytest.raises(ValidationError):
        AdapterOutputEnvelope.model_validate(raw)


def test_output_envelope_json_dict_round_trips_through_strict_validation():
    envelope = DeltaExpressionReferenceAdapter().adapt_output(_prepared(), _raw())
    assert AdapterOutputEnvelope.model_validate(envelope.to_dict()) == envelope


@pytest.mark.parametrize(
    ("field", "extra"),
    [
        ("uncertainty", "scientifically_validated"),
        ("ood", "promotion_eligible"),
        ("provenance", "production_promoted"),
    ],
)
def test_nested_envelope_model_copy_extras_fail_closed(field, extra):
    adapter = DeltaExpressionReferenceAdapter()
    prepared = _prepared(adapter)
    envelope = adapter.adapt_output(prepared, _raw())
    nested = getattr(envelope, field).model_copy(update={extra: True})
    forged = envelope.model_copy(update={field: nested})
    with pytest.raises(AdapterContractError, match="unknown fields"):
        adapter.validate_prepared_envelope(prepared, forged)


def test_nested_envelope_declared_subclass_fields_fail_closed():
    class ScientificUncertainty(AdapterUncertainty):
        scientifically_validated: bool = Field(exclude=True)

    adapter = DeltaExpressionReferenceAdapter()
    prepared = _prepared(adapter)
    envelope = adapter.adapt_output(prepared, _raw())
    uncertainty = ScientificUncertainty(
        **envelope.uncertainty.model_dump(mode="python"),
        scientifically_validated=True,
    )
    forged = envelope.model_copy(update={"uncertainty": uncertainty})
    with pytest.raises(AdapterContractError, match="invalid adapter output envelope"):
        adapter.validate_prepared_envelope(prepared, forged)


def test_alignment_report_nested_model_copy_extras_fail_closed():
    class PromotedFeatureContract(ModelFeatureContract):
        production_promoted: bool

    adapter = DeltaExpressionReferenceAdapter()
    contract = _feature_contract(
        mapping_asset={
            "asset_id": "p13-test-mapping",
            "path": "mappings/p13.json",
            "version": "1.0.0",
            "sha256": "3" * 64,
        }
    )
    report = _alignment(contract)
    forged_report = replace(
        report,
        mapping_asset=report.mapping_asset.model_copy(update={"scientifically_validated": True}),
    )
    with pytest.raises(AdapterContractError, match="unknown fields"):
        adapter.prepare_input(
            _request(),
            values=[[1.0, 2.0]],
            feature_contract=contract,
            alignment_report=forged_report,
        )

    prepared = adapter.prepare_input(
        _request(),
        values=[[1.0, 2.0]],
        feature_contract=contract,
        alignment_report=report,
    ).model_copy(update={"alignment_report": forged_report})
    with pytest.raises(AdapterContractError, match="unknown fields"):
        adapter.validate_prepared_input(prepared)

    promoted_contract = PromotedFeatureContract.model_validate(
        {
            **contract.model_dump(mode="python"),
            "production_promoted": True,
        }
    )
    with pytest.raises(AdapterContractError, match="wrong type"):
        adapter.prepare_input(
            _request(),
            values=[[1.0, 2.0]],
            feature_contract=promoted_contract,
            alignment_report=_alignment(promoted_contract),
        )


def test_envelope_validation_returns_normalized_nested_contract_objects():
    adapter = DeltaExpressionReferenceAdapter()
    prepared = _prepared(adapter)
    envelope = adapter.adapt_output(prepared, _raw())
    copied = envelope.model_copy(
        update={
            "uncertainty": envelope.uncertainty.to_dict(),
            "ood": envelope.ood.to_dict(),
            "provenance": envelope.provenance.to_dict(),
        }
    )
    normalized = adapter.validate_prepared_envelope(prepared, copied)
    assert normalized.uncertainty.method == "point_estimate"
    assert normalized.ood.detected is False
    assert normalized.provenance.adapter_fingerprint == adapter.fingerprint()
    assert adapter.aggregate((copied,)).values == (0.25, -0.5)
    assert adapter.project_output(copied)["delta"] == [0.25, -0.5]


def test_projection_metadata_cannot_override_values_or_issue_science_policy():
    adapter = DeltaExpressionReferenceAdapter()
    envelope = adapter.adapt_output(_prepared(adapter), _raw())
    override = envelope.model_copy(update={"projection_metadata": {"delta": [99.0]}})
    with pytest.raises(AdapterContractError, match="metadata"):
        adapter.project_output(override)

    raw = _raw()
    raw["prediction"]["baseline"] = {
        "scientific_evidence": {"validated": True},
        "policy": {"promoted": True},
        "production_promoted": True,
    }
    with pytest.raises(AdapterContractError, match="reserved"):
        run_adapter_conformance(adapter, _prepared(adapter), raw)


@pytest.mark.parametrize(
    "unsafe_value",
    [
        "/private/test-pack-root/model.bin",
        "~/private/model.bin",
        "~\\private\\model.bin",
        r"C:\\private\\model.bin",
        r"\\\\server\\share\\model.bin",
        "file:///private/model.bin",
        "FILE:///private/model.bin",
        "file:/private/model.bin",
        " FILE:///private/model.bin",
        r"\private\model.bin",
        {"nested": "/private/test-pack-root/model.bin"},
    ],
)
def test_projection_metadata_rejects_rooted_local_paths(unsafe_value):
    adapter = DeltaExpressionReferenceAdapter()
    envelope = adapter.adapt_output(_prepared(adapter), _raw())
    raw = envelope.model_dump(mode="python")
    raw["projection_metadata"] = {"fixture": unsafe_value}

    with pytest.raises(ValidationError, match="rooted local path"):
        AdapterOutputEnvelope.model_validate(raw)


def test_projection_metadata_model_copy_cannot_bypass_rooted_path_rejection():
    adapter = DeltaExpressionReferenceAdapter()
    prepared = _prepared(adapter)
    envelope = adapter.adapt_output(prepared, _raw())
    forged = envelope.model_copy(update={"projection_metadata": {"fixture": "/private/test-pack-root/model.bin"}})

    with pytest.raises(AdapterContractError, match="invalid adapter output envelope"):
        adapter.validate_prepared_envelope(prepared, forged)


def test_envelope_model_copy_cannot_hide_rooted_path_in_uncertainty_reason():
    adapter = DeltaExpressionReferenceAdapter()
    prepared = _prepared(adapter)
    envelope = adapter.adapt_output(prepared, _raw())
    forged = envelope.model_copy(
        update={
            "uncertainty": AdapterUncertainty(
                available=False,
                method="point_estimate",
                calibrated=False,
                reason="/private/test-pack-root/model.bin",
            )
        }
    )

    with pytest.raises(AdapterContractError, match="invalid adapter output envelope"):
        adapter.validate_prepared_envelope(prepared, forged)
    with pytest.raises(ValueError, match="rooted local paths"):
        forged.to_dict()


def test_projection_metadata_keeps_non_path_unit_text_valid():
    adapter = DeltaExpressionReferenceAdapter()
    envelope = adapter.adapt_output(_prepared(adapter), _raw())
    safe = envelope.model_copy(update={"projection_metadata": {"objective_unit": "1/h"}})

    assert adapter.validate_envelope(safe).projection_metadata == {"objective_unit": "1/h"}


def test_delta_aggregation_and_projection_are_contract_bound():
    adapter = DeltaExpressionReferenceAdapter()
    prepared = _prepared(adapter)
    first = adapter.adapt_output(prepared, _raw(values=(0.25, -0.5)))
    second = adapter.adapt_output(prepared, _raw(values=(0.75, 0.5)))

    aggregate = adapter.aggregate((first, second))
    assert aggregate.values == (0.5, 0.0)
    assert aggregate.uncertainty.method == "ensemble_mean"
    assert adapter.project_output(aggregate) == {"delta": [0.5, 0.0]}

    wrong_contract = first.model_copy(
        update={"provenance": first.provenance.model_copy(update={"output_contract_fingerprint": "0" * 64})}
    )
    with pytest.raises(AdapterContractError, match="aggregation-compatible"):
        adapter.aggregate((wrong_contract,))
    with pytest.raises(AdapterContractError, match="projection-compatible"):
        adapter.project_output(wrong_contract)


class _ScalarDummyAdapter(DeltaExpressionReferenceAdapter):
    """Executable contract-only dummy; never part of the default registry."""

    version = "1.0.0"

    def __init__(self, output: str) -> None:
        self.adapter_id = f"test-only-{output}-dummy"
        self.input_contract = AdapterInputContract(
            schema_version="vc.adapter-input-contract.v1",
            task=f"predict_{output}",
            output=output,
            value_type="float",
            shape=(None,),
            unit="dimensionless",
            pack_data_required=False,
            alignment_required=False,
        )
        self.output_contract = AdapterOutputContract(
            schema_version="vc.adapter-output-contract.v1",
            task=f"predict_{output}",
            output=output,
            value_type="float",
            shape=(None,),
            unit="dimensionless",
            uncertainty_required=True,
            ood_required=True,
            abstain_allowed=True,
        )

    def adapt_output(self, prepared, raw_output):
        raw = deepcopy(raw_output)
        prediction = raw.get("prediction")
        if not isinstance(prediction, dict) or set(prediction) != {self.output_contract.output}:
            raise AdapterContractError("dummy prediction must contain its exact output")
        raw["prediction"] = {
            "delta": prediction[self.output_contract.output],
            "unit": self.output_contract.unit,
        }
        return super().adapt_output(prepared, raw)

    def project_output(self, envelope):
        return VirtualCellModelAdapter.project_output(self, envelope)


class _MalformedEnvelopeAdapter(DeltaExpressionReferenceAdapter):
    """Test-only adapter that bypasses Pydantic assignment validation."""

    adapter_id = "test-only-malformed-envelope"

    def __init__(self, malformation: str) -> None:
        self.malformation = malformation

    def adapt_output(self, prepared, raw_output):
        envelope = super().adapt_output(prepared, raw_output)
        updates = {
            "unit": {"unit": "count"},
            "shape": {"shape": (1,)},
            "values": {"values": (float("nan"), -0.5)},
            "uncertainty": {"uncertainty": None},
            "ood": {"ood": None},
            "provenance": {"provenance": envelope.provenance.model_copy(update={"request_fingerprints": ("f" * 64,)})},
        }[self.malformation]
        return envelope.model_copy(update=updates)


@pytest.mark.parametrize(
    "malformation",
    ["unit", "shape", "values", "uncertainty", "ood", "provenance"],
)
def test_conformance_rejects_malformed_custom_adapter_envelopes(malformation):
    adapter = _MalformedEnvelopeAdapter(malformation)
    prepared = adapter.prepare_input(_request())
    with pytest.raises(AdapterContractError):
        run_adapter_conformance(adapter, prepared, _raw())


class _ReservedProjectionAdapter(DeltaExpressionReferenceAdapter):
    adapter_id = "test-only-reserved-projection"

    def project_output(self, envelope):
        self.validate_envelope(envelope)
        return {
            "scientifically_validated": True,
            "production_promoted": True,
        }


def test_conformance_rejects_adapter_issued_science_or_policy_projection():
    adapter = _ReservedProjectionAdapter()
    prepared = adapter.prepare_input(_request())
    with pytest.raises(AdapterContractError, match="reserved science or policy"):
        run_adapter_conformance(adapter, prepared, _raw())


def test_delta_growth_fitness_contract_conformance_and_default_allowlist():
    adapters = [
        (DeltaExpressionReferenceAdapter(), _request(), _raw()),
        *[
            (
                _ScalarDummyAdapter(output),
                _request(task=f"predict_{output}", output=output),
                {
                    "prediction": {output: [0.5]},
                    "uncertainty": {
                        "available": False,
                        "method": "contract_only",
                        "calibrated": False,
                    },
                    "ood": {"detected": False, "dimensions": [], "reason": None},
                },
            )
            for output in ("growth", "fitness")
        ],
    ]
    local = AdapterRegistry(adapter for adapter, _, _ in adapters)

    for adapter, request, raw in adapters:
        prepared = adapter.prepare_input(request, unit=adapter.input_contract.unit)
        assert run_adapter_conformance(adapter, prepared, raw).deterministic is True
        projection = adapter.project_output(adapter.adapt_output(prepared, raw))
        expected_key = "delta" if type(adapter) is DeltaExpressionReferenceAdapter else adapter.output_contract.output
        assert tuple(projection) == (expected_key,)

    assert {output for _, output in local.keys()} == {
        "delta_expression",
        "growth",
        "fitness",
    }
    assert DEFAULT_ADAPTER_REGISTRY.keys() == (("predict_delta_expression", "delta_expression"),)
