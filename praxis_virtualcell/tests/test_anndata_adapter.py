"""P3 contracts for the optional backed AnnData/H5AD adapter."""

from __future__ import annotations

import builtins
import hashlib
import json
import subprocess
import sys
import tomllib
from pathlib import Path

import anndata
import numpy as np
import pandas as pd
import pytest
import yaml
from scipy import sparse

from praxis_virtualcell.data_packs import anndata_adapter as adapter_module
from praxis_virtualcell.data_packs import validator as validator_module
from praxis_virtualcell.data_packs.anndata_adapter import load_anndata_view
from praxis_virtualcell.data_packs.errors import (
    OmicsDataError,
    OmicsDependencyError,
    OmicsMappingError,
    PackManifestError,
)
from praxis_virtualcell.data_packs.validator import validate_pack

_P2_FIXTURE = Path(__file__).parent / "fixtures" / "data_packs" / "valid_tiny"
_P2_FINGERPRINT = "5973dc852f8d7d0cb73ce333d3f99beb2f94c66b7cdf4e6d2e7fc4c422651192"
_MATRIX = np.array(
    [
        [1.0, 0.0, 3.0],
        [0.0, 4.0, 0.0],
        [5.0, 0.0, 6.0],
    ],
    dtype=np.float32,
)
_OBS_IDS = ["cell-1", "cell-2", "cell-3"]
_VAR_IDS = ["gene-A", "gene-B", "gene-C"]
_CONDITIONS = ["control", "AHR_KO", "control"]
_SPLITS = ["train", "test", "train"]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_pack(
    root: Path,
    variant: str = "a",
    *,
    observation_ids: list[str] | None = None,
    feature_ids: list[str] | None = None,
    observation_names: list[str] | None = None,
    feature_names: list[str] | None = None,
    include_split: bool = True,
    matrix_location: str = "X",
    sparse_format: str = "csr",
) -> Path:
    root.mkdir()
    if variant == "a":
        obs_id_key, var_id_key = "cell_id", "gene_id"
        condition_key, split_key = "condition", "split"
    else:
        obs_id_key, var_id_key = "barcode", "ensembl_id"
        condition_key, split_key = "treatment", "partition"

    obs = {
        obs_id_key: observation_ids or _OBS_IDS,
        condition_key: _CONDITIONS,
    }
    if include_split:
        obs[split_key] = _SPLITS
    sparse_matrix = (
        sparse.csr_matrix(_MATRIX)
        if sparse_format == "csr"
        else sparse.csc_matrix(_MATRIX)
    )
    adata = anndata.AnnData(
        X=sparse_matrix,
        obs=pd.DataFrame(
            obs,
            index=observation_names or [f"{variant}-row-{index}" for index in range(3)],
        ),
        var=pd.DataFrame(
            {var_id_key: feature_ids or _VAR_IDS},
            index=feature_names or [f"{variant}-column-{index}" for index in range(3)],
        ),
        layers=(
            {"counts": sparse_matrix.copy()}
            if matrix_location == "layers/counts"
            else None
        ),
    )
    asset = root / "tiny.h5ad"
    adata.write_h5ad(asset)

    manifest = {
        "schema_version": "vc.pack.v0.1",
        "pack_id": f"tiny-anndata-{variant}",
        "pack_version": "0.1.0",
        "taxon": {"ontology_id": "NCBITaxon:9606", "scientific_name": "Homo sapiens"},
        "assembly": {"name": "GRCh38", "accession": "GCF_000001405.40"},
        "identity": {"observation_key": obs_id_key, "feature_key": var_id_key},
        "modality": {"name": "scRNA", "ontology_id": "EFO:0008913"},
        "feature_namespace": {"name": "EnsemblGene", "version": "GRCh38"},
        "assets": [
            {
                "id": "expression",
                "path": "tiny.h5ad",
                "media_type": "application/vnd.anndata+hdf5",
                "sha256": _sha256(asset),
                "size_bytes": asset.stat().st_size,
            }
        ],
        "matrix": {"asset": "expression", "location": matrix_location, "shape": [3, 3]},
        "condition": {
            "field": condition_key,
            "values": ["control", "AHR_KO"],
            "control": "control",
        },
        "split": {"field": split_key, "strategy": "predefined", "values": ["train", "test"]},
        "provenance": {
            "source": "runtime-generated P3 fixture",
            "created_by": "pytest",
            "citation": "none",
        },
        "license": {"id": "CC0-1.0", "name": "CC0"},
    }
    (root / "manifest.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=False),
        encoding="utf-8",
    )
    return root


def _rewrite_manifest(pack: Path, update) -> None:
    path = pack / "manifest.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    update(raw)
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")


def test_two_differently_named_h5ad_packs_produce_the_same_canonical_view(tmp_path):
    pack_a = _write_pack(tmp_path / "a", "a")
    pack_b = _write_pack(tmp_path / "b", "b")
    hashes_before = [_sha256(pack / "tiny.h5ad") for pack in (pack_a, pack_b)]
    observation_ids = ["cell-1", "cell-3"]
    feature_ids = ["gene-A", "gene-C"]

    with (
        load_anndata_view(
            pack_a,
            observation_ids=observation_ids,
            feature_ids=feature_ids,
        ) as first,
        load_anndata_view(
            pack_b,
            observation_ids=observation_ids,
            feature_ids=feature_ids,
        ) as second,
    ):
        assert first.canonical_key == second.canonical_key
        assert first.is_backed and second.is_backed
        assert first.is_view and second.is_view
        assert first.observation_ids == tuple(observation_ids)
        assert first.feature_ids == tuple(feature_ids)
        assert first.conditions == ("control", "control")
        assert first.splits == ("train", "train")
        assert first.shape == (2, 2)
        assert first.matrix_format == "csr"
        assert sparse.issparse(first.matrix)
        assert sparse.issparse(second.matrix)
        expected = _MATRIX[np.ix_([0, 2], [0, 2])]
        np.testing.assert_array_equal(first.matrix.toarray(), expected)
        np.testing.assert_array_equal(second.matrix.toarray(), expected)

    assert [_sha256(pack / "tiny.h5ad") for pack in (pack_a, pack_b)] == hashes_before


def test_loader_uses_public_backed_read_api(tmp_path, monkeypatch):
    pack = _write_pack(tmp_path / "pack")
    calls = []
    real_read_h5ad = anndata.read_h5ad

    def tracked_read_h5ad(*args, **kwargs):
        calls.append((args, kwargs))
        return real_read_h5ad(*args, **kwargs)

    monkeypatch.setattr(anndata, "read_h5ad", tracked_read_h5ad)

    with load_anndata_view(pack) as view:
        assert view.is_backed
        assert not view.is_view
        assert view.matrix_format == "csr"
        assert getattr(view.matrix, "format", None) == "csr"

    assert len(calls) == 1
    assert calls[0][1] == {"backed": "r"}


@pytest.mark.parametrize("sparse_format", ["csr", "csc"])
def test_sparse_encoding_is_preserved_before_and_after_selection(tmp_path, sparse_format):
    pack = _write_pack(tmp_path / "pack", sparse_format=sparse_format)

    with load_anndata_view(pack) as whole:
        assert whole.matrix_format == sparse_format
        assert getattr(whole.matrix, "format", None) == sparse_format

    with load_anndata_view(
        pack,
        observation_ids=["cell-1", "cell-3"],
        feature_ids=["gene-A", "gene-C"],
    ) as selected:
        assert selected.matrix_format == sparse_format
        assert sparse.issparse(selected.matrix)
        assert selected.matrix.format == sparse_format


def test_checksum_finishes_before_h5ad_is_opened(tmp_path, monkeypatch):
    pack = _write_pack(tmp_path / "pack")
    events = []
    real_validate = adapter_module.validate_pack
    real_read_h5ad = anndata.read_h5ad

    def tracked_validate(pack_root):
        manifest = real_validate(pack_root)
        events.append("checksum-complete")
        return manifest

    def tracked_read_h5ad(*args, **kwargs):
        events.append("h5ad-open")
        return real_read_h5ad(*args, **kwargs)

    monkeypatch.setattr(adapter_module, "validate_pack", tracked_validate)
    monkeypatch.setattr(anndata, "read_h5ad", tracked_read_h5ad)

    with load_anndata_view(pack):
        pass

    assert events == ["checksum-complete", "h5ad-open"]


def test_checksum_reads_large_assets_in_fixed_chunks():
    chunk_size = 1024 * 1024

    class ChunkStream:
        def __init__(self):
            self.remaining = 2 * chunk_size + 17
            self.read_sizes = []

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return None

        def read(self, size):
            self.read_sizes.append(size)
            count = min(size, self.remaining)
            self.remaining -= count
            return b"x" * count

    class ChunkSource:
        def __init__(self, stream):
            self.stream = stream

        def open(self, mode):
            assert mode == "rb"
            return self.stream

    stream = ChunkStream()
    digest = validator_module._sha256(ChunkSource(stream))

    assert len(digest) == 64
    assert stream.read_sizes == [chunk_size, chunk_size, chunk_size, chunk_size]


@pytest.mark.parametrize(
    "axis",
    ["obs", "var"],
)
def test_mapped_obs_and_var_ids_must_be_unique(tmp_path, axis):
    kwargs = (
        {"observation_ids": ["cell-1", "cell-1", "cell-3"]}
        if axis == "obs"
        else {"feature_ids": ["gene-A", "gene-A", "gene-C"]}
    )
    pack = _write_pack(tmp_path / "pack", **kwargs)

    with pytest.raises(OmicsDataError, match=f"{axis}.*unique"):
        load_anndata_view(pack)


@pytest.mark.parametrize(
    "axis,kwargs",
    [
        ("obs", {"observation_names": ["row-1", "row-1", "row-3"]}),
        ("var", {"feature_names": ["column-1", "column-1", "column-3"]}),
    ],
)
def test_anndata_obs_and_var_names_must_be_unique(tmp_path, axis, kwargs):
    label = "Observation" if axis == "obs" else "Variable"
    with pytest.warns(UserWarning, match=f"{label} names are not unique"):
        pack = _write_pack(tmp_path / "pack", **kwargs)

    with (
        pytest.warns(UserWarning, match=f"{label} names are not unique"),
        pytest.raises(OmicsDataError, match=f"{axis}.*unique"),
    ):
        load_anndata_view(pack)


def test_mapped_ids_reject_whitespace_without_rewriting_it(tmp_path):
    pack = _write_pack(
        tmp_path / "pack",
        observation_ids=["cell-1", " ", "cell-3"],
    )

    with pytest.raises(OmicsDataError, match="non-empty strings"):
        load_anndata_view(pack)


@pytest.mark.parametrize(
    "update,match",
    [
        (lambda raw: raw["matrix"].update(shape=[99, 3]), "shape"),
        (lambda raw: raw["matrix"].update(location="layers/missing"), "location"),
        (lambda raw: raw["matrix"].update(asset="missing"), "asset"),
    ],
)
def test_matrix_asset_location_and_shape_fail_closed(tmp_path, update, match):
    pack = _write_pack(tmp_path / "pack")
    _rewrite_manifest(pack, update)

    with pytest.raises((PackManifestError, OmicsMappingError, OmicsDataError), match=match):
        load_anndata_view(pack)


def test_manifest_rejects_layer_matrix_location_before_adapter_open(tmp_path):
    pack = _write_pack(tmp_path / "pack", matrix_location="layers/counts")

    with pytest.raises(PackManifestError, match="matrix.location"):
        validate_pack(pack)


def test_manifest_rejects_explicit_null_matrix_mapping(tmp_path):
    pack = _write_pack(tmp_path / "pack")
    _rewrite_manifest(pack, lambda raw: raw.update(matrix=None))

    with pytest.raises(PackManifestError, match="matrix.*omit|matrix.*object"):
        validate_pack(pack)


def test_selection_rejects_unknown_or_duplicate_ids_without_reordering(tmp_path):
    pack = _write_pack(tmp_path / "pack")

    with pytest.raises(OmicsMappingError, match="unknown feature"):
        load_anndata_view(pack, feature_ids=["not-a-gene"])
    with pytest.raises(OmicsMappingError, match="duplicate observation"):
        load_anndata_view(pack, observation_ids=["cell-1", "cell-1"])
    with pytest.raises(OmicsMappingError, match="feature.*source order"):
        load_anndata_view(pack, feature_ids=["gene-C", "gene-A"])
    with pytest.raises(OmicsMappingError, match="observation.*source order"):
        load_anndata_view(pack, observation_ids=["cell-3", "cell-1"])


def test_loader_does_not_generate_a_missing_split(tmp_path):
    pack = _write_pack(tmp_path / "pack", include_split=False)

    with pytest.raises(OmicsMappingError, match="split"):
        load_anndata_view(pack)


def test_p2_manifest_without_matrix_mapping_stays_valid_and_byte_stable():
    manifest = validate_pack(_P2_FIXTURE)

    assert manifest.matrix is None
    assert manifest.fingerprint() == _P2_FINGERPRINT


def test_p2_optional_license_null_keeps_its_original_fingerprint_semantics():
    raw = yaml.safe_load((_P2_FIXTURE / "manifest.yaml").read_text(encoding="utf-8"))
    raw["license"].pop("url")
    manifest = type(validate_pack(_P2_FIXTURE)).from_dict(raw)
    pre_p3_dict = {**raw, "license": {**raw["license"], "url": None}}
    expected = hashlib.sha256(
        json.dumps(
            pre_p3_dict,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()

    assert "matrix" not in manifest.to_dict()
    assert manifest.to_dict()["license"]["url"] is None
    assert manifest.fingerprint() == expected


def test_anndata_is_only_in_the_omics_extra_and_dev_lock():
    root = Path(__file__).resolve().parents[2]
    cfg = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    extras = cfg["project"]["optional-dependencies"]
    dev_lock = (root / "requirements" / "dev-py313.lock").read_text(encoding="utf-8")
    runtime_lock = (root / "requirements" / "runtime-py313.lock").read_text(encoding="utf-8")
    lock_docs = (root / "requirements" / "README.md").read_text(encoding="utf-8")

    assert extras["omics"] == ["anndata>=0.12.10,<0.13"]
    assert not any(requirement.startswith("anndata") for requirement in cfg["project"]["dependencies"])
    assert "\nanndata==" in dev_lock
    assert "\nanndata==" not in runtime_lock
    assert "--extra omics" in lock_docs


def test_importing_base_data_packs_does_not_import_optional_anndata():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import praxis_virtualcell.data_packs; "
            "assert 'anndata' not in sys.modules",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_loader_fails_closed_when_optional_anndata_is_unavailable(tmp_path, monkeypatch):
    real_import = builtins.__import__

    def import_without_anndata(name, *args, **kwargs):
        if name == "anndata":
            raise ImportError("blocked optional dependency")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", import_without_anndata)

    with pytest.raises(OmicsDependencyError, match="omics"):
        load_anndata_view(tmp_path)
