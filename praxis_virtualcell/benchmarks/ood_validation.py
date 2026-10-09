"""Strict Phase 9 OOD, abstention, and external-validation contracts.

The contract fixture proves split and governance behavior, not scientific
performance.  External data derivation is explicit and opt-in; this module
does not download data, create splits, convert identifiers, fill features, or
fall back to mock inputs.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

OOD_AXES = (
    "iid",
    "perturbation",
    "combination",
    "cell_type",
    "donor",
    "dataset_platform",
    "species",
    "dose_time",
)
P9_EXTERNAL_FILES = {
    "source_counts": {
        "filename": "GSE67402_counts.csv.gz",
        "size_bytes": 168809,
        "sha256": "4d8e8e4bee7cf08dea4247f319403c1399af6c9e4069f40f65f54911b748a688",
        "source_url": (
            "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE67nnn/GSE67402/"
            "suppl/GSE67402_counts.csv.gz"
        ),
    },
    "source_soft": {
        "filename": "GSE67402_family.soft.gz",
        "size_bytes": 5055,
        "sha256": "2b150e6b48a0d7fc48aa1a5b8de4e7c3a6b569206d054ca3e22fcd33154ff881",
        "source_url": (
            "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE67nnn/GSE67402/"
            "soft/GSE67402_family.soft.gz"
        ),
    },
    "external_raw": {
        "filename": "GSE94117_RAW.tar",
        "size_bytes": 2560000,
        "sha256": "3433f1d37d90fd24fa59b19b04e52cb68fc6201d5e49408efcb610fe47d18483",
        "source_url": (
            "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE94nnn/GSE94117/"
            "suppl/GSE94117_RAW.tar"
        ),
    },
    "external_soft": {
        "filename": "GSE94117_family.soft.gz",
        "size_bytes": 11234,
        "sha256": "7b99331077d6aaa392c65a5070baf279bcfc5174d6daff512120c0a2f5f179a4",
        "source_url": (
            "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE94nnn/GSE94117/"
            "soft/GSE94117_family.soft.gz"
        ),
    },
}
_P9_FEATURE_CONTRACT = {
    "namespace": "E. coli REL606 locus tag plus Rfam accession",
    "policy": "exact_identifier_intersection",
    "ordered_feature_count": 4484,
    "ordered_feature_ids_sha256": "07a2c6513281b33faef4bf71735d70c6efc201d1dbd965746c8327324fdabc81",
    "source_only_dropped_ids": ["RF01769.1", "RF01771.1"],
    "external_summary_rows_excluded": [
        "no_feature",
        "ambiguous",
        "too_low_aQual",
        "not_aligned",
        "alignment_not_unique",
        "__no_feature",
        "__ambiguous",
        "__too_low_aQual",
        "__not_aligned",
        "__alignment_not_unique",
    ],
    "identifier_conversion_steps": [],
    "fill_steps": [],
}
_PARTITIONS = ("train", "validation", "test")
_SHA256 = set("0123456789abcdef")


class OODValidationError(ValueError):
    """A frozen Phase 9 contract or result was not satisfied."""


def _duplicate_rejecting_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise OODValidationError(f"duplicate JSON key: {key!r}")
        value[key] = item
    return value


def _reject_nonfinite_json(value):
    raise OODValidationError(f"non-finite JSON number is forbidden: {value}")


def _load_json(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    try:
        value = json.loads(
            source.read_text(encoding="utf-8"),
            object_pairs_hook=_duplicate_rejecting_object,
            parse_constant=_reject_nonfinite_json,
        )
    except OODValidationError:
        raise
    except (OSError, json.JSONDecodeError) as exc:
        raise OODValidationError(f"cannot read Phase 9 JSON {source}: {exc}") from exc
    if not isinstance(value, dict):
        raise OODValidationError("Phase 9 JSON root must be an object")
    return value


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
        raise OODValidationError(f"value is not canonical JSON: {exc}") from exc


def canonical_sha256(value: Any) -> str:
    """Return the deterministic SHA-256 of canonical JSON."""

    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _exact_fields(value: Any, fields: set[str], path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise OODValidationError(f"{path} must be an object")
    actual = set(value)
    if actual != fields:
        raise OODValidationError(
            f"{path} fields must be exactly {sorted(fields)}; got {sorted(actual)}"
        )
    return value


def _text(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise OODValidationError(f"{path} must be a non-empty string")
    return value


def _text_list(value: Any, path: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not value and not allow_empty):
        qualifier = "" if allow_empty else " non-empty"
        raise OODValidationError(f"{path} must be a{qualifier} JSON array")
    items = [_text(item, f"{path}[]") for item in value]
    if len(set(items)) != len(items):
        raise OODValidationError(f"{path} must not contain duplicates")
    return items


def _number(value: Any, path: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise OODValidationError(f"{path} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise OODValidationError(f"{path} must be a finite number")
    return result


def _positive_int(value: Any, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise OODValidationError(f"{path} must be a positive integer")
    return value


def _sha256(value: Any, path: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _SHA256 for character in value)
    ):
        raise OODValidationError(f"{path} must be a lowercase SHA-256")
    return value


def _git_sha(value: Any, path: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) not in {40, 64}
        or any(character not in _SHA256 for character in value)
    ):
        raise OODValidationError(f"{path} must be a lowercase full Git object ID")
    return value


def _validate_file_record(value: Any, path: str) -> None:
    source_file = _exact_fields(
        value, {"filename", "size_bytes", "sha256", "source_url"}, path
    )
    _text(source_file["filename"], f"{path}.filename")
    _positive_int(source_file["size_bytes"], f"{path}.size_bytes")
    _sha256(source_file["sha256"], f"{path}.sha256")
    _text(source_file["source_url"], f"{path}.source_url")


def _validate_manifest(manifest: dict[str, Any]) -> None:
    _exact_fields(
        manifest,
        {
            "schema_version",
            "benchmark_id",
            "axes",
            "data_roles",
            "metrics",
            "confidence_interval",
            "seeds",
            "threshold_policy",
            "external_validation",
            "promotion_gate",
        },
        "manifest",
    )
    if manifest["schema_version"] != "vc.ood-manifest.v1":
        raise OODValidationError("unsupported OOD manifest schema_version")
    _text(manifest["benchmark_id"], "manifest.benchmark_id")

    axes = manifest["axes"]
    if not isinstance(axes, list):
        raise OODValidationError("manifest.axes must be a JSON array")
    axis_ids = []
    for index, axis in enumerate(axes):
        path = f"manifest.axes[{index}]"
        _exact_fields(
            axis,
            {"id", "biological_unit", "groups", "evidence_kind"},
            path,
        )
        axis_id = _text(axis["id"], f"{path}.id")
        axis_ids.append(axis_id)
        _text(axis["biological_unit"], f"{path}.biological_unit")
        if axis["evidence_kind"] != "contract_fixture":
            raise OODValidationError(
                f"{path}.evidence_kind must remain contract_fixture"
            )
        if not isinstance(axis["groups"], Mapping) or set(axis["groups"]) != set(
            _PARTITIONS
        ):
            raise OODValidationError(
                f"{path}.groups must declare train, validation, and test"
            )
        groups = axis["groups"]
        partition_groups = {
            partition: _text_list(
                groups[partition], f"{path}.groups.{partition}"
            )
            for partition in _PARTITIONS
        }
        for left_index, left in enumerate(_PARTITIONS):
            for right in _PARTITIONS[left_index + 1 :]:
                overlap = set(partition_groups[left]) & set(partition_groups[right])
                if overlap:
                    raise OODValidationError(
                        f"{path} biological groups overlap across {left}/{right}: "
                        f"{sorted(overlap)}"
                    )
    if tuple(axis_ids) != OOD_AXES:
        raise OODValidationError(
            f"manifest.axes must be exactly {list(OOD_AXES)} in canonical order"
        )

    roles = _exact_fields(
        manifest["data_roles"],
        {
            "feature_fields",
            "label_fields",
            "fit_partitions",
            "threshold_partitions",
            "evaluation_partitions",
        },
        "manifest.data_roles",
    )
    features = _text_list(roles["feature_fields"], "manifest.data_roles.feature_fields")
    labels = _text_list(roles["label_fields"], "manifest.data_roles.label_fields")
    if set(features) & set(labels):
        raise OODValidationError(
            "manifest.data_roles feature_fields and label_fields must be disjoint"
        )
    if roles["fit_partitions"] != ["train"]:
        raise OODValidationError("fit_partitions must be exactly ['train']")
    if roles["threshold_partitions"] != ["train", "validation"]:
        raise OODValidationError(
            "threshold_partitions must be exactly ['train', 'validation']"
        )
    if roles["evaluation_partitions"] != ["test", "external"]:
        raise OODValidationError(
            "evaluation_partitions must be exactly ['test', 'external']"
        )

    metrics = _exact_fields(
        manifest["metrics"],
        {"primary", "secondary", "selective"},
        "manifest.metrics",
    )
    primary = _exact_fields(
        metrics["primary"],
        {"name", "direction", "aggregation"},
        "manifest.metrics.primary",
    )
    if (
        primary["name"] != "condition_macro_full_shared_feature_delta_mse"
        or primary["direction"] != "lower_is_better"
        or primary["aggregation"] != "mean_over_biological_conditions"
    ):
        raise OODValidationError("manifest.metrics.primary is not the frozen metric")
    secondary = _text_list(metrics["secondary"], "manifest.metrics.secondary")
    if secondary != ["condition_macro_mae", "condition_macro_pearson"]:
        raise OODValidationError("manifest.metrics.secondary is not frozen")
    selective = _text_list(metrics["selective"], "manifest.metrics.selective")
    if selective != [
        "risk_coverage",
        "wrong_accept_rate",
        "unnecessary_abstain_rate",
        "coverage",
    ]:
        raise OODValidationError("manifest.metrics.selective is not frozen")

    confidence = _exact_fields(
        manifest["confidence_interval"],
        {"level", "method", "group_unit", "rng", "seed", "replicates"},
        "manifest.confidence_interval",
    )
    if confidence != {
        "level": 0.95,
        "method": "paired_group_percentile",
        "group_unit": "biological_condition",
        "rng": "numpy.PCG64",
        "seed": 0,
        "replicates": 2000,
    }:
        raise OODValidationError("manifest.confidence_interval is not frozen")

    seeds = manifest["seeds"]
    if (
        not isinstance(seeds, list)
        or len(seeds) < 3
        or len(set(seeds)) != len(seeds)
        or any(isinstance(seed, bool) or not isinstance(seed, int) for seed in seeds)
    ):
        raise OODValidationError("manifest.seeds must contain at least three unique integers")

    threshold = _exact_fields(
        manifest["threshold_policy"],
        {
            "objective",
            "selection_partition",
            "minimum_validation_coverage",
            "tie_break",
        },
        "manifest.threshold_policy",
    )
    if (
        threshold["objective"] != "minimize_candidate_risk"
        or threshold["selection_partition"] != "validation"
        or threshold["tie_break"]
        != "lowest_risk_then_highest_coverage_then_highest_threshold"
    ):
        raise OODValidationError("manifest.threshold_policy is not frozen")
    coverage = _number(
        threshold["minimum_validation_coverage"],
        "manifest.threshold_policy.minimum_validation_coverage",
    )
    if not 0 < coverage <= 1:
        raise OODValidationError("minimum_validation_coverage must be in (0, 1]")

    external = _exact_fields(
        manifest["external_validation"],
        {
            "source_dataset",
            "external_dataset",
            "cohort",
            "adaptation_steps",
            "feature_policy",
            "files",
        },
        "manifest.external_validation",
    )
    files = _exact_fields(
        external["files"],
        set(P9_EXTERNAL_FILES),
        "manifest.external_validation.files",
    )
    for role, value in files.items():
        _validate_file_record(
            value, f"manifest.external_validation.files.{role}"
        )
    expected_external = {
        "source_dataset": "GSE67402",
        "external_dataset": "GSE94117",
        "cohort": "glycerol_time_course",
        "adaptation_steps": 0,
        "feature_policy": "exact_identifier_intersection",
        "files": P9_EXTERNAL_FILES,
    }
    if external != expected_external:
        raise OODValidationError("manifest.external_validation is not frozen")

    gate = _exact_fields(
        manifest["promotion_gate"],
        {
            "primary_requirement",
            "ci_requirement",
            "leakage_required",
            "minimum_seeds",
            "external_adaptation_steps",
        },
        "manifest.promotion_gate",
    )
    if gate != {
        "primary_requirement": "candidate_strictly_below_simple_baseline",
        "ci_requirement": "paired_difference_ci95_high_below_zero",
        "leakage_required": True,
        "minimum_seeds": 3,
        "external_adaptation_steps": 0,
    }:
        raise OODValidationError("manifest.promotion_gate is not frozen")


def load_ood_manifest(path: str | Path) -> dict[str, Any]:
    """Load and strictly validate a frozen Phase 9 OOD manifest."""

    manifest = _load_json(path)
    _validate_manifest(manifest)
    return manifest


def audit_leakage(
    manifest: Mapping[str, Any], records: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Audit predefined groups before evaluation and fail on any identity overlap."""

    copied_manifest = json.loads(_canonical_bytes(manifest))
    _validate_manifest(copied_manifest)
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)) or not records:
        raise OODValidationError("leakage records must be a non-empty array")

    declared = {
        (axis["id"], partition): set(axis["groups"][partition])
        for axis in copied_manifest["axes"]
        for partition in _PARTITIONS
    }
    seen_units: dict[tuple[str, str], str] = {}
    seen_replicates: dict[tuple[str, str], str] = {}
    observed_groups: dict[tuple[str, str], set[str]] = {
        key: set() for key in declared
    }
    for index, record in enumerate(records):
        path = f"leakage_records[{index}]"
        _exact_fields(
            record,
            {"axis_id", "partition", "biological_unit_id", "replicate_id"},
            path,
        )
        axis_id = _text(record["axis_id"], f"{path}.axis_id")
        partition = _text(record["partition"], f"{path}.partition")
        unit_id = _text(record["biological_unit_id"], f"{path}.biological_unit_id")
        replicate_id = _text(record["replicate_id"], f"{path}.replicate_id")
        key = (axis_id, partition)
        if key not in declared:
            raise OODValidationError(f"{path} names an undeclared axis/partition")
        if unit_id not in declared[key]:
            raise OODValidationError(
                f"{path}.biological_unit_id is not declared for {axis_id}/{partition}"
            )
        observed_groups[key].add(unit_id)
        for field, identity, seen in (
            ("biological_unit_id", unit_id, seen_units),
            ("replicate_id", replicate_id, seen_replicates),
        ):
            identity_key = (axis_id, identity)
            previous = seen.get(identity_key)
            if previous is not None and previous != partition:
                raise OODValidationError(
                    f"{field} overlaps {axis_id} partitions {previous}/{partition}: "
                    f"{identity!r}"
                )
            seen[identity_key] = partition

    missing = [
        f"{axis}/{partition}:{sorted(groups - observed_groups[(axis, partition)])}"
        for (axis, partition), groups in declared.items()
        if groups - observed_groups[(axis, partition)]
    ]
    if missing:
        raise OODValidationError(
            "leakage records do not cover every declared biological group: "
            + "; ".join(missing)
        )
    return {
        "passed": True,
        "checked_before_evaluation": True,
        "axes": list(OOD_AXES),
        "partitions": list(_PARTITIONS),
        "unit_count": len(records),
        "overlaps": [],
    }


def _prediction_rows(
    records: Sequence[Mapping[str, Any]], *, partition: str | None = None
) -> list[dict[str, Any]]:
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
        raise OODValidationError("prediction records must be a JSON array")
    rows = []
    unit_ids = set()
    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            raise OODValidationError(f"prediction_records[{index}] must be an object")
        record_partition = record.get("partition")
        if partition is not None and record_partition != partition:
            continue
        unit_id = _text(record.get("unit_id"), f"prediction_records[{index}].unit_id")
        if unit_id in unit_ids:
            raise OODValidationError(f"duplicate prediction unit_id: {unit_id!r}")
        unit_ids.add(unit_id)
        row = {
            "unit_id": unit_id,
            "reliability_score": _number(
                record.get("reliability_score"),
                f"prediction_records[{index}].reliability_score",
            ),
            "candidate_loss": _number(
                record.get("candidate_loss"),
                f"prediction_records[{index}].candidate_loss",
            ),
            "baseline_loss": _number(
                record.get("baseline_loss"),
                f"prediction_records[{index}].baseline_loss",
            ),
        }
        if row["candidate_loss"] < 0 or row["baseline_loss"] < 0:
            raise OODValidationError("prediction losses must be non-negative")
        rows.append(row)
    return rows


def select_threshold(
    records: Sequence[Mapping[str, Any]],
    minimum_validation_coverage: float,
) -> dict[str, Any]:
    """Select a reliability threshold from validation rows only."""

    minimum = _number(
        minimum_validation_coverage, "minimum_validation_coverage"
    )
    if not 0 < minimum <= 1:
        raise OODValidationError("minimum_validation_coverage must be in (0, 1]")
    rows = _prediction_rows(records, partition="validation")
    if not rows:
        raise OODValidationError("validation records are required for threshold selection")

    candidates = []
    for threshold in sorted({row["reliability_score"] for row in rows}, reverse=True):
        accepted = [row for row in rows if row["reliability_score"] >= threshold]
        coverage = len(accepted) / len(rows)
        if coverage + 1e-15 < minimum:
            continue
        risk = sum(row["candidate_loss"] for row in accepted) / len(accepted)
        candidates.append((risk, -coverage, -threshold, threshold, accepted, coverage))
    if not candidates:
        raise OODValidationError("no validation threshold meets minimum coverage")
    _, _, _, threshold, accepted, coverage = min(candidates)
    return {
        "threshold": threshold,
        "selection_partition": "validation",
        "accepted_units": len(accepted),
        "total_units": len(rows),
        "coverage": coverage,
        "candidate_risk": sum(row["candidate_loss"] for row in accepted) / len(accepted),
    }


def selective_metrics(
    records: Sequence[Mapping[str, Any]], threshold: float
) -> dict[str, Any]:
    """Compute condition-level selective-prediction metrics."""

    frozen_threshold = _number(threshold, "threshold")
    rows = _prediction_rows(records)
    if not rows:
        raise OODValidationError("selective metrics require at least one record")
    accepted = [row for row in rows if row["reliability_score"] >= frozen_threshold]
    harmful = [row for row in rows if row["candidate_loss"] >= row["baseline_loss"]]
    beneficial = [row for row in rows if row["candidate_loss"] < row["baseline_loss"]]

    wrong_accept = sum(
        row["reliability_score"] >= frozen_threshold for row in harmful
    )
    unnecessary = sum(
        row["reliability_score"] < frozen_threshold for row in beneficial
    )
    ordered = sorted(
        rows, key=lambda row: (-row["reliability_score"], row["unit_id"])
    )
    curve = []
    cumulative = 0.0
    for index, row in enumerate(ordered, start=1):
        cumulative += row["candidate_loss"]
        curve.append(
            {
                "coverage": index / len(ordered),
                "risk": cumulative / index,
                "accepted_units": index,
            }
        )
    return {
        "threshold": frozen_threshold,
        "coverage": len(accepted) / len(rows),
        "accepted_risk": (
            sum(row["candidate_loss"] for row in accepted) / len(accepted)
            if accepted
            else None
        ),
        "wrong_accept_rate": wrong_accept / len(harmful) if harmful else None,
        "unnecessary_abstain_rate": (
            unnecessary / len(beneficial) if beneficial else None
        ),
        "risk_coverage": curve,
        "denominators": {
            "all_units": len(rows),
            "harmful_units": len(harmful),
            "beneficial_units": len(beneficial),
        },
    }


def promotion_status(
    *,
    candidate_primary: float,
    baseline_primary: float,
    paired_difference_ci95: Mapping[str, Any],
    leakage_audit_passed: bool,
    external_adaptation_steps: int,
    seed_count: int,
) -> dict[str, Any]:
    """Apply the frozen fail-closed scientific promotion gate."""

    candidate = _number(candidate_primary, "candidate_primary")
    baseline = _number(baseline_primary, "baseline_primary")
    _exact_fields(paired_difference_ci95, {"low", "high"}, "paired_difference_ci95")
    _number(paired_difference_ci95["low"], "paired_difference_ci95.low")
    high = _number(paired_difference_ci95["high"], "paired_difference_ci95.high")
    reasons = []
    if leakage_audit_passed is not True:
        reasons.append("leakage_audit_failed")
    if (
        isinstance(external_adaptation_steps, bool)
        or external_adaptation_steps != 0
    ):
        reasons.append("external_adaptation_not_zero")
    if isinstance(seed_count, bool) or not isinstance(seed_count, int) or seed_count < 3:
        reasons.append("fewer_than_three_seeds")
    if candidate >= baseline:
        reasons.append("primary_not_better_than_baseline")
    if high >= 0:
        reasons.append("primary_ci_not_below_zero")
    passed = not reasons
    return {
        "available": passed,
        "scientifically_validated": passed,
        "reason_codes": reasons,
    }


def _validate_source_file(value: Any, path: str) -> None:
    _validate_file_record(value, path)


def _validate_source(value: Any, path: str, *, external: bool) -> None:
    fields = {
        "accession",
        "cohort",
        "role",
        "platform",
        "organism",
        "data_file",
        "metadata_file",
    }
    if external:
        fields.add("adaptation_steps")
    source = _exact_fields(value, fields, path)
    for field in ("accession", "cohort", "role", "platform", "organism"):
        _text(source[field], f"{path}.{field}")
    _validate_source_file(source["data_file"], f"{path}.data_file")
    _validate_source_file(source["metadata_file"], f"{path}.metadata_file")
    if external and source["adaptation_steps"] != 0:
        raise OODValidationError(f"{path}.adaptation_steps must be zero")


def _validate_external_artifact(
    result: dict[str, Any], manifest: Mapping[str, Any]
) -> None:
    _exact_fields(
        result,
        {
            "schema_version",
            "benchmark_id",
            "manifest_sha256",
            "source_dataset",
            "external_dataset",
            "feature_contract",
            "split_contract",
            "leakage_audit",
            "model",
            "baseline",
            "threshold",
            "evaluation",
            "status",
            "provenance",
        },
        "result",
    )
    if result["schema_version"] != "vc.ood-result.v1":
        raise OODValidationError("unsupported OOD result schema_version")
    if result["benchmark_id"] != manifest["benchmark_id"]:
        raise OODValidationError("result benchmark_id does not match manifest")
    if result["manifest_sha256"] != canonical_sha256(manifest):
        raise OODValidationError("result manifest_sha256 does not match manifest")
    _validate_source(result["source_dataset"], "result.source_dataset", external=False)
    _validate_source(result["external_dataset"], "result.external_dataset", external=True)
    expected_files = manifest["external_validation"]["files"]
    file_pairs = (
        (
            result["source_dataset"]["data_file"],
            expected_files["source_counts"],
            "result.source_dataset.data_file",
        ),
        (
            result["source_dataset"]["metadata_file"],
            expected_files["source_soft"],
            "result.source_dataset.metadata_file",
        ),
        (
            result["external_dataset"]["data_file"],
            expected_files["external_raw"],
            "result.external_dataset.data_file",
        ),
        (
            result["external_dataset"]["metadata_file"],
            expected_files["external_soft"],
            "result.external_dataset.metadata_file",
        ),
    )
    for actual, expected, path in file_pairs:
        if actual != expected:
            raise OODValidationError(f"{path} does not match the frozen manifest")
    external = result["external_dataset"]
    source_metadata = {
        key: result["source_dataset"][key]
        for key in ("accession", "cohort", "role", "platform", "organism")
    }
    if source_metadata != {
        "accession": "GSE67402",
        "cohort": "glucose_time_course:rRNA-depleted_total_RNA",
        "role": "fit_and_internal_split_source",
        "platform": "GPL14548 / Illumina HiSeq 2000",
        "organism": "Escherichia coli REL606",
    }:
        raise OODValidationError("source dataset metadata is not frozen")
    external_metadata = {
        key: external[key]
        for key in ("accession", "cohort", "role", "platform", "organism")
    }
    if external_metadata != {
        "accession": "GSE94117",
        "cohort": "glycerol_time_course",
        "role": "adaptation_free_external_evaluation",
        "platform": "GPL22993 / Illumina HiSeq 2500",
        "organism": "Escherichia coli B str. REL606",
    }:
        raise OODValidationError("external dataset metadata is not frozen")
    if (
        external["accession"] != manifest["external_validation"]["external_dataset"]
        or external["cohort"] != manifest["external_validation"]["cohort"]
    ):
        raise OODValidationError("external dataset does not match frozen manifest")

    features = _exact_fields(
        result["feature_contract"],
        {
            "namespace",
            "policy",
            "ordered_feature_count",
            "ordered_feature_ids_sha256",
            "source_only_dropped_ids",
            "external_summary_rows_excluded",
            "identifier_conversion_steps",
            "fill_steps",
        },
        "result.feature_contract",
    )
    if features["policy"] != "exact_identifier_intersection":
        raise OODValidationError("feature policy must be exact_identifier_intersection")
    _text(features["namespace"], "result.feature_contract.namespace")
    _positive_int(
        features["ordered_feature_count"],
        "result.feature_contract.ordered_feature_count",
    )
    _sha256(
        features["ordered_feature_ids_sha256"],
        "result.feature_contract.ordered_feature_ids_sha256",
    )
    _text_list(
        features["source_only_dropped_ids"],
        "result.feature_contract.source_only_dropped_ids",
        allow_empty=True,
    )
    _text_list(
        features["external_summary_rows_excluded"],
        "result.feature_contract.external_summary_rows_excluded",
        allow_empty=True,
    )
    if features["identifier_conversion_steps"] != [] or features["fill_steps"] != []:
        raise OODValidationError("identifier conversion and feature filling are forbidden")
    if features != _P9_FEATURE_CONTRACT:
        raise OODValidationError("result feature contract is not frozen")

    split = _exact_fields(
        result["split_contract"],
        {
            "source_train_time_hours",
            "source_validation_time_hours",
            "source_test_time_hours",
            "external_reference_time_hours",
            "external_evaluation_time_hours",
            "group_unit",
            "split_generation",
        },
        "result.split_contract",
    )
    for field in (
        "source_train_time_hours",
        "source_validation_time_hours",
        "source_test_time_hours",
        "external_evaluation_time_hours",
    ):
        values = split[field]
        if not isinstance(values, list) or not values:
            raise OODValidationError(f"result.split_contract.{field} must be non-empty")
        for index, value in enumerate(values):
            _number(value, f"result.split_contract.{field}[{index}]")
    _number(
        split["external_reference_time_hours"],
        "result.split_contract.external_reference_time_hours",
    )
    if (
        split["group_unit"] != "biological_condition"
        or split["split_generation"] != "predeclared_no_random_split"
    ):
        raise OODValidationError("result split contract is not frozen")
    if split != {
        "source_train_time_hours": [3, 4, 6, 24, 168],
        "source_validation_time_hours": [5, 8, 48],
        "source_test_time_hours": [336],
        "external_reference_time_hours": 5,
        "external_evaluation_time_hours": [7, 8, 10, 14, 24, 48, 168, 336],
        "group_unit": "biological_condition",
        "split_generation": "predeclared_no_random_split",
    }:
        raise OODValidationError("result split contract is not the frozen P9 split")

    leakage = _exact_fields(
        result["leakage_audit"],
        {
            "passed",
            "checked_before_evaluation",
            "group_unit",
            "overlaps",
            "excluded_external_cohorts",
        },
        "result.leakage_audit",
    )
    if (
        leakage["passed"] is not True
        or leakage["checked_before_evaluation"] is not True
        or leakage["group_unit"] != "biological_condition"
        or leakage["overlaps"] != []
    ):
        raise OODValidationError("external leakage audit did not pass")
    _text_list(
        leakage["excluded_external_cohorts"],
        "result.leakage_audit.excluded_external_cohorts",
    )

    model = _exact_fields(
        result["model"],
        {"id", "kind", "fit_dataset", "fit_partition", "parameter_sha256", "input_transform"},
        "result.model",
    )
    for field in ("id", "kind", "fit_dataset", "fit_partition", "input_transform"):
        _text(model[field], f"result.model.{field}")
    _sha256(model["parameter_sha256"], "result.model.parameter_sha256")
    baseline = _exact_fields(
        result["baseline"], {"id", "kind"}, "result.baseline"
    )
    _text(baseline["id"], "result.baseline.id")
    _text(baseline["kind"], "result.baseline.kind")

    threshold = _exact_fields(
        result["threshold"],
        {
            "selection_partition",
            "reliability_score",
            "selected_value",
            "minimum_validation_coverage",
            "accepted_units",
            "total_units",
            "coverage",
            "candidate_risk",
        },
        "result.threshold",
    )
    if threshold["selection_partition"] != "validation":
        raise OODValidationError("threshold must be selected on validation")
    _text(threshold["reliability_score"], "result.threshold.reliability_score")
    for field in (
        "selected_value",
        "minimum_validation_coverage",
        "coverage",
        "candidate_risk",
    ):
        _number(threshold[field], f"result.threshold.{field}")
    accepted_units = _positive_int(
        threshold["accepted_units"], "result.threshold.accepted_units"
    )
    total_units = _positive_int(
        threshold["total_units"], "result.threshold.total_units"
    )
    if accepted_units > total_units or threshold["coverage"] != accepted_units / total_units:
        raise OODValidationError("threshold coverage does not match accepted units")

    evaluation = _exact_fields(
        result["evaluation"],
        {"primary", "secondary", "by_condition", "seeds", "seed_runs", "selective"},
        "result.evaluation",
    )
    primary = _exact_fields(
        evaluation["primary"],
        {"name", "direction", "candidate", "baseline", "difference", "paired_ci95"},
        "result.evaluation.primary",
    )
    if (
        primary["name"] != manifest["metrics"]["primary"]["name"]
        or primary["direction"] != "lower_is_better"
    ):
        raise OODValidationError("result primary metric does not match manifest")
    candidate = _number(primary["candidate"], "result.evaluation.primary.candidate")
    simple = _number(primary["baseline"], "result.evaluation.primary.baseline")
    difference = _number(primary["difference"], "result.evaluation.primary.difference")
    if not math.isclose(difference, candidate - simple, rel_tol=0, abs_tol=1e-12):
        raise OODValidationError("primary difference does not equal candidate - baseline")
    ci = _exact_fields(
        primary["paired_ci95"],
        {"low", "high", "method", "group_count", "replicates", "seed"},
        "result.evaluation.primary.paired_ci95",
    )
    low = _number(ci["low"], "result.evaluation.primary.paired_ci95.low")
    high = _number(ci["high"], "result.evaluation.primary.paired_ci95.high")
    if low > high:
        raise OODValidationError("paired CI low must not exceed high")
    if (
        ci["method"] != "paired_group_percentile"
        or ci["replicates"] != manifest["confidence_interval"]["replicates"]
        or ci["seed"] != manifest["confidence_interval"]["seed"]
    ):
        raise OODValidationError("paired CI does not match manifest")
    _positive_int(ci["group_count"], "result.evaluation.primary.paired_ci95.group_count")

    secondary = _exact_fields(
        evaluation["secondary"],
        {"candidate_mae", "baseline_mae", "candidate_pearson", "baseline_pearson"},
        "result.evaluation.secondary",
    )
    _number(secondary["candidate_mae"], "result.evaluation.secondary.candidate_mae")
    _number(secondary["baseline_mae"], "result.evaluation.secondary.baseline_mae")
    _number(
        secondary["candidate_pearson"],
        "result.evaluation.secondary.candidate_pearson",
    )
    if secondary["baseline_pearson"] is not None:
        _number(
            secondary["baseline_pearson"],
            "result.evaluation.secondary.baseline_pearson",
        )

    conditions = evaluation["by_condition"]
    if not isinstance(conditions, list) or not conditions:
        raise OODValidationError("result.evaluation.by_condition must be non-empty")
    condition_losses = []
    for index, row in enumerate(conditions):
        path = f"result.evaluation.by_condition[{index}]"
        _exact_fields(
            row,
            {
                "time_hours",
                "replicate_count",
                "candidate_mse",
                "baseline_mse",
                "candidate_mae",
                "baseline_mae",
                "candidate_pearson",
                "reliability_score",
                "accepted",
            },
            path,
        )
        for field in (
            "time_hours",
            "candidate_mse",
            "baseline_mse",
            "candidate_mae",
            "baseline_mae",
            "candidate_pearson",
            "reliability_score",
        ):
            _number(row[field], f"{path}.{field}")
        _positive_int(row["replicate_count"], f"{path}.replicate_count")
        if not isinstance(row["accepted"], bool):
            raise OODValidationError(f"{path}.accepted must be boolean")
        if row["accepted"] != (
            row["reliability_score"] >= threshold["selected_value"]
        ):
            raise OODValidationError(
                f"{path}.accepted does not match the frozen threshold"
            )
        condition_losses.append((row["candidate_mse"], row["baseline_mse"]))
    macro_candidate = sum(item[0] for item in condition_losses) / len(condition_losses)
    macro_baseline = sum(item[1] for item in condition_losses) / len(condition_losses)
    if not math.isclose(candidate, macro_candidate, rel_tol=0, abs_tol=1e-12):
        raise OODValidationError("candidate primary is not condition-macro MSE")
    if not math.isclose(simple, macro_baseline, rel_tol=0, abs_tol=1e-12):
        raise OODValidationError("baseline primary is not condition-macro MSE")

    if evaluation["seeds"] != manifest["seeds"]:
        raise OODValidationError("result seeds do not match manifest")
    runs = evaluation["seed_runs"]
    if not isinstance(runs, list) or len(runs) != len(manifest["seeds"]):
        raise OODValidationError("result must report one run per frozen seed")
    for index, run in enumerate(runs):
        path = f"result.evaluation.seed_runs[{index}]"
        _exact_fields(run, {"seed", "candidate", "baseline", "difference"}, path)
        if run["seed"] != manifest["seeds"][index]:
            raise OODValidationError(f"{path}.seed is not in frozen order")
        run_candidate = _number(run["candidate"], f"{path}.candidate")
        run_baseline = _number(run["baseline"], f"{path}.baseline")
        run_difference = _number(run["difference"], f"{path}.difference")
        if not (
            math.isclose(run_candidate, candidate, rel_tol=0, abs_tol=1e-12)
            and math.isclose(run_baseline, simple, rel_tol=0, abs_tol=1e-12)
            and math.isclose(
                run_difference, run_candidate - run_baseline, rel_tol=0, abs_tol=1e-12
            )
        ):
            raise OODValidationError("seed run does not reproduce deterministic primary")

    selective = evaluation["selective"]
    _exact_fields(
        selective,
        {
            "threshold",
            "coverage",
            "accepted_risk",
            "wrong_accept_rate",
            "unnecessary_abstain_rate",
            "risk_coverage",
            "denominators",
        },
        "result.evaluation.selective",
    )
    for field in (
        "threshold",
        "coverage",
        "accepted_risk",
        "wrong_accept_rate",
        "unnecessary_abstain_rate",
    ):
        if selective[field] is not None:
            _number(selective[field], f"result.evaluation.selective.{field}")
    if not isinstance(selective["risk_coverage"], list) or not selective["risk_coverage"]:
        raise OODValidationError("selective risk_coverage must be non-empty")
    _exact_fields(
        selective["denominators"],
        {"all_units", "harmful_units", "beneficial_units"},
        "result.evaluation.selective.denominators",
    )
    expected_selective = selective_metrics(
        [
            {
                "unit_id": f"GSE94117:glycerol:{row['time_hours']}h",
                "reliability_score": row["reliability_score"],
                "candidate_loss": row["candidate_mse"],
                "baseline_loss": row["baseline_mse"],
            }
            for row in conditions
        ],
        threshold["selected_value"],
    )
    if selective != expected_selective:
        raise OODValidationError(
            "result selective metrics do not match condition-level records"
        )

    expected_status = promotion_status(
        candidate_primary=candidate,
        baseline_primary=simple,
        paired_difference_ci95={"low": low, "high": high},
        leakage_audit_passed=leakage["passed"],
        external_adaptation_steps=external["adaptation_steps"],
        seed_count=len(runs),
    )
    _exact_fields(
        result["status"],
        {"available", "scientifically_validated", "reason_codes"},
        "result.status",
    )
    if result["status"] != expected_status:
        raise OODValidationError("result status does not match fail-closed promotion gate")

    provenance = _exact_fields(
        result["provenance"],
        {"generator", "code_baseline", "raw_data_committed", "model_weights_committed"},
        "result.provenance",
    )
    _text(provenance["generator"], "result.provenance.generator")
    _git_sha(provenance["code_baseline"], "result.provenance.code_baseline")
    if (
        provenance["raw_data_committed"] is not False
        or provenance["model_weights_committed"] is not False
    ):
        raise OODValidationError("raw data and model weights must not be committed")


def load_validation_artifact(
    path: str | Path, *, manifest_path: str | Path
) -> dict[str, Any]:
    """Load and verify a frozen adaptation-free external-validation result."""

    manifest = load_ood_manifest(manifest_path)
    result = _load_json(path)
    _validate_external_artifact(result, manifest)
    return result
