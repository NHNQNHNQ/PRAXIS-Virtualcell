"""Read-only backed MuData/H5MU adapter for versioned multi-omics Packs."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from praxis_virtualcell.data_packs.anndata_adapter import (
    _FEATURE_IDS,
    _index_values,
    _matrix,
    _matrix_format,
    _positions,
    _string_values,
    _validate_semantics,
)
from praxis_virtualcell.data_packs.errors import (
    OmicsDataError,
    OmicsDependencyError,
    OmicsMappingError,
)
from praxis_virtualcell.data_packs.manifest import PackManifest
from praxis_virtualcell.data_packs.validator import resolve_asset_path, validate_pack

_H5MU_MEDIA_TYPES = {"application/vnd.mudata+hdf5", "application/x-hdf5"}


def _manifest_semantics(manifest: PackManifest) -> tuple[Any, ...]:
    multiomics = manifest.multiomics
    cell_semantics = manifest.cell_semantics
    conditions = manifest.conditions
    perturbations = manifest.perturbations
    if any(
        value is None
        for value in (multiomics, cell_semantics, conditions, perturbations)
    ):  # pragma: no cover - rejected by the manifest contract
        raise OmicsMappingError("vc.pack.v0.3 semantic mappings are incomplete")
    return (
        manifest.schema_version,
        (manifest.taxon.ontology_id, manifest.taxon.scientific_name),
        (manifest.assembly.name, manifest.assembly.accession),
        (
            multiomics.observation_pairing,
            tuple(
                (
                    value.key,
                    (value.modality.name, value.modality.ontology_id),
                    (
                        value.feature_namespace.name,
                        value.feature_namespace.version,
                    ),
                    (
                        value.feature_semantics.id_source,
                        value.feature_semantics.id_format,
                    ),
                    value.shape,
                )
                for value in multiomics.modalities
            ),
        ),
        tuple(
            (term.id, term.role, term.label, term.definition)
            for term in cell_semantics.local_terms
        ),
        conditions.values,
        (
            perturbations.target_modality,
            tuple(
                (value.id, value.kind, value.targets)
                for value in perturbations.values
            ),
        ),
        (
            manifest.split.strategy,
            manifest.split.values,
            manifest.split.name,
            manifest.split.leakage_guard,
        ),
    )


@dataclass(frozen=True, eq=False)
class CanonicalModalityView:
    """One backed modality with explicit scientific feature identity."""

    key: str
    observation_ids: tuple[str, ...]
    feature_ids: tuple[str, ...]
    feature_symbols: tuple[str, ...] | None
    taxonomy_id: str
    assembly_accession: str
    modality_name: str
    modality_ontology_id: str
    feature_namespace_name: str
    feature_namespace_version: str
    feature_id_format: str
    matrix_location: Literal["X"]
    matrix_format: Literal["csr", "csc", "dense"]
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
        matrix = _matrix(self._adata)
        if (
            self.matrix_format in {"csr", "csc"}
            and _matrix_format(matrix) != self.matrix_format
        ):
            raise OmicsDataError(
                "sparse matrix format changed while selecting the backed modality"
            )
        return matrix

    @property
    def canonical_key(self) -> tuple[Any, ...]:
        return (
            self.key,
            self.taxonomy_id,
            self.assembly_accession,
            self.modality_name,
            self.modality_ontology_id,
            self.feature_namespace_name,
            self.feature_namespace_version,
            self.feature_id_format,
            self.observation_ids,
            self.feature_ids,
            self.shape,
            self.matrix_location,
            self.matrix_format,
        )


@dataclass(frozen=True, eq=False)
class CanonicalMuDataView:
    """Canonical multi-omics metadata plus separately accessed backed matrices."""

    observation_ids: tuple[str, ...]
    observation_pairing: Literal["paired", "partially_paired"]
    shared_observation_ids: tuple[str, ...]
    modalities: tuple[CanonicalModalityView, ...]
    conditions: tuple[str, ...]
    splits: tuple[str, ...]
    cell_identity_ids: tuple[str, ...]
    cell_state_ids: tuple[tuple[str, ...], ...]
    cell_context_ids: tuple[tuple[str, ...], ...]
    perturbation_ids: tuple[str, ...]
    perturbation_kinds: tuple[str, ...]
    perturbation_targets: tuple[tuple[str, ...], ...]
    matched_control_ids: tuple[str, ...]
    doses: tuple[tuple[float, str], ...]
    times: tuple[tuple[float, str], ...]
    split_name: str
    manifest_semantics: tuple[Any, ...]
    manifest: PackManifest = field(repr=False, compare=False)
    _mdata: Any = field(repr=False, compare=False)

    @property
    def is_backed(self) -> bool:
        return bool(self._mdata.isbacked)

    @property
    def canonical_key(self) -> tuple[Any, ...]:
        return (
            self.observation_ids,
            self.observation_pairing,
            self.shared_observation_ids,
            tuple(value.canonical_key for value in self.modalities),
            self.conditions,
            self.splits,
            self.cell_identity_ids,
            self.cell_state_ids,
            self.cell_context_ids,
            self.perturbation_ids,
            self.perturbation_kinds,
            self.perturbation_targets,
            self.matched_control_ids,
            self.doses,
            self.times,
            self.split_name,
            self.manifest_semantics,
        )

    def modality(self, key: str) -> CanonicalModalityView:
        for value in self.modalities:
            if value.key == key:
                return value
        raise OmicsMappingError(f"unknown modality: {key!r}")

    def close(self) -> None:
        self._mdata.file.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


def load_mudata_view(
    pack_root: str | Path,
    *,
    observation_ids: list[str] | tuple[str, ...] | None = None,
) -> CanonicalMuDataView:
    """Validate a v0.3 Pack and open its H5MU as a read-only backed view."""
    try:
        import mudata
    except ImportError as exc:  # pragma: no cover - base-only install gate
        raise OmicsDependencyError("MuData support requires the 'omics' extra") from exc

    manifest = validate_pack(pack_root)
    if manifest.schema_version != "vc.pack.v0.3" or manifest.multiomics is None:
        raise OmicsMappingError("MuData loader requires vc.pack.v0.3 multiomics")
    root = Path(pack_root).resolve(strict=True)
    assets = {asset.id: asset for asset in manifest.assets}
    asset = assets[manifest.multiomics.asset]
    if asset.media_type not in _H5MU_MEDIA_TYPES:
        raise OmicsMappingError(
            f"multiomics asset must declare an H5MU media type, got {asset.media_type!r}"
        )
    path = resolve_asset_path(root, asset.path)

    try:
        with mudata.set_options(pull_on_update=False):
            mdata = mudata.read_h5mu(path, backed="r")
    except Exception as exc:
        raise OmicsDataError(f"cannot open declared H5MU asset {asset.id!r}: {exc}") from exc

    try:
        declared = manifest.multiomics.modalities
        declared_keys = tuple(value.key for value in declared)
        actual_keys = tuple(mdata.mod)
        if actual_keys != declared_keys:
            raise OmicsDataError(
                f"H5MU modality order {actual_keys} does not match manifest "
                f"modality order {declared_keys}"
            )

        all_observations = _index_values(mdata.obs_names, "global obs")
        observation_sets: list[set[str]] = []
        modality_metadata = []
        for spec in declared:
            adata = mdata.mod[spec.key]
            observations = _index_values(adata.obs_names, f"{spec.key} obs")
            features = _index_values(adata.var_names, f"{spec.key} var")
            if tuple(adata.shape) != spec.shape:
                raise OmicsDataError(
                    f"H5MU modality {spec.key!r} shape {tuple(adata.shape)} "
                    f"does not match manifest shape {spec.shape}"
                )
            matrix = _matrix(adata)
            pattern = _FEATURE_IDS[spec.feature_semantics.id_format]
            invalid = [value for value in features if not pattern.fullmatch(value)]
            if invalid:
                raise OmicsDataError(
                    f"{spec.key} var_names contain non-canonical feature ids: {invalid}"
                )
            symbols = (
                None
                if spec.feature_semantics.symbol_field is None
                else _string_values(
                    adata.var,
                    spec.feature_semantics.symbol_field,
                    f"{spec.key} feature symbol",
                    unique=False,
                )
            )
            observation_sets.append(set(observations))
            modality_metadata.append(
                (spec, observations, features, symbols, _matrix_format(matrix))
            )

        global_set = set(all_observations)
        if set().union(*observation_sets) != global_set:
            raise OmicsDataError(
                "global H5MU observations must equal the modality observation union"
            )
        shared_set = set.intersection(*observation_sets)
        shared = tuple(value for value in all_observations if value in shared_set)
        if manifest.multiomics.observation_pairing == "paired":
            if any(
                observations != all_observations
                for _, observations, _, _, _ in modality_metadata
            ):
                raise OmicsDataError(
                    "paired modalities must have identical observations in identical order"
                )
        else:
            if not shared:
                raise OmicsDataError(
                    "partially_paired modalities must have observation overlap"
                )
            if all(
                observations == all_observations
                for _, observations, _, _, _ in modality_metadata
            ):
                raise OmicsDataError(
                    "partially_paired modalities must have explicit missing observations"
                )

        all_splits = _string_values(
            mdata.obs,
            manifest.split.field,
            "split",
            unique=False,
        )
        undeclared_splits = set(all_splits).difference(manifest.split.values)
        if undeclared_splits:
            raise OmicsDataError(f"undeclared split values: {sorted(undeclared_splits)}")
        target_key = manifest.perturbations.target_modality
        target_spec, _, target_features, _, _ = next(
            value for value in modality_metadata if value[0].key == target_key
        )
        semantics = _validate_semantics(
            mdata.obs,
            mdata.mod[target_key].var,
            manifest,
            target_features,
            all_splits,
            target_spec.feature_semantics,
        )

        positions = _positions(all_observations, observation_ids, "observation")
        selected_observations = tuple(all_observations[index] for index in positions)
        if observation_ids is None:
            selected = mdata
        else:
            with mudata.set_options(pull_on_update=False):
                selected = mdata[positions, :]
        selected_sets = {
            key: set(_index_values(selected.mod[key].obs_names, f"{key} obs"))
            for key in declared_keys
        }
        selected_shared = tuple(
            value
            for value in selected_observations
            if all(value in values for values in selected_sets.values())
        )
        modalities = tuple(
            CanonicalModalityView(
                key=spec.key,
                observation_ids=_index_values(
                    selected.mod[spec.key].obs_names,
                    f"{spec.key} obs",
                ),
                feature_ids=features,
                feature_symbols=symbols,
                taxonomy_id=manifest.taxon.ontology_id,
                assembly_accession=manifest.assembly.accession,
                modality_name=spec.modality.name,
                modality_ontology_id=spec.modality.ontology_id,
                feature_namespace_name=spec.feature_namespace.name,
                feature_namespace_version=spec.feature_namespace.version,
                feature_id_format=spec.feature_semantics.id_format,
                matrix_location="X",
                matrix_format=matrix_format,
                _adata=selected.mod[spec.key],
            )
            for spec, _, features, symbols, matrix_format in modality_metadata
        )
        return CanonicalMuDataView(
            observation_ids=selected_observations,
            observation_pairing=manifest.multiomics.observation_pairing,
            shared_observation_ids=selected_shared,
            modalities=modalities,
            conditions=tuple(semantics.condition_ids[index] for index in positions),
            splits=tuple(all_splits[index] for index in positions),
            cell_identity_ids=tuple(
                semantics.cell_identity_ids[index] for index in positions
            ),
            cell_state_ids=tuple(
                semantics.cell_state_ids[index] for index in positions
            ),
            cell_context_ids=tuple(
                semantics.cell_context_ids[index] for index in positions
            ),
            perturbation_ids=tuple(
                semantics.perturbation_ids[index] for index in positions
            ),
            perturbation_kinds=tuple(
                semantics.perturbation_kinds[index] for index in positions
            ),
            perturbation_targets=tuple(
                semantics.perturbation_targets[index] for index in positions
            ),
            matched_control_ids=tuple(
                semantics.matched_control_ids[index] for index in positions
            ),
            doses=tuple(semantics.doses[index] for index in positions),
            times=tuple(semantics.times[index] for index in positions),
            split_name=semantics.split_name,
            manifest_semantics=_manifest_semantics(manifest),
            manifest=manifest,
            _mdata=mdata,
        )
    except Exception:
        mdata.file.close()
        raise
