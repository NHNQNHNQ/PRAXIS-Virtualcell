"""Build the three tiny P8 product fixtures from explicit P4 semantic records."""

from __future__ import annotations

import hashlib
from copy import deepcopy
from pathlib import Path

import anndata
import numpy as np
import pandas as pd
import yaml
from scipy import sparse

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "praxis_virtualcell" / "tests" / "fixtures" / "pack_semantics"
OUTPUT = ROOT / "praxis_virtualcell" / "example_packs"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build(species: str) -> None:
    source = yaml.safe_load(
        (SOURCES / f"{species}.yaml").read_text(encoding="utf-8")
    )
    manifest = deepcopy(source)
    observations = manifest.pop("fixture_observations")
    features = manifest.pop("fixture_features")
    manifest["pack_id"] = f"p8-{species}-tiny"
    manifest["pack_version"] = "1.0.0"
    manifest["provenance"] = {
        "source": "synthetic P8 product fixture; no P7 data",
        "created_by": "PRAXIS-VirtualCell",
        "citation": "none",
    }

    pack_root = OUTPUT / species
    pack_root.mkdir(parents=True, exist_ok=True)
    matrix = sparse.csr_matrix(
        np.arange(
            1,
            len(observations) * len(features) + 1,
            dtype=np.float32,
        ).reshape(len(observations), len(features))
    )
    adata = anndata.AnnData(
        X=matrix,
        obs=pd.DataFrame(observations).set_index("obs_name"),
        var=pd.DataFrame(features).set_index("id"),
    )
    asset = pack_root / "tiny.h5ad"
    adata.write_h5ad(asset)
    manifest["assets"] = [
        {
            "id": "expression",
            "path": "tiny.h5ad",
            "media_type": "application/vnd.anndata+hdf5",
            "sha256": sha256(asset),
            "size_bytes": asset.stat().st_size,
        }
    ]
    manifest["matrix"] = {
        "asset": "expression",
        "location": "X",
        "shape": [len(observations), len(features)],
    }
    (pack_root / "manifest.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=False),
        encoding="utf-8",
    )


if __name__ == "__main__":
    for name in ("human", "mouse", "bacteria"):
        build(name)
