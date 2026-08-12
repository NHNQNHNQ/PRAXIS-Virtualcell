#!/usr/bin/env python3
"""Run the preregistered GSE220974 external stress test, never P16 validation."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import itertools
import json
import math
import os
import platform
from importlib.metadata import version
from pathlib import Path, PurePosixPath
from typing import Any

import anndata
import numpy as np
import pandas as pd
from scipy import io, sparse, stats

from praxis_virtualcell.benchmarks import golden_norman
from praxis_virtualcell.data_packs.validator import validate_pack
from praxis_virtualcell.model_zoo.registry import ModelZooRegistry


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _barcodes(path: Path) -> list[str]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as stream:
        rows = [line.rstrip("\r\n").split("\t") for line in stream]
    if any(len(row) != 1 or not row[0] for row in rows):
        raise ValueError("external barcode file must contain one non-empty column")
    return [row[0] for row in rows]


def _feature_symbols(path: Path) -> list[str]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as stream:
        rows = [line.rstrip("\r\n").split("\t") for line in stream]
    if any(len(row) != 3 or not row[0] or not row[1] or row[2] != "Gene Expression" for row in rows):
        raise ValueError("external RNA feature contract changed")
    return [row[1] for row in rows]


def _exact_sign_flip_p(differences: np.ndarray) -> float:
    if differences.shape != (5,) or not np.isfinite(differences).all():
        raise ValueError("the exact sign-flip test requires five finite effects")
    observed = float(differences.mean())
    null = [
        float(np.mean(differences * np.asarray(signs, dtype=np.float64)))
        for signs in itertools.product((-1.0, 1.0), repeat=5)
    ]
    return sum(value >= observed - 1e-15 for value in null) / len(null)


def _log_normalise(expression: sparse.spmatrix, library_sizes: np.ndarray) -> sparse.csc_matrix:
    normalised = expression.multiply(10000.0 / library_sizes).tocsc()
    normalised.data = np.log1p(normalised.data)
    return normalised


def _checked_file(root: Path, name: str, record: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    path = root / name
    if path.is_symlink() or not path.is_file() or path.stat().st_size != record["size_bytes"]:
        raise ValueError(f"external input identity mismatch: {name}")
    actual = _sha256(path)
    expected = record["sha256_known_before_outcome"]
    if expected is not None and actual != expected:
        raise ValueError(f"external input SHA-256 mismatch: {name}")
    return path, {"size_bytes": path.stat().st_size, "sha256": actual}


def _model_card(
    *, protocol_path: Path, relative_path: str, expected_name: str, expected_fingerprint: str
) -> tuple[Path, str]:
    relative = PurePosixPath(relative_path)
    if (
        relative.is_absolute()
        or not relative.parts
        or any(part in (".", "..") for part in relative.parts)
        or str(relative) != relative_path
    ):
        raise ValueError("unsafe model-card path in external protocol")
    root = protocol_path.parent.resolve(strict=True)
    path = root.joinpath(*relative.parts)
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
        raise ValueError("external protocol model card is unavailable")
    registry = ModelZooRegistry(registry_path=str(path), enable_v2=False)
    if registry.names() != [expected_name]:
        raise ValueError("external protocol model card is not a one-card registry")
    if registry.card(expected_name).fingerprint() != expected_fingerprint:
        raise ValueError("external protocol model-card fingerprint changed")
    return path, _sha256(path)


def _write_new(path: Path, data: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def _pack_symbols(pack_root: Path) -> tuple[list[str], list[str]]:
    source = pack_root / "norman_k562_golden.h5ad"
    if source.is_symlink() or not source.is_file():
        raise ValueError("Golden Pack expression asset is unavailable")
    adata = anndata.read_h5ad(source, backed="r")
    try:
        symbols = [str(value) for value in adata.var["gene_symbols"].tolist()]
        identifiers = [str(value) for value in adata.var_names.tolist()]
    finally:
        adata.file.close()
    if len(symbols) != len(set(symbols)) or len(identifiers) != len(set(identifiers)):
        raise ValueError("Golden Pack feature symbols and IDs must be unique")
    return symbols, identifiers


def evaluate(
    *,
    protocol_path: Path,
    input_dir: Path,
    pack_root: Path,
    model_cache_root: Path,
    output_path: Path,
) -> dict[str, Any]:
    if output_path.is_symlink() or os.path.lexists(output_path):
        raise ValueError("output must be a new non-symlink file")
    if not output_path.parent.is_dir():
        raise ValueError("output parent must already exist")
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    if protocol.get("schema_version") != "vc.golden-gse220974-external-stress-protocol.v1":
        raise ValueError("unsupported external stress protocol")
    evaluator_sha256 = _sha256(Path(__file__))
    if protocol.get("evaluator_sha256_known_before_outcome") != evaluator_sha256:
        raise ValueError("external stress evaluator differs from the preregistration")
    golden_norman_path = Path(golden_norman.__file__)
    if (
        golden_norman_path.is_symlink()
        or _sha256(golden_norman_path) != protocol["prediction_implementation"]["golden_norman_sha256"]
    ):
        raise ValueError("Golden prediction implementation differs from the preregistration")
    observed_runtime = {
        "python": platform.python_version(),
        **{package: version(package) for package in ("anndata", "numpy", "pandas", "scipy", "praxis-virtualcell")},
    }
    if observed_runtime != protocol["runtime_environment"]:
        raise ValueError("external stress runtime differs from the preregistration")

    candidate = protocol["candidate"]
    candidate_card_path, candidate_card_sha256 = _model_card(
        protocol_path=protocol_path,
        relative_path=candidate["model_card_relative_path"],
        expected_name=candidate["name"],
        expected_fingerprint=candidate["model_card_fingerprint"],
    )
    comparator_card_path, comparator_card_sha256 = _model_card(
        protocol_path=protocol_path,
        relative_path=candidate["comparison_model_card_relative_path"],
        expected_name=candidate["comparison"],
        expected_fingerprint=candidate["comparison_model_card_fingerprint"],
    )

    if any(record["sha256_known_before_outcome"] is None for record in protocol["external_dataset"]["files"].values()):
        raise ValueError("all external input SHA-256 identities must be frozen before execution")
    checked_files = {
        name: _checked_file(input_dir, name, record) for name, record in protocol["external_dataset"]["files"].items()
    }
    files = {name: checked[0] for name, checked in checked_files.items()}
    input_identities = {name: checked[1] for name, checked in checked_files.items()}
    metadata = pd.read_csv(files["GSE220974_K562_cell_metadata.csv.gz"])
    if metadata["cell"].duplicated().any():
        raise ValueError("external cell IDs must be unique")
    selected_conditions = {item["condition"]: item for item in protocol["selection"]["targets"]}
    allowed = {protocol["selection"]["control"], *selected_conditions}
    selected = metadata.loc[
        metadata["orig.ident"].eq(protocol["selection"]["orig_ident"])
        & metadata["num_features_gRNA"].eq(protocol["selection"]["num_features_gRNA"])
        & metadata["guide_group2"].isin(allowed)
    ].copy()
    observed_counts = selected["guide_group2"].value_counts().to_dict()
    expected_counts = {
        protocol["selection"]["control"]: protocol["selection"]["expected_control_cells"],
        **{item["condition"]: item["expected_cells"] for item in selected_conditions.values()},
    }
    if observed_counts != expected_counts:
        raise ValueError("external preregistered cell counts changed")
    observed_control_guides = (
        selected.loc[
            selected["guide_group2"].eq(protocol["selection"]["control"]),
            "guide_group",
        ]
        .value_counts()
        .to_dict()
    )
    if observed_control_guides != protocol["selection"]["expected_control_guides"]:
        raise ValueError("external preregistered control-guide counts changed")

    guide_features = pd.read_csv(files["GSE220974_features.csv.gz"])
    if (
        list(guide_features.columns)
        != [
            "id",
            "name",
            "read",
            "pattern",
            "sequence",
            "feature_type",
            "target_gene_id",
            "target_gene_name",
        ]
        or guide_features["id"].duplicated().any()
    ):
        raise ValueError("external guide-feature contract changed")
    candidate_root = model_cache_root / "norman_additive_linear"
    comparator_root = model_cache_root / "norman_global_mean"
    if (
        _sha256(candidate_root / "baseline.json") != candidate["asset_metadata_sha256"]
        or _sha256(comparator_root / "baseline.json") != candidate["comparison_asset_metadata_sha256"]
    ):
        raise ValueError("candidate or comparator metadata differs from the preregistration")
    candidate_metadata = json.loads((candidate_root / "baseline.json").read_text())
    selected_target_ids = {item["ensembl_id"] for item in protocol["selection"]["targets"]}
    if (
        not protocol["selection"]["all_targets_seen_in_candidate_training"]
        or not selected_target_ids.issubset(candidate_metadata["seen_train_target_ids"])
        or selected_target_ids.intersection(candidate_metadata["unseen_train_target_ids"])
    ):
        raise ValueError("external target training-membership contract changed")
    available_conditions = set(
        metadata.loc[
            metadata["orig.ident"].eq(protocol["selection"]["orig_ident"])
            & metadata["num_features_gRNA"].eq(protocol["selection"]["num_features_gRNA"]),
            "guide_group2",
        ]
    )
    eligible_seen_targets = {
        str(row.target_gene_id)
        for row in guide_features.itertuples()
        if str(row.id).endswith(("-a1", "-a2"))
        and row.target_gene_id in candidate_metadata["seen_train_target_ids"]
        and f"{row.target_gene_name}-a" in available_conditions
    }
    if selected_target_ids != eligible_seen_targets:
        raise ValueError("external preregistered target selection is no longer exhaustive")
    for item in protocol["selection"]["targets"]:
        observed_guides = (
            selected.loc[selected["guide_group2"].eq(item["condition"]), "guide_group"].value_counts().to_dict()
        )
        if observed_guides != item["expected_guides"]:
            raise ValueError("external preregistered target-guide counts changed")
        declared_ids = {value.split("|", 1)[0] for value in item["expected_guides"]}
        guide_rows = guide_features.loc[guide_features["id"].isin(declared_ids)]
        if (
            set(guide_rows["id"]) != declared_ids
            or not guide_rows["name"].eq(guide_rows["id"]).all()
            or not guide_rows["feature_type"].eq("CRISPR Guide Capture").all()
            or not guide_rows["target_gene_id"].eq(item["ensembl_id"]).all()
            or not guide_rows["target_gene_name"].eq(item["symbol"]).all()
        ):
            raise ValueError("external guide-to-target identity changed")

    barcodes = _barcodes(files["GSE220974_RNA_barcodes.tsv.gz"])
    features = _feature_symbols(files["GSE220974_RNA_features.tsv.gz"])
    expected_shape = tuple(protocol["external_dataset"]["expected_matrix_shape"])
    if len(barcodes) != expected_shape[1] or len(features) != expected_shape[0]:
        raise ValueError("external feature/barcode dimensions changed")
    if len(barcodes) != len(set(barcodes)) or len(features) != len(set(features)):
        raise ValueError("external feature symbols and barcodes must be unique")
    barcode_position = {value: index for index, value in enumerate(barcodes)}
    if not set(selected["cell"]).issubset(barcode_position):
        raise ValueError("selected metadata cells are absent from the RNA matrix")

    pack_manifest = validate_pack(pack_root)
    if (
        pack_manifest.pack_id != protocol["norman"]["pack_id"]
        or pack_manifest.pack_version != protocol["norman"]["pack_version"]
        or pack_manifest.fingerprint() != protocol["norman"]["pack_fingerprint"]
    ):
        raise ValueError("Golden Pack identity differs from the preregistration")
    pack_symbols, pack_ids = _pack_symbols(pack_root)
    if (
        _fingerprint(pack_ids) != protocol["norman"]["feature_ids_sha256"]
        or _fingerprint(pack_symbols) != protocol["norman"]["feature_symbols_sha256"]
        or _fingerprint(list(map(list, zip(pack_ids, pack_symbols, strict=True))))
        != protocol["norman"]["feature_id_symbol_pairs_sha256"]
    ):
        raise ValueError("Golden Pack ordered feature identity changed")
    external_position = {value: index for index, value in enumerate(features)}
    pack_position = {value: index for index, value in enumerate(pack_symbols)}
    common_symbols = sorted(set(external_position).intersection(pack_position))
    if (
        len(common_symbols) != protocol["feature_mapping"]["expected_overlap_count"]
        or _fingerprint(common_symbols) != protocol["feature_mapping"]["expected_overlap_symbols_sha256"]
    ):
        raise ValueError("external exact feature overlap changed")
    common_external = np.asarray([external_position[value] for value in common_symbols])
    common_pack = np.asarray([pack_position[value] for value in common_symbols])
    if (
        _fingerprint([pack_ids[index] for index in common_pack])
        != protocol["feature_mapping"]["expected_overlap_norman_feature_ids_sha256"]
    ):
        raise ValueError("external-to-Norman feature mapping changed")

    with gzip.open(files["GSE220974_RNA_matrix.mtx.gz"], "rb") as stream:
        matrix = io.mmread(stream)
    if matrix.shape != expected_shape or not sparse.issparse(matrix):
        raise ValueError("external RNA matrix shape/storage changed")
    matrix = matrix.tocsc()
    selected_cells = selected["cell"].tolist()
    selected_columns = np.asarray([barcode_position[value] for value in selected_cells])
    selected_matrix = matrix[:, selected_columns]
    library_sizes = np.asarray(selected_matrix.sum(axis=0)).ravel().astype(np.float64)
    if np.any(library_sizes <= 0) or not np.isfinite(library_sizes).all():
        raise ValueError("external selected cells have invalid library sizes")
    expression = selected_matrix[common_external, :].astype(np.float64).tocsc()
    expression = _log_normalise(expression, library_sizes)

    selected_conditions_by_cell = selected["guide_group2"].tolist()
    control_columns = np.flatnonzero(np.asarray(selected_conditions_by_cell) == protocol["selection"]["control"])
    control_mean = np.asarray(expression[:, control_columns].mean(axis=1)).ravel()
    per_target = []
    differences = []
    for item in protocol["selection"]["targets"]:
        target_columns = np.flatnonzero(np.asarray(selected_conditions_by_cell) == item["condition"])
        external_delta = np.asarray(expression[:, target_columns].mean(axis=1)).ravel() - control_mean
        candidate_prediction = golden_norman.predict_from_artifact(candidate_root, [item["ensembl_id"]])
        comparator_prediction = golden_norman.predict_from_artifact(comparator_root, [item["ensembl_id"]])
        if (
            candidate_prediction["baseline"] != "additive_linear"
            or comparator_prediction["baseline"] != "global_mean"
            or candidate_prediction["feature_ids_sha256"] != protocol["norman"]["feature_ids_sha256"]
            or comparator_prediction["feature_ids_sha256"] != protocol["norman"]["feature_ids_sha256"]
            or candidate_prediction["n_features"] != len(pack_ids)
            or comparator_prediction["n_features"] != len(pack_ids)
            or candidate_prediction["unseen_train_targets"]
            or comparator_prediction["unseen_train_targets"]
        ):
            raise ValueError("candidate or comparator prediction contract changed")
        candidate_values = np.asarray(candidate_prediction["delta"], dtype=np.float64)[common_pack]
        comparator_values = np.asarray(comparator_prediction["delta"], dtype=np.float64)[common_pack]
        candidate_rho = float(stats.spearmanr(candidate_values, external_delta).statistic)
        comparator_rho = float(stats.spearmanr(comparator_values, external_delta).statistic)
        if not math.isfinite(candidate_rho) or not math.isfinite(comparator_rho):
            raise ValueError("external correlation is non-finite")
        difference = candidate_rho - comparator_rho
        differences.append(difference)
        per_target.append(
            {
                "symbol": item["symbol"],
                "ensembl_id": item["ensembl_id"],
                "n_cells": int(len(target_columns)),
                "candidate_spearman_rho": candidate_rho,
                "global_mean_spearman_rho": comparator_rho,
                "difference": difference,
                "external_delta_sha256": _fingerprint(external_delta.tolist()),
                "candidate_projection_sha256": _fingerprint(candidate_values.tolist()),
                "global_mean_projection_sha256": _fingerprint(comparator_values.tolist()),
            }
        )

    candidate_mean = float(np.mean([item["candidate_spearman_rho"] for item in per_target]))
    comparator_mean = float(np.mean([item["global_mean_spearman_rho"] for item in per_target]))
    differences_array = np.asarray(differences, dtype=np.float64)
    p_value = _exact_sign_flip_p(differences_array)
    passed = bool(
        candidate_mean > 0.0 and candidate_mean > comparator_mean and p_value <= protocol["primary_test"]["alpha"]
    )
    if {
        name: {"size_bytes": path.stat().st_size, "sha256": _sha256(path)} for name, path in files.items()
    } != input_identities:
        raise ValueError("external input bytes changed during evaluation")
    if (
        _sha256(candidate_card_path) != candidate_card_sha256
        or _sha256(comparator_card_path) != comparator_card_sha256
        or validate_pack(pack_root).fingerprint() != pack_manifest.fingerprint()
    ):
        raise ValueError("local model or Pack identity changed during evaluation")
    result = {
        "schema_version": "vc.golden-gse220974-external-stress-result.v1",
        "protocol_sha256": _sha256(protocol_path),
        "protocol_canonical_fingerprint": _fingerprint(protocol),
        "evaluator_sha256": evaluator_sha256,
        "input_files": dict(sorted(input_identities.items())),
        "dataset": {
            "accession": protocol["external_dataset"]["accession"],
            "matrix_shape": list(matrix.shape),
            "selected_cells": len(selected_cells),
            "control_cells": len(control_columns),
            "common_feature_count": len(common_symbols),
            "common_feature_symbols_sha256": _fingerprint(common_symbols),
            "common_norman_feature_ids_sha256": _fingerprint([pack_ids[index] for index in common_pack]),
        },
        "candidate": {
            **protocol["candidate"],
            "model_card_sha256": candidate_card_sha256,
            "comparison_model_card_sha256": comparator_card_sha256,
        },
        "per_target": per_target,
        "primary_test": {
            "candidate_mean_spearman_rho": candidate_mean,
            "global_mean_mean_spearman_rho": comparator_mean,
            "mean_difference": float(differences_array.mean()),
            "exact_sign_flip_p_value": p_value,
            "alternative": "greater",
            "permutations": 32,
            "alpha": protocol["primary_test"]["alpha"],
            "external_stress_test_passed": passed,
        },
        "states": {
            "external_data_used": True,
            "external_stress_test_passed": passed,
            "p16_exact_external_gate_satisfied": False,
            "scientifically_validated": False,
            "promotion_eligible": False,
            "production_promoted": False,
        },
        "claim_ceiling": protocol["claim_ceiling"],
        "runtime": observed_runtime,
    }
    _write_new(output_path, _canonical_bytes(result) + b"\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", required=True, type=Path)
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--pack-root", required=True, type=Path)
    parser.add_argument("--model-cache-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = evaluate(
        protocol_path=args.protocol,
        input_dir=args.input_dir,
        pack_root=args.pack_root,
        model_cache_root=args.model_cache_root,
        output_path=args.output,
    )
    print(json.dumps(result["primary_test"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
