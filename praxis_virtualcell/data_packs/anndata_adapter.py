"""Backed, selection-only AnnData/H5AD adapter."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from praxis_virtualcell.data_packs.errors import (
    OmicsDataError,
    OmicsDependencyError,
    OmicsMappingError,
)
from praxis_virtualcell.data_packs.validator import resolve_asset_path, validate_pack

_H5AD_MEDIA_TYPES = {"application/vnd.anndata+hdf5", "application/x-hdf5"}


def _matrix(adata, location: str):
    if location == "X":
        matrix = adata.X
    else:
        layer = location.removeprefix("layers/")
        if layer not in adata.layers:
            raise OmicsMappingError(f"matrix location does not exist: {location!r}")
        matrix = adata.layers[layer]
    if matrix is None or tuple(matrix.shape) != tuple(adata.shape):
        raise OmicsDataError(
            f"matrix location {location!r} has shape {getattr(matrix, 'shape', None)}, "
            f"expected {tuple(adata.shape)}"
        )
    return matrix


def _string_values(frame, key: str, label: str, *, unique: bool) -> tuple[str, ...]:
    if key not in frame.columns:
        raise OmicsMappingError(f"{label} mapping does not exist: {key!r}")
    values = tuple(frame[key].tolist())
    if any(not isinstance(value, str) or not value for value in values):
        raise OmicsDataError(f"{label} values must be non-empty strings")
    if unique and len(set(values)) != len(values):
        raise OmicsDataError(f"{label} ids must be unique")
    return values


def _positions(all_ids: tuple[str, ...], requested, label: str) -> list[int]:
    if requested is None:
        return list(range(len(all_ids)))
    if not isinstance(requested, (list, tuple)) or not requested:
        raise OmicsMappingError(f"{label} selection must be a non-empty list of ids")
    if any(not isinstance(value, str) or not value for value in requested):
        raise OmicsMappingError(f"{label} selection ids must be non-empty strings")
    if len(set(requested)) != len(requested):
        raise OmicsMappingError(f"duplicate {label} selection ids are not allowed")
    missing = set(requested).difference(all_ids)
    if missing:
        raise OmicsMappingError(f"unknown {label} selection ids: {sorted(missing)}")
    selected = set(requested)
    return [index for index, value in enumerate(all_ids) if value in selected]


@dataclass(frozen=True, eq=False)
class CanonicalOmicsView:
    observation_ids: tuple[str, ...]
    feature_ids: tuple[str, ...]
    conditions: tuple[str, ...]
    splits: tuple[str, ...]
    matrix_location: str
    _adata: Any = field(repr=False, compare=False)

    @property
    def shape(self) -> tuple[int, int]:
        return self._adata.shape

    @property
    def is_backed(self) -> bool:
        return bool(self._adata.isbacked)

    @property
    def is_view(self) -> bool:
        return bool(self._adata.is_view)

    @property
    def matrix(self):
        return _matrix(self._adata, self.matrix_location)

    def close(self) -> None:
        self._adata.file.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


def load_anndata_view(
    pack_root: str | Path,
    *,
    observation_ids: list[str] | tuple[str, ...] | None = None,
    feature_ids: list[str] | tuple[str, ...] | None = None,
) -> CanonicalOmicsView:
    """Validate a Pack and open its declared H5AD as a read-only backed view."""
    try:
        import anndata
    except ImportError as exc:  # pragma: no cover - exercised in base-only install verification
        raise OmicsDependencyError("AnnData support requires the 'omics' extra") from exc

    manifest = validate_pack(pack_root)
    root = Path(pack_root).resolve(strict=True)
    if manifest.matrix is None:
        raise OmicsMappingError("AnnData Pack requires an explicit matrix mapping")
    if manifest.matrix.location != "X":
        raise OmicsMappingError("backed H5AD adapter only supports matrix location 'X'")
    assets = {asset.id: asset for asset in manifest.assets}
    asset = assets[manifest.matrix.asset]
    if asset.media_type not in _H5AD_MEDIA_TYPES:
        raise OmicsMappingError(
            f"matrix asset must declare an H5AD media type, got {asset.media_type!r}"
        )
    path = resolve_asset_path(root, asset.path)

    try:
        adata = anndata.read_h5ad(path, backed="r")
    except Exception as exc:
        raise OmicsDataError(f"cannot open declared H5AD asset {asset.id!r}: {exc}") from exc
    try:
        if not adata.obs_names.is_unique:
            raise OmicsDataError("AnnData obs names must be unique")
        if not adata.var_names.is_unique:
            raise OmicsDataError("AnnData var names must be unique")
        if tuple(adata.shape) != manifest.matrix.shape:
            raise OmicsDataError(
                f"AnnData shape {tuple(adata.shape)} does not match manifest shape "
                f"{manifest.matrix.shape}"
            )
        _matrix(adata, manifest.matrix.location)

        all_observations = _string_values(
            adata.obs,
            manifest.identity.observation_key,
            "obs",
            unique=True,
        )
        all_features = _string_values(
            adata.var,
            manifest.identity.feature_key,
            "var",
            unique=True,
        )
        all_conditions = _string_values(
            adata.obs,
            manifest.condition.field,
            "condition",
            unique=False,
        )
        all_splits = _string_values(
            adata.obs,
            manifest.split.field,
            "split",
            unique=False,
        )
        undeclared_conditions = set(all_conditions).difference(manifest.condition.values)
        undeclared_splits = set(all_splits).difference(manifest.split.values)
        if undeclared_conditions:
            raise OmicsDataError(f"undeclared condition values: {sorted(undeclared_conditions)}")
        if undeclared_splits:
            raise OmicsDataError(f"undeclared split values: {sorted(undeclared_splits)}")

        obs_positions = _positions(all_observations, observation_ids, "observation")
        var_positions = _positions(all_features, feature_ids, "feature")
        selected = adata
        if observation_ids is not None or feature_ids is not None:
            selected = adata[obs_positions, var_positions]
        return CanonicalOmicsView(
            observation_ids=tuple(all_observations[index] for index in obs_positions),
            feature_ids=tuple(all_features[index] for index in var_positions),
            conditions=tuple(all_conditions[index] for index in obs_positions),
            splits=tuple(all_splits[index] for index in obs_positions),
            matrix_location=manifest.matrix.location,
            _adata=selected,
        )
    except Exception:
        adata.file.close()
        raise
