"""Small real H5AD files verify the recovered reader's actual I/O boundaries."""
from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd
import pytest
import yaml
from scipy import sparse

from praxis_virtualcell.data_packs import load_anndata_view
from praxis_virtualcell.data_packs.errors import OmicsDataError, OmicsMappingError, PackAssetHashMismatch

anndata = pytest.importorskip("anndata")


@pytest.fixture
def h5ad_pack(tmp_path):
    root = tmp_path / "pack"
    root.mkdir()
    asset = root / "expression.h5ad"
    adata = anndata.AnnData(
        X=sparse.csr_matrix(np.array([[0.0, 2.0], [3.0, 4.0]], dtype=np.float32)),
        obs=pd.DataFrame({"sample_id": ["sample-a", "sample-b"],
                          "condition": ["baseline", "baseline"], "split": ["external", "external"]},
                         index=["row-a", "row-b"]),
        var=pd.DataFrame(index=["ABUW_0001", "ABUW_0002"]),
    )
    adata.write_h5ad(asset)
    manifest = {
        "schema_version": "vc.pack.v0.1", "pack_id": "synthetic-bacterial-reader", "pack_version": "1.0.0",
        "taxon": {"ontology_id": "NCBITaxon:470", "scientific_name": "Acinetobacter baumannii"},
        "assembly": {"name": "AB5075 reference", "accession": "CP008706.1"},
        "identity": {"observation_key": "sample_id", "feature_key": "var_names"},
        "modality": {"name": "RNA", "ontology_id": "EFO:0008913"},
        "feature_namespace": {"name": "ABUW native locus tags", "version": "fixture-v1"},
        "assets": [{"id": "expression", "path": asset.name, "media_type": "application/vnd.anndata+hdf5",
                    "sha256": hashlib.sha256(asset.read_bytes()).hexdigest(), "size_bytes": asset.stat().st_size}],
        "matrix": {"asset": "expression", "location": "X", "shape": [2, 2]},
        "condition": {"field": "condition", "values": ["baseline"], "control": "baseline"},
        "split": {"field": "split", "strategy": "predefined", "values": ["external"]},
        "provenance": {"source": "synthetic test matrix", "created_by": "pytest", "citation": "none"},
        "license": {"id": "CC0-1.0", "name": "CC0"},
    }
    (root / "manifest.yaml").write_text(yaml.safe_dump(manifest, sort_keys=False))
    return root


def _rewrite(root, update):
    path = root / "manifest.yaml"
    manifest = yaml.safe_load(path.read_text())
    update(manifest)
    path.write_text(yaml.safe_dump(manifest, sort_keys=False))


def test_real_backed_h5ad_selection_preserves_native_ids_values_and_file(h5ad_pack):
    path = h5ad_pack / "expression.h5ad"
    original = path.read_bytes()
    with load_anndata_view(h5ad_pack, observation_ids=["sample-a"], feature_ids=["ABUW_0001"]) as view:
        assert view.is_backed and view.is_view
        assert view.observation_ids == ("sample-a",) and view.feature_ids == ("ABUW_0001",)
        assert view.taxonomy_id == "NCBITaxon:470" and view.assembly_accession == "CP008706.1"
        assert view.shape == (1, 1) and view.matrix_format == "csr"
        np.testing.assert_array_equal(view.matrix.toarray(), [[0.0]])
    assert path.read_bytes() == original


def test_h5ad_hash_is_checked_before_opening(h5ad_pack, monkeypatch):
    _rewrite(h5ad_pack, lambda manifest: manifest["assets"][0].update(sha256="0" * 64))
    monkeypatch.setattr(anndata, "read_h5ad", lambda *args, **kwargs: pytest.fail("Corrupt H5AD was opened"))
    with pytest.raises(PackAssetHashMismatch):
        load_anndata_view(h5ad_pack)


def test_h5ad_shape_must_match_manifest(h5ad_pack):
    _rewrite(h5ad_pack, lambda manifest: manifest["matrix"].update(shape=[3, 2]))
    with pytest.raises(OmicsDataError, match="does not match manifest shape"):
        load_anndata_view(h5ad_pack)


@pytest.mark.parametrize("feature_ids", [["unknown-gene"], ["ABUW_0002", "ABUW_0001"]])
def test_h5ad_selection_rejects_unknown_ids_and_unrequested_reordering(h5ad_pack, feature_ids):
    with pytest.raises(OmicsMappingError):
        load_anndata_view(h5ad_pack, feature_ids=feature_ids)
