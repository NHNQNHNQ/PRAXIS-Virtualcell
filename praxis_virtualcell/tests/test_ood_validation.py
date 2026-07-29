"""Phase 9 multi-axis OOD, abstention, and external-validation contracts."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from praxis_virtualcell.benchmarks.ood_validation import (
    OOD_AXES,
    OODValidationError,
    audit_leakage,
    load_ood_manifest,
    load_validation_artifact,
    promotion_status,
    select_threshold,
    selective_metrics,
)

_ROOT = Path(__file__).parents[2]
_MANIFEST = _ROOT / "data" / "benchmarks" / "p9" / "ood-manifest.json"
_GROUPS = _ROOT / "data" / "benchmarks" / "p9" / "group-fixture.json"
_RESULT = _ROOT / "data" / "benchmarks" / "p9" / "external-validation.json"


def _selection_records() -> list[dict[str, object]]:
    return [
        {
            "unit_id": "train-1",
            "partition": "train",
            "reliability_score": 0.9,
            "candidate_loss": 0.2,
            "baseline_loss": 0.4,
        },
        {
            "unit_id": "validation-1",
            "partition": "validation",
            "reliability_score": 0.8,
            "candidate_loss": 0.1,
            "baseline_loss": 0.4,
        },
        {
            "unit_id": "validation-2",
            "partition": "validation",
            "reliability_score": 0.6,
            "candidate_loss": 0.2,
            "baseline_loss": 0.4,
        },
        {
            "unit_id": "validation-3",
            "partition": "validation",
            "reliability_score": 0.1,
            "candidate_loss": 1.0,
            "baseline_loss": 0.4,
        },
        {
            "unit_id": "test-1",
            "partition": "test",
            "reliability_score": 0.95,
            "candidate_loss": 999.0,
            "baseline_loss": 0.4,
        },
        {
            "unit_id": "external-1",
            "partition": "external",
            "reliability_score": 0.95,
            "candidate_loss": 999.0,
            "baseline_loss": 0.4,
        },
    ]


def test_authoritative_manifest_freezes_all_axes_and_evaluation_policy():
    manifest = load_ood_manifest(_MANIFEST)

    assert tuple(axis["id"] for axis in manifest["axes"]) == OOD_AXES
    assert len(set(manifest["seeds"])) >= 3
    assert manifest["threshold_policy"]["selection_partition"] == "validation"
    assert set(manifest["data_roles"]["fit_partitions"]) <= {"train"}
    assert set(manifest["data_roles"]["threshold_partitions"]) <= {
        "train",
        "validation",
    }
    assert set(manifest["data_roles"]["evaluation_partitions"]) == {
        "test",
        "external",
    }
    assert manifest["external_validation"]["adaptation_steps"] == 0
    assert manifest["external_validation"]["files"]["source_counts"][
        "sha256"
    ] == "4d8e8e4bee7cf08dea4247f319403c1399af6c9e4069f40f65f54911b748a688"
    assert manifest["external_validation"]["files"]["external_raw"][
        "sha256"
    ] == "3433f1d37d90fd24fa59b19b04e52cb68fc6201d5e49408efcb610fe47d18483"
    assert manifest["confidence_interval"] == {
        "level": 0.95,
        "method": "paired_group_percentile",
        "group_unit": "biological_condition",
        "rng": "numpy.PCG64",
        "seed": 0,
        "replicates": 2000,
    }
    assert manifest["metrics"]["primary"]["name"] == (
        "condition_macro_full_shared_feature_delta_mse"
    )
    assert {
        "risk_coverage",
        "wrong_accept_rate",
        "unnecessary_abstain_rate",
        "coverage",
    } <= set(manifest["metrics"]["selective"])


def test_manifest_is_strict_and_rejects_duplicate_or_unknown_fields(tmp_path):
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text(
        '{"schema_version":"vc.ood-manifest.v1",'
        '"schema_version":"vc.ood-manifest.v1"}',
        encoding="utf-8",
    )
    with pytest.raises(OODValidationError, match="duplicate"):
        load_ood_manifest(duplicate)

    value = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    value["silent_fallback"] = True
    unknown = tmp_path / "unknown.json"
    unknown.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(OODValidationError, match="fields must be exactly"):
        load_ood_manifest(unknown)


def test_every_axis_uses_disjoint_biological_units_and_replicates():
    manifest = load_ood_manifest(_MANIFEST)
    records = json.loads(_GROUPS.read_text(encoding="utf-8"))

    audit = audit_leakage(manifest, records)

    assert audit["passed"] is True
    assert audit["axes"] == list(OOD_AXES)
    assert audit["partitions"] == ["train", "validation", "test"]
    assert audit["overlaps"] == []
    assert audit["unit_count"] == len(records)


@pytest.mark.parametrize("identity_field", ["biological_unit_id", "replicate_id"])
def test_leakage_audit_fails_closed_on_cross_partition_identity(identity_field):
    manifest = load_ood_manifest(_MANIFEST)
    records = json.loads(_GROUPS.read_text(encoding="utf-8"))
    records[1][identity_field] = records[0][identity_field]

    with pytest.raises(OODValidationError, match=identity_field):
        audit_leakage(manifest, records)


def test_manifest_rejects_missing_partition_and_feature_label_overlap(tmp_path):
    value = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    del value["axes"][0]["groups"]["test"]
    path = tmp_path / "missing-test.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(OODValidationError, match="train, validation, and test"):
        load_ood_manifest(path)

    value = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    value["data_roles"]["label_fields"].append(
        value["data_roles"]["feature_fields"][0]
    )
    path = tmp_path / "leaking-label.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(OODValidationError, match="feature_fields.*label_fields"):
        load_ood_manifest(path)


def test_threshold_is_selected_on_validation_only():
    records = _selection_records()
    selected = select_threshold(records, minimum_validation_coverage=2 / 3)
    assert selected == {
        "threshold": 0.6,
        "selection_partition": "validation",
        "accepted_units": 2,
        "total_units": 3,
        "coverage": pytest.approx(2 / 3),
        "candidate_risk": pytest.approx(0.15),
    }

    poisoned = copy.deepcopy(records)
    for record in poisoned:
        if record["partition"] in {"test", "external"}:
            record["reliability_score"] = -999.0
            record["candidate_loss"] = -999.0
            record["baseline_loss"] = -999.0
    assert select_threshold(poisoned, 2 / 3) == selected


def test_selective_metrics_report_all_required_failure_modes():
    records = [
        {
            "unit_id": "beneficial-accepted",
            "reliability_score": 0.9,
            "candidate_loss": 0.1,
            "baseline_loss": 0.4,
        },
        {
            "unit_id": "harmful-accepted",
            "reliability_score": 0.8,
            "candidate_loss": 0.8,
            "baseline_loss": 0.4,
        },
        {
            "unit_id": "beneficial-rejected",
            "reliability_score": 0.2,
            "candidate_loss": 0.2,
            "baseline_loss": 0.4,
        },
        {
            "unit_id": "harmful-rejected",
            "reliability_score": 0.1,
            "candidate_loss": 0.9,
            "baseline_loss": 0.4,
        },
    ]

    metrics = selective_metrics(records, threshold=0.5)

    assert metrics["coverage"] == 0.5
    assert metrics["wrong_accept_rate"] == 0.5
    assert metrics["unnecessary_abstain_rate"] == 0.5
    assert metrics["accepted_risk"] == pytest.approx(0.45)
    assert len(metrics["risk_coverage"]) == 4
    assert metrics["risk_coverage"][-1]["coverage"] == 1.0


@pytest.mark.parametrize(
    ("candidate", "baseline", "ci_high", "expected_reason"),
    [
        (1.1, 1.0, -0.01, "primary_not_better_than_baseline"),
        (0.9, 1.0, 0.02, "primary_ci_not_below_zero"),
    ],
)
def test_model_that_does_not_clear_simple_baseline_gate_is_unavailable(
    candidate, baseline, ci_high, expected_reason
):
    status = promotion_status(
        candidate_primary=candidate,
        baseline_primary=baseline,
        paired_difference_ci95={"low": -0.2, "high": ci_high},
        leakage_audit_passed=True,
        external_adaptation_steps=0,
        seed_count=3,
    )

    assert status["available"] is False
    assert status["scientifically_validated"] is False
    assert expected_reason in status["reason_codes"]


def test_external_result_is_real_adaptation_free_and_fail_closed():
    result = load_validation_artifact(_RESULT, manifest_path=_MANIFEST)

    assert result["external_dataset"]["accession"] == "GSE94117"
    assert result["external_dataset"]["cohort"] == "glycerol_time_course"
    assert result["external_dataset"]["adaptation_steps"] == 0
    assert result["feature_contract"]["policy"] == "exact_identifier_intersection"
    assert result["feature_contract"]["ordered_feature_count"] == 4484
    assert result["feature_contract"]["source_only_dropped_ids"] == [
        "RF01769.1",
        "RF01771.1",
    ]
    assert result["feature_contract"]["identifier_conversion_steps"] == []
    assert result["feature_contract"]["fill_steps"] == []
    assert result["leakage_audit"]["passed"] is True
    assert result["evaluation"]["primary"]["candidate"] >= (
        result["evaluation"]["primary"]["baseline"]
    )
    assert len(result["evaluation"]["seed_runs"]) >= 3
    assert result["status"]["available"] is False
    assert result["status"]["scientifically_validated"] is False
    assert "primary_not_better_than_baseline" in result["status"]["reason_codes"]


def test_external_result_rejects_tampering_and_unknown_fields(tmp_path):
    value = json.loads(_RESULT.read_text(encoding="utf-8"))
    value["external_dataset"]["adaptation_steps"] = 1
    tampered = tmp_path / "adapted.json"
    tampered.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(OODValidationError, match="adaptation_steps"):
        load_validation_artifact(tampered, manifest_path=_MANIFEST)

    value = json.loads(_RESULT.read_text(encoding="utf-8"))
    value["source_dataset"]["data_file"]["sha256"] = "0" * 64
    tampered = tmp_path / "source-hash.json"
    tampered.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(OODValidationError, match="source_dataset.*data_file"):
        load_validation_artifact(tampered, manifest_path=_MANIFEST)

    value = json.loads(_RESULT.read_text(encoding="utf-8"))
    value["feature_contract"]["ordered_feature_count"] = 4483
    tampered = tmp_path / "feature-count.json"
    tampered.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(OODValidationError, match="feature contract"):
        load_validation_artifact(tampered, manifest_path=_MANIFEST)

    value = json.loads(_RESULT.read_text(encoding="utf-8"))
    value["external_dataset"]["platform"] = "unverified platform"
    tampered = tmp_path / "platform.json"
    tampered.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(OODValidationError, match="external dataset metadata"):
        load_validation_artifact(tampered, manifest_path=_MANIFEST)

    value = json.loads(_RESULT.read_text(encoding="utf-8"))
    value["evaluation"]["selective"]["wrong_accept_rate"] = 0.0
    tampered = tmp_path / "selective.json"
    tampered.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(OODValidationError, match="selective metrics"):
        load_validation_artifact(tampered, manifest_path=_MANIFEST)

    value = json.loads(_RESULT.read_text(encoding="utf-8"))
    value["optimistic_note"] = "ignore primary metric"
    unknown = tmp_path / "unknown.json"
    unknown.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(OODValidationError, match="fields must be exactly"):
        load_validation_artifact(unknown, manifest_path=_MANIFEST)
