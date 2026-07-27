"""Strict VirtualCellPack manifest contracts."""

from praxis_virtualcell.data_packs.anndata_adapter import CanonicalOmicsView, load_anndata_view
from praxis_virtualcell.data_packs.feature_alignment import (
    AlignedFeatureMatrix,
    AlignmentReport,
    ModelFeatureContract,
    align_features,
)
from praxis_virtualcell.data_packs.manifest import PackManifest, load_manifest
from praxis_virtualcell.data_packs.mudata_adapter import CanonicalMuDataView, load_mudata_view
from praxis_virtualcell.data_packs.registry import PackRegistry, RegisteredPack
from praxis_virtualcell.data_packs.validator import validate_pack

__all__ = [
    "AlignedFeatureMatrix",
    "AlignmentReport",
    "CanonicalMuDataView",
    "CanonicalOmicsView",
    "ModelFeatureContract",
    "PackManifest",
    "PackRegistry",
    "RegisteredPack",
    "align_features",
    "load_anndata_view",
    "load_manifest",
    "load_mudata_view",
    "validate_pack",
]
