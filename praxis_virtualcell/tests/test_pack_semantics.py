"""P4 contracts for the offline VirtualCellPack semantic layer."""

from __future__ import annotations

import builtins
import hashlib
import socket
from copy import deepcopy
from pathlib import Path

import anndata
import numpy as np
import pandas as pd
import pytest
import yaml
from scipy import sparse

from praxis_virtualcell.data_packs import registry as registry_module
from praxis_virtualcell.data_packs.anndata_adapter import load_anndata_view
from praxis_virtualcell.data_packs.errors import (
    OmicsDataError,
    OmicsDependencyError,
    PackManifestError,
)
from praxis_virtualcell.data_packs.registry import PackRegistry
from praxis_virtualcell.data_packs.validator import validate_pack

_FIXTURES = Path(__file__).parent / "fixtures" / "pack_semantics"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fixture(name: str) -> dict:
    return yaml.safe_load((_FIXTURES / f"{name}.yaml").read_text(encoding="utf-8"))


def _write_pack(root: Path, source: dict) -> Path:
    raw = deepcopy(source)
    observations = raw.pop("fixture_observations")
    features = raw.pop("fixture_features")
    root.mkdir()

    matrix = sparse.csr_matrix(
        np.arange(1, len(observations) * len(features) + 1, dtype=np.float32).reshape(
            len(observations),
            len(features),
        )
    )
    adata = anndata.AnnData(
        X=matrix,
        obs=pd.DataFrame(observations).set_index("obs_name"),
        var=pd.DataFrame(features).set_index("id"),
    )
    asset = root / "tiny.h5ad"
    adata.write_h5ad(asset)

    raw["assets"] = [
        {
            "id": "expression",
            "path": "tiny.h5ad",
            "media_type": "application/vnd.anndata+hdf5",
            "sha256": _sha256(asset),
            "size_bytes": asset.stat().st_size,
        }
    ]
    raw["matrix"] = {
        "asset": "expression",
        "location": "X",
        "shape": [len(observations), len(features)],
    }
    (root / "manifest.yaml").write_text(
        yaml.safe_dump(raw, sort_keys=False),
        encoding="utf-8",
    )
    return root


@pytest.mark.parametrize(
    "name,taxonomy_id,assembly_accession,feature_prefix",
    [
        ("human", "NCBITaxon:9606", "GCF_000001405.40", "ENSG"),
        ("mouse", "NCBITaxon:10090", "GCF_000001635.27", "ENSMUSG"),
        ("bacteria", "NCBITaxon:562", "GCF_000005845.2", "NCBIGene:"),
    ],
)
def test_human_mouse_and_bacteria_semantics_are_exposed_without_rewriting(
    tmp_path,
    name,
    taxonomy_id,
    assembly_accession,
    feature_prefix,
):
    source = _fixture(name)
    pack = _write_pack(tmp_path / name, source)

    with load_anndata_view(pack) as view:
        assert view.taxonomy_id == taxonomy_id
        assert view.assembly_accession == assembly_accession
        assert all(value.startswith(feature_prefix) for value in view.feature_ids)
        assert view.feature_ids == tuple(item["id"] for item in source["fixture_features"])
        assert view.feature_symbols == tuple(
            item["feature_symbol"] for item in source["fixture_features"]
        )
        assert len(view.cell_identity_ids) == 4
        assert all(view.cell_state_ids)
        assert all(view.cell_context_ids)
        assert len(view.condition_ids) == 4
        assert len(view.perturbation_ids) == 4
        assert len(view.matched_control_ids) == 4
        assert view.doses == ((0.0, "1"), (1.0, "1"), (0.0, "1"), (1.0, "1"))
        assert view.times == ((24.0, "h"),) * 4
        assert view.split_name == "target-holdout-v1"


def test_feature_symbols_are_display_only_and_need_not_be_unique(tmp_path):
    source = _fixture("human")
    source["fixture_features"][1]["feature_symbol"] = source["fixture_features"][0][
        "feature_symbol"
    ]
    pack = _write_pack(tmp_path / "pack", source)

    with load_anndata_view(pack) as view:
        assert view.feature_symbols == ("AHR", "AHR")
        assert view.feature_ids == ("ENSG00000106546", "ENSG00000141510")


def test_var_names_must_be_canonical_feature_ids(tmp_path):
    source = _fixture("human")
    source["fixture_features"][0]["id"] = "AHR"
    source["perturbations"]["values"][1]["targets"] = ["AHR"]
    pack = _write_pack(tmp_path / "pack", source)

    with pytest.raises(OmicsDataError, match="canonical feature"):
        load_anndata_view(pack)


def test_short_ensembl_like_ids_are_not_canonical(tmp_path):
    source = _fixture("human")
    source["fixture_features"][0]["id"] = "ENSG1"
    source["perturbations"]["values"][1]["targets"] = ["ENSG1"]
    pack = _write_pack(tmp_path / "pack", source)

    with pytest.raises(OmicsDataError, match="canonical feature"):
        load_anndata_view(pack)


def test_perturbation_targets_are_exact_feature_foreign_keys_without_ortholog_projection(
    tmp_path,
):
    source = _fixture("mouse")
    source["perturbations"]["values"][1]["targets"] = ["ENSG00000141510"]
    pack = _write_pack(tmp_path / "pack", source)

    with pytest.raises(OmicsDataError, match="unknown target"):
        load_anndata_view(pack)


@pytest.mark.parametrize(
    "field,value,match",
    [
        ("condition_id", "condition:not-declared", "unknown condition"),
        ("perturbation_id", "perturbation:not-declared", "unknown perturbation"),
    ],
)
def test_observation_condition_and_perturbation_values_are_foreign_keys(
    tmp_path,
    field,
    value,
    match,
):
    source = _fixture("human")
    source["fixture_observations"][1][field] = value
    pack = _write_pack(tmp_path / "pack", source)

    with pytest.raises(OmicsDataError, match=match):
        load_anndata_view(pack)


@pytest.mark.parametrize(
    "mutation,match",
    [
        (
            lambda source: source["fixture_observations"][1].update(
                matched_control_id="condition:missing"
            ),
            "matched control",
        ),
        (
            lambda source: source["fixture_observations"][1].update(
                matched_control_id="condition:human-test-perturbed"
            ),
            "control perturbation",
        ),
        (
            lambda source: source["fixture_observations"][1].update(
                tissue_id="UBERON:0000955"
            ),
            "control context",
        ),
    ],
)
def test_control_matching_fails_closed(tmp_path, mutation, match):
    source = _fixture("human")
    mutation(source)
    pack = _write_pack(tmp_path / "pack", source)

    with pytest.raises(OmicsDataError, match=match):
        load_anndata_view(pack)


@pytest.mark.parametrize(
    "field,value,match",
    [
        ("dose_unit", "furlong", "dose unit"),
        ("time_unit", "fortnight", "time unit"),
        ("dose_value", -1, "dose value"),
        ("time_value", float("nan"), "time value"),
    ],
)
def test_dose_and_time_require_explicit_supported_units_and_finite_values(
    tmp_path,
    field,
    value,
    match,
):
    source = _fixture("human")
    source["fixture_observations"][1][field] = value
    pack = _write_pack(tmp_path / "pack", source)

    with pytest.raises(OmicsDataError, match=match):
        load_anndata_view(pack)


def test_named_split_leakage_guard_rejects_a_group_seen_in_two_partitions(tmp_path):
    source = _fixture("human")
    source["fixture_observations"][2]["donor_id"] = source["fixture_observations"][0][
        "donor_id"
    ]
    pack = _write_pack(tmp_path / "pack", source)

    with pytest.raises(OmicsDataError, match="leakage.*donor_id"):
        load_anndata_view(
            pack,
            observation_ids=["human-1", "human-2"],
        )


def test_target_holdout_rejects_the_same_feature_behind_different_perturbation_ids(
    tmp_path,
):
    source = _fixture("human")
    source["perturbations"]["values"][3]["targets"] = source["perturbations"]["values"][1][
        "targets"
    ]
    pack = _write_pack(tmp_path / "pack", source)

    with pytest.raises(OmicsDataError, match="leakage.*target_ids"):
        load_anndata_view(pack)


@pytest.mark.parametrize(
    "mutation,match",
    [
        (lambda source: source["split"].pop("name"), "split.name"),
        (lambda source: source["split"].update(leakage_guard=[]), "leakage"),
        (
            lambda source: source["cell_semantics"].update(
                state=[source["cell_semantics"]["identity"]]
            ),
            "identity, state, and context",
        ),
        (lambda source: source.update(condition=None), "legacy condition"),
        (
            lambda source: source["feature_namespace"].update(name="NCBIGene"),
            "feature_namespace",
        ),
        (
            lambda source: source["assembly"].update(accession="GRCh38"),
            "assembly.accession",
        ),
    ],
)
def test_p4_manifest_requires_named_split_guard_and_assembly_accession(
    tmp_path,
    mutation,
    match,
):
    source = _fixture("human")
    mutation(source)
    pack = _write_pack(tmp_path / "pack", source)

    with pytest.raises(PackManifestError, match=match):
        validate_pack(pack)


def test_local_cell_terms_require_an_explicit_semantic_role(tmp_path):
    source = _fixture("human")
    source["cell_semantics"]["local_terms"][0].pop("role")
    pack = _write_pack(tmp_path / "pack", source)

    with pytest.raises(PackManifestError, match="role"):
        validate_pack(pack)


def test_undefined_local_cell_curie_fails_closed(tmp_path):
    source = _fixture("bacteria")
    source["fixture_observations"][0]["cell_identity_id"] = "UNKNOWN:cell"
    pack = _write_pack(tmp_path / "pack", source)

    with pytest.raises(OmicsDataError, match="undefined local CURIE"):
        load_anndata_view(pack)


@pytest.mark.parametrize(
    "field,value",
    [
        ("cell_identity_id", "UBERON:0000178"),
        ("cell_state_id", "CL:0000540"),
        ("tissue_id", "CVCL_0004"),
    ],
)
def test_standard_cell_ids_are_bound_to_their_semantic_role(tmp_path, field, value):
    source = _fixture("human")
    for observation in source["fixture_observations"]:
        observation[field] = value
    pack = _write_pack(tmp_path / "pack", source)

    with pytest.raises(OmicsDataError, match="semantic role"):
        load_anndata_view(pack)


def test_nonstandard_cellosaurus_curie_fails_closed(tmp_path):
    source = _fixture("human")
    for observation in source["fixture_observations"]:
        observation["cell_identity_id"] = "cellosaurus:0004"
    pack = _write_pack(tmp_path / "pack", source)

    with pytest.raises(OmicsDataError, match="undefined local CURIE"):
        load_anndata_view(pack)


def test_local_cell_terms_are_bound_to_their_declared_semantic_role(tmp_path):
    source = _fixture("human")
    for observation in source["fixture_observations"]:
        observation["cell_identity_id"] = "VCSTATE:baseline"
    pack = _write_pack(tmp_path / "pack", source)

    with pytest.raises(OmicsDataError, match="semantic role"):
        load_anndata_view(pack)


def test_canonical_key_includes_cell_state_semantics(tmp_path):
    first_source = _fixture("human")
    second_source = _fixture("human")
    second_source["cell_semantics"]["local_terms"][0]["id"] = "VCSTATE:alternate"
    for observation in second_source["fixture_observations"]:
        observation["cell_state_id"] = "VCSTATE:alternate"

    first_pack = _write_pack(tmp_path / "first", first_source)
    second_pack = _write_pack(tmp_path / "second", second_source)

    with (
        load_anndata_view(first_pack) as first,
        load_anndata_view(second_pack) as second,
    ):
        assert first.cell_state_ids != second.cell_state_ids
        assert first.canonical_key != second.canonical_key


def test_canonical_key_includes_perturbation_target_mapping(tmp_path):
    first_source = _fixture("human")
    second_source = _fixture("human")
    train_targets = second_source["perturbations"]["values"][1]["targets"]
    test_targets = second_source["perturbations"]["values"][3]["targets"]
    second_source["perturbations"]["values"][1]["targets"] = test_targets
    second_source["perturbations"]["values"][3]["targets"] = train_targets

    first_pack = _write_pack(tmp_path / "first", first_source)
    second_pack = _write_pack(tmp_path / "second", second_source)

    with (
        load_anndata_view(first_pack) as first,
        load_anndata_view(second_pack) as second,
    ):
        assert first.canonical_key != second.canonical_key


@pytest.mark.parametrize(
    "difference",
    [
        "modality",
        "feature_namespace_version",
        "local_term_definition",
        "leakage_guard",
        "unused_perturbation",
    ],
)
def test_canonical_key_includes_pack_level_scientific_semantics(tmp_path, difference):
    first_source = _fixture("human")
    second_source = _fixture("human")
    if difference == "modality":
        second_source["modality"] = {"name": "ATAC", "ontology_id": "EFO:0007045"}
    elif difference == "feature_namespace_version":
        second_source["feature_namespace"]["version"] = "Ensembl-999"
    elif difference == "local_term_definition":
        second_source["cell_semantics"]["local_terms"][0][
            "definition"
        ] = "A scientifically different state definition."
    elif difference == "leakage_guard":
        second_source["split"]["leakage_guard"].remove("donor_id")
    else:
        second_source["perturbations"]["values"].append(
            {
                "id": "perturbation:unused",
                "kind": "genetic",
                "targets": ["ENSG00000106546"],
            }
        )

    first_pack = _write_pack(tmp_path / "first", first_source)
    second_pack = _write_pack(tmp_path / "second", second_source)

    with (
        load_anndata_view(first_pack) as first,
        load_anndata_view(second_pack) as second,
    ):
        assert first.canonical_key != second.canonical_key


def test_canonical_key_covers_all_p4_scientific_metadata(tmp_path):
    pack = _write_pack(tmp_path / "pack", _fixture("human"))

    with load_anndata_view(pack) as view:
        assert view.canonical_key == (
            view.taxonomy_id,
            view.assembly_accession,
            view.observation_ids,
            view.feature_ids,
            view.conditions,
            view.splits,
            view.cell_identity_ids,
            view.cell_state_ids,
            view.cell_context_ids,
            view.perturbation_ids,
            view.perturbation_kinds,
            view.perturbation_targets,
            view.matched_control_ids,
            view.doses,
            view.times,
            view.split_name,
            view.shape,
            view.matrix_location,
            view.matrix_format,
            view.manifest_semantics,
        )


def test_registry_rejects_v02_pack_with_invalid_h5ad_semantics(tmp_path):
    source = _fixture("human")
    source["fixture_observations"][1]["condition_id"] = "condition:not-declared"
    pack = _write_pack(tmp_path / "pack", source)

    with pytest.raises(OmicsDataError, match="unknown condition"):
        PackRegistry().register(pack)


def test_registry_registers_v02_only_after_semantic_validation(tmp_path):
    pack = _write_pack(tmp_path / "pack", _fixture("human"))
    registry = PackRegistry()

    manifest = registry.register(pack)

    assert manifest.schema_version == "vc.pack.v0.2"
    assert registry.get(manifest.pack_id, manifest.pack_version) is manifest


def test_registry_cannot_switch_v01_candidate_to_invalid_v02(tmp_path, monkeypatch):
    source = _fixture("human")
    source["fixture_observations"][1]["condition_id"] = "condition:not-declared"
    pack = _write_pack(tmp_path / "pack", source)
    manifest_path = pack / "manifest.yaml"
    invalid_v02 = manifest_path.read_text(encoding="utf-8")

    v01_candidate = yaml.safe_load(invalid_v02)
    v01_candidate["schema_version"] = "vc.pack.v0.1"
    for field in (
        "feature_semantics",
        "cell_semantics",
        "conditions",
        "perturbations",
    ):
        v01_candidate.pop(field)
    v01_candidate["condition"] = {
        "field": "condition_id",
        "values": ["placeholder"],
        "control": "placeholder",
    }
    v01_candidate["split"].pop("name")
    v01_candidate["split"].pop("leakage_guard")
    manifest_path.write_text(
        yaml.safe_dump(v01_candidate, sort_keys=False),
        encoding="utf-8",
    )

    real_validate = registry_module.validate_pack

    def switch_to_v02(pack_root):
        manifest_path.write_text(invalid_v02, encoding="utf-8")
        return real_validate(pack_root)

    monkeypatch.setattr(registry_module, "validate_pack", switch_to_v02)
    registry = PackRegistry()

    with pytest.raises(OmicsDataError, match="unknown condition"):
        registry.register(pack)
    assert registry.keys() == []


def test_registry_does_not_fallback_when_v02_omics_dependency_is_unavailable(
    tmp_path,
    monkeypatch,
):
    pack = _write_pack(tmp_path / "pack", _fixture("human"))
    real_import = builtins.__import__

    def import_without_anndata(name, *args, **kwargs):
        if name == "anndata":
            raise ImportError("blocked optional dependency")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", import_without_anndata)

    with pytest.raises(OmicsDependencyError, match="omics"):
        PackRegistry().register(pack)


def test_semantic_validation_has_no_online_ontology_dependency(tmp_path, monkeypatch):
    pack = _write_pack(tmp_path / "pack", _fixture("human"))

    def deny_network(*args, **kwargs):
        raise AssertionError("semantic validation attempted network access")

    monkeypatch.setattr(socket, "create_connection", deny_network)

    with load_anndata_view(pack) as view:
        assert view.taxonomy_id == "NCBITaxon:9606"
