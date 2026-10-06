"""Backed, selection-only AnnData/H5AD adapter."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from numbers import Real
from pathlib import Path
from typing import Any, Literal

from praxis_virtualcell.data_packs.errors import (
    OmicsDataError,
    OmicsDependencyError,
    OmicsMappingError,
)
from praxis_virtualcell.data_packs.manifest import PackManifest
from praxis_virtualcell.data_packs.validator import resolve_asset_path, validate_pack

_H5AD_MEDIA_TYPES = {"application/vnd.anndata+hdf5", "application/x-hdf5"}
_CELL_CURIE = re.compile(r"^[A-Za-z][A-Za-z0-9._-]*:[A-Za-z0-9][A-Za-z0-9._-]*$")
_STANDARD_CELL_IDS = {
    "identity": (
        re.compile(r"^CL:[0-9]+$"),
        re.compile(r"^CVCL_[A-Z0-9]{4}$"),
    ),
    "state": (),
    "context": (re.compile(r"^UBERON:[0-9]+$"),),
}
_FEATURE_IDS = {
    "ensembl_gene": re.compile(r"^ENS[A-Z0-9]*G[0-9]{11}(?:\.[0-9]+)?$"),
    "ncbi_gene_curie": re.compile(r"^NCBIGene:[0-9]+$"),
    "uniprot_protein": re.compile(
        r"^UniProtKB:(?:[OPQ][0-9][A-Z0-9]{3}[0-9]|"
        r"[A-NR-Z][0-9](?:[A-Z][A-Z0-9]{2}[0-9]){1,2})$"
    ),
}
_DOSE_UNITS = {"1", "M", "mM", "uM", "nM", "pM", "g/L", "mg/L", "ug/mL"}
_TIME_UNITS = {"s", "min", "h", "d"}


def _matrix(adata):
    matrix = adata.X
    if matrix is None or tuple(matrix.shape) != tuple(adata.shape):
        raise OmicsDataError(
            f"matrix location 'X' has shape {getattr(matrix, 'shape', None)}, "
            f"expected {tuple(adata.shape)}"
        )
    return matrix


def _matrix_format(matrix) -> Literal["csr", "csc", "dense"]:
    value = getattr(matrix, "format", None)
    return value if value in {"csr", "csc"} else "dense"


def _string_values(frame, key: str, label: str, *, unique: bool) -> tuple[str, ...]:
    if key not in frame.columns:
        raise OmicsMappingError(f"{label} mapping does not exist: {key!r}")
    values = tuple(frame[key].tolist())
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise OmicsDataError(f"{label} values must be non-empty strings")
    if unique and len(set(values)) != len(values):
        raise OmicsDataError(f"{label} ids must be unique")
    return values


def _index_values(index, label: str) -> tuple[str, ...]:
    values = tuple(index.tolist())
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise OmicsDataError(f"{label} values must be non-empty strings")
    if len(set(values)) != len(values):
        raise OmicsDataError(f"{label} ids must be unique")
    return values


def _numeric_values(frame, key: str, label: str) -> tuple[float, ...]:
    if key not in frame.columns:
        raise OmicsMappingError(f"{label} mapping does not exist: {key!r}")
    values = []
    for value in frame[key].tolist():
        if (
            isinstance(value, bool)
            or not isinstance(value, Real)
            or not math.isfinite(float(value))
            or value < 0
        ):
            raise OmicsDataError(f"{label} values must be finite non-negative numbers")
        values.append(float(value))
    return tuple(values)


def _semantic_matrix(
    frame,
    fields,
    local_roles: dict[str, str],
    role: Literal["identity", "state", "context"],
) -> tuple[tuple[str, ...], ...]:
    columns = [
        _string_values(frame, key, f"cell semantic {key}", unique=False)
        for key in fields
    ]
    for values in columns:
        for value in values:
            standard_role = next(
                (
                    candidate
                    for candidate, patterns in _STANDARD_CELL_IDS.items()
                    if any(pattern.fullmatch(value) for pattern in patterns)
                ),
                None,
            )
            if standard_role == role:
                continue
            if standard_role is not None:
                raise OmicsDataError(
                    f"cell semantic id {value!r} is not valid for the {role} semantic role"
                )
            if not _CELL_CURIE.fullmatch(value) or value not in local_roles:
                raise OmicsDataError(
                    f"undefined local CURIE in cell semantics: {value!r}"
                )
            if local_roles[value] != role:
                raise OmicsDataError(
                    f"local cell term {value!r} is not valid for the {role} semantic role"
                )
    return tuple(zip(*columns, strict=True))


@dataclass(frozen=True)
class _SemanticColumns:
    feature_symbols: tuple[str, ...] | None
    cell_identity_ids: tuple[str, ...]
    cell_state_ids: tuple[tuple[str, ...], ...]
    cell_context_ids: tuple[tuple[str, ...], ...]
    condition_ids: tuple[str, ...]
    perturbation_ids: tuple[str, ...]
    perturbation_kinds: tuple[str, ...]
    perturbation_targets: tuple[tuple[str, ...], ...]
    matched_control_ids: tuple[str, ...]
    doses: tuple[tuple[float, str], ...]
    times: tuple[tuple[float, str], ...]
    split_name: str


def _manifest_semantics(manifest: PackManifest) -> tuple[Any, ...]:
    feature_semantics = manifest.feature_semantics
    cell_semantics = manifest.cell_semantics
    conditions = manifest.conditions
    perturbations = manifest.perturbations
    return (
        manifest.schema_version,
        (manifest.taxon.ontology_id, manifest.taxon.scientific_name),
        (manifest.assembly.name, manifest.assembly.accession),
        (manifest.modality.name, manifest.modality.ontology_id),
        (manifest.feature_namespace.name, manifest.feature_namespace.version),
        (
            None
            if feature_semantics is None
            else (feature_semantics.id_source, feature_semantics.id_format)
        ),
        (
            ()
            if cell_semantics is None
            else tuple(
                (term.id, term.role, term.label, term.definition)
                for term in cell_semantics.local_terms
            )
        ),
        (
            (manifest.condition.values, manifest.condition.control)
            if manifest.condition is not None
            else (conditions.values, None)
        ),
        (
            ()
            if perturbations is None
            else tuple(
                (value.id, value.kind, value.targets) for value in perturbations.values
            )
        ),
        (
            manifest.split.strategy,
            manifest.split.values,
            manifest.split.name,
            manifest.split.leakage_guard,
        ),
    )


def _validate_semantics(
    obs,
    var,
    manifest,
    feature_ids,
    splits,
    feature_semantics,
) -> _SemanticColumns:
    cell_semantics = manifest.cell_semantics
    conditions = manifest.conditions
    perturbations = manifest.perturbations
    if any(
        value is None
        for value in (feature_semantics, cell_semantics, conditions, perturbations)
    ):  # pragma: no cover - rejected by the manifest contract
        raise OmicsMappingError("vc.pack.v0.2 semantic mappings are incomplete")

    pattern = _FEATURE_IDS[feature_semantics.id_format]
    invalid_features = [value for value in feature_ids if not pattern.fullmatch(value)]
    if invalid_features:
        raise OmicsDataError(
            f"var_names contain non-canonical feature ids: {invalid_features}"
        )
    feature_symbols = (
        None
        if feature_semantics.symbol_field is None
        else _string_values(
            var,
            feature_semantics.symbol_field,
            "feature symbol",
            unique=False,
        )
    )

    local_roles = {term.id: term.role for term in cell_semantics.local_terms}
    identities = _semantic_matrix(
        obs,
        (cell_semantics.identity,),
        local_roles,
        "identity",
    )
    states = _semantic_matrix(obs, cell_semantics.state, local_roles, "state")
    contexts = _semantic_matrix(
        obs,
        cell_semantics.context,
        local_roles,
        "context",
    )
    identity_ids = tuple(value[0] for value in identities)

    condition_ids = _string_values(
        obs,
        conditions.field,
        "condition",
        unique=False,
    )
    unknown_conditions = sorted(set(condition_ids).difference(conditions.values))
    if unknown_conditions:
        raise OmicsDataError(f"unknown condition foreign keys: {unknown_conditions}")
    missing_conditions = sorted(set(conditions.values).difference(condition_ids))
    if missing_conditions:
        raise OmicsDataError(f"declared conditions have no observations: {missing_conditions}")
    perturbation_ids = _string_values(
        obs,
        perturbations.field,
        "perturbation",
        unique=False,
    )
    matched_controls = _string_values(
        obs,
        conditions.matched_control_field,
        "matched control",
        unique=False,
    )
    dose_values = _numeric_values(obs, conditions.dose.value_field, "dose value")
    dose_units = _string_values(
        obs,
        conditions.dose.unit_field,
        "dose unit",
        unique=False,
    )
    time_values = _numeric_values(obs, conditions.time.value_field, "time value")
    time_units = _string_values(
        obs,
        conditions.time.unit_field,
        "time unit",
        unique=False,
    )
    invalid_dose_units = sorted(set(dose_units).difference(_DOSE_UNITS))
    invalid_time_units = sorted(set(time_units).difference(_TIME_UNITS))
    if invalid_dose_units:
        raise OmicsDataError(f"unsupported dose unit values: {invalid_dose_units}")
    if invalid_time_units:
        raise OmicsDataError(f"unsupported time unit values: {invalid_time_units}")

    perturbation_by_id = {value.id: value for value in perturbations.values}
    unknown_perturbations = sorted(set(perturbation_ids).difference(perturbation_by_id))
    if unknown_perturbations:
        raise OmicsDataError(f"unknown perturbation foreign keys: {unknown_perturbations}")
    targets = {
        target
        for perturbation in perturbations.values
        for target in perturbation.targets
    }
    unknown_targets = sorted(targets.difference(feature_ids))
    if unknown_targets:
        raise OmicsDataError(f"unknown target feature foreign keys: {unknown_targets}")

    quantities = tuple(zip(dose_values, dose_units, time_values, time_units, strict=True))
    condition_rows: dict[str, int] = {}
    condition_signatures: dict[str, tuple] = {}
    for index, condition_id in enumerate(condition_ids):
        signature = (
            perturbation_ids[index],
            matched_controls[index],
            identity_ids[index],
            states[index],
            contexts[index],
            quantities[index],
            splits[index],
        )
        previous = condition_signatures.setdefault(condition_id, signature)
        if previous != signature:
            raise OmicsDataError(
                f"condition {condition_id!r} has inconsistent semantic definitions"
            )
        condition_rows.setdefault(condition_id, index)

    missing_controls = sorted(set(matched_controls).difference(condition_rows))
    if missing_controls:
        raise OmicsDataError(f"matched control foreign keys are missing: {missing_controls}")
    for condition_id, index in condition_rows.items():
        control_id = matched_controls[index]
        control_index = condition_rows[control_id]
        perturbation = perturbation_by_id[perturbation_ids[index]]
        control_perturbation = perturbation_by_id[perturbation_ids[control_index]]
        if perturbation.kind == "control":
            if control_id != condition_id:
                raise OmicsDataError("control conditions must match themselves")
            continue
        if control_perturbation.kind != "control":
            raise OmicsDataError(
                f"matched condition {control_id!r} does not use a control perturbation"
            )
        control_context = (
            identity_ids[control_index],
            states[control_index],
            contexts[control_index],
            time_values[control_index],
            time_units[control_index],
            splits[control_index],
        )
        condition_context = (
            identity_ids[index],
            states[index],
            contexts[index],
            time_values[index],
            time_units[index],
            splits[index],
        )
        if control_context != condition_context:
            raise OmicsDataError(
                f"condition {condition_id!r} does not match its control context"
            )

    if set(splits) != set(manifest.split.values):
        missing = sorted(set(manifest.split.values).difference(splits))
        raise OmicsDataError(f"named split has no observations for partitions: {missing}")
    for key in manifest.split.leakage_guard:
        if key == "target_ids":
            partition_by_target: dict[str, str] = {}
            for perturbation_id, partition in zip(
                perturbation_ids,
                splits,
                strict=True,
            ):
                for target in perturbation_by_id[perturbation_id].targets:
                    previous = partition_by_target.setdefault(target, partition)
                    if previous != partition:
                        raise OmicsDataError(
                            f"split leakage detected for target_ids: {target!r} "
                            f"occurs in {previous!r} and {partition!r}"
                        )
            continue
        values = _string_values(obs, key, f"leakage guard {key}", unique=False)
        partition_by_value: dict[str, str] = {}
        for value, partition in zip(values, splits, strict=True):
            previous = partition_by_value.setdefault(value, partition)
            if previous != partition:
                raise OmicsDataError(
                    f"split leakage detected for {key}: {value!r} occurs in "
                    f"{previous!r} and {partition!r}"
                )

    return _SemanticColumns(
        feature_symbols=feature_symbols,
        cell_identity_ids=identity_ids,
        cell_state_ids=states,
        cell_context_ids=contexts,
        condition_ids=condition_ids,
        perturbation_ids=perturbation_ids,
        perturbation_kinds=tuple(
            perturbation_by_id[value].kind for value in perturbation_ids
        ),
        perturbation_targets=tuple(
            perturbation_by_id[value].targets for value in perturbation_ids
        ),
        matched_control_ids=matched_controls,
        doses=tuple(zip(dose_values, dose_units, strict=True)),
        times=tuple(zip(time_values, time_units, strict=True)),
        split_name=manifest.split.name,
    )


def _validate_p4_semantics(adata, manifest, feature_ids, splits) -> _SemanticColumns:
    return _validate_semantics(
        adata.obs,
        adata.var,
        manifest,
        feature_ids,
        splits,
        manifest.feature_semantics,
    )


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
    positions_by_id = {value: index for index, value in enumerate(all_ids)}
    positions = [positions_by_id[value] for value in requested]
    if positions != sorted(positions):
        raise OmicsMappingError(f"{label} selection must preserve source order")
    return positions


@dataclass(frozen=True, eq=False)
class CanonicalOmicsView:
    """Canonical metadata plus a separately accessed read-only matrix."""

    observation_ids: tuple[str, ...]
    feature_ids: tuple[str, ...]
    conditions: tuple[str, ...]
    splits: tuple[str, ...]
    taxonomy_id: str
    assembly_accession: str
    feature_symbols: tuple[str, ...] | None
    cell_identity_ids: tuple[str, ...]
    cell_state_ids: tuple[tuple[str, ...], ...]
    cell_context_ids: tuple[tuple[str, ...], ...]
    condition_ids: tuple[str, ...]
    perturbation_ids: tuple[str, ...]
    perturbation_kinds: tuple[str, ...]
    perturbation_targets: tuple[tuple[str, ...], ...]
    matched_control_ids: tuple[str, ...]
    doses: tuple[tuple[float, str], ...]
    times: tuple[tuple[float, str], ...]
    split_name: str | None
    matrix_location: Literal["X"]
    matrix_format: Literal["csr", "csc", "dense"]
    manifest_semantics: tuple[Any, ...]
    manifest: PackManifest = field(repr=False, compare=False)
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
    def canonical_key(
        self,
    ) -> tuple[Any, ...]:
        """Scientific metadata identity; display symbols and matrix values are separate."""
        return (
            self.taxonomy_id,
            self.assembly_accession,
            self.observation_ids,
            self.feature_ids,
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
            self.shape,
            self.matrix_location,
            self.matrix_format,
            self.manifest_semantics,
        )

    @property
    def matrix(self):
        matrix = _matrix(self._adata)
        if self.matrix_format in {"csr", "csc"} and _matrix_format(matrix) != self.matrix_format:
            raise OmicsDataError("sparse matrix format changed while selecting the backed view")
        return matrix

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
        matrix = _matrix(adata)

        all_observations = _string_values(
            adata.obs,
            manifest.identity.observation_key,
            "obs",
            unique=True,
        )
        all_features = (
            _index_values(adata.var_names, "var")
            if manifest.identity.feature_key == "var_names"
            else _string_values(
                adata.var,
                manifest.identity.feature_key,
                "var",
                unique=True,
            )
        )
        all_splits = _string_values(
            adata.obs,
            manifest.split.field,
            "split",
            unique=False,
        )
        undeclared_splits = set(all_splits).difference(manifest.split.values)
        if undeclared_splits:
            raise OmicsDataError(f"undeclared split values: {sorted(undeclared_splits)}")
        if manifest.schema_version == "vc.pack.v0.1":
            all_conditions = _string_values(
                adata.obs,
                manifest.condition.field,
                "condition",
                unique=False,
            )
            undeclared_conditions = set(all_conditions).difference(
                manifest.condition.values
            )
            if undeclared_conditions:
                raise OmicsDataError(
                    f"undeclared condition values: {sorted(undeclared_conditions)}"
                )
            semantics = None
        else:
            semantics = _validate_p4_semantics(
                adata,
                manifest,
                all_features,
                all_splits,
            )
            all_conditions = semantics.condition_ids

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
            taxonomy_id=manifest.taxon.ontology_id,
            assembly_accession=manifest.assembly.accession,
            feature_symbols=(
                None
                if semantics is None or semantics.feature_symbols is None
                else tuple(semantics.feature_symbols[index] for index in var_positions)
            ),
            cell_identity_ids=(
                ()
                if semantics is None
                else tuple(semantics.cell_identity_ids[index] for index in obs_positions)
            ),
            cell_state_ids=(
                ()
                if semantics is None
                else tuple(semantics.cell_state_ids[index] for index in obs_positions)
            ),
            cell_context_ids=(
                ()
                if semantics is None
                else tuple(semantics.cell_context_ids[index] for index in obs_positions)
            ),
            condition_ids=(
                ()
                if semantics is None
                else tuple(semantics.condition_ids[index] for index in obs_positions)
            ),
            perturbation_ids=(
                ()
                if semantics is None
                else tuple(semantics.perturbation_ids[index] for index in obs_positions)
            ),
            perturbation_kinds=(
                ()
                if semantics is None
                else tuple(
                    semantics.perturbation_kinds[index] for index in obs_positions
                )
            ),
            perturbation_targets=(
                ()
                if semantics is None
                else tuple(
                    semantics.perturbation_targets[index] for index in obs_positions
                )
            ),
            matched_control_ids=(
                ()
                if semantics is None
                else tuple(semantics.matched_control_ids[index] for index in obs_positions)
            ),
            doses=(
                ()
                if semantics is None
                else tuple(semantics.doses[index] for index in obs_positions)
            ),
            times=(
                ()
                if semantics is None
                else tuple(semantics.times[index] for index in obs_positions)
            ),
            split_name=None if semantics is None else semantics.split_name,
            matrix_location=manifest.matrix.location,
            matrix_format=_matrix_format(matrix),
            manifest_semantics=_manifest_semantics(manifest),
            manifest=manifest,
            _adata=selected,
        )
    except Exception:
        adata.file.close()
        raise
