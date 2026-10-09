"""P5 contracts for H5MU multi-omics loading and explicit feature alignment."""

from __future__ import annotations

import builtins
import hashlib
import json
import shutil
import subprocess
import sys
import tomllib
from copy import deepcopy
from pathlib import Path

import anndata
import mudata
import numpy as np
import pandas as pd
import pytest
import yaml
from scipy import sparse

from praxis_virtualcell.data_packs.errors import (
    FeatureAlignmentError,
    OmicsDataError,
    OmicsDependencyError,
    OmicsMappingError,
    PackManifestError,
)
from praxis_virtualcell.data_packs.feature_alignment import (
    AlignmentReport,
    ModelFeatureContract,
    align_features,
)
from praxis_virtualcell.data_packs.mudata_adapter import load_mudata_view
from praxis_virtualcell.data_packs.registry import PackRegistry
from praxis_virtualcell.data_packs.validator import validate_pack

_FIXTURES = Path(__file__).parent / "fixtures" / "mudata"
_P2_FIXTURE = Path(__file__).parent / "fixtures" / "data_packs" / "valid_tiny"
_P2_FINGERPRINT = "5973dc852f8d7d0cb73ce333d3f99beb2f94c66b7cdf4e6d2e7fc4c422651192"
_FILLED_FEATURE = "ENSG00000136997"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fixture() -> dict:
    return yaml.safe_load((_FIXTURES / "rna_protein.yaml").read_text(encoding="utf-8"))


def _write_pack(
    root: Path,
    *,
    pairing: str | None = None,
    modality_observations: dict[str, list[str]] | None = None,
    modality_feature_ids: dict[str, list[str]] | None = None,
) -> Path:
    raw = deepcopy(_fixture())
    observations = raw.pop("fixture_observations")
    modality_sources = raw.pop("fixture_modalities")
    if pairing is not None:
        raw["multiomics"]["observation_pairing"] = pairing
    if pairing == "paired" and modality_observations is None:
        all_ids = [row["obs_name"] for row in observations]
        modality_observations = {key: all_ids for key in modality_sources}
    modality_observations = modality_observations or {
        key: value["observation_ids"] for key, value in modality_sources.items()
    }

    root.mkdir()
    modalities = {}
    for offset, (key, source) in enumerate(modality_sources.items()):
        obs_ids = modality_observations[key]
        features = source["features"]
        if modality_feature_ids is not None and key in modality_feature_ids:
            replacements = modality_feature_ids[key]
            if len(replacements) != len(features):
                raise ValueError("feature replacement count must preserve fixture shape")
            for feature, replacement in zip(features, replacements, strict=True):
                feature["id"] = replacement
        matrix = np.arange(
            1 + offset * 100,
            1 + offset * 100 + len(obs_ids) * len(features),
            dtype=np.float32,
        ).reshape(len(obs_ids), len(features))
        modalities[key] = anndata.AnnData(
            X=sparse.csr_matrix(matrix),
            obs=pd.DataFrame(index=obs_ids),
            var=pd.DataFrame(features).set_index("id"),
        )
        declared = next(
            value for value in raw["multiomics"]["modalities"] if value["key"] == key
        )
        declared["shape"] = [len(obs_ids), len(features)]

    global_obs = pd.DataFrame(observations).set_index("obs_name")
    global_obs.index.name = None
    h5mu_path = root / "tiny.h5mu"
    with mudata.set_options(pull_on_update=False):
        mdata = mudata.MuData(modalities)
        mdata.obs = global_obs.loc[list(mdata.obs_names)].copy()
        mdata.write_h5mu(h5mu_path)

    mapping_path = root / "rna_mapping.json"
    shutil.copy2(_FIXTURES / "rna_mapping.json", mapping_path)
    raw["assets"] = [
        {
            "id": "multiomics",
            "path": "tiny.h5mu",
            "media_type": "application/vnd.mudata+hdf5",
            "sha256": _sha256(h5mu_path),
            "size_bytes": h5mu_path.stat().st_size,
        },
        {
            "id": "rna-mapping",
            "path": "rna_mapping.json",
            "media_type": "application/json",
            "sha256": _sha256(mapping_path),
            "size_bytes": mapping_path.stat().st_size,
        },
    ]
    (root / "manifest.yaml").write_text(
        yaml.safe_dump(raw, sort_keys=False),
        encoding="utf-8",
    )
    return root


def _rewrite_manifest(pack: Path, update) -> None:
    path = pack / "manifest.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    update(raw)
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")


def _refresh_mapping_asset(pack: Path) -> None:
    mapping_path = pack / "rna_mapping.json"

    def update(raw):
        asset = next(item for item in raw["assets"] if item["id"] == "rna-mapping")
        asset["sha256"] = _sha256(mapping_path)
        asset["size_bytes"] = mapping_path.stat().st_size

    _rewrite_manifest(pack, update)


def _mapping_reference(pack: Path) -> dict:
    raw = json.loads((pack / "rna_mapping.json").read_text(encoding="utf-8"))
    return {
        "asset_id": "rna-mapping",
        "path": "rna_mapping.json",
        "version": raw["mapping_version"],
        "sha256": _sha256(pack / "rna_mapping.json"),
    }


def _contract(
    feature_ids: list[str],
    *,
    reorder: bool = False,
    drop: list[str] | None = None,
    fill: list[dict] | None = None,
    mapping_asset: dict | None = None,
    taxonomy_id: str = "NCBITaxon:9606",
    namespace_version: str = "GRCh38",
) -> ModelFeatureContract:
    return ModelFeatureContract.from_dict(
        {
            "schema_version": "vc.model-feature-contract.v1",
            "model_id": "tiny-rna-model",
            "model_version": "1.0.0",
            "taxonomy_id": taxonomy_id,
            "assembly_accession": "GCF_000001405.40",
            "modality": "rna",
            "feature_namespace": {
                "name": "EnsemblGene",
                "version": namespace_version,
            },
            "feature_id_format": "ensembl_gene",
            "feature_ids": feature_ids,
            "reorder": reorder,
            "drop": drop or [],
            "fill": fill or [],
            **({} if mapping_asset is None else {"mapping_asset": mapping_asset}),
        }
    )


def _dense(matrix) -> np.ndarray:
    if hasattr(matrix, "to_memory"):
        matrix = matrix.to_memory()
    return matrix.toarray() if sparse.issparse(matrix) else np.asarray(matrix)


def test_partial_rna_protein_pack_is_backed_and_never_pads_missing_observations(
    tmp_path,
):
    pack = _write_pack(tmp_path / "pack")

    with load_mudata_view(
        pack,
        observation_ids=["cell-1", "cell-4"],
    ) as view:
        assert view.manifest.schema_version == "vc.pack.v0.3"
        assert view.is_backed
        assert view.observation_pairing == "partially_paired"
        assert view.observation_ids == ("cell-1", "cell-4")
        assert view.shared_observation_ids == ()
        assert view.modality("rna").observation_ids == ("cell-1",)
        assert view.modality("protein").observation_ids == ("cell-4",)
        assert view.modality("rna").shape == (1, 5)
        assert view.modality("protein").shape == (1, 2)
        assert view.modality("rna").matrix_format == "csr"
        assert view.modality("protein").matrix_format == "csr"


def test_paired_pack_requires_identical_observations_in_identical_order(tmp_path):
    pack = _write_pack(tmp_path / "pack", pairing="paired")

    with load_mudata_view(pack) as view:
        assert view.observation_pairing == "paired"
        assert view.shared_observation_ids == view.observation_ids
        assert view.modality("rna").observation_ids == view.observation_ids
        assert view.modality("protein").observation_ids == view.observation_ids


@pytest.mark.parametrize(
    "accession",
    [
        "UniProtKB:A2BC19",
        "UniProtKB:A0A023GPI8",
    ],
)
def test_uniprot_six_and_ten_character_accessions_are_canonical(
    tmp_path,
    accession,
):
    pack = _write_pack(
        tmp_path / "pack",
        modality_feature_ids={
            "protein": [accession, "UniProtKB:P04637"],
        },
    )

    with load_mudata_view(pack) as view:
        assert view.modality("protein").feature_ids[0] == accession


def test_noncanonical_uniprot_accession_is_rejected(tmp_path):
    pack = _write_pack(
        tmp_path / "pack",
        modality_feature_ids={
            "protein": ["UniProtKB:A00000", "UniProtKB:P04637"],
        },
    )

    with pytest.raises(OmicsDataError, match="canonical feature"):
        load_mudata_view(pack)


def test_declared_paired_pack_rejects_partial_membership(tmp_path):
    pack = _write_pack(tmp_path / "pack")
    _rewrite_manifest(
        pack,
        lambda raw: raw["multiomics"].update(observation_pairing="paired"),
    )

    with pytest.raises(OmicsDataError, match="paired.*identical"):
        load_mudata_view(pack)


def test_partially_paired_pack_requires_real_overlap_and_real_missingness(tmp_path):
    disjoint = _write_pack(
        tmp_path / "disjoint",
        modality_observations={
            "rna": ["cell-1", "cell-2"],
            "protein": ["cell-3", "cell-4"],
        },
    )
    fully_paired = _write_pack(tmp_path / "fully-paired", pairing="paired")
    _rewrite_manifest(
        fully_paired,
        lambda raw: raw["multiomics"].update(
            observation_pairing="partially_paired"
        ),
    )

    with pytest.raises(OmicsDataError, match="partially_paired.*overlap"):
        load_mudata_view(disjoint)
    with pytest.raises(OmicsDataError, match="partially_paired.*missing"):
        load_mudata_view(fully_paired)


def test_loader_uses_public_read_only_h5mu_api_without_annotation_pull(
    tmp_path,
    monkeypatch,
):
    pack = _write_pack(tmp_path / "pack")
    events = []
    real_read = mudata.read_h5mu
    real_options = mudata.set_options

    def tracked_read(*args, **kwargs):
        events.append(("read_h5mu", kwargs))
        return real_read(*args, **kwargs)

    def tracked_options(**kwargs):
        events.append(("set_options", kwargs))
        return real_options(**kwargs)

    monkeypatch.setattr(mudata, "read_h5mu", tracked_read)
    monkeypatch.setattr(mudata, "set_options", tracked_options)

    with load_mudata_view(pack):
        pass

    assert events == [
        ("set_options", {"pull_on_update": False}),
        ("read_h5mu", {"backed": "r"}),
    ]


def test_loader_fails_closed_when_optional_mudata_is_unavailable(
    tmp_path,
    monkeypatch,
):
    pack = _write_pack(tmp_path / "pack")
    real_import = builtins.__import__

    def import_without_mudata(name, *args, **kwargs):
        if name == "mudata":
            raise ImportError("blocked optional dependency")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", import_without_mudata)

    with pytest.raises(OmicsDependencyError, match="omics"):
        load_mudata_view(pack)


@pytest.mark.parametrize(
    "mutation,match",
    [
        (
            lambda raw: raw["multiomics"]["modalities"].reverse(),
            "modality order",
        ),
        (
            lambda raw: raw["multiomics"]["modalities"][0].update(shape=[99, 5]),
            "shape",
        ),
        (
            lambda raw: raw["multiomics"].update(asset="rna-mapping"),
            "H5MU media type",
        ),
        (
            lambda raw: raw["perturbations"].update(target_modality="missing"),
            "target_modality",
        ),
    ],
)
def test_h5mu_manifest_and_content_mappings_fail_closed(
    tmp_path,
    mutation,
    match,
):
    pack = _write_pack(tmp_path / "pack")
    _rewrite_manifest(pack, mutation)

    with pytest.raises(
        (PackManifestError, OmicsMappingError, OmicsDataError),
        match=match,
    ):
        load_mudata_view(pack)


def test_registry_requires_full_v03_h5mu_semantic_validation(tmp_path):
    pack = _write_pack(tmp_path / "pack")
    _rewrite_manifest(
        pack,
        lambda raw: raw["multiomics"]["modalities"][0].update(shape=[99, 5]),
    )

    with pytest.raises(OmicsDataError, match="shape"):
        PackRegistry().register(pack)


def test_v03_does_not_change_the_frozen_v01_fingerprint():
    assert validate_pack(_P2_FIXTURE).fingerprint() == _P2_FINGERPRINT


def test_strict_alignment_accepts_only_an_exact_contract(tmp_path):
    pack = _write_pack(tmp_path / "pack")

    with load_mudata_view(pack) as view:
        rna = view.modality("rna")
        contract = _contract(list(rna.feature_ids))
        aligned = align_features(rna, contract, mapping_root=pack)

        assert aligned.feature_ids == rna.feature_ids
        np.testing.assert_array_equal(_dense(aligned.matrix), _dense(rna.matrix))
        assert isinstance(aligned.report, AlignmentReport)
        assert aligned.report.steps == ()
        assert aligned.report.contract_fingerprint == contract.fingerprint()


def test_model_contract_rejects_feature_ids_outside_declared_format():
    with pytest.raises(FeatureAlignmentError, match="canonical.*feature_ids"):
        _contract(["AHR"])


def test_model_contract_rejects_fill_values_too_large_for_finite_float():
    with pytest.raises(FeatureAlignmentError, match="finite"):
        _contract(
            [_FILLED_FEATURE],
            fill=[{"feature_id": _FILLED_FEATURE, "value": 10**10000}],
        )


@pytest.mark.parametrize(
    "contract_factory,match",
    [
        (
            lambda ids: _contract(list(reversed(ids))),
            "reorder",
        ),
        (
            lambda ids: _contract(["ENSG00000106546", *ids[1:]]),
            "alias|aggregate",
        ),
        (
            lambda ids: _contract(list(ids[:-1])),
            "drop",
        ),
        (
            lambda ids: _contract([*ids, _FILLED_FEATURE]),
            "fill",
        ),
        (
            lambda ids: _contract(
                ["ENSG00000106546.1", "ENSG00000141510", *ids[3:]]
            ),
            "drop|aggregate",
        ),
    ],
)
def test_reorder_alias_drop_fill_and_aggregate_never_happen_implicitly(
    tmp_path,
    contract_factory,
    match,
):
    pack = _write_pack(tmp_path / "pack")

    with load_mudata_view(pack) as view:
        rna = view.modality("rna")
        with pytest.raises(FeatureAlignmentError, match=match):
            align_features(
                rna,
                contract_factory(rna.feature_ids),
                mapping_root=pack,
            )


def test_all_explicit_alignment_operations_transform_data_and_enter_provenance(
    tmp_path,
):
    pack = _write_pack(tmp_path / "pack")
    target_ids = [
        "ENSG00000157764",
        "ENSG00000106546",
        "ENSG00000141510",
        _FILLED_FEATURE,
    ]
    contract = _contract(
        target_ids,
        reorder=True,
        drop=["ENSG00000171862"],
        fill=[{"feature_id": _FILLED_FEATURE, "value": 0.5}],
        mapping_asset=_mapping_reference(pack),
    )

    with load_mudata_view(pack) as view:
        rna = view.modality("rna")
        source = _dense(rna.matrix)
        aligned = align_features(rna, contract, mapping_root=pack)

    expected = np.column_stack(
        [
            source[:, 3],
            source[:, 0],
            source[:, [1, 2]].mean(axis=1),
            np.full(source.shape[0], 0.5),
        ]
    )
    np.testing.assert_allclose(_dense(aligned.matrix), expected)
    assert aligned.feature_ids == tuple(target_ids)
    assert tuple(step.operation for step in aligned.report.steps) == (
        "alias",
        "aggregate",
        "drop",
        "fill",
        "reorder",
    )
    provenance = aligned.report.to_dict()
    assert provenance["contract_fingerprint"] == contract.fingerprint()
    assert provenance["mapping_asset"] == {
        "asset_id": "rna-mapping",
        "path": "rna_mapping.json",
        "version": "1.0.0",
        "sha256": _sha256(pack / "rna_mapping.json"),
    }
    assert [step["operation"] for step in provenance["steps"]] == [
        "alias",
        "aggregate",
        "drop",
        "fill",
        "reorder",
    ]
    assert provenance["source_feature_ids"] == list(rna.feature_ids)
    assert provenance["target_feature_ids"] == target_ids


def test_missing_features_are_not_automatically_zero_filled(tmp_path):
    pack = _write_pack(tmp_path / "pack")

    with load_mudata_view(pack) as view:
        rna = view.modality("rna")
        contract = _contract([*rna.feature_ids, _FILLED_FEATURE])
        with pytest.raises(FeatureAlignmentError, match="fill"):
            align_features(rna, contract, mapping_root=pack)


def test_taxonomy_and_namespace_mismatch_never_use_ortholog_or_alias_fallback(
    tmp_path,
):
    pack = _write_pack(tmp_path / "pack")

    with load_mudata_view(pack) as view:
        rna = view.modality("rna")
        with pytest.raises(FeatureAlignmentError, match="taxonomy"):
            align_features(
                rna,
                _contract(
                    list(rna.feature_ids),
                    taxonomy_id="NCBITaxon:10090",
                    mapping_asset=_mapping_reference(pack),
                ),
                mapping_root=pack,
            )
        with pytest.raises(FeatureAlignmentError, match="namespace"):
            align_features(
                rna,
                _contract(
                    list(rna.feature_ids),
                    namespace_version="GRCm39",
                    mapping_asset=_mapping_reference(pack),
                ),
                mapping_root=pack,
            )


def test_mapping_bytes_and_version_are_bound_to_pack_and_contract_fingerprints(
    tmp_path,
):
    pack = _write_pack(tmp_path / "pack")
    first_manifest_fingerprint = validate_pack(pack).fingerprint()
    first_contract = _contract(
        ["ENSG00000106546"],
        mapping_asset=_mapping_reference(pack),
    )
    first_contract_fingerprint = first_contract.fingerprint()

    mapping_path = pack / "rna_mapping.json"
    raw = json.loads(mapping_path.read_text(encoding="utf-8"))
    raw["mapping_version"] = "1.0.1"
    mapping_path.write_text(
        json.dumps(raw, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _refresh_mapping_asset(pack)
    second_manifest_fingerprint = validate_pack(pack).fingerprint()
    second_contract = _contract(
        ["ENSG00000106546"],
        mapping_asset=_mapping_reference(pack),
    )

    assert second_manifest_fingerprint != first_manifest_fingerprint
    assert second_contract.fingerprint() != first_contract_fingerprint


def test_mapping_asset_content_cannot_change_behind_its_declared_hash(tmp_path):
    pack = _write_pack(tmp_path / "pack")
    contract = _contract(
        [
            "ENSG00000157764",
            "ENSG00000106546",
            "ENSG00000141510",
            _FILLED_FEATURE,
        ],
        reorder=True,
        drop=["ENSG00000171862"],
        fill=[{"feature_id": _FILLED_FEATURE, "value": 0.5}],
        mapping_asset=_mapping_reference(pack),
    )

    with load_mudata_view(pack) as view:
        mapping_path = pack / "rna_mapping.json"
        mapping_path.write_text(
            mapping_path.read_text(encoding="utf-8") + "\n",
            encoding="utf-8",
        )
        with pytest.raises(FeatureAlignmentError, match="hash"):
            align_features(view.modality("rna"), contract, mapping_root=pack)


def test_mapping_file_must_be_a_declared_pack_asset(tmp_path):
    pack = _write_pack(tmp_path / "pack")
    contract = _contract(
        [
            "ENSG00000157764",
            "ENSG00000106546",
            "ENSG00000141510",
            _FILLED_FEATURE,
        ],
        reorder=True,
        drop=["ENSG00000171862"],
        fill=[{"feature_id": _FILLED_FEATURE, "value": 0.5}],
        mapping_asset=_mapping_reference(pack),
    )
    _rewrite_manifest(
        pack,
        lambda raw: raw.update(
            assets=[
                asset for asset in raw["assets"] if asset["id"] != "rna-mapping"
            ]
        ),
    )

    with load_mudata_view(pack) as view:
        with pytest.raises(FeatureAlignmentError, match="declared Pack asset"):
            align_features(view.modality("rna"), contract, mapping_root=pack)


def test_mapping_asset_rejects_ids_outside_the_contract_format(tmp_path):
    pack = _write_pack(tmp_path / "pack")
    mapping_path = pack / "rna_mapping.json"
    raw = json.loads(mapping_path.read_text(encoding="utf-8"))
    raw["aliases"][0]["source"] = "AHR"
    mapping_path.write_text(
        json.dumps(raw, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _refresh_mapping_asset(pack)

    with load_mudata_view(pack) as view:
        contract = _contract(
            list(view.modality("rna").feature_ids),
            mapping_asset=_mapping_reference(pack),
        )
        with pytest.raises(FeatureAlignmentError, match="canonical.*mapping"):
            align_features(view.modality("rna"), contract, mapping_root=pack)


def test_mudata_is_optional_and_tiny_pack_assets_are_not_checked_in():
    root = Path(__file__).resolve().parents[2]
    cfg = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    extras = cfg["project"]["optional-dependencies"]
    dev_lock = (root / "requirements" / "dev-py313.lock").read_text(encoding="utf-8")
    runtime_lock = (root / "requirements" / "runtime-py313.lock").read_text(
        encoding="utf-8"
    )

    assert "mudata>=0.3.10,<0.4" in extras["omics"]
    assert not any(
        requirement.startswith("mudata")
        for requirement in cfg["project"]["dependencies"]
    )
    assert "\nmudata==" in dev_lock
    assert "\nmudata==" not in runtime_lock
    assert not list(_FIXTURES.rglob("*.h5mu"))


def test_importing_base_data_packs_requires_no_optional_omics_modules():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import builtins, sys; "
            "real_import = builtins.__import__; "
            "builtins.__import__ = lambda name, *args, **kwargs: "
            "(_ for _ in ()).throw(ImportError('blocked optional omics')) "
            "if name.split('.', 1)[0] in {'anndata', 'mudata', 'numpy', 'scipy'} "
            "else real_import(name, *args, **kwargs); "
            "import praxis_virtualcell.data_packs; "
            "assert not {'anndata', 'mudata', 'numpy', 'scipy'}.intersection(sys.modules)",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
