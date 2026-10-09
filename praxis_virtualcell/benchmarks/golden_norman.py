"""Deterministic Norman/K562 Golden Pack derivation and simple baselines.

This module deliberately contains no data download, model inference, split
generation, symbol conversion, or fallback behavior.  It only executes the
checked, predefined Golden contract.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from yaml.constructor import ConstructorError

from praxis_virtualcell.core.request import VirtualCellRequest
from praxis_virtualcell.data_packs.manifest import load_manifest
from praxis_virtualcell.data_packs.registry import PackRegistry
from praxis_virtualcell.model_zoo.cache import ModelCache
from praxis_virtualcell.model_zoo.registry import ModelZooRegistry
from praxis_virtualcell.workflows.predict_delta_expression import build_runtime

_DEFAULT_CONTRACT = (
    Path(__file__).parents[2] / "data" / "golden" / "norman_2019" / "contract.yaml"
)
_SHA256 = set("0123456789abcdef")
_PARTITIONS = ("train", "validation", "test")
_BASELINES = ("no_change", "global_mean", "additive_linear")
_WRAPPER = (
    "praxis_virtualcell.model_zoo.wrappers.golden_baseline_wrapper."
    "GoldenBaselineWrapper"
)


class GoldenNormanError(ValueError):
    """A frozen Golden contract or artifact was not satisfied."""


class _UniqueKeyLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        self.flatten_mapping(node)
        mapping = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                hash(key)
            except TypeError as exc:
                raise ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    f"unhashable mapping key: {key!r}",
                    key_node.start_mark,
                ) from exc
            if key in mapping:
                raise ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    f"duplicate key: {key!r}",
                    key_node.start_mark,
                )
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise GoldenNormanError(f"contract is not canonical JSON: {exc}") from exc


def _canonical_hash(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in _SHA256 for character in value)
    )


def _contract_copy(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise GoldenNormanError("Golden Norman contract must be an object")
    try:
        copied = json.loads(_canonical_bytes(dict(value)))
    except json.JSONDecodeError as exc:  # pragma: no cover - canonical encoder owns bytes
        raise GoldenNormanError("Golden Norman contract is invalid") from exc
    return copied


def _validate_contract(contract: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "benchmark_id",
        "pack_version",
        "source",
        "biology",
        "split",
        "expected",
        "metric",
        "baselines",
    }
    if set(contract) != required:
        raise GoldenNormanError(
            f"Golden Norman contract fields must be exactly {sorted(required)}"
        )
    if contract["schema_version"] != "vc.golden-norman.v1":
        raise GoldenNormanError("unsupported Golden Norman contract schema")
    if contract["benchmark_id"] != "norman-2019-k562-golden":
        raise GoldenNormanError("unexpected Golden Norman benchmark_id")

    h5ad = contract.get("source", {}).get("h5ad", {})
    for field in (
        "sha256",
        "observation_ids_sha256",
        "feature_ids_sha256",
        "feature_symbols_sha256",
        "condition_by_observation_sha256",
        "split_by_observation_sha256",
        "guide_by_observation_sha256",
    ):
        if not _is_sha256(h5ad.get(field)):
            raise GoldenNormanError(f"source.h5ad.{field} must be a SHA-256")
    shape = h5ad.get("shape")
    if (
        not isinstance(shape, list)
        or len(shape) != 2
        or any(isinstance(value, bool) or not isinstance(value, int) or value <= 0 for value in shape)
    ):
        raise GoldenNormanError("source.h5ad.shape must contain two positive integers")

    split = contract.get("split", {})
    if split.get("source_mapping") != {
        "train": "train",
        "test": "validation",
        "ood": "test",
    }:
        raise GoldenNormanError(
            "source split mapping must be train/test/ood to train/validation/test"
        )
    if set(split.get("control_guides", {})) != set(_PARTITIONS):
        raise GoldenNormanError("control guides must be declared in canonical partition order")
    guides = tuple(split["control_guides"].values())
    if any(not isinstance(value, str) or not value for value in guides) or len(set(guides)) != 3:
        raise GoldenNormanError("control guides must be three distinct non-empty strings")
    if split.get("leakage_guard") != ["condition_id"]:
        raise GoldenNormanError("Golden split leakage guard must be condition_id")

    metric = contract.get("metric", {})
    bootstrap = metric.get("bootstrap", {})
    if (
        metric.get("name") != "condition_macro_full_feature_delta_mse"
        or metric.get("direction") != "lower_is_better"
        or metric.get("features") != "all_ordered_pack_features"
        or metric.get("truth")
        != "condition_mean_X_minus_matched_split_control_mean_X"
        or bootstrap.get("unit") != "held_out_perturbation_condition"
        or bootstrap.get("method") != "paired_percentile"
        or bootstrap.get("rng") != "numpy.PCG64"
        or not isinstance(bootstrap.get("seed"), int)
        or isinstance(bootstrap.get("seed"), bool)
        or bootstrap["seed"] != 0
        or not isinstance(bootstrap.get("replicates"), int)
        or isinstance(bootstrap.get("replicates"), bool)
        or bootstrap["replicates"] != 2000
        or bootstrap.get("interval") != [0.025, 0.975]
    ):
        raise GoldenNormanError("primary metric/bootstrap contract has changed")

    if set(contract.get("baselines", {})) != set(_BASELINES):
        raise GoldenNormanError("Golden baselines must use the canonical order")
    definitions = {
        "no_change": "delta equals zero",
        "global_mean": "equal mean of train condition deltas",
        "additive_linear": "condition-level additive ridge",
    }
    if any(
        contract["baselines"][baseline].get("definition") != definition
        for baseline, definition in definitions.items()
    ):
        raise GoldenNormanError("Golden baseline definition contract has changed")
    ridge = contract["baselines"]["additive_linear"]
    if (
        not isinstance(ridge.get("alpha"), float)
        or ridge["alpha"] != 1.0
        or ridge.get("intercept") != "unpenalized"
    ):
        raise GoldenNormanError("additive linear baseline must use fixed ridge alpha=1")


def load_contract(path: str | Path = _DEFAULT_CONTRACT) -> dict[str, Any]:
    """Load the duplicate-key-safe frozen Golden contract."""

    contract_path = Path(path)
    try:
        raw = yaml.load(
            contract_path.read_text(encoding="utf-8"),
            Loader=_UniqueKeyLoader,
        )
    except (OSError, yaml.YAMLError) as exc:
        raise GoldenNormanError(f"cannot load Golden Norman contract: {exc}") from exc
    contract = _contract_copy(raw)
    _validate_contract(contract)
    return contract


def _coerce_contract(contract: Mapping[str, Any] | None) -> dict[str, Any]:
    value = load_contract() if contract is None else _contract_copy(contract)
    _validate_contract(value)
    return value


def _checked_hash(actual_value: Any, expected: str, label: str) -> None:
    actual = _canonical_hash(actual_value)
    if actual != expected:
        raise GoldenNormanError(
            f"{label} hash mismatch: expected {expected}, got {actual}"
        )


def _hash_h5_dataset(dataset) -> str:
    digest = hashlib.sha256()
    if dataset.ndim == 0:
        digest.update(np.asarray(dataset[()]).tobytes(order="C"))
        return digest.hexdigest()
    step = max(1, min(int(dataset.shape[0]), 1024))
    for start in range(0, int(dataset.shape[0]), step):
        digest.update(
            np.asarray(dataset[start : start + step]).tobytes(order="C")
        )
    return digest.hexdigest()


def _verify_matrix_storage(source: Path, h5ad_contract: dict[str, Any]) -> None:
    matrix_contract = h5ad_contract.get("matrix")
    if matrix_contract is None:
        return
    try:
        import h5py
    except ImportError as exc:  # pragma: no cover - anndata installs h5py
        raise GoldenNormanError("h5py is required to verify Golden matrix hashes") from exc

    with h5py.File(source, "r") as handle:
        x_contract = matrix_contract["X"]
        x_group = handle["X"]
        if x_contract["format"] != "csr" or x_group.attrs.get("encoding-type") != "csr_matrix":
            raise GoldenNormanError("source X is not the frozen CSR representation")
        if str(x_group["data"].dtype) != x_contract["dtype"]:
            raise GoldenNormanError("source X dtype changed")
        for key in ("data", "indices", "indptr"):
            expected = x_contract[f"{key}_sha256"]
            actual = _hash_h5_dataset(x_group[key])
            if actual != expected:
                raise GoldenNormanError(
                    f"source X/{key} hash mismatch: expected {expected}, got {actual}"
                )

        counts_contract = matrix_contract["counts"]
        counts = handle[counts_contract["location"]]
        if str(counts.dtype) != counts_contract["dtype"]:
            raise GoldenNormanError("source counts dtype changed")
        actual = _hash_h5_dataset(counts)
        expected = counts_contract["data_sha256"]
        if actual != expected:
            raise GoldenNormanError(
                f"source counts hash mismatch: expected {expected}, got {actual}"
            )


def _source_strings(values, label: str) -> list[str]:
    result = list(values)
    if any(
        not isinstance(value, str) or not value
        for value in result
    ):
        raise GoldenNormanError(f"{label} must be strings")
    return result


def _read_source_metadata(
    source: Path,
    contract: dict[str, Any],
) -> tuple[Any, Any, list[str], list[str]]:
    try:
        import anndata
    except ImportError as exc:
        raise GoldenNormanError("anndata is required for Golden Pack derivation") from exc

    source_contract = contract["source"]
    h5ad_contract = source_contract["h5ad"]
    if not source.is_file():
        raise GoldenNormanError(f"source H5AD does not exist: {source}")
    if source.stat().st_size != h5ad_contract["size_bytes"]:
        raise GoldenNormanError("source H5AD size mismatch")
    actual_hash = _file_hash(source)
    if actual_hash != h5ad_contract["sha256"]:
        raise GoldenNormanError(
            f"source H5AD hash mismatch: expected {h5ad_contract['sha256']}, "
            f"got {actual_hash}"
        )

    adata = anndata.read_h5ad(source, backed="r")
    try:
        if list(adata.shape) != h5ad_contract["shape"]:
            raise GoldenNormanError(
                f"source H5AD shape mismatch: expected {h5ad_contract['shape']}, "
                f"got {list(adata.shape)}"
            )
        obs = adata.obs.copy()
        var = adata.var.copy()
        observation_ids = _source_strings(
            adata.obs_names.tolist(),
            "observation ids",
        )
        feature_ids = _source_strings(
            adata.var_names.tolist(),
            "feature ids",
        )
    finally:
        adata.file.close()

    fields = source_contract["fields"]
    missing_obs = sorted(
        {
            fields["condition"],
            fields["split"],
            fields["guide"],
            fields["source_cell_type"],
        }.difference(obs.columns)
    )
    if missing_obs:
        raise GoldenNormanError(f"source H5AD missing obs fields: {missing_obs}")
    if fields["feature_symbol"] not in var.columns:
        raise GoldenNormanError("source H5AD missing feature symbol field")

    conditions = _source_strings(
        obs[fields["condition"]].tolist(),
        "source conditions",
    )
    splits = _source_strings(
        obs[fields["split"]].tolist(),
        "source splits",
    )
    guides = _source_strings(
        obs[fields["guide"]].tolist(),
        "source guides",
    )
    feature_symbols = _source_strings(
        var[fields["feature_symbol"]].tolist(),
        "feature symbols",
    )
    _checked_hash(
        observation_ids,
        h5ad_contract["observation_ids_sha256"],
        "source observation ids",
    )
    _checked_hash(
        feature_ids,
        h5ad_contract["feature_ids_sha256"],
        "source feature ids",
    )
    _checked_hash(
        feature_symbols,
        h5ad_contract["feature_symbols_sha256"],
        "source feature symbols",
    )
    _checked_hash(
        conditions,
        h5ad_contract["condition_by_observation_sha256"],
        "source condition",
    )
    _checked_hash(
        splits,
        h5ad_contract["split_by_observation_sha256"],
        "source split",
    )
    _checked_hash(
        guides,
        h5ad_contract["guide_by_observation_sha256"],
        "source guide",
    )
    feature_records_hash = h5ad_contract.get("feature_records_sha256")
    if feature_records_hash is not None:
        _checked_hash(
            [
                {"id": feature_id, "symbol": symbol}
                for feature_id, symbol in zip(
                    feature_ids,
                    feature_symbols,
                    strict=True,
                )
            ],
            feature_records_hash,
            "source feature records",
        )

    expected_cell_type = contract["biology"]["source_cell_type_value"]
    source_cell_types = obs[fields["source_cell_type"]].tolist()
    if any(value != expected_cell_type for value in source_cell_types):
        raise GoldenNormanError(
            "source cell_type changed; the known upstream metadata error must be preserved"
        )
    _verify_matrix_storage(source, h5ad_contract)
    return obs, var, feature_ids, feature_symbols


def _derive_semantics(
    obs,
    feature_ids: list[str],
    feature_symbols: list[str],
    contract: dict[str, Any],
) -> tuple[Any, list[dict[str, Any]], list[str], list[str]]:
    fields = contract["source"]["fields"]
    split_contract = contract["split"]
    biology = contract["biology"]
    expected = contract["expected"]

    symbol_to_id: dict[str, str] = {}
    for feature_id, symbol in zip(feature_ids, feature_symbols, strict=True):
        if symbol in symbol_to_id:
            raise GoldenNormanError(
                f"ambiguous source feature symbol cannot identify a target: {symbol!r}"
            )
        symbol_to_id[symbol] = feature_id

    source_mapping = split_contract["source_mapping"]
    source_control = split_contract["source_control_condition"]
    guide_to_partition = {
        guide: partition
        for partition, guide in split_contract["control_guides"].items()
    }
    control_ids = split_contract["control_condition_ids"]
    delimiter = split_contract["condition_delimiter"]
    ignored_control_target = split_contract["ignored_control_target"]

    golden_splits: list[str] = []
    condition_ids: list[str] = []
    perturbation_ids: list[str] = []
    matched_controls: list[str] = []
    condition_partition: dict[str, str] = {}
    targets_by_condition: dict[str, tuple[str, ...]] = {}

    for source_condition, source_split, guide in zip(
        obs[fields["condition"]].tolist(),
        obs[fields["split"]].tolist(),
        obs[fields["guide"]].tolist(),
        strict=True,
    ):
        if source_condition == source_control:
            partition = guide_to_partition.get(guide)
            if partition is None:
                raise GoldenNormanError(
                    f"control guide is not one of the three frozen guides: {guide!r}"
                )
            condition_id = control_ids[partition]
            perturbation_id = source_control
            targets: tuple[str, ...] = ()
        else:
            partition = source_mapping.get(source_split)
            if partition is None:
                raise GoldenNormanError(
                    f"unknown source split for non-control condition: {source_split!r}"
                )
            condition_id = str(source_condition)
            perturbation_id = str(source_condition)
            target_symbols = [
                value
                for value in str(source_condition).split(delimiter)
                if value != ignored_control_target
            ]
            if not target_symbols:
                raise GoldenNormanError(
                    f"non-control condition has no target: {source_condition!r}"
                )
            if len(set(target_symbols)) != len(target_symbols):
                raise GoldenNormanError(
                    f"condition contains duplicate target symbols: {source_condition!r}"
                )
            unknown = sorted(set(target_symbols).difference(symbol_to_id))
            if unknown:
                raise GoldenNormanError(
                    f"condition contains unknown source target symbols: {unknown}"
                )
            targets = tuple(symbol_to_id[symbol] for symbol in target_symbols)

        previous_partition = condition_partition.setdefault(condition_id, partition)
        if previous_partition != partition:
            raise GoldenNormanError(
                f"condition occurs in multiple Golden partitions: {condition_id!r}"
            )
        previous_targets = targets_by_condition.setdefault(condition_id, targets)
        if previous_targets != targets:
            raise GoldenNormanError(
                f"condition target definition is inconsistent: {condition_id!r}"
            )
        golden_splits.append(partition)
        condition_ids.append(condition_id)
        perturbation_ids.append(perturbation_id)
        matched_controls.append(control_ids[partition])

    if "control_assignment_sha256" in expected:
        _checked_hash(
            [
                {
                    "obs_id": observation_id,
                    "guide_identity": guide,
                    "split": partition,
                }
                for observation_id, source_condition, guide, partition in zip(
                    obs.index.tolist(),
                    obs[fields["condition"]].tolist(),
                    obs[fields["guide"]].tolist(),
                    golden_splits,
                    strict=True,
                )
                if source_condition == source_control
            ],
            expected["control_assignment_sha256"],
            "Golden control assignment",
        )

    observed_control_partitions = {
        partition
        for condition_id, partition in condition_partition.items()
        if condition_id == control_ids[partition]
    }
    if observed_control_partitions != set(_PARTITIONS):
        raise GoldenNormanError(
            "all three frozen control guides must have observations"
        )

    output = obs.copy()
    output["observation_id"] = [str(value) for value in obs.index.tolist()]
    output["cell_identity_id"] = biology["cell_identity_id"]
    output["cell_state_id"] = biology["state_id"]
    output["cell_context_id"] = biology["context_id"]
    output["condition_id"] = condition_ids
    output["perturbation_id"] = perturbation_ids
    output["matched_control_id"] = matched_controls
    output["dose_value"] = [
        biology["dose"]["control"]
        if value == source_control
        else biology["dose"]["perturbation"]
        for value in perturbation_ids
    ]
    output["dose_unit"] = biology["dose"]["unit"]
    output["time_value"] = biology["time"]["value"]
    output["time_unit"] = biology["time"]["unit"]
    output["split"] = golden_splits

    for values, field, label in (
        (
            golden_splits,
            "golden_split_by_observation_sha256",
            "Golden split",
        ),
        (
            condition_ids,
            "condition_id_by_observation_sha256",
            "Golden condition ids",
        ),
        (
            matched_controls,
            "matched_control_by_observation_sha256",
            "Golden matched controls",
        ),
        (
            perturbation_ids,
            "perturbation_id_by_observation_sha256",
            "Golden perturbation ids",
        ),
    ):
        if field in expected:
            _checked_hash(values, expected[field], label)

    rows_by_split = {
        partition: golden_splits.count(partition) for partition in _PARTITIONS
    }
    controls_by_split = {
        partition: sum(
            condition_id == control_ids[partition]
            for condition_id in condition_ids
        )
        for partition in _PARTITIONS
    }
    noncontrol_conditions_by_split = {
        partition: len(
            {
                condition_id
                for condition_id, value in condition_partition.items()
                if value == partition and condition_id != control_ids[partition]
            }
        )
        for partition in _PARTITIONS
    }
    for actual, key in (
        (rows_by_split, "rows_by_split"),
        (controls_by_split, "controls_by_split"),
        (noncontrol_conditions_by_split, "noncontrol_conditions_by_split"),
    ):
        if actual != expected[key]:
            raise GoldenNormanError(
                f"{key} mismatch: expected {expected[key]}, got {actual}"
            )

    noncontrols = sorted(
        condition_id
        for condition_id in condition_partition
        if condition_id not in set(control_ids.values())
    )
    condition_values = sorted(
        [control_ids[key] for key in _PARTITIONS] + noncontrols
    )
    perturbation_records = [
        {"id": source_control, "kind": "control", "targets": []}
    ] + [
        {
            "id": condition_id,
            "kind": "genetic",
            "targets": list(targets_by_condition[condition_id]),
        }
        for condition_id in noncontrols
    ]
    if "condition_values_sha256" in expected:
        _checked_hash(
            condition_values,
            expected["condition_values_sha256"],
            "Golden condition values",
        )
    if "perturbation_records_sha256" in expected:
        _checked_hash(
            perturbation_records,
            expected["perturbation_records_sha256"],
            "Golden perturbation records",
        )

    target_set = {
        target
        for condition_id, targets in targets_by_condition.items()
        if condition_id not in set(control_ids.values())
        for target in targets
    }
    target_ids = sorted(target_set)
    train_target_set = {
        target
        for condition_id, targets in targets_by_condition.items()
        if condition_partition[condition_id] == "train"
        and condition_id != control_ids["train"]
        for target in targets
    }
    unseen_train_target_ids = [
        target for target in target_ids if target not in train_target_set
    ]
    _checked_hash(
        target_ids,
        expected["target_ids_sha256"],
        "Golden target ids",
    )
    _checked_hash(
        unseen_train_target_ids,
        expected["unseen_train_target_ids_sha256"],
        "Golden unseen-train target ids",
    )
    return output, perturbation_records, condition_values, target_ids


def _write_obs(asset: Path, obs) -> None:
    try:
        import anndata
        import h5py
    except ImportError as exc:
        raise GoldenNormanError("anndata and h5py are required to write the Pack") from exc
    with h5py.File(asset, "r+") as handle:
        del handle["obs"]
        anndata.io.write_elem(handle, "obs", obs)


def _pack_manifest(
    contract: dict[str, Any],
    asset: Path,
    contract_asset: Path,
    conditions: list[str],
    perturbations: list[dict[str, Any]],
) -> dict[str, Any]:
    biology = contract["biology"]
    return {
        "schema_version": "vc.pack.v0.2",
        "pack_id": contract["benchmark_id"],
        "pack_version": contract["pack_version"],
        "taxon": biology["taxon"],
        "assembly": biology["assembly"],
        "identity": {
            "observation_key": "observation_id",
            "feature_key": "var_names",
        },
        "modality": {"name": "scRNA", "ontology_id": "EFO:0008913"},
        "feature_namespace": biology["feature_namespace"],
        "feature_semantics": {
            "id_source": "var_names",
            "id_format": "ensembl_gene",
            "symbol_field": contract["source"]["fields"]["feature_symbol"],
        },
        "cell_semantics": {
            "identity": "cell_identity_id",
            "state": ["cell_state_id"],
            "context": ["cell_context_id"],
            "local_terms": [
                {
                    "id": biology["state_id"],
                    "role": "state",
                    "label": "unspecified source state",
                    "definition": (
                        "The frozen source does not provide a more specific "
                        "cell-state ontology annotation."
                    ),
                },
                {
                    "id": biology["context_id"],
                    "role": "context",
                    "label": "in vitro",
                    "definition": "Cells assayed in the Norman et al. in-vitro experiment.",
                },
            ],
        },
        "assets": [
            {
                "id": "expression",
                "path": asset.name,
                "media_type": "application/vnd.anndata+hdf5",
                "sha256": _file_hash(asset),
                "size_bytes": asset.stat().st_size,
            },
            {
                "id": "golden-contract",
                "path": contract_asset.name,
                "media_type": "application/json",
                "sha256": _file_hash(contract_asset),
                "size_bytes": contract_asset.stat().st_size,
            },
        ],
        "matrix": {
            "asset": "expression",
            "location": "X",
            "shape": contract["source"]["h5ad"]["shape"],
        },
        "conditions": {
            "field": "condition_id",
            "values": conditions,
            "matched_control_field": "matched_control_id",
            "dose": {"value_field": "dose_value", "unit_field": "dose_unit"},
            "time": {"value_field": "time_value", "unit_field": "time_unit"},
        },
        "perturbations": {
            "field": "perturbation_id",
            "values": perturbations,
        },
        "split": {
            "name": contract["split"]["name"],
            "field": "split",
            "strategy": "predefined",
            "values": list(_PARTITIONS),
            "leakage_guard": contract["split"]["leakage_guard"],
        },
        "provenance": {
            "source": contract["source"]["dataset_doi"],
            "created_by": "PRAXIS-VirtualCell Phase 8 deterministic derivation",
            "citation": "Norman et al., Science 2019, doi:10.1126/science.aax4438",
        },
        "license": {
            "id": "CC0-1.0",
            "name": "CC0 1.0",
            "url": "https://creativecommons.org/publicdomain/zero/1.0/",
        },
    }


def derive_pack(
    source_h5ad: str | Path,
    output_dir: str | Path,
    *,
    contract: Mapping[str, Any] | None = None,
) -> Path:
    """Copy the frozen H5AD and add explicit Pack semantics without changing arrays."""

    source = Path(source_h5ad).resolve()
    output = Path(output_dir).resolve()
    if output.exists():
        raise GoldenNormanError(f"output Pack directory already exists: {output}")
    value = _coerce_contract(contract)
    obs, _var, feature_ids, feature_symbols = _read_source_metadata(source, value)
    derived_obs, perturbations, conditions, _target_ids = _derive_semantics(
        obs,
        feature_ids,
        feature_symbols,
        value,
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.", dir=str(output.parent))
    )
    try:
        asset = temporary / "norman_k562_golden.h5ad"
        shutil.copyfile(source, asset)
        _write_obs(asset, derived_obs)
        contract_asset = temporary / "golden_contract.json"
        contract_asset.write_bytes(_canonical_bytes(value) + b"\n")
        manifest = _pack_manifest(
            value,
            asset,
            contract_asset,
            conditions,
            perturbations,
        )
        (temporary / "manifest.yaml").write_text(
            yaml.safe_dump(manifest, sort_keys=False),
            encoding="utf-8",
        )
        PackRegistry().register(temporary)
        temporary.replace(output)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return output


def _pack_condition_deltas(
    pack_root: Path,
    *,
    pack_registry: PackRegistry | None = None,
) -> tuple[
    Any,
    dict[str, np.ndarray],
    dict[str, tuple[str, ...]],
    dict[str, str],
    list[str],
]:
    try:
        import anndata
        from scipy import sparse
    except ImportError as exc:
        raise GoldenNormanError("anndata and scipy are required for baselines") from exc

    packs = PackRegistry() if pack_registry is None else pack_registry
    manifest = packs.register(pack_root)
    asset = next(item for item in manifest.assets if item.id == "expression")
    adata = anndata.read_h5ad(pack_root / asset.path, backed="r")
    try:
        obs = adata.obs.copy()
        feature_ids = [str(value) for value in adata.var_names.tolist()]
        condition_ids = obs["condition_id"].tolist()
        unique_conditions = sorted(set(condition_ids))
        sums = {
            condition_id: np.zeros(len(feature_ids), dtype=np.float64)
            for condition_id in unique_conditions
        }
        counts = {condition_id: 0 for condition_id in unique_conditions}
        chunk_size = 512
        for start in range(0, adata.n_obs, chunk_size):
            stop = min(start + chunk_size, adata.n_obs)
            labels = np.asarray(condition_ids[start:stop], dtype=object)
            block = adata.X[start:stop]
            for condition_id in sorted(set(labels.tolist())):
                positions = np.flatnonzero(labels == condition_id)
                selected = block[positions]
                summed = selected.sum(axis=0)
                if sparse.issparse(summed):
                    summed = summed.toarray()
                sums[condition_id] += np.asarray(summed).reshape(-1)
                counts[condition_id] += len(positions)
    finally:
        adata.file.close()

    perturbation_by_id = {
        item.id: item for item in manifest.perturbations.values
    }
    first_row_by_condition = {
        condition_id: int(np.flatnonzero(np.asarray(condition_ids) == condition_id)[0])
        for condition_id in unique_conditions
    }
    deltas: dict[str, np.ndarray] = {}
    targets: dict[str, tuple[str, ...]] = {}
    partitions: dict[str, str] = {}
    for condition_id in unique_conditions:
        row = first_row_by_condition[condition_id]
        perturbation = perturbation_by_id[obs.iloc[row]["perturbation_id"]]
        if perturbation.kind == "control":
            continue
        control_id = obs.iloc[row]["matched_control_id"]
        deltas[condition_id] = (
            sums[condition_id] / counts[condition_id]
            - sums[control_id] / counts[control_id]
        )
        targets[condition_id] = perturbation.targets
        partitions[condition_id] = obs.iloc[row]["split"]
    return manifest, deltas, targets, partitions, feature_ids


def _save_array(path: Path, array: np.ndarray) -> dict[str, Any]:
    value = np.asarray(array, dtype="<f8")
    np.save(path, value, allow_pickle=False)
    return {
        "filename": path.name,
        "sha256": _file_hash(path),
        "shape": list(value.shape),
        "dtype": "float64",
    }


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(_canonical_bytes(value) + b"\n")


def _model_card(
    baseline: str,
    metadata: dict[str, Any],
    asset_dir: Path,
    contract: dict[str, Any],
) -> dict[str, Any]:
    model_name = contract["baselines"][baseline]["model_name"]
    assets = []
    for filename in ["baseline.json", *sorted(metadata["arrays"])]:
        path = asset_dir / filename
        assets.append(
            {
                "filename": filename,
                "sha256": _file_hash(path),
                "media_type": (
                    "application/json"
                    if filename.endswith(".json")
                    else "application/x-npy"
                ),
                "source_note": (
                    "Deterministically derived from the hash-locked Golden "
                    "Norman training partition."
                ),
            }
        )
    biology = contract["biology"]
    metric = contract["metric"]["name"]
    return {
        "schema_version": "vc.model-card.v1",
        "name": model_name,
        "type": "self_trained",
        "species": ["human"],
        "taxon": [biology["taxon"]["ontology_id"]],
        "module": "genetic_hub",
        "modality": [{"name": "scRNA", "ontology_id": "EFO:0008913"}],
        "assay": ["EFO:0008913"],
        "cell_domain": {
            "cell_type_ids": [biology["cell_identity_id"]],
            "cell_type_names": ["K562"],
            "tissue_ids": [],
            "tissue_names": [],
            "allow_unspecified": False,
        },
        "perturbation": ["gene"],
        "task": "predict_delta_expression",
        "output": ["delta_expression"],
        "feature_namespace": [
            {
                **biology["feature_namespace"],
                "id_format": "ensembl_gene",
            }
        ],
        "representation": ["matrix:X"],
        "source": "cache:golden-norman",
        "license": "CC0-1.0",
        "status": "available",
        "wrapper": _WRAPPER,
        "version": contract["pack_version"],
        "requires": [],
        "assets": assets,
        "resources": {"python_dependencies": [], "required": ["cpu"]},
        "uncertainty": {
            "required": True,
            "methods": ["point_estimate"],
            "calibrated": False,
        },
        "ood": {
            "action": "abstain",
            "dimensions": [
                "taxon",
                "modality",
                "assay",
                "cell_domain",
                "perturbation",
                "task",
                "output",
                "feature_namespace",
                "representation",
            ],
        },
        "reliability_policy": "benchmark_baseline_not_scientifically_validated",
        "training_card": {
            "training_data": (
                f"{contract['benchmark_id']}@{contract['pack_version']} train"
            ),
            "split": contract["split"]["name"],
            "baseline": contract["baselines"][baseline]["definition"],
            "metrics": {
                "primary": metric,
                "result_location": "external Golden evaluation artifact",
            },
            "provenance": "Golden contract and all assets are SHA-256 locked",
        },
        "provenance": {
            "pack_fingerprint": metadata["pack"]["fingerprint"],
            "contract_sha256": metadata["contract_sha256"],
            "scientifically_validated": False,
            "distributable": True,
        },
    }


def build_baseline_assets(
    pack_root: str | Path,
    model_cache_root: str | Path,
    registry_root: str | Path,
    *,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, dict[str, Path]]:
    """Fit the three fixed condition-level baselines and write hash-locked assets."""

    value = _coerce_contract(contract)
    pack = Path(pack_root).resolve()
    cache_root = Path(model_cache_root).resolve()
    registries = Path(registry_root).resolve()
    manifest, deltas, condition_targets, partitions, feature_ids = (
        _pack_condition_deltas(pack)
    )
    if (
        manifest.pack_id != value["benchmark_id"]
        or manifest.pack_version != value["pack_version"]
    ):
        raise GoldenNormanError("baseline Pack identity does not match the contract")

    train_conditions = sorted(
        condition_id
        for condition_id, partition in partitions.items()
        if partition == "train"
    )
    if not train_conditions:
        raise GoldenNormanError("Golden training partition has no perturbation conditions")
    train_deltas = np.stack([deltas[value] for value in train_conditions])
    target_set = {
        target for targets in condition_targets.values() for target in targets
    }
    target_ids = sorted(target_set)
    target_position = {value: index for index, value in enumerate(target_ids)}
    design = np.zeros((len(train_conditions), len(target_ids)), dtype=np.float64)
    for row, condition_id in enumerate(train_conditions):
        for target in condition_targets[condition_id]:
            design[row, target_position[target]] = 1.0
    seen_target_ids = [
        target_ids[index]
        for index in np.flatnonzero(design.sum(axis=0) > 0).tolist()
    ]
    unseen_target_ids = [
        value for value in target_ids if value not in set(seen_target_ids)
    ]

    global_mean = train_deltas.mean(axis=0)
    x_mean = design.mean(axis=0)
    y_mean = train_deltas.mean(axis=0)
    centered_x = design - x_mean
    centered_y = train_deltas - y_mean
    alpha = float(value["baselines"]["additive_linear"]["alpha"])
    coefficients = np.linalg.solve(
        centered_x.T @ centered_x + alpha * np.eye(len(target_ids)),
        centered_x.T @ centered_y,
    )
    intercept = y_mean - x_mean @ coefficients

    cache_root.mkdir(parents=True, exist_ok=True)
    registries.mkdir(parents=True, exist_ok=True)
    result: dict[str, dict[str, Path]] = {}
    for baseline in _BASELINES:
        model_name = value["baselines"][baseline]["model_name"]
        asset_dir = cache_root / model_name
        if asset_dir.exists():
            raise GoldenNormanError(
                f"baseline asset directory already exists: {asset_dir}"
            )
        asset_dir.mkdir()
        arrays: dict[str, Any] = {}
        if baseline == "global_mean":
            arrays["global_mean_delta.npy"] = _save_array(
                asset_dir / "global_mean_delta.npy",
                global_mean,
            )
        elif baseline == "additive_linear":
            arrays["linear_coefficients.npy"] = _save_array(
                asset_dir / "linear_coefficients.npy",
                coefficients,
            )
            arrays["linear_intercept.npy"] = _save_array(
                asset_dir / "linear_intercept.npy",
                intercept,
            )
        metadata = {
            "schema_version": "vc.golden-baseline.v1",
            "baseline": baseline,
            "model_name": model_name,
            "algorithm": value["baselines"][baseline]["definition"],
            "pack": {
                "id": manifest.pack_id,
                "version": manifest.pack_version,
                "fingerprint": manifest.fingerprint(),
            },
            "contract_sha256": _canonical_hash(value),
            "feature_ids": feature_ids,
            "feature_ids_sha256": _canonical_hash(feature_ids),
            "target_ids": target_ids,
            "target_ids_sha256": _canonical_hash(target_ids),
            "seen_train_target_ids": seen_target_ids,
            "unseen_train_target_ids": unseen_target_ids,
            "train_condition_ids_sha256": _canonical_hash(train_conditions),
            "arrays": arrays,
        }
        _write_json(asset_dir / "baseline.json", metadata)
        card = _model_card(baseline, metadata, asset_dir, value)
        registry = registries / f"{baseline}.yaml"
        registry.write_text(
            yaml.safe_dump({"models": {model_name: card}}, sort_keys=False),
            encoding="utf-8",
        )
        ModelZooRegistry(registry_path=str(registry))
        result[baseline] = {"asset_dir": asset_dir, "registry": registry}
    return result


def _load_array(asset_dir: Path, record: dict[str, Any]) -> np.ndarray:
    path = asset_dir / record["filename"]
    if not path.is_file():
        raise GoldenNormanError(f"baseline array is missing: {path.name}")
    actual = _file_hash(path)
    if actual != record["sha256"]:
        raise GoldenNormanError(
            f"baseline array hash mismatch for {path.name}: "
            f"expected {record['sha256']}, got {actual}"
        )
    value = np.load(path, allow_pickle=False)
    if list(value.shape) != record["shape"] or str(value.dtype) != record["dtype"]:
        raise GoldenNormanError(f"baseline array contract changed: {path.name}")
    if not np.isfinite(value).all():
        raise GoldenNormanError(f"baseline array is non-finite: {path.name}")
    return value


def predict_from_artifact(
    asset_dir: str | Path,
    target_ids: Sequence[str],
) -> dict[str, Any]:
    """Predict from an exact baseline artifact; target IDs are never converted."""

    root = Path(asset_dir)
    metadata_path = root / "baseline.json"
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GoldenNormanError(f"cannot load baseline metadata: {exc}") from exc
    if metadata.get("schema_version") != "vc.golden-baseline.v1":
        raise GoldenNormanError("unsupported baseline artifact schema")
    baseline = metadata.get("baseline")
    if baseline not in _BASELINES:
        raise GoldenNormanError(f"unknown baseline artifact: {baseline!r}")
    if not isinstance(target_ids, Sequence) or isinstance(target_ids, (str, bytes)):
        raise GoldenNormanError("targets must be an ordered sequence of canonical IDs")
    targets = list(target_ids)
    if not targets or any(not isinstance(value, str) or not value for value in targets):
        raise GoldenNormanError("targets must contain canonical non-empty IDs")
    if len(set(targets)) != len(targets):
        raise GoldenNormanError("duplicate target IDs are not allowed")
    known_targets = metadata.get("target_ids")
    if not isinstance(known_targets, list):
        raise GoldenNormanError("baseline target universe is missing")
    unknown = sorted(set(targets).difference(known_targets))
    if unknown:
        raise GoldenNormanError(
            f"unknown target IDs; no symbol conversion or fallback is allowed: {unknown}"
        )

    feature_ids = metadata.get("feature_ids")
    if (
        not isinstance(feature_ids, list)
        or _canonical_hash(feature_ids) != metadata.get("feature_ids_sha256")
    ):
        raise GoldenNormanError("baseline ordered feature IDs are invalid")
    arrays = metadata.get("arrays")
    if not isinstance(arrays, dict):
        raise GoldenNormanError("baseline arrays contract is invalid")
    if baseline == "no_change":
        delta = np.zeros(len(feature_ids), dtype=np.float64)
    elif baseline == "global_mean":
        delta = _load_array(root, arrays["global_mean_delta.npy"])
    else:
        coefficients = _load_array(root, arrays["linear_coefficients.npy"])
        intercept = _load_array(root, arrays["linear_intercept.npy"])
        design = np.zeros(len(known_targets), dtype=np.float64)
        target_position = {
            value: index for index, value in enumerate(known_targets)
        }
        for target in targets:
            design[target_position[target]] = 1.0
        delta = intercept + design @ coefficients
    if delta.shape != (len(feature_ids),) or not np.isfinite(delta).all():
        raise GoldenNormanError("baseline prediction violates the feature contract")
    unseen = set(metadata.get("unseen_train_target_ids", []))
    return {
        "delta": delta,
        "baseline": baseline,
        "feature_ids_sha256": metadata["feature_ids_sha256"],
        "n_features": len(feature_ids),
        "value_type": "delta_expression",
        "unseen_train_targets": [value for value in targets if value in unseen],
    }


def condition_macro_mse(
    truth: Mapping[str, np.ndarray],
    prediction: Mapping[str, np.ndarray],
) -> tuple[float, dict[str, float]]:
    """Equal-weight condition macro MSE over every ordered Pack feature."""

    if not truth or set(truth) != set(prediction):
        raise GoldenNormanError("truth and prediction condition IDs must match exactly")
    losses: dict[str, float] = {}
    for condition_id in sorted(truth):
        observed = np.asarray(truth[condition_id], dtype=np.float64)
        predicted = np.asarray(prediction[condition_id], dtype=np.float64)
        if (
            observed.ndim != 1
            or observed.shape != predicted.shape
            or not np.isfinite(observed).all()
            or not np.isfinite(predicted).all()
        ):
            raise GoldenNormanError(
                f"invalid truth/prediction vector for {condition_id!r}"
            )
        losses[condition_id] = float(np.mean(np.square(predicted - observed)))
    return float(np.mean(list(losses.values()))), losses


def paired_bootstrap_ci(values: Sequence[float]) -> dict[str, Any]:
    """Frozen condition-level PCG64 percentile interval for a mean or paired delta."""

    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 1 or array.size == 0 or not np.isfinite(array).all():
        raise GoldenNormanError("bootstrap values must be a non-empty finite vector")
    rng = np.random.Generator(np.random.PCG64(0))
    positions = rng.integers(0, array.size, size=(2000, array.size))
    means = array[positions].mean(axis=1)
    low, high = np.quantile(means, [0.025, 0.975], method="linear")
    return {
        "estimate": float(array.mean()),
        "low": float(low),
        "high": float(high),
        "unit": "held_out_perturbation_condition",
        "method": "paired_percentile",
        "rng": "numpy.PCG64",
        "seed": 0,
        "replicates": 2000,
        "interval": [0.025, 0.975],
        "quantile_method": "linear",
    }


def run_baseline_runtime(
    pack_root: str | Path,
    registry_path: str | Path,
    model_cache_root: str | Path,
    target_ids: Sequence[str],
) -> dict[str, Any]:
    """Run one one-card baseline through Pack→broker→governance→Report."""

    pack = Path(pack_root)
    manifest = load_manifest(pack / "manifest.yaml")
    packs = PackRegistry()
    packs.register(pack)
    zoo = ModelZooRegistry(registry_path=str(registry_path))
    if len(zoo.capability_names()) != 1:
        raise GoldenNormanError("a baseline runtime registry must contain exactly one card")
    model_name = zoo.capability_names()[0]
    request = VirtualCellRequest.from_dict(
        {
            "request_id": f"golden-{model_name}-{_canonical_hash(list(target_ids))[:12]}",
            "species": "human",
            "cell_type": "K562",
            "perturbation_type": "gene",
            "perturbation_targets": list(target_ids),
            "input_modality": "scRNA",
            "output_modality": "delta_expression",
            "task_type": "predict_delta_expression",
        }
    )
    runtime = build_runtime(
        model_registry=zoo,
        model_cache=ModelCache(root=str(model_cache_root)),
        pack_registry=packs,
    )
    return runtime.run_workflow(
        request,
        pack_id=manifest.pack_id,
        pack_version=manifest.pack_version,
    )


def _evaluation_request(
    baseline: str,
    condition_id: str,
    target_ids: Sequence[str],
) -> VirtualCellRequest:
    return VirtualCellRequest.from_dict(
        {
            "request_id": (
                f"golden-eval-{baseline}-"
                f"{_canonical_hash([condition_id, *target_ids])[:12]}"
            ),
            "species": "human",
            "cell_type": "K562",
            "perturbation_type": "gene",
            "perturbation_targets": list(target_ids),
            "input_modality": "scRNA",
            "output_modality": "delta_expression",
            "task_type": "predict_delta_expression",
        }
    )


def _stable_runtime_evidence(
    report: dict[str, Any],
    compatibility: dict[str, Any],
    step: dict[str, Any],
) -> tuple[str, str]:
    """Hash formal runtime evidence without machine-local cache paths."""

    compatibility_contract = {
        key: value
        for key, value in compatibility.items()
        if key != "asset_paths"
    }
    execution_contract = {
        key: value
        for key, value in step.items()
        if key not in {"asset_paths", "compatibility_fingerprint"}
    }
    report_contract = {
        "request": report["request"],
        "request_id": report["request_id"],
        "abstain": report["abstain"],
        "reliability": report["reliability"],
        "prediction": report["prediction"],
        "models_used": report["models_used"],
        "models_rejected": report["models_rejected"],
        "models_failed": report["models_failed"],
        "abstain_reasons": report["abstain_reasons"],
        "downgrade_reasons": report["downgrade_reasons"],
        "failed_checks": report["failed_checks"],
        "model_disagreement": report["model_disagreement"],
        "critic_violations": report["critic_violations"],
        "per_call_hashes": report["provenance"]["per_call_hashes"],
        "compatibility": compatibility_contract,
        "execution_step": execution_contract,
    }
    return _canonical_hash(compatibility_contract), _canonical_hash(report_contract)


def evaluate_baselines(
    pack_root: str | Path,
    model_cache_root: str | Path,
    registry_root: str | Path,
    output_path: str | Path,
    *,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Score all validation/test conditions through the formal one-card runtime."""

    value = _coerce_contract(contract)
    pack = Path(pack_root).resolve()
    cache_root = Path(model_cache_root).resolve()
    registries = Path(registry_root).resolve()
    output = Path(output_path).resolve()
    if output.exists():
        raise GoldenNormanError(f"evaluation artifact already exists: {output}")

    pack_registry = PackRegistry()
    manifest, truth, targets, partitions, feature_ids = _pack_condition_deltas(
        pack,
        pack_registry=pack_registry,
    )
    conditions_by_partition = {
        partition: sorted(
            condition_id
            for condition_id, assigned in partitions.items()
            if assigned == partition
        )
        for partition in ("validation", "test")
    }
    expected_counts = value["expected"]["noncontrol_conditions_by_split"]
    for partition, conditions in conditions_by_partition.items():
        if len(conditions) != expected_counts[partition]:
            raise GoldenNormanError(
                f"{partition} condition count mismatch before evaluation"
            )

    results: dict[str, Any] = {}
    card_inventory: dict[str, Any] = {}
    for baseline in _BASELINES:
        registry_path = registries / f"{baseline}.yaml"
        zoo = ModelZooRegistry(registry_path=str(registry_path))
        names = zoo.capability_names()
        if names != [value["baselines"][baseline]["model_name"]]:
            raise GoldenNormanError(
                f"{baseline} registry is not the frozen one-card registry"
            )
        model_name = names[0]
        card = zoo.card(model_name)
        runtime = build_runtime(
            model_registry=zoo,
            model_cache=ModelCache(root=str(cache_root)),
            pack_registry=pack_registry,
        )
        card_inventory[baseline] = {
            "model_name": model_name,
            "model_card_fingerprint": card.fingerprint(),
            "assets": {
                asset.filename: asset.sha256 for asset in card.assets
            },
        }
        baseline_results: dict[str, Any] = {}
        for partition in ("validation", "test"):
            predictions: dict[str, np.ndarray] = {}
            formal_runtime: list[dict[str, Any]] = []
            for condition_id in conditions_by_partition[partition]:
                report = runtime.run_workflow(
                    _evaluation_request(
                        baseline,
                        condition_id,
                        targets[condition_id],
                    ),
                    pack_id=manifest.pack_id,
                    pack_version=manifest.pack_version,
                )
                if (
                    report.get("abstain")
                    or report.get("models_used") != [model_name]
                    or not isinstance(report.get("prediction"), dict)
                ):
                    raise GoldenNormanError(
                        f"formal runtime did not produce {baseline} for "
                        f"{condition_id!r}"
                    )
                prediction = report["prediction"]
                if (
                    prediction.get("baseline") != baseline
                    or prediction.get("feature_ids_sha256")
                    != _canonical_hash(feature_ids)
                    or prediction.get("n_features") != len(feature_ids)
                    or prediction.get("value_type") != "delta_expression"
                ):
                    raise GoldenNormanError(
                        f"formal runtime metadata mismatch for {condition_id!r}"
                    )
                vector = np.asarray(prediction["delta"], dtype=np.float64)
                if vector.shape != (len(feature_ids),) or not np.isfinite(vector).all():
                    raise GoldenNormanError(
                        f"formal runtime vector mismatch for {condition_id!r}"
                    )
                predictions[condition_id] = vector
                compatibility = report["provenance"]["compatibility_reports"][0]
                if (
                    compatibility["pack_valid"] is not True
                    or compatibility["model_compatible"] is not True
                    or compatibility["scientifically_validated"] is not False
                ):
                    raise GoldenNormanError(
                        f"compatibility states changed for {condition_id!r}"
                    )
                step = report["provenance"]["execution_plan"]["steps"][0]
                compatibility_hash, report_hash = _stable_runtime_evidence(
                    report,
                    compatibility,
                    step,
                )
                formal_runtime.append(
                    {
                        "condition_id": condition_id,
                        "targets": list(targets[condition_id]),
                        "abstain": False,
                        "model_name": model_name,
                        "prediction_sha256": _canonical_hash(
                            prediction["delta"]
                        ),
                        "report_contract_sha256": report_hash,
                        "compatibility_contract_sha256": compatibility_hash,
                        "pack_valid": True,
                        "model_compatible": True,
                        "scientifically_validated": False,
                    }
                )
            partition_truth = {
                condition_id: truth[condition_id]
                for condition_id in conditions_by_partition[partition]
            }
            score, losses = condition_macro_mse(partition_truth, predictions)
            baseline_results[partition] = {
                "score": score,
                "condition_losses": losses,
                "bootstrap": paired_bootstrap_ci(
                    [losses[key] for key in conditions_by_partition[partition]]
                ),
                "formal_runtime": formal_runtime,
            }
        results[baseline] = baseline_results

    paired_comparisons: dict[str, Any] = {}
    for first_index, first in enumerate(_BASELINES):
        for second in _BASELINES[first_index + 1 :]:
            ordered = conditions_by_partition["test"]
            differences = [
                results[first]["test"]["condition_losses"][condition_id]
                - results[second]["test"]["condition_losses"][condition_id]
                for condition_id in ordered
            ]
            paired_comparisons[f"{first}_minus_{second}"] = paired_bootstrap_ci(
                differences
            )

    artifact = {
        "schema_version": "vc.golden-evaluation.v1",
        "benchmark_id": value["benchmark_id"],
        "pack": {
            "id": manifest.pack_id,
            "version": manifest.pack_version,
            "fingerprint": manifest.fingerprint(),
            "assets": {
                asset.path: {
                    "sha256": asset.sha256,
                    "size_bytes": asset.size_bytes,
                }
                for asset in manifest.assets
            },
        },
        "contract_sha256": _canonical_hash(value),
        "primary_metric": value["metric"],
        "partitions": {
            partition: {
                "condition_ids": conditions,
                "n_conditions": len(conditions),
                "truth_by_condition_sha256": {
                    condition_id: _canonical_hash(
                        truth[condition_id].tolist()
                    )
                    for condition_id in conditions
                },
            }
            for partition, conditions in conditions_by_partition.items()
        },
        "model_cards": card_inventory,
        "results": results,
        "paired_test_comparisons": paired_comparisons,
        "states": {
            "pack_valid": True,
            "model_compatible": True,
            "scientifically_validated": False,
        },
        "gears": {
            "run": False,
            "assets_accessed": False,
            "reason": "outside Phase 8 authorization",
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    _write_json(output, artifact)
    return artifact
