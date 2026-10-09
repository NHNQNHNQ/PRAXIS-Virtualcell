"""Reproduce the frozen Phase 9 adaptation-free external validation.

Inputs are local copies of four public GEO files with frozen hashes.  The
builder performs no download, identifier conversion, missing-feature fill,
random split, external fit, or model fallback.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import math
import tarfile
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from praxis_virtualcell.benchmarks.ood_validation import (
    P9_EXTERNAL_FILES,
    OODValidationError,
    canonical_sha256,
    load_ood_manifest,
    promotion_status,
    select_threshold,
    selective_metrics,
)

_CODE_BASELINE = "480706fbf58343565532debeca70c4de093b045f"
_SOURCE_TRAIN = (3, 4, 6, 24, 168)
_SOURCE_VALIDATION = (5, 8, 48)
_SOURCE_TEST = (336,)
_EXTERNAL_REFERENCE = 5
_EXTERNAL_EVALUATION = (7, 8, 10, 14, 24, 48, 168, 336)
_SUMMARY_ROWS = (
    "no_feature",
    "ambiguous",
    "too_low_aQual",
    "not_aligned",
    "alignment_not_unique",
)
_SUMMARY_ROWS_PREFIXED = tuple(f"__{value}" for value in _SUMMARY_ROWS)
_SOURCE_ONLY = ("RF01769.1", "RF01771.1")
_FILES = P9_EXTERNAL_FILES


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _check_file(path: str | Path, role: str) -> Path:
    source = Path(path)
    expected = _FILES[role]
    try:
        size = source.stat().st_size
    except OSError as exc:
        raise OODValidationError(f"cannot read {role} file {source}: {exc}") from exc
    if source.name != expected["filename"]:
        raise OODValidationError(
            f"{role} filename must be {expected['filename']!r}, got {source.name!r}"
        )
    if size != expected["size_bytes"]:
        raise OODValidationError(
            f"{role} size mismatch: expected {expected['size_bytes']}, got {size}"
        )
    digest = _file_sha256(source)
    if digest != expected["sha256"]:
        raise OODValidationError(
            f"{role} SHA-256 mismatch: expected {expected['sha256']}, got {digest}"
        )
    return source


def _parse_soft(path: Path) -> list[dict[str, Any]]:
    samples = []
    current = None

    def finish():
        if current is not None:
            samples.append(current)

    try:
        with gzip.open(path, "rt", encoding="utf-8", newline="") as stream:
            for raw_line in stream:
                line = raw_line.rstrip("\r\n")
                if line.startswith("^SAMPLE = "):
                    finish()
                    current = {
                        "accession": line.removeprefix("^SAMPLE = "),
                        "characteristics": {},
                    }
                    continue
                if current is None or not line.startswith("!Sample_"):
                    continue
                key, separator, value = line.partition(" = ")
                if not separator:
                    raise OODValidationError(f"malformed SOFT sample line: {line!r}")
                field = key.removeprefix("!Sample_")
                if field == "characteristics_ch1":
                    characteristic, marker, item = value.partition(": ")
                    if not marker or characteristic in current["characteristics"]:
                        raise OODValidationError(
                            f"ambiguous SOFT characteristic: {value!r}"
                        )
                    current["characteristics"][characteristic] = item
                elif field in {
                    "title",
                    "geo_accession",
                    "description",
                    "supplementary_file_2",
                }:
                    if field in current:
                        raise OODValidationError(f"duplicate SOFT field: {field}")
                    current[field] = value
            finish()
    except (OSError, EOFError) as exc:
        raise OODValidationError(f"cannot parse SOFT metadata {path}: {exc}") from exc
    if not samples:
        raise OODValidationError(f"SOFT metadata contains no samples: {path}")
    return samples


def _integer(value: str, path: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise OODValidationError(f"{path} must be an integer") from exc
    if parsed < 0:
        raise OODValidationError(f"{path} must be non-negative")
    return parsed


def _source_time(sample: dict[str, Any]) -> int:
    value = sample["characteristics"].get("time point", "")
    number, separator, unit = value.partition(" ")
    if separator != " " or unit != "hours":
        raise OODValidationError(f"unexpected GSE67402 time point: {value!r}")
    return _integer(number, "GSE67402 time point")


def _external_time(sample: dict[str, Any]) -> int:
    return _integer(
        sample["characteristics"].get("growth time (hours)", ""),
        "GSE94117 growth time",
    )


def _source_matrix(path: Path, samples: list[dict[str, Any]], np):
    selected = [
        sample
        for sample in samples
        if sample.get("description", "").startswith("AG3C-")
        and sample["characteristics"].get("molecule subtype")
        == "rRNA-depleted total RNA"
    ]
    if len(selected) != 27:
        raise OODValidationError(
            f"GSE67402 source cohort must contain 27 samples, got {len(selected)}"
        )
    by_name = {sample["description"]: sample for sample in selected}
    if len(by_name) != len(selected):
        raise OODValidationError("GSE67402 source sample descriptions are not unique")
    try:
        stream = gzip.open(path, "rt", encoding="utf-8", newline="")
        with stream:
            reader = csv.reader(stream)
            header = next(reader)
            if not header or header[0] != "gene_id" or len(set(header)) != len(header):
                raise OODValidationError("GSE67402 count header is invalid")
            missing = sorted(set(by_name) - set(header[1:]))
            if missing:
                raise OODValidationError(
                    f"GSE67402 count matrix is missing source samples: {missing}"
                )
            selected_names = [name for name in header[1:] if name in by_name]
            columns = [header.index(name) for name in selected_names]
            feature_ids = []
            rows = []
            for row_index, row in enumerate(reader, start=2):
                if len(row) != len(header):
                    raise OODValidationError(
                        f"GSE67402 count row {row_index} has wrong width"
                    )
                feature_ids.append(row[0])
                rows.append(
                    [
                        _integer(row[column], f"GSE67402 row {row_index}")
                        for column in columns
                    ]
                )
    except (OSError, EOFError, StopIteration) as exc:
        raise OODValidationError(f"cannot parse GSE67402 counts: {exc}") from exc
    if len(feature_ids) != 4486 or len(set(feature_ids)) != len(feature_ids):
        raise OODValidationError("GSE67402 must contain 4,486 unique feature IDs")
    times = [_source_time(by_name[name]) for name in selected_names]
    expected_times = set(_SOURCE_TRAIN + _SOURCE_VALIDATION + _SOURCE_TEST)
    counts = {time: times.count(time) for time in expected_times}
    if set(times) != expected_times or set(counts.values()) != {3}:
        raise OODValidationError(
            f"GSE67402 source cohort must have three replicates per time: {counts}"
        )
    return feature_ids, np.asarray(rows, dtype=np.float64).T, times


def _count_member(archive: tarfile.TarFile, name: str) -> tuple[list[str], list[int]]:
    try:
        member = archive.getmember(name)
        raw = archive.extractfile(member)
    except (KeyError, OSError, tarfile.TarError) as exc:
        raise OODValidationError(f"cannot read external count member {name}: {exc}") from exc
    if raw is None or not member.isfile():
        raise OODValidationError(f"external count member is not a regular file: {name}")
    try:
        with raw, gzip.GzipFile(fileobj=raw, mode="rb") as compressed:
            with io.TextIOWrapper(compressed, encoding="utf-8", newline="") as stream:
                reader = csv.reader(stream, delimiter="\t")
                header = next(reader)
                if header != ["gene_ID", "count"]:
                    raise OODValidationError(
                        f"external count header is invalid in {name}"
                    )
                ids = []
                values = []
                for row_index, row in enumerate(reader, start=2):
                    if len(row) != 2:
                        raise OODValidationError(
                            f"external count row {row_index} has wrong width in {name}"
                        )
                    ids.append(row[0])
                    values.append(_integer(row[1], f"{name} row {row_index}"))
    except (OSError, EOFError, StopIteration) as exc:
        raise OODValidationError(f"cannot parse external count member {name}: {exc}") from exc
    if len(ids) != len(set(ids)):
        raise OODValidationError(f"external feature IDs are duplicated in {name}")
    return ids, values


def _external_matrix(path: Path, samples: list[dict[str, Any]], np):
    selected = [
        sample
        for sample in samples
        if sample.get("description") == "glycerol_time_course"
    ]
    if len(selected) != 25:
        raise OODValidationError(
            f"GSE94117 glycerol cohort must contain 25 samples, got {len(selected)}"
        )
    feature_ids = None
    excluded_summary_rows = set()
    rows = []
    times = []
    try:
        with tarfile.open(path, mode="r:") as archive:
            for sample in selected:
                source_url = sample.get("supplementary_file_2")
                if not source_url:
                    raise OODValidationError(
                        f"GSE94117 sample lacks count file: {sample.get('accession')}"
                    )
                filename = Path(urlparse(source_url).path).name
                ids, values = _count_member(archive, filename)
                summary = tuple(ids[-len(_SUMMARY_ROWS) :])
                if summary not in {_SUMMARY_ROWS, _SUMMARY_ROWS_PREFIXED}:
                    raise OODValidationError(
                        f"unexpected HTSeq summary rows in {filename}: {summary}"
                    )
                excluded_summary_rows.update(summary)
                ids = ids[: -len(_SUMMARY_ROWS)]
                values = values[: -len(_SUMMARY_ROWS)]
                if feature_ids is None:
                    feature_ids = ids
                elif ids != feature_ids:
                    raise OODValidationError(
                        f"external feature order differs in {filename}"
                    )
                rows.append(values)
                times.append(_external_time(sample))
    except (OSError, tarfile.TarError) as exc:
        raise OODValidationError(f"cannot parse GSE94117 archive: {exc}") from exc
    expected_replicates = {
        5: 3,
        7: 3,
        8: 3,
        10: 3,
        14: 3,
        24: 3,
        48: 3,
        168: 3,
        336: 1,
    }
    counts = {time: times.count(time) for time in expected_replicates}
    if counts != expected_replicates:
        raise OODValidationError(
            f"GSE94117 glycerol replicate counts do not match contract: {counts}"
        )
    ordered_excluded = [
        value
        for variant in (_SUMMARY_ROWS, _SUMMARY_ROWS_PREFIXED)
        for value in variant
        if value in excluded_summary_rows
    ]
    return feature_ids, np.asarray(rows, dtype=np.float64), times, ordered_excluded


def _log_cpm(matrix, np):
    library_sizes = matrix.sum(axis=1)
    if np.any(library_sizes <= 0):
        raise OODValidationError("shared-feature library sizes must be positive")
    return np.log1p(matrix * (1_000_000.0 / library_sizes[:, None]))


def _condition_means(matrix, times, np):
    grouped = defaultdict(list)
    for index, time in enumerate(times):
        grouped[time].append(matrix[index])
    return {
        time: np.mean(np.stack(rows, axis=0), axis=0)
        for time, rows in grouped.items()
    }


def _pearson(left, right, np) -> float:
    left_centered = left - np.mean(left)
    right_centered = right - np.mean(right)
    denominator = float(
        np.sqrt(np.sum(left_centered**2) * np.sum(right_centered**2))
    )
    if denominator == 0:
        raise OODValidationError("candidate Pearson is undefined")
    return float(np.sum(left_centered * right_centered) / denominator)


def _parameter_hash(feature_ids: list[str], slopes, np) -> str:
    digest = hashlib.sha256()
    digest.update(
        json.dumps(
            feature_ids,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    )
    digest.update(np.asarray(slopes, dtype="<f8").tobytes(order="C"))
    return digest.hexdigest()


def _paired_ci(differences, np) -> dict[str, Any]:
    values = np.asarray(differences, dtype=np.float64)
    rng = np.random.Generator(np.random.PCG64(0))
    indices = rng.integers(0, len(values), size=(2000, len(values)))
    sampled = np.mean(values[indices], axis=1)
    low, high = np.quantile(sampled, [0.025, 0.975])
    return {
        "low": float(low),
        "high": float(high),
        "method": "paired_group_percentile",
        "group_count": len(values),
        "replicates": 2000,
        "seed": 0,
    }


def build_external_validation(
    *,
    manifest_path: str | Path,
    source_counts: str | Path,
    source_soft: str | Path,
    external_raw: str | Path,
    external_soft: str | Path,
) -> dict[str, Any]:
    """Build the deterministic GSE67402-to-GSE94117 result artifact."""

    try:
        import numpy as np
    except ImportError as exc:  # pragma: no cover - exercised in base-only installs
        raise OODValidationError(
            "external validation requires the omics/test environment with numpy"
        ) from exc

    manifest = load_ood_manifest(manifest_path)
    if manifest["external_validation"]["files"] != _FILES:
        raise OODValidationError("manifest does not name the frozen external validation")

    paths = {
        "source_counts": _check_file(source_counts, "source_counts"),
        "source_soft": _check_file(source_soft, "source_soft"),
        "external_raw": _check_file(external_raw, "external_raw"),
        "external_soft": _check_file(external_soft, "external_soft"),
    }
    source_samples = _parse_soft(paths["source_soft"])
    external_samples = _parse_soft(paths["external_soft"])
    source_ids, source_matrix, source_times = _source_matrix(
        paths["source_counts"], source_samples, np
    )
    external_ids, external_matrix, external_times, excluded_summary_rows = _external_matrix(
        paths["external_raw"], external_samples, np
    )

    external_biological = external_ids
    external_id_set = set(external_biological)
    shared = [feature_id for feature_id in source_ids if feature_id in external_id_set]
    dropped = [feature_id for feature_id in source_ids if feature_id not in external_id_set]
    if tuple(dropped) != _SOURCE_ONLY:
        raise OODValidationError(f"unexpected source-only feature IDs: {dropped}")
    if shared != external_biological or len(shared) != 4484:
        raise OODValidationError(
            "source/external features must be the exact ordered 4,484-ID intersection"
        )
    source_positions = [source_ids.index(feature_id) for feature_id in shared]
    source_shared = source_matrix[:, source_positions]
    external_shared = external_matrix

    source_transformed = _log_cpm(source_shared, np)
    external_transformed = _log_cpm(external_shared, np)
    source_means = _condition_means(source_transformed, source_times, np)
    external_means = _condition_means(external_transformed, external_times, np)

    if set(_SOURCE_TRAIN) & set(_SOURCE_VALIDATION + _SOURCE_TEST):
        raise OODValidationError("source biological condition split overlaps")
    reference = source_means[3]
    train_x = np.asarray([math.log2(time / 3) for time in _SOURCE_TRAIN])
    train_deltas = np.stack(
        [source_means[time] - reference for time in _SOURCE_TRAIN], axis=0
    )
    denominator = float(np.sum(train_x**2))
    slopes = np.sum(train_x[:, None] * train_deltas, axis=0) / denominator

    def reliability(time: int, reference_time: int) -> float:
        coordinate = math.log2(time / reference_time)
        return -min(abs(coordinate - float(value)) for value in train_x)

    validation_records = []
    for time in _SOURCE_VALIDATION:
        truth = source_means[time] - reference
        prediction = slopes * math.log2(time / 3)
        validation_records.append(
            {
                "unit_id": f"GSE67402:glucose:{time}h",
                "partition": "validation",
                "reliability_score": reliability(time, 3),
                "candidate_loss": float(np.mean((prediction - truth) ** 2)),
                "baseline_loss": float(np.mean(truth**2)),
            }
        )
    selected = select_threshold(
        validation_records,
        manifest["threshold_policy"]["minimum_validation_coverage"],
    )
    threshold = selected["threshold"]

    external_reference = external_means[_EXTERNAL_REFERENCE]
    by_condition = []
    selective_rows = []
    for time in _EXTERNAL_EVALUATION:
        truth = external_means[time] - external_reference
        prediction = slopes * math.log2(time / _EXTERNAL_REFERENCE)
        candidate_mse = float(np.mean((prediction - truth) ** 2))
        baseline_mse = float(np.mean(truth**2))
        score = reliability(time, _EXTERNAL_REFERENCE)
        by_condition.append(
            {
                "time_hours": time,
                "replicate_count": external_times.count(time),
                "candidate_mse": candidate_mse,
                "baseline_mse": baseline_mse,
                "candidate_mae": float(np.mean(np.abs(prediction - truth))),
                "baseline_mae": float(np.mean(np.abs(truth))),
                "candidate_pearson": _pearson(prediction, truth, np),
                "reliability_score": score,
                "accepted": score >= threshold,
            }
        )
        selective_rows.append(
            {
                "unit_id": f"GSE94117:glycerol:{time}h",
                "reliability_score": score,
                "candidate_loss": candidate_mse,
                "baseline_loss": baseline_mse,
            }
        )

    candidate = sum(row["candidate_mse"] for row in by_condition) / len(by_condition)
    baseline = sum(row["baseline_mse"] for row in by_condition) / len(by_condition)
    difference = candidate - baseline
    ci = _paired_ci(
        [row["candidate_mse"] - row["baseline_mse"] for row in by_condition],
        np,
    )
    status = promotion_status(
        candidate_primary=candidate,
        baseline_primary=baseline,
        paired_difference_ci95={"low": ci["low"], "high": ci["high"]},
        leakage_audit_passed=True,
        external_adaptation_steps=0,
        seed_count=len(manifest["seeds"]),
    )
    seed_runs = [
        {
            "seed": seed,
            "candidate": candidate,
            "baseline": baseline,
            "difference": difference,
        }
        for seed in manifest["seeds"]
    ]
    source_file = dict(_FILES["source_counts"])
    source_metadata = dict(_FILES["source_soft"])
    external_file = dict(_FILES["external_raw"])
    external_metadata = dict(_FILES["external_soft"])
    return {
        "schema_version": "vc.ood-result.v1",
        "benchmark_id": manifest["benchmark_id"],
        "manifest_sha256": canonical_sha256(manifest),
        "source_dataset": {
            "accession": "GSE67402",
            "cohort": "glucose_time_course:rRNA-depleted_total_RNA",
            "role": "fit_and_internal_split_source",
            "platform": "GPL14548 / Illumina HiSeq 2000",
            "organism": "Escherichia coli REL606",
            "data_file": source_file,
            "metadata_file": source_metadata,
        },
        "external_dataset": {
            "accession": "GSE94117",
            "cohort": "glycerol_time_course",
            "role": "adaptation_free_external_evaluation",
            "platform": "GPL22993 / Illumina HiSeq 2500",
            "organism": "Escherichia coli B str. REL606",
            "data_file": external_file,
            "metadata_file": external_metadata,
            "adaptation_steps": 0,
        },
        "feature_contract": {
            "namespace": "E. coli REL606 locus tag plus Rfam accession",
            "policy": "exact_identifier_intersection",
            "ordered_feature_count": len(shared),
            "ordered_feature_ids_sha256": canonical_sha256(shared),
            "source_only_dropped_ids": dropped,
            "external_summary_rows_excluded": excluded_summary_rows,
            "identifier_conversion_steps": [],
            "fill_steps": [],
        },
        "split_contract": {
            "source_train_time_hours": list(_SOURCE_TRAIN),
            "source_validation_time_hours": list(_SOURCE_VALIDATION),
            "source_test_time_hours": list(_SOURCE_TEST),
            "external_reference_time_hours": _EXTERNAL_REFERENCE,
            "external_evaluation_time_hours": list(_EXTERNAL_EVALUATION),
            "group_unit": "biological_condition",
            "split_generation": "predeclared_no_random_split",
        },
        "leakage_audit": {
            "passed": True,
            "checked_before_evaluation": True,
            "group_unit": "biological_condition",
            "overlaps": [],
            "excluded_external_cohorts": ["GSE94117:glucose_time_course"],
        },
        "model": {
            "id": "source-log-time-feature-trend-v1",
            "kind": "per_feature_least_squares_log_time_trend",
            "fit_dataset": "GSE67402",
            "fit_partition": "train",
            "parameter_sha256": _parameter_hash(shared, slopes, np),
            "input_transform": (
                "log1p(1e6 * exact_shared_feature_count / "
                "sample_exact_shared_feature_count_sum)"
            ),
        },
        "baseline": {
            "id": "no-change-v1",
            "kind": "zero_delta_for_every_exact_shared_feature",
        },
        "threshold": {
            "selection_partition": selected["selection_partition"],
            "reliability_score": (
                "negative_nearest_source_train_log2_time_coordinate_distance"
            ),
            "selected_value": selected["threshold"],
            "minimum_validation_coverage": manifest["threshold_policy"][
                "minimum_validation_coverage"
            ],
            "accepted_units": selected["accepted_units"],
            "total_units": selected["total_units"],
            "coverage": selected["coverage"],
            "candidate_risk": selected["candidate_risk"],
        },
        "evaluation": {
            "primary": {
                "name": manifest["metrics"]["primary"]["name"],
                "direction": "lower_is_better",
                "candidate": candidate,
                "baseline": baseline,
                "difference": difference,
                "paired_ci95": ci,
            },
            "secondary": {
                "candidate_mae": sum(row["candidate_mae"] for row in by_condition)
                / len(by_condition),
                "baseline_mae": sum(row["baseline_mae"] for row in by_condition)
                / len(by_condition),
                "candidate_pearson": sum(
                    row["candidate_pearson"] for row in by_condition
                )
                / len(by_condition),
                "baseline_pearson": None,
            },
            "by_condition": by_condition,
            "seeds": manifest["seeds"],
            "seed_runs": seed_runs,
            "selective": selective_metrics(selective_rows, threshold),
        },
        "status": status,
        "provenance": {
            "generator": "praxis_virtualcell.benchmarks.p9_external.build_external_validation",
            "code_baseline": _CODE_BASELINE,
            "raw_data_committed": False,
            "model_weights_committed": False,
        },
    }
