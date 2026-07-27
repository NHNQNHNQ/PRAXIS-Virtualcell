"""P1 contract tests for strict, versioned VirtualCell domain objects."""

from __future__ import annotations

import ast
import json
from dataclasses import asdict
from pathlib import Path

import pytest

from praxis_virtualcell.core.exceptions import InputValidationError
from praxis_virtualcell.core.request import VirtualCellRequest
from praxis_virtualcell.core.request_v2 import (
    CellContext,
    DatasetRef,
    ModalitySpec,
    ModelInputBundle,
    PerturbationSpec,
    PredictionBundle,
    SpeciesRef,
    TaskSpec,
    VirtualCellRequestV2,
    legacy_request_to_v2,
    v2_request_to_legacy,
)

SPECIES = {
    "schema_version": "vc.species-ref.v1",
    "taxonomy_id": "NCBITaxon:9606",
    "scientific_name": "Homo sapiens",
    "common_name": "human",
}
CELL = {
    "schema_version": "vc.cell-context.v1",
    "cell_type_name": "K562",
    "cell_type_id": "CL:0000123",
    "tissue_name": "blood",
    "tissue_id": "UBERON:0000178",
    "attributes": {"condition": "control"},
}
INPUT_MODALITY = {
    "schema_version": "vc.modality.v1",
    "name": "scRNA",
    "ontology_id": "OBI:0002631",
    "unit": "count",
    "feature_namespace": "HGNC",
}
OUTPUT_MODALITY = {
    "schema_version": "vc.modality.v1",
    "name": "delta_expression",
    "ontology_id": None,
    "unit": "log2_fold_change",
    "feature_namespace": "HGNC",
}
DATASET = {
    "schema_version": "vc.dataset-ref.v1",
    "dataset_id": "norman_2019",
    "version": "1",
    "sha256": "a" * 64,
    "uri": "file:///data/norman_2019.h5ad",
}
PERTURBATION = {
    "schema_version": "vc.perturbation.v1",
    "kind": "gene",
    "targets": ["AHR"],
    "dose_value": 1.0,
    "dose_unit": "uM",
    "timepoint": "24h",
}
TASK = {
    "schema_version": "vc.task.v1",
    "task_type": "predict_delta_expression",
    "requested_outputs": ["delta_expression", "reliability_report"],
}
REQUEST_V2 = {
    "schema_version": "vc.request.v2",
    "request_id": "req-v2-001",
    "species": SPECIES,
    "cell_context": CELL,
    "input_modality": INPUT_MODALITY,
    "output_modality": OUTPUT_MODALITY,
    "perturbation": PERTURBATION,
    "task": TASK,
    "baseline_context": {"control": "vehicle"},
    "metadata": {"source": "unit-test"},
    "constraints": {"offline": True},
}
MODEL_INPUT = {
    "schema_version": "vc.model-input.v1",
    "bundle_id": "input-001",
    "request": REQUEST_V2,
    "datasets": [DATASET],
    "metadata": {"split": "test"},
}
PREDICTION = {
    "schema_version": "vc.prediction.v1",
    "prediction_id": "pred-001",
    "request_id": "req-v2-001",
    "model_id": "example-model@v1",
    "task": TASK,
    "output_modality": OUTPUT_MODALITY,
    "feature_ids": ["AHR", "CYP1A1"],
    "values": [0.1, -0.2],
    "provenance": {"call_hash": "sha256:abc"},
}


@pytest.mark.parametrize(
    "cls,payload",
    [
        (SpeciesRef, SPECIES),
        (CellContext, CELL),
        (ModalitySpec, INPUT_MODALITY),
        (DatasetRef, DATASET),
        (PerturbationSpec, PERTURBATION),
        (TaskSpec, TASK),
        (VirtualCellRequestV2, REQUEST_V2),
        (ModelInputBundle, MODEL_INPUT),
        (PredictionBundle, PREDICTION),
    ],
)
def test_every_domain_object_json_round_trips(cls, payload):
    first = cls.from_dict(json.loads(json.dumps(payload, allow_nan=False)))
    encoded = json.loads(json.dumps(first.to_dict(), allow_nan=False))
    second = cls.from_dict(encoded)

    assert second == first
    assert second.to_dict() == encoded


@pytest.mark.parametrize(
    "cls,payload",
    [
        (SpeciesRef, SPECIES),
        (CellContext, CELL),
        (ModalitySpec, INPUT_MODALITY),
        (DatasetRef, DATASET),
        (PerturbationSpec, PERTURBATION),
        (TaskSpec, TASK),
        (VirtualCellRequestV2, REQUEST_V2),
        (ModelInputBundle, MODEL_INPUT),
        (PredictionBundle, PREDICTION),
    ],
)
def test_unknown_fields_fail_closed(cls, payload):
    with pytest.raises(InputValidationError):
        cls.from_dict({**payload, "unexpected": "must-not-be-ignored"})


@pytest.mark.parametrize(
    "cls,payload",
    [
        (SpeciesRef, SPECIES),
        (CellContext, CELL),
        (ModalitySpec, INPUT_MODALITY),
        (DatasetRef, DATASET),
        (PerturbationSpec, PERTURBATION),
        (TaskSpec, TASK),
        (VirtualCellRequestV2, REQUEST_V2),
        (ModelInputBundle, MODEL_INPUT),
        (PredictionBundle, PREDICTION),
    ],
)
def test_missing_or_wrong_schema_versions_fail_closed(cls, payload):
    missing = {key: value for key, value in payload.items() if key != "schema_version"}

    with pytest.raises(InputValidationError):
        cls.from_dict(missing)
    with pytest.raises(InputValidationError):
        cls.from_dict({**payload, "schema_version": "vc.wrong.v999"})


def test_unknown_nested_field_fails_closed():
    bad = {**REQUEST_V2, "species": {**SPECIES, "unexpected": True}}

    with pytest.raises(InputValidationError):
        VirtualCellRequestV2.from_dict(bad)


@pytest.mark.parametrize(
    "cls,payload",
    [
        (SpeciesRef, {**SPECIES, "taxonomy_id": "9606"}),
        (SpeciesRef, {**SPECIES, "taxonomy_id": "NCBITaxon:not-a-number"}),
        (CellContext, {**CELL, "cell_type_id": "CL_0000123"}),
        (CellContext, {**CELL, "tissue_id": "UBERON"}),
        (ModalitySpec, {**INPUT_MODALITY, "ontology_id": "not-an-ontology-id"}),
    ],
)
def test_illegal_ontology_ids_fail_closed(cls, payload):
    with pytest.raises(InputValidationError):
        cls.from_dict(payload)


@pytest.mark.parametrize(
    "cls,payload",
    [
        (ModalitySpec, {**INPUT_MODALITY, "unit": "bananas"}),
        (PerturbationSpec, {**PERTURBATION, "dose_unit": "furlong"}),
        (PerturbationSpec, {**PERTURBATION, "timepoint": "24fortnights"}),
        (
            PredictionBundle,
            {**PREDICTION, "output_modality": {**OUTPUT_MODALITY, "unit": "mystery-unit"}},
        ),
    ],
)
def test_illegal_units_fail_closed(cls, payload):
    with pytest.raises(InputValidationError):
        cls.from_dict(payload)


@pytest.mark.parametrize(
    "updates",
    [
        {"feature_ids": []},
        {"feature_ids": ["AHR"], "values": [0.1, 0.2]},
        {"feature_ids": ["AHR", "AHR"]},
        {"feature_ids": ["AHR", ""]},
        {"model_id": ""},
        {"values": [float("nan"), 0.2]},
    ],
)
def test_anonymous_or_non_json_prediction_vectors_fail_closed(updates):
    with pytest.raises(InputValidationError):
        PredictionBundle.from_dict({**PREDICTION, **updates})


@pytest.mark.parametrize(
    "field,value",
    [
        ("metadata", {"bad": float("nan")}),
        ("metadata", {"bad": ("tuple",)}),
        ("constraints", {1: "non-string-key"}),
    ],
)
def test_non_json_request_fields_fail_closed(field, value):
    with pytest.raises(InputValidationError):
        VirtualCellRequestV2.from_dict({**REQUEST_V2, field: value})


def test_validated_domain_objects_are_deeply_immutable():
    payload = json.loads(json.dumps(REQUEST_V2))
    payload["metadata"] = {"nested": {"items": ["original"]}}
    request = VirtualCellRequestV2.from_dict(payload)
    model_input = ModelInputBundle.from_dict(MODEL_INPUT)
    prediction = PredictionBundle.from_dict(PREDICTION)

    mappings = (
        request.cell_context.attributes,
        request.baseline_context,
        request.metadata,
        request.constraints,
        model_input.metadata,
        prediction.provenance,
    )
    for mapping in mappings:
        with pytest.raises(TypeError):
            mapping["post_validation_mutation"] = True
    with pytest.raises(TypeError):
        request.metadata["nested"]["added"] = True
    with pytest.raises(TypeError):
        request.metadata["nested"]["items"][0] = "changed"

    assert request.to_dict() == payload


def test_dataset_reference_requires_content_hash():
    without_hash = {key: value for key, value in DATASET.items() if key != "sha256"}

    with pytest.raises(InputValidationError):
        DatasetRef.from_dict(without_hash)


def test_perturbation_targets_preserve_order_and_duplicates():
    spec = PerturbationSpec.from_dict({**PERTURBATION, "targets": ["AHR", "CYP1A1", "AHR"]})

    assert spec.targets == ("AHR", "CYP1A1", "AHR")


def test_legacy_request_adapter_is_lossless_for_existing_fields():
    legacy = VirtualCellRequest.from_dict(
        {
            "request_id": "legacy-001",
            "species": "human",
            "cell_type": "K562",
            "tissue": "blood",
            "perturbation_type": "gene",
            "perturbation_targets": ["AHR"],
            "perturbation_dose": 1.0,
            "perturbation_time": "24h",
            "input_modality": "scRNA",
            "output_modality": "delta_expression",
            "task_type": "predict_delta_expression",
            "baseline_context": {"control": "vehicle"},
            "metadata": {"requested_outputs": ["delta_expression"]},
            "constraints": {"offline": True},
        }
    )

    v2 = legacy_request_to_v2(legacy)
    restored = v2_request_to_legacy(v2)

    assert v2.schema_version == "vc.request.v2"
    assert v2.species.taxonomy_id == "NCBITaxon:9606"
    assert v2.perturbation.targets == ("AHR",)
    assert asdict(restored) == asdict(legacy)


def test_legacy_virtual_cell_request_remains_directly_usable():
    legacy = VirtualCellRequest.from_dict(
        {
            "request_id": "legacy-002",
            "species": "human",
            "perturbation_type": "gene",
            "perturbation_targets": ["AHR"],
            "input_modality": "scRNA",
            "output_modality": "delta_expression",
            "task_type": "predict_delta_expression",
        }
    )

    assert legacy.species == "human"
    assert legacy.perturbation_targets == ["AHR"]


def test_v2_to_legacy_rejects_unrepresentable_context_instead_of_dropping_it():
    request = VirtualCellRequestV2.from_dict(REQUEST_V2)

    with pytest.raises(InputValidationError):
        v2_request_to_legacy(request)


def test_request_v2_has_no_h5ad_pack_registry_or_model_dependency():
    import praxis_virtualcell.core.request_v2 as module

    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imports |= {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    calls |= {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }

    assert not any(
        name.startswith(("anndata", "scanpy", "h5py", "praxis_virtualcell.model_zoo"))
        or "pack_registry" in name
        for name in imports
    )
    assert calls.isdisjoint({"open", "read_h5ad", "read_text", "read_bytes"})
