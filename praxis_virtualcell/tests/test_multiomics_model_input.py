"""P18 typed joint multi-omics input contracts and no-fabrication gates."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import numpy as np
import pytest

from praxis_virtualcell.core.request_v2 import SpeciesRef, VirtualCellRequestV2
from praxis_virtualcell.data_packs.feature_alignment import ModelFeatureContract
from praxis_virtualcell.data_packs.manifest import PackManifest
from praxis_virtualcell.data_packs.mudata_adapter import (
    CanonicalModalityView,
    CanonicalMuDataView,
    _manifest_semantics,
)
from praxis_virtualcell.data_packs.registry import RegisteredPack
from praxis_virtualcell.model_zoo.adapter_sdk import AdapterInputContract
from praxis_virtualcell.model_zoo.registry_v2 import AdapterIdentity
from praxis_virtualcell.multiomics_input import (
    MultiOmicsInputContractV1,
    MultiOmicsInputError,
    MultiOmicsLayerInputV1,
    MultiOmicsModalitySlotV1,
    MultiOmicsModelInputV1,
    PreparedMultiOmicsModelInput,
    _join_fingerprint,
    _matrix_fingerprint,
    _MatrixSnapshot,
    _missingness_fingerprint,
    _view_identity_fingerprint,
    compile_multiomics_model_input,
)

_MODEL_FINGERPRINT = "1" * 64
_OUTPUT_CONTRACT_FINGERPRINT = "2" * 64


class _TinyAnnData:
    def __init__(self, matrix) -> None:
        self.X = np.asarray(matrix, dtype=np.float32)
        self.shape = self.X.shape
        self.isbacked = True
        self.is_view = False


class _TinyMuData:
    isbacked = True


_MODALITIES = {
    "rna": {
        "name": "RNA",
        "ontology_id": "EFO:0008913",
        "namespace": "EnsemblGene",
        "namespace_version": "GRCh38",
        "id_format": "ensembl_gene",
        "features": ("ENSG00000106546", "ENSG00000141510"),
        "observations": ("cell-1", "cell-2", "cell-3"),
        "matrix": ((1.0, 2.0), (0.0, 0.0), (3.0, 4.0)),
    },
    "protein": {
        "name": "protein",
        "ontology_id": "EFO:0007937",
        "namespace": "UniProtKB",
        "namespace_version": "2026_03",
        "id_format": "uniprot_protein",
        "features": ("UniProtKB:P35869", "UniProtKB:P04637"),
        "observations": ("cell-2", "cell-3", "cell-4"),
        "matrix": ((5.0, 6.0), (7.0, 8.0), (9.0, 10.0)),
    },
    "atac": {
        "name": "ATAC",
        "ontology_id": "EFO:0010891",
        "namespace": "EnsemblGene",
        "namespace_version": "GRCh38",
        "id_format": "ensembl_gene",
        "features": ("ENSG00000157764", "ENSG00000171862"),
        "observations": ("cell-2", "cell-3"),
        "matrix": ((11.0, 12.0), (13.0, 14.0)),
    },
}


def _manifest(keys=("rna", "protein"), *, pairing="partially_paired") -> PackManifest:
    modalities = []
    for key in keys:
        value = _MODALITIES[key]
        rows = 4 if pairing == "paired" else len(value["observations"])
        modalities.append(
            {
                "key": key,
                "modality": {
                    "name": value["name"],
                    "ontology_id": value["ontology_id"],
                },
                "feature_namespace": {
                    "name": value["namespace"],
                    "version": value["namespace_version"],
                },
                "feature_semantics": {
                    "id_source": "var_names",
                    "id_format": value["id_format"],
                    "symbol_field": None,
                },
                "shape": [rows, len(value["features"])],
            }
        )
    return PackManifest.from_dict(
        {
            "schema_version": "vc.pack.v0.3",
            "pack_id": "tiny-human-multiomics",
            "pack_version": "1.0.0",
            "taxon": {
                "ontology_id": "NCBITaxon:9606",
                "scientific_name": "Homo sapiens",
            },
            "assembly": {
                "name": "GRCh38",
                "accession": "GCF_000001405.40",
            },
            "identity": {
                "observation_key": "obs_names",
                "feature_key": "var_names",
            },
            "assets": [
                {
                    "id": "multiomics",
                    "path": "tiny.h5mu",
                    "media_type": "application/vnd.mudata+hdf5",
                    "sha256": "a" * 64,
                    "size_bytes": 1,
                }
            ],
            "multiomics": {
                "asset": "multiomics",
                "observation_pairing": pairing,
                "modalities": modalities,
            },
            "cell_semantics": {
                "identity": "cell_identity_id",
                "state": ["cell_state_id"],
                "context": ["tissue_id"],
                "local_terms": [],
            },
            "conditions": {
                "field": "condition_id",
                "values": ["condition:control", "condition:perturbed"],
                "matched_control_field": "matched_control_id",
                "dose": {"value_field": "dose_value", "unit_field": "dose_unit"},
                "time": {"value_field": "time_value", "unit_field": "time_unit"},
            },
            "perturbations": {
                "field": "perturbation_id",
                "target_modality": "rna",
                "values": [
                    {"id": "perturbation:control", "kind": "control", "targets": []},
                    {
                        "id": "perturbation:ahr",
                        "kind": "genetic",
                        "targets": ["ENSG00000106546"],
                    },
                ],
            },
            "split": {
                "field": "split",
                "strategy": "predefined",
                "values": ["train", "test"],
                "name": "target-holdout-v1",
                "leakage_guard": ["target_ids"],
            },
            "provenance": {
                "source": "P18 in-memory contract fixture",
                "created_by": "pytest",
                "citation": "none",
            },
            "license": {"id": "CC0-1.0", "name": "CC0"},
        }
    )


def _view(keys=("rna", "protein"), *, pairing="partially_paired"):
    manifest = _manifest(keys, pairing=pairing)
    global_ids = ("cell-1", "cell-2", "cell-3", "cell-4")
    modalities = []
    for key in keys:
        value = _MODALITIES[key]
        observations = global_ids if pairing == "paired" else value["observations"]
        matrix = np.vstack((value["matrix"], value["matrix"][-1])) if pairing == "paired" else value["matrix"]
        adata = _TinyAnnData(matrix)
        modalities.append(
            CanonicalModalityView(
                key=key,
                observation_ids=tuple(observations),
                feature_ids=value["features"],
                feature_symbols=None,
                taxonomy_id="NCBITaxon:9606",
                assembly_accession="GCF_000001405.40",
                modality_name=value["name"],
                modality_ontology_id=value["ontology_id"],
                feature_namespace_name=value["namespace"],
                feature_namespace_version=value["namespace_version"],
                feature_id_format=value["id_format"],
                matrix_location="X",
                matrix_format="dense",
                _adata=adata,
            )
        )
    membership = [set(value.observation_ids) for value in modalities]
    shared = tuple(observation for observation in global_ids if all(observation in values for values in membership))
    view = CanonicalMuDataView(
        observation_ids=global_ids,
        observation_pairing=pairing,
        shared_observation_ids=shared,
        modalities=tuple(modalities),
        conditions=("condition:control",) * 4,
        splits=("train",) * 4,
        cell_identity_ids=("CVCL_0004",) * 4,
        cell_state_ids=(("VCSTATE:baseline",),) * 4,
        cell_context_ids=(("UBERON:0000178",),) * 4,
        perturbation_ids=("perturbation:control",) * 4,
        perturbation_kinds=("control",) * 4,
        perturbation_targets=((),) * 4,
        matched_control_ids=("condition:control",) * 4,
        doses=((0.0, "1"),) * 4,
        times=((24.0, "h"),) * 4,
        split_name="target-holdout-v1",
        manifest_semantics=_manifest_semantics(manifest),
        manifest=manifest,
        _mdata=_TinyMuData(),
    )
    pack = RegisteredPack(
        manifest=manifest,
        root=Path("/tmp/p18-tiny-pack"),
        fingerprint=manifest.fingerprint(),
    )
    return pack, view


def _feature_contract(key: str, *, fill=()):
    value = _MODALITIES[key]
    feature_ids = list(value["features"])
    feature_ids.extend(item["feature_id"] for item in fill if item["feature_id"] not in feature_ids)
    return {
        "schema_version": "vc.model-feature-contract.v1",
        "model_id": "joint_state_model",
        "model_version": "1.0.0",
        "taxonomy_id": "NCBITaxon:9606",
        "assembly_accession": "GCF_000001405.40",
        "modality": key,
        "feature_namespace": {
            "name": value["namespace"],
            "version": value["namespace_version"],
        },
        "feature_id_format": value["id_format"],
        "feature_ids": feature_ids,
        "reorder": False,
        "drop": [],
        "fill": list(fill),
    }


def _slot_payload(key: str, *, required: bool = True, fill=()):
    value = _MODALITIES[key]
    feature_contract = _feature_contract(key, fill=fill)
    feature_fingerprint = ModelFeatureContract.from_dict(feature_contract).fingerprint()
    return {
        "schema_version": "vc.multiomics-modality-slot.v1",
        "key": key,
        "required": required,
        "modality_name": value["name"],
        "modality_ontology_id": value["ontology_id"],
        "representation": "matrix:X",
        "feature_contract": feature_contract,
        "feature_contract_fingerprint": feature_fingerprint,
    }


def _contract_payload(
    slots=None,
    *,
    join_policy="required_inner",
    missingness_policy="reject",
    target="rna",
    normalization="none",
):
    return {
        "schema_version": "vc.multiomics-input-contract.v1",
        "model_name": "joint_state_model",
        "model_version": "1.0.0",
        "model_fingerprint": _MODEL_FINGERPRINT,
        "taxonomy_id": "NCBITaxon:9606",
        "assembly_accession": "GCF_000001405.40",
        "task": "predict_cell_state",
        "outputs": ["cell_state_embedding"],
        "target_modality_key": target,
        "join_policy": join_policy,
        "missingness_policy": missingness_policy,
        "normalization": normalization,
        "slots": slots or [_slot_payload("rna"), _slot_payload("protein")],
    }


def _contract(**kwargs) -> MultiOmicsInputContractV1:
    return MultiOmicsInputContractV1.from_dict(_contract_payload(**kwargs))


def _adapter(contract: MultiOmicsInputContractV1, **updates) -> AdapterIdentity:
    payload = {
        "schema_version": "vc.model-adapter.v1",
        "adapter_id": "p18-joint-input-contract",
        "version": "1.0.0",
        "implementation": "tests.ContractOnlyMultiOmicsAdapter",
        "task": contract.task,
        "outputs": list(contract.outputs),
        "input_contract_fingerprint": contract.fingerprint(),
        "output_contract_fingerprint": _OUTPUT_CONTRACT_FINGERPRINT,
        "legacy_incomplete": False,
    }
    payload.update(updates)
    return AdapterIdentity.from_dict(payload)


def _request(
    contract: MultiOmicsInputContractV1,
    pack: RegisteredPack,
    *,
    task="predict_cell_state",
    outputs=("cell_state_embedding",),
    input_update=None,
    perturbation_kind="gene",
    targets=("ENSG00000106546",),
    dose_value=None,
    dose_unit=None,
) -> VirtualCellRequestV2:
    target = next(slot for slot in contract.slots if slot.key == contract.target_modality_key)
    input_modality = {
        "schema_version": "vc.modality.v1",
        "name": target.modality_name,
        "ontology_id": target.modality_ontology_id,
        "unit": None,
        "feature_namespace": target.feature_contract.feature_namespace.name,
    }
    input_modality.update(input_update or {})
    return VirtualCellRequestV2.from_dict(
        {
            "schema_version": "vc.request.v2",
            "request_id": "p18-contract-test",
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
            "input_modality": input_modality,
            "output_modality": {
                "schema_version": "vc.modality.v1",
                "name": "cell_state_embedding",
                "ontology_id": None,
                "unit": None,
                "feature_namespace": None,
            },
            "perturbation": {
                "schema_version": "vc.perturbation.v1",
                "kind": perturbation_kind,
                "targets": list(targets),
                "dose_value": dose_value,
                "dose_unit": dose_unit,
                "timepoint": None,
            },
            "task": {
                "schema_version": "vc.task.v1",
                "task_type": task,
                "requested_outputs": list(outputs),
            },
            "baseline_context": None,
            "metadata": {},
            "constraints": {},
        }
    )


def _compile(
    *,
    keys=("rna", "protein"),
    pairing="partially_paired",
    contract=None,
):
    pack, view = _view(keys, pairing=pairing)
    contract = contract or _contract()
    prepared = compile_multiomics_model_input(
        _request(contract, pack),
        pack,
        view,
        contract,
        _adapter(contract),
    )
    return prepared, pack, view, contract


def _contains_matrix_key(value) -> bool:
    if isinstance(value, dict):
        return any(key in {"matrix", "matrices"} or _contains_matrix_key(item) for key, item in value.items())
    if isinstance(value, list):
        return any(_contains_matrix_key(item) for item in value)
    return False


def _fingerprint(value) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def test_slot_and_contract_parsing_is_strict_and_order_sensitive():
    slot_payload = _slot_payload("rna")
    slot = MultiOmicsModalitySlotV1.from_dict(slot_payload)
    assert slot.feature_contract_fingerprint == slot.feature_contract.fingerprint()

    with pytest.raises(MultiOmicsInputError):
        MultiOmicsModalitySlotV1.from_dict({**slot_payload, "unexpected": True})
    with pytest.raises(MultiOmicsInputError):
        MultiOmicsModalitySlotV1.from_dict({**slot_payload, "feature_contract_fingerprint": "f" * 64})

    forward = _contract()
    reverse = _contract(slots=[_slot_payload("protein"), _slot_payload("rna")])
    assert forward.fingerprint() != reverse.fingerprint()
    with pytest.raises(MultiOmicsInputError):
        _contract(slots=[_slot_payload("rna"), _slot_payload("rna")])


def test_paired_compile_is_deterministic_contract_only_and_serializes_no_matrices():
    first, pack, view, contract = _compile(pairing="paired")
    second = compile_multiomics_model_input(_request(contract, pack), pack, view, contract, _adapter(contract))

    assert first.model_input == second.model_input
    assert first.model_input.fingerprint() == second.model_input.fingerprint()
    with pytest.raises(FrozenInstanceError):
        first.matrices = ()
    assert tuple(key for key, _ in first.matrices) == ("rna", "protein")
    for (_, left), (_, right) in zip(first.matrices, second.matrices, strict=True):
        np.testing.assert_array_equal(left, right)
    assert first.alignment_reports == second.alignment_reports

    serialized = first.model_input.to_dict()
    assert not _contains_matrix_key(serialized)
    assert first.model_input.executable is False
    assert first.model_input.execution_performed is False
    assert first.model_input.execution_step_created is False
    assert first.model_input.abstain is True
    assert first.model_input.abstain_reason == "contract_only_execution_not_authorized"


def test_required_inner_uses_only_real_shared_rows_and_preserves_zero_row():
    prepared, _, _, _ = _compile()
    model_input = prepared.model_input
    assert model_input.global_observation_ids == (
        "cell-1",
        "cell-2",
        "cell-3",
        "cell-4",
    )
    assert model_input.joined_observation_ids == ("cell-2", "cell-3")

    layers = {layer.slot.key: layer for layer in model_input.layers}
    assert layers["rna"].source_observation_ids == (
        "cell-1",
        "cell-2",
        "cell-3",
    )
    assert layers["rna"].input_observation_ids == ("cell-2", "cell-3")
    assert layers["rna"].observation_mask == (True, True)
    assert layers["rna"].source_shape == (3, 2)
    assert layers["rna"].aligned_shape == (3, 2)
    assert layers["rna"].input_shape == (2, 2)

    matrices = dict(prepared.matrices)
    assert matrices["rna"].shape == (2, 2)
    assert matrices["protein"].shape == (2, 2)
    np.testing.assert_array_equal(matrices["rna"][0], np.array([0.0, 0.0]))
    assert tuple(key for key, _ in prepared.alignment_reports) == (
        "rna",
        "protein",
    )
    for layer, (key, report) in zip(model_input.layers, prepared.alignment_reports, strict=True):
        assert layer.slot.key == key
        assert layer.alignment_report == report
        assert len(layer.alignment_report_fingerprint) == 64


def test_global_explicit_masks_never_pad_local_matrices_or_treat_zero_as_missing():
    contract = _contract(
        join_policy="global",
        missingness_policy="explicit_mask",
    )
    prepared, _, _, _ = _compile(contract=contract)
    model_input = prepared.model_input
    assert model_input.joined_observation_ids == model_input.global_observation_ids

    layers = {layer.slot.key: layer for layer in model_input.layers}
    assert layers["rna"].observation_mask == (True, True, True, False)
    assert layers["protein"].observation_mask == (False, True, True, True)
    assert layers["rna"].input_observation_ids == (
        "cell-1",
        "cell-2",
        "cell-3",
    )
    assert layers["protein"].input_observation_ids == (
        "cell-2",
        "cell-3",
        "cell-4",
    )

    matrices = dict(prepared.matrices)
    assert matrices["rna"].shape == (3, 2)
    assert matrices["protein"].shape == (3, 2)
    np.testing.assert_array_equal(matrices["rna"][1], np.array([0.0, 0.0]))
    assert layers["rna"].input_shape == (3, 2)
    assert layers["protein"].input_shape == (3, 2)


def test_missing_required_atac_cannot_be_excused_by_rna_protein_intersection():
    contract = _contract(
        slots=[
            _slot_payload("rna"),
            _slot_payload("protein"),
            _slot_payload("atac"),
        ]
    )
    pack, view = _view()
    with pytest.raises(MultiOmicsInputError):
        compile_multiomics_model_input(_request(contract, pack), pack, view, contract, _adapter(contract))


def test_at_least_two_distinct_contract_layers_must_be_present():
    contract = _contract(slots=[_slot_payload("rna"), _slot_payload("atac", required=False)])
    pack, view = _view()
    with pytest.raises(MultiOmicsInputError):
        compile_multiomics_model_input(_request(contract, pack), pack, view, contract, _adapter(contract))


def test_single_tensor_adapter_contract_cannot_authorize_joint_input():
    pack, view = _view()
    contract = _contract()
    single_tensor = AdapterInputContract(
        schema_version="vc.adapter-input-contract.v1",
        task=contract.task,
        output=contract.outputs[0],
        value_type="float",
        shape=(None, None),
        unit=None,
        pack_data_required=True,
        alignment_required=True,
    )
    with pytest.raises(MultiOmicsInputError):
        compile_multiomics_model_input(
            _request(contract, pack),
            pack,
            view,
            contract,
            single_tensor,
        )


def test_malformed_observation_membership_is_rejected_before_joining():
    pack, view = _view()
    contract = _contract()
    malformed_views = [
        replace(
            view,
            observation_ids=("cell-1", "cell-2", "cell-2", "cell-4"),
        ),
        replace(
            view,
            modalities=(
                replace(
                    view.modalities[0],
                    observation_ids=("cell-1", "cell-unknown", "cell-3"),
                ),
                view.modalities[1],
            ),
        ),
    ]
    for malformed in malformed_views:
        with pytest.raises(MultiOmicsInputError):
            compile_multiomics_model_input(
                _request(contract, pack),
                pack,
                malformed,
                contract,
                _adapter(contract),
            )


def test_declared_optional_absence_is_a_typed_layer_not_a_fabricated_matrix():
    contract = _contract(
        slots=[
            _slot_payload("rna"),
            _slot_payload("protein"),
            _slot_payload("atac", required=False),
        ]
    )
    prepared, _, _, _ = _compile(contract=contract)

    assert tuple(key for key, _ in prepared.matrices) == ("rna", "protein")
    absent = prepared.model_input.layers[2]
    assert absent.slot.key == "atac"
    assert absent.present is False
    assert absent.source_observation_ids == ()
    assert absent.input_observation_ids == ()
    assert absent.observation_mask == (False, False)
    assert absent.alignment_report is None
    assert absent.alignment_report_fingerprint is None
    assert absent.matrix_fingerprint is None
    assert absent.source_matrix_format is None
    assert absent.source_shape is None
    assert absent.aligned_shape is None
    assert absent.input_shape is None


def test_target_modality_must_be_declared_required_and_present():
    payload = _contract_payload(
        slots=[
            _slot_payload("rna"),
            _slot_payload("protein"),
            _slot_payload("atac", required=False),
        ],
        target="atac",
    )
    with pytest.raises(MultiOmicsInputError):
        MultiOmicsInputContractV1.from_dict(payload)


@pytest.mark.parametrize(
    ("join_policy", "missingness_policy"),
    [("required_inner", "explicit_mask"), ("global", "reject")],
)
def test_join_and_missingness_policy_pairs_are_closed(join_policy, missingness_policy):
    with pytest.raises(MultiOmicsInputError):
        _contract(
            join_policy=join_policy,
            missingness_policy=missingness_policy,
        )


@pytest.mark.parametrize("normalization", ["log1p", "library_size"])
def test_implicit_normalization_is_rejected(normalization):
    with pytest.raises(MultiOmicsInputError):
        _contract(normalization=normalization)


def test_any_feature_fill_is_rejected_even_when_the_fill_value_is_zero():
    filled = _slot_payload(
        "rna",
        fill=[{"feature_id": "ENSG00000157764", "value": 0.0}],
    )
    with pytest.raises(MultiOmicsInputError):
        _contract(slots=[filled, _slot_payload("protein")])


def test_explicit_feature_mapping_is_aligned_and_bound_to_pack(tmp_path):
    pack, view = _view()
    mapping = {
        "schema_version": "vc.feature-mapping.v1",
        "mapping_id": "rna-map",
        "mapping_version": "1.0.0",
        "aliases": [
            {
                "source": "ENSG00000106546",
                "target": "ENSG00000157764",
            }
        ],
        "aggregates": [],
    }
    mapping_bytes = json.dumps(
        mapping,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    mapping_path = tmp_path / "rna_mapping.json"
    mapping_path.write_bytes(mapping_bytes)
    mapping_ref = {
        "asset_id": "rna-map",
        "path": mapping_path.name,
        "version": "1.0.0",
        "sha256": hashlib.sha256(mapping_bytes).hexdigest(),
    }

    manifest_value = pack.manifest.to_dict()
    manifest_value["assets"].append(
        {
            "id": "rna-map",
            "path": mapping_path.name,
            "media_type": "application/json",
            "sha256": mapping_ref["sha256"],
            "size_bytes": len(mapping_bytes),
        }
    )
    manifest = PackManifest.from_dict(manifest_value)
    (tmp_path / "manifest.yaml").write_text(
        json.dumps(manifest.to_dict()),
        encoding="utf-8",
    )
    pack = RegisteredPack(
        manifest=manifest,
        root=tmp_path,
        fingerprint=manifest.fingerprint(),
    )
    view = replace(
        view,
        manifest=manifest,
        manifest_semantics=_manifest_semantics(manifest),
    )

    feature = _feature_contract("rna")
    feature["feature_ids"][0] = "ENSG00000157764"
    feature["mapping_asset"] = mapping_ref
    rna_slot = _slot_payload("rna")
    rna_slot["feature_contract"] = feature
    rna_slot["feature_contract_fingerprint"] = ModelFeatureContract.from_dict(feature).fingerprint()
    contract = _contract(slots=[rna_slot, _slot_payload("protein")])
    prepared = compile_multiomics_model_input(
        _request(contract, pack),
        pack,
        view,
        contract,
        _adapter(contract),
    )
    report = prepared.model_input.layers[0].alignment_report
    assert tuple(step.operation for step in report.steps) == ("alias",)
    assert report.mapping_asset.model_dump(mode="json") == mapping_ref

    with pytest.raises(MultiOmicsInputError):
        compile_multiomics_model_input(
            _request(contract, pack, targets=("ENSG00000157764",)),
            pack,
            view,
            contract,
            _adapter(contract),
        )

    aggregate_mapping = {
        **mapping,
        "aliases": [],
        "aggregates": [
            {
                "sources": ["ENSG00000106546", "ENSG00000141510"],
                "target": "ENSG00000157764",
                "reducer": "sum",
            }
        ],
    }
    aggregate_bytes = json.dumps(
        aggregate_mapping,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    mapping_path.write_bytes(aggregate_bytes)
    aggregate_ref = {
        **mapping_ref,
        "sha256": hashlib.sha256(aggregate_bytes).hexdigest(),
    }
    aggregate_manifest_value = manifest.to_dict()
    aggregate_manifest_value["assets"][-1].update(
        sha256=aggregate_ref["sha256"],
        size_bytes=len(aggregate_bytes),
    )
    aggregate_manifest = PackManifest.from_dict(aggregate_manifest_value)
    (tmp_path / "manifest.yaml").write_text(
        json.dumps(aggregate_manifest.to_dict()),
        encoding="utf-8",
    )
    aggregate_pack = RegisteredPack(
        manifest=aggregate_manifest,
        root=tmp_path,
        fingerprint=aggregate_manifest.fingerprint(),
    )
    aggregate_view = replace(
        view,
        manifest=aggregate_manifest,
        manifest_semantics=_manifest_semantics(aggregate_manifest),
    )
    aggregate_feature = _feature_contract("rna")
    aggregate_feature["feature_ids"] = ["ENSG00000157764"]
    aggregate_feature["mapping_asset"] = aggregate_ref
    aggregate_slot = _slot_payload("rna")
    aggregate_slot["feature_contract"] = aggregate_feature
    aggregate_slot["feature_contract_fingerprint"] = ModelFeatureContract.from_dict(aggregate_feature).fingerprint()
    aggregate_contract = _contract(slots=[aggregate_slot, _slot_payload("protein")])
    with pytest.raises(MultiOmicsInputError):
        compile_multiomics_model_input(
            _request(aggregate_contract, aggregate_pack),
            aggregate_pack,
            aggregate_view,
            aggregate_contract,
            _adapter(aggregate_contract),
        )

    value = prepared.model_input.to_dict()
    value["pack_manifest"]["assets"] = [value["pack_manifest"]["assets"][0]]
    reduced_manifest = PackManifest.from_dict(value["pack_manifest"])
    value["pack_fingerprint"] = reduced_manifest.fingerprint()
    layers = tuple(MultiOmicsLayerInputV1.from_dict(item) for item in value["layers"])
    value["view_identity_fingerprint"] = _view_identity_fingerprint(
        value["pack_fingerprint"],
        tuple(value["global_observation_ids"]),
        layers,
        value["observation_semantics_fingerprint"],
    )
    with pytest.raises(MultiOmicsInputError):
        MultiOmicsModelInputV1.from_dict(value)


def test_exact_modality_namespace_taxon_and_assembly_bindings_fail_closed():
    pack, view = _view()
    mutations = []

    wrong_modality = _slot_payload("rna")
    wrong_modality["modality_name"] = "transcript abundance"
    mutations.append(_contract(slots=[wrong_modality, _slot_payload("protein")]))

    wrong_namespace = _slot_payload("rna")
    wrong_namespace["feature_contract"]["feature_namespace"]["version"] = "GRCh37"
    wrong_namespace["feature_contract_fingerprint"] = ModelFeatureContract.from_dict(
        wrong_namespace["feature_contract"]
    ).fingerprint()
    mutations.append(_contract(slots=[wrong_namespace, _slot_payload("protein")]))

    taxonomy = _contract_payload()
    taxonomy["taxonomy_id"] = "NCBITaxon:10090"
    assembly = _contract_payload()
    assembly["assembly_accession"] = "GCF_000001635.27"
    for payload in (taxonomy, assembly):
        with pytest.raises(MultiOmicsInputError):
            MultiOmicsInputContractV1.from_dict(payload)

    for contract in mutations:
        with pytest.raises(MultiOmicsInputError):
            compile_multiomics_model_input(_request(contract, pack), pack, view, contract, _adapter(contract))


def test_request_target_metadata_task_output_and_pack_binding_is_exact():
    pack, view = _view()
    contract = _contract()
    bad_requests = [
        _request(contract, pack, input_update={"name": "protein"}),
        _request(contract, pack, input_update={"ontology_id": "EFO:0007937"}),
        _request(contract, pack, input_update={"feature_namespace": "UniProtKB"}),
        _request(contract, pack, task="another-task"),
        _request(contract, pack, outputs=("another-output",)),
    ]
    for request in bad_requests:
        with pytest.raises(MultiOmicsInputError):
            compile_multiomics_model_input(request, pack, view, contract, _adapter(contract))

    bad_pack = RegisteredPack(
        manifest=pack.manifest,
        root=pack.root,
        fingerprint="c" * 64,
    )
    with pytest.raises(MultiOmicsInputError):
        compile_multiomics_model_input(
            _request(contract, bad_pack),
            bad_pack,
            view,
            contract,
            _adapter(contract),
        )

    fallback = compile_multiomics_model_input(
        _request(contract, pack, outputs=()),
        pack,
        view,
        contract,
        _adapter(contract),
    )
    assert fallback.model_input.input_contract.model_fingerprint == _MODEL_FINGERPRINT
    assert fallback.model_input.adapter_fingerprint == _adapter(contract).fingerprint()


def test_request_species_name_and_target_feature_identity_fail_closed():
    pack, view = _view()
    contract = _contract()
    with pytest.raises(MultiOmicsInputError):
        compile_multiomics_model_input(
            _request(contract, pack, targets=("UniProtKB:P04637",)),
            pack,
            view,
            contract,
            _adapter(contract),
        )
    with pytest.raises(MultiOmicsInputError):
        compile_multiomics_model_input(
            _request(
                contract,
                pack,
                perturbation_kind="drug",
                targets=("CHEBI:15365",),
            ),
            pack,
            view,
            contract,
            _adapter(contract),
        )
    with pytest.raises(MultiOmicsInputError):
        compile_multiomics_model_input(
            _request(contract, pack, perturbation_kind="gene_combination"),
            pack,
            view,
            contract,
            _adapter(contract),
        )
    for dose_value, dose_unit in ((1.0, None), (1.0, "count"), (1.0, "h"), (1.0, "TPM")):
        with pytest.raises(MultiOmicsInputError):
            compile_multiomics_model_input(
                _request(
                    contract,
                    pack,
                    dose_value=dose_value,
                    dose_unit=dose_unit,
                ),
                pack,
                view,
                contract,
                _adapter(contract),
            )
    assert compile_multiomics_model_input(
        _request(contract, pack, dose_value=1.0, dose_unit="nM"),
        pack,
        view,
        contract,
        _adapter(contract),
    ).model_input.abstain

    prepared, _, _, _ = _compile()
    value = prepared.model_input.to_dict()
    value["request"]["species"]["scientific_name"] = "Mus musculus"
    value["request_fingerprint"] = _fingerprint(value["request"])
    with pytest.raises(MultiOmicsInputError):
        MultiOmicsModelInputV1.from_dict(value)


@pytest.mark.parametrize(
    "tamper",
    [
        lambda value: value.update(join_fingerprint="f" * 64),
        lambda value: value["layers"][0]["observation_mask"].__setitem__(0, False),
        lambda value: value["layers"][0]["alignment_report"]["target_shape"].__setitem__(0, 99),
    ],
)
def test_serialized_join_mask_and_alignment_tampering_is_rejected(tamper):
    prepared, _, _, _ = _compile(
        contract=_contract(
            join_policy="global",
            missingness_policy="explicit_mask",
        )
    )
    value = deepcopy(prepared.model_input.to_dict())
    tamper(value)
    with pytest.raises(MultiOmicsInputError):
        MultiOmicsModelInputV1.from_dict(value)


def test_serialized_model_input_is_strict_and_self_bound():
    prepared, _, _, _ = _compile()
    value = prepared.model_input.to_dict()
    assert MultiOmicsModelInputV1.from_dict(value) == prepared.model_input

    with pytest.raises(MultiOmicsInputError):
        MultiOmicsModelInputV1.from_dict({**value, "matrix": [[1.0]]})
    wrong_contract = deepcopy(value)
    wrong_contract["input_contract_fingerprint"] = "b" * 64
    with pytest.raises(MultiOmicsInputError):
        MultiOmicsModelInputV1.from_dict(wrong_contract)

    resigned_request = deepcopy(value)
    resigned_request["request"]["task"]["task_type"] = "another-task"
    resigned_request["request_fingerprint"] = _fingerprint(resigned_request["request"])
    with pytest.raises(MultiOmicsInputError):
        MultiOmicsModelInputV1.from_dict(resigned_request)


@pytest.mark.parametrize(
    "adapter_updates",
    [
        {"input_contract_fingerprint": "f" * 64},
        {"task": "another-task"},
        {"outputs": ["another-output"]},
        {"legacy_incomplete": True},
    ],
)
def test_adapter_identity_must_exactly_own_the_joint_contract(adapter_updates):
    pack, view = _view()
    contract = _contract()
    with pytest.raises(MultiOmicsInputError):
        compile_multiomics_model_input(
            _request(contract, pack),
            pack,
            view,
            contract,
            _adapter(contract, **adapter_updates),
        )

    class AdapterSubclass(AdapterIdentity):
        pass

    adapter = AdapterSubclass.from_dict(_adapter(contract).to_dict())
    with pytest.raises(MultiOmicsInputError):
        compile_multiomics_model_input(
            _request(contract, pack),
            pack,
            view,
            contract,
            adapter,
        )


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("broker_agent", "SomeOtherAgent"),
        ("broker_resolution", "registry_evaluated"),
    ],
)
def test_serialized_broker_status_is_closed_to_contract_only_literals(field, replacement):
    prepared, _, _, _ = _compile()
    value = prepared.model_input.to_dict()
    value[field] = replacement
    with pytest.raises(MultiOmicsInputError):
        MultiOmicsModelInputV1.from_dict(value)


@pytest.mark.parametrize(
    "tamper",
    [
        lambda value: value.update(pack_id="another-pack"),
        lambda value: value.update(pack_version="2.0.0"),
        lambda value: value.update(pack_fingerprint="f" * 64),
        lambda value: value["pack_manifest"].update(pack_id="another-pack"),
    ],
)
def test_embedded_pack_manifest_is_independently_self_bound(tamper):
    prepared, _, _, _ = _compile()
    value = prepared.model_input.to_dict()
    tamper(value)
    with pytest.raises(MultiOmicsInputError):
        MultiOmicsModelInputV1.from_dict(value)


def test_view_identity_changes_with_declared_semantics():
    pack, view = _view()
    contract = _contract()
    request = _request(contract, pack)
    first = compile_multiomics_model_input(request, pack, view, contract, _adapter(contract))
    changed = replace(view, doses=((1.0, "nM"),) * 4)
    second = compile_multiomics_model_input(request, pack, changed, contract, _adapter(contract))

    assert first.model_input.view_identity_fingerprint != second.model_input.view_identity_fingerprint
    assert first.model_input.fingerprint() != second.model_input.fingerprint()


def test_view_backing_split_condition_and_perturbation_gates_fail_closed():
    pack, view = _view()
    contract = _contract()
    request = _request(contract, pack)

    class UnbackedMuData:
        isbacked = False

    unbacked_modality = replace(view.modalities[0], _adata=_TinyAnnData(view.modalities[0].matrix))
    unbacked_modality._adata.isbacked = False
    invalid_views = (
        replace(view, _mdata=UnbackedMuData()),
        replace(view, modalities=(unbacked_modality, view.modalities[1])),
        replace(view, split_name="another-split"),
        replace(view, splits=("undeclared",) * 4),
        replace(view, splits=("train", "test", "train", "train")),
        replace(view, conditions=("condition:unknown",) * 4),
        replace(view, perturbation_ids=("perturbation:ahr",) * 4),
        replace(view, matched_control_ids=("condition:perturbed",) * 4),
        replace(view, doses=((0.0, "mol/L"),) * 4),
        replace(view, times=((0.0, "hours"),) * 4),
    )
    for invalid in invalid_views:
        with pytest.raises(MultiOmicsInputError):
            compile_multiomics_model_input(request, pack, invalid, contract, _adapter(contract))


def test_view_identity_is_recomputed_and_actual_storage_must_match():
    prepared, pack, view, contract = _compile()
    value = prepared.model_input.to_dict()
    rename = {item: f"renamed-{index}" for index, item in enumerate(value["global_observation_ids"])}
    value["global_observation_ids"] = [rename[item] for item in value["global_observation_ids"]]
    value["joined_observation_ids"] = [rename[item] for item in value["joined_observation_ids"]]
    for layer in value["layers"]:
        layer["source_observation_ids"] = [rename[item] for item in layer["source_observation_ids"]]
        layer["input_observation_ids"] = [rename[item] for item in layer["input_observation_ids"]]
    layers = tuple(MultiOmicsLayerInputV1.from_dict(item) for item in value["layers"])
    value["join_fingerprint"] = _join_fingerprint(
        contract.join_policy,
        tuple(value["global_observation_ids"]),
        tuple(value["joined_observation_ids"]),
        layers,
    )
    value["missingness_fingerprint"] = _missingness_fingerprint(
        contract.missingness_policy,
        value["join_fingerprint"],
        layers,
    )
    with pytest.raises(MultiOmicsInputError):
        MultiOmicsModelInputV1.from_dict(value)

    sparse = pytest.importorskip("scipy.sparse")
    view.modalities[0]._adata.X = sparse.csr_matrix(view.modalities[0]._adata.X)
    with pytest.raises(MultiOmicsInputError):
        compile_multiomics_model_input(
            _request(contract, pack),
            pack,
            view,
            contract,
            _adapter(contract),
        )


def test_runtime_matrices_are_content_bound_immutable_and_finite():
    prepared, pack, view, contract = _compile()
    matrices = dict(prepared.matrices)
    assert all(not matrix.flags.writeable for matrix in matrices.values())
    with pytest.raises(ValueError):
        matrices["rna"][0, 0] = 99.0

    changed = matrices["rna"].copy()
    changed[0, 0] += 1.0
    with pytest.raises(MultiOmicsInputError):
        PreparedMultiOmicsModelInput(
            prepared.model_input,
            (("rna", changed), ("protein", matrices["protein"])),
        )

    view.modalities[0]._adata.X[1, 0] = np.nan
    with pytest.raises(MultiOmicsInputError):
        compile_multiomics_model_input(
            _request(contract, pack),
            pack,
            view,
            contract,
            _adapter(contract),
        )


def test_matrix_value_changes_change_layer_and_model_identity():
    pack, view = _view()
    contract = _contract()
    request = _request(contract, pack)
    first = compile_multiomics_model_input(request, pack, view, contract, _adapter(contract))
    view.modalities[0]._adata.X[1, 0] += 1.0
    second = compile_multiomics_model_input(request, pack, view, contract, _adapter(contract))

    assert first.model_input.view_identity_fingerprint == second.model_input.view_identity_fingerprint
    assert first.model_input.layers[0].matrix_fingerprint != second.model_input.layers[0].matrix_fingerprint
    assert first.model_input.fingerprint() != second.model_input.fingerprint()


def test_matrix_identity_is_layout_stable_and_sparse_format_explicit():
    sparse = pytest.importorskip("scipy.sparse")
    values = np.array([[1.0, 0.0], [2.0, 3.0]], dtype="<f4")
    assert _matrix_fingerprint(values) == _matrix_fingerprint(np.asfortranarray(values))
    assert _matrix_fingerprint(values) == _matrix_fingerprint(values.astype(">f4"))

    csr = sparse.csr_matrix(values)
    csc = sparse.csc_matrix(values)
    assert _matrix_fingerprint(csr) != _matrix_fingerprint(csc)
    snapshot = _MatrixSnapshot.from_matrix(csr)
    exposed = snapshot.materialize()
    exposed.data = np.array([99.0, 98.0, 97.0], dtype=np.float32)
    assert _matrix_fingerprint(snapshot.materialize()) == _matrix_fingerprint(csr)

    duplicate = sparse.csr_matrix(
        (
            np.array([1.0, 2.0]),
            np.array([0, 0]),
            np.array([0, 2, 2]),
        ),
        shape=(2, 2),
    )
    with pytest.raises(MultiOmicsInputError):
        _matrix_fingerprint(duplicate)

    pack, view = _view()
    contract = _contract()
    view.modalities[0]._adata.X = sparse.csr_matrix(view.modalities[0]._adata.X)
    sparse_rna = replace(view.modalities[0], matrix_format="csr")
    sparse_view = replace(
        view,
        modalities=(sparse_rna, view.modalities[1]),
    )
    prepared = compile_multiomics_model_input(
        _request(contract, pack),
        pack,
        sparse_view,
        contract,
        _adapter(contract),
    )
    exposed = dict(prepared.matrices)["rna"]
    exposed.data = np.full(exposed.nnz, 99.0, dtype=exposed.dtype)
    replayed = dict(prepared.matrices)["rna"]
    assert _matrix_fingerprint(replayed) == prepared.model_input.layers[0].matrix_fingerprint

    value = prepared.model_input.to_dict()
    value["layers"][0]["source_matrix_format"] = "csc"
    layers = tuple(MultiOmicsLayerInputV1.from_dict(item) for item in value["layers"])
    value["view_identity_fingerprint"] = _view_identity_fingerprint(
        value["pack_fingerprint"],
        tuple(value["global_observation_ids"]),
        layers,
        value["observation_semantics_fingerprint"],
    )
    resigned = MultiOmicsModelInputV1.from_dict(value)
    with pytest.raises(MultiOmicsInputError):
        PreparedMultiOmicsModelInput(resigned, prepared.matrices)


@pytest.mark.parametrize(
    "tamper",
    [
        lambda report, layer: (
            report["source_feature_ids"].append("forged-feature"),
            report["source_shape"].__setitem__(1, 3),
            layer["source_shape"].__setitem__(1, 3),
        ),
        lambda report, layer: report.update(mapping_asset="mapping.json"),
        lambda report, layer: report["steps"].append(
            {
                "operation": "alias",
                "source_ids": [report["source_feature_ids"][0]],
                "target_ids": [report["target_feature_ids"][0]],
                "reducer": None,
                "value": None,
            }
        ),
    ],
)
def test_coherently_resigned_alignment_tampering_is_rejected(tamper):
    prepared, _, _, _ = _compile()
    value = prepared.model_input.to_dict()
    layer = value["layers"][0]
    report = layer["alignment_report"]
    tamper(report, layer)
    layer["alignment_report_fingerprint"] = _fingerprint(report)
    with pytest.raises(MultiOmicsInputError):
        MultiOmicsModelInputV1.from_dict(value)


def test_model_construct_cannot_bypass_execution_literals_or_nested_exact_types():
    prepared, _, _, contract = _compile()
    forged = MultiOmicsModelInputV1.model_construct(**{**prepared.model_input.__dict__, "executable": True})
    with pytest.raises(MultiOmicsInputError):
        forged.to_dict()
    with pytest.raises(MultiOmicsInputError):
        PreparedMultiOmicsModelInput(
            forged,
            prepared.matrices,
        )

    class SlotSubclass(MultiOmicsModalitySlotV1):
        pass

    nested = SlotSubclass.from_dict(contract.slots[0].to_dict())
    forged_contract = MultiOmicsInputContractV1.model_construct(
        **{**contract.__dict__, "slots": (nested, contract.slots[1])}
    )
    with pytest.raises(MultiOmicsInputError):
        forged_contract.to_dict()


def test_nested_request_subtypes_and_non_json_mappings_are_rejected():
    pack, view = _view()
    contract = _contract()
    request = _request(contract, pack)

    class SpeciesSubclass(SpeciesRef):
        pass

    species = SpeciesSubclass.model_construct(**request.species.__dict__)
    forged_request = VirtualCellRequestV2.model_construct(**{**request.__dict__, "species": species})
    with pytest.raises(MultiOmicsInputError):
        compile_multiomics_model_input(
            forged_request,
            pack,
            view,
            contract,
            _adapter(contract),
        )

    prepared, _, _, _ = _compile()
    value = prepared.model_input.to_dict()
    value["request"]["metadata"]["opaque"] = object()
    with pytest.raises(MultiOmicsInputError):
        MultiOmicsModelInputV1.from_dict(value)
