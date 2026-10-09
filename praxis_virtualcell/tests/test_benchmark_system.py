from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

from praxis_virtualcell.benchmarks.golden_norman import paired_bootstrap_ci
from praxis_virtualcell.benchmarks.system import (
    BenchmarkEvidenceBundleV1,
    BenchmarkEvidenceLedger,
    BenchmarkProtocolV1,
    BenchmarkResultV1,
    BenchmarkRunV1,
    BenchmarkSystemError,
    GroupIdentityV1,
    ThresholdReceiptV1,
    audit_group_leakage,
    compute_p21b_execution_fingerprint,
    derive_evidence,
    replay_checked_in_benchmarks,
    select_validation_threshold,
)

_ROOT = Path(__file__).parents[2]
_VALIDATION_GROUP_IDS = ("validation-1", "validation-2")
_TEST_GROUP_IDS = ("test-1", "test-2", "test-3", "test-4")
_EXTERNAL_GROUP_IDS = ("external-1", "external-2", "external-3", "external-4")


def _fp(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def _canonical_fp(value) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _mean(values) -> float:
    values = tuple(values)
    return math.fsum(values) / len(values)


def _bind(raw: dict, field: str) -> dict:
    payload = dict(raw)
    payload.pop(field, None)
    raw[field] = _canonical_fp(payload)
    return raw


def _scope() -> dict:
    return {
        "schema_version": "vc.benchmark-scope.v1",
        "organism": "synthetic-organism",
        "cell_type": "synthetic-cell",
        "intervention": "synthetic-perturbation",
        "endpoint": "synthetic-delta",
    }


def _group_rows_raw() -> list[dict]:
    rows = []
    by_partition = {
        "train": ("train-1", "train-2"),
        "validation": _VALIDATION_GROUP_IDS,
        "test": _TEST_GROUP_IDS,
        "external": _EXTERNAL_GROUP_IDS,
    }
    index = 0
    for partition, group_ids in by_partition.items():
        for group_id in group_ids:
            rows.append(
                {
                    "schema_version": "vc.benchmark-group-identity.v1",
                    "partition": partition,
                    "group_id": group_id,
                    "donor": f"donor-{index}",
                    "condition": f"condition-{index}",
                    "replicate": f"replicate-{index}",
                    "batch": f"batch-{index}",
                }
            )
            index += 1
    return rows


def _protocol_raw(*, direction: str = "lower_is_better") -> dict:
    scope = _scope()
    leakage_records = _group_rows_raw()
    scope_fingerprint = hashlib.sha256(json.dumps(scope, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {
        "schema_version": "vc.benchmark-protocol.v1",
        "protocol_id": "p21a-synthetic-contract-v1",
        "task": "synthetic_perturbation_delta_prediction",
        "scope": scope,
        "pack_fingerprint": _fp("pack"),
        "dataset": {
            "schema_version": "vc.benchmark-dataset-binding.v1",
            "dataset_fingerprint": _fp("internal-dataset"),
            "platform_fingerprint": _fp("internal-platform"),
        },
        "feature_contract_fingerprint": _fp("features"),
        "output_contract_fingerprint": _fp("outputs"),
        "split": {
            "schema_version": "vc.benchmark-split.v1",
            "split_fingerprint": _fp("split"),
            "partitions": ["train", "validation", "test", "external"],
            "group_unit": "biological_condition",
            "leakage_dimensions": ["donor", "condition", "replicate", "batch"],
            "leakage_record_count": len(leakage_records),
            "leakage_records_fingerprint": _canonical_fp(leakage_records),
            "fit_partitions": ["train"],
            "tuning_partitions": ["train", "validation"],
            "threshold_selection_partition": "validation",
            "evaluation_partitions": ["test", "external"],
            "validation_group_ids": list(_VALIDATION_GROUP_IDS),
            "validation_group_set_fingerprint": _canonical_fp(sorted(_VALIDATION_GROUP_IDS)),
            "validation_group_count": len(_VALIDATION_GROUP_IDS),
            "test_group_ids": list(_TEST_GROUP_IDS),
            "test_group_set_fingerprint": _canonical_fp(sorted(_TEST_GROUP_IDS)),
            "test_group_count": len(_TEST_GROUP_IDS),
            "external_group_ids": list(_EXTERNAL_GROUP_IDS),
            "external_group_set_fingerprint": _canonical_fp(sorted(_EXTERNAL_GROUP_IDS)),
            "external_group_count": len(_EXTERNAL_GROUP_IDS),
            "random_split": False,
        },
        "baseline": {
            "schema_version": "vc.benchmark-baseline.v1",
            "baseline_id": "no-change-v1",
            "baseline_fingerprint": _fp("baseline"),
            "kind": "no_change",
            "fit_partition": "train",
            "simple": True,
        },
        "primary_metric": {
            "schema_version": "vc.benchmark-metric.v1",
            "name": "condition_macro_delta_score",
            "direction": direction,
            "aggregation": "biological_group_macro",
            "difference": "candidate_minus_baseline",
        },
        "confidence_interval": {
            "schema_version": "vc.benchmark-ci-policy.v1",
            "method": "paired_group_percentile",
            "rng": "numpy.PCG64",
            "quantile_method": "linear",
            "group_unit": "biological_condition",
            "confidence_level": 0.95,
            "replicates": 2000,
            "seed": 0,
        },
        "seeds": [11, 23, 37],
        "threshold_policy": {
            "schema_version": "vc.benchmark-threshold-policy.v1",
            "selection_partition": "validation",
            "reliability_name": "synthetic_reliability",
            "minimum_coverage": 0.5,
            "objective": "minimize_candidate_risk",
            "tie_break": "higher_coverage_then_higher_threshold",
        },
        "calibration_policy": {
            "schema_version": "vc.benchmark-calibration-policy.v1",
            "metric_name": "expected_calibration_error",
            "method": "equal_width",
            "bins": 10,
            "evaluation_partition": "test",
        },
        "ood_policy": [
            {
                "schema_version": "vc.benchmark-ood-gate.v1",
                "axis": "perturbation",
                "metric_name": "condition_macro_delta_score",
                "direction": "lower_is_better",
                "threshold": 0.3,
            },
            {
                "schema_version": "vc.benchmark-ood-gate.v1",
                "axis": "dataset_platform",
                "metric_name": "condition_macro_delta_score",
                "direction": "lower_is_better",
                "threshold": 0.3,
            },
        ],
        "external_policy": {
            "schema_version": "vc.benchmark-external-policy.v1",
            "required": True,
            "dataset_fingerprint": _fp("external-dataset"),
            "platform_fingerprint": _fp("external-platform"),
            "scope_fingerprint": scope_fingerprint,
            "independent_dataset": True,
            "independent_platform": True,
            "adaptation_steps": 0,
        },
        "promotion_gate": {
            "schema_version": "vc.benchmark-promotion-gate.v1",
            "maximum_calibration_error": 0.1,
            "minimum_coverage": 0.5,
            "maximum_selective_risk": 0.3,
            "maximum_wrong_accept_rate": 0.2,
            "maximum_unnecessary_abstain_rate": 0.4,
        },
        "candidate_result_observed": False,
        "frozen": True,
        "composite_score": None,
    }


def _protocol(*, direction: str = "lower_is_better") -> BenchmarkProtocolV1:
    return BenchmarkProtocolV1.from_dict(_protocol_raw(direction=direction))


def _run_raw(protocol: BenchmarkProtocolV1, *, evidence_class: str = "authorized_candidate") -> dict:
    contract_fixture = evidence_class == "contract_fixture"
    candidate_fingerprint = _fp("model")
    run_id = "p21a-synthetic-run-v1"
    raw = {
        "schema_version": "vc.benchmark-run.v1",
        "run_id": run_id,
        "protocol_fingerprint": protocol.fingerprint(),
        "training_job_fingerprint": _fp("job"),
        "training_result_fingerprint": _fp("training-result"),
        "checkpoint_fingerprint": _fp("checkpoint"),
        "artifact_fingerprint": _fp("artifact"),
        "model_card_fingerprint": _fp("model-card"),
        "candidate_model_fingerprint": candidate_fingerprint,
        "model_identity_fingerprint": _fp("model-identity"),
        "factory_registration_fingerprint": _fp("factory-registration"),
        "pack_fingerprint": protocol.pack_fingerprint,
        "feature_contract_fingerprint": protocol.feature_contract_fingerprint,
        "output_contract_fingerprint": protocol.output_contract_fingerprint,
        "trainer_revision": "synthetic-conformance-only",
        "trainer_source_sha256": _fp("trainer-source"),
        "training_environment_fingerprint": _fp("training-environment"),
        "adapter_fingerprints": [_fp("adapter")],
        "evaluation_environment_fingerprint": _fp("evaluation-environment"),
        "evaluation_code_sha256": _fp("evaluation-code"),
        "compatibility_report_fingerprints": [_fp("compatibility")],
        "compatibility_passed": True,
        "seeds": list(protocol.seeds),
        "candidate_registry_state": (
            "candidate_cataloged_contract_only" if contract_fixture else "candidate_cataloged"
        ),
        "candidate_identity_immutable": True,
        "execution_path": "model_adapter_broker_runtime",
        "broker_contract_fingerprint": _fp("broker"),
        "runtime_receipt_fingerprint": _fp("runtime"),
        "direct_model_invocation": False,
        "direct_asset_access": False,
        "fit_partition": "train",
        "threshold_partition": "validation",
        "evaluation_partitions": ["test", "external"],
        "evidence_class": evidence_class,
    }
    provenance_fields = (
        "training_job_fingerprint",
        "training_result_fingerprint",
        "checkpoint_fingerprint",
        "artifact_fingerprint",
        "model_card_fingerprint",
        "candidate_model_fingerprint",
        "model_identity_fingerprint",
        "factory_registration_fingerprint",
        "pack_fingerprint",
        "feature_contract_fingerprint",
        "output_contract_fingerprint",
        "trainer_revision",
        "trainer_source_sha256",
        "training_environment_fingerprint",
    )
    raw["candidate_provenance_fingerprint"] = _canonical_fp({field: raw[field] for field in provenance_fields})
    authorization = {
        "schema_version": "vc.benchmark-run-authorization.v1",
        "authorization_id": ("synthetic-contract-fixture" if contract_fixture else "synthetic-p21b-conformance"),
        "authorized_run_id": run_id,
        "authorized_run_payload_fingerprint": _canonical_fp(raw),
        "authorization_kind": ("contract_fixture" if contract_fixture else "p21b_single_candidate"),
        "protocol_fingerprint": protocol.fingerprint(),
        "scope_fingerprint": protocol.scope.fingerprint(),
        "candidate_model_fingerprint": candidate_fingerprint,
        "asset_manifest_fingerprint": _fp("synthetic-asset-manifest"),
        "output_root_identity_fingerprint": _fp("synthetic-output-root-identity"),
        "real_candidate_run_authorized": not contract_fixture,
        "test_external_access_authorized": not contract_fixture,
    }
    raw["authorization"] = _bind(authorization, "authorization_record_sha256")
    return raw


def _run(protocol: BenchmarkProtocolV1, *, evidence_class: str = "authorized_candidate") -> BenchmarkRunV1:
    return BenchmarkRunV1.from_dict(_run_raw(protocol, evidence_class=evidence_class))


def _rebind_run_authorization(raw: dict) -> dict:
    authorization = raw.pop("authorization")
    authorization["authorized_run_id"] = raw["run_id"]
    authorization["authorized_run_payload_fingerprint"] = _canonical_fp(raw)
    raw["authorization"] = _bind(authorization, "authorization_record_sha256")
    return raw


def _group_rows() -> tuple[GroupIdentityV1, ...]:
    return tuple(GroupIdentityV1.from_dict(item) for item in _group_rows_raw())


def _primary(
    protocol: BenchmarkProtocolV1,
    run: BenchmarkRunV1,
    *,
    partition: str,
    passing: bool = True,
) -> dict:
    lower = protocol.primary_metric.direction == "lower_is_better"
    if passing:
        candidate, baseline = (0.6, 1.0) if lower else (1.4, 1.0)
    else:
        candidate = baseline = 1.0
    row_difference = candidate - baseline
    group_ids = _EXTERNAL_GROUP_IDS if partition == "external" else _TEST_GROUP_IDS
    measurement_rows = [
        {
            "schema_version": "vc.benchmark-primary-measurement-row.v1",
            "group_id": group_id,
            "seed": seed,
            "candidate": candidate,
            "baseline": baseline,
            "difference": row_difference,
        }
        for group_id in group_ids
        for seed in sorted(protocol.seeds)
    ]
    group_differences = [
        {
            "schema_version": "vc.benchmark-group-metric-value.v1",
            "group_id": group_id,
            "value": _mean(item["difference"] for item in measurement_rows if item["group_id"] == group_id),
        }
        for group_id in group_ids
    ]
    seed_results = [
        {
            "schema_version": "vc.benchmark-seed-result.v1",
            "seed": seed,
            "candidate": _mean(item["candidate"] for item in measurement_rows if item["seed"] == seed),
            "baseline": _mean(item["baseline"] for item in measurement_rows if item["seed"] == seed),
            "difference": _mean(item["difference"] for item in measurement_rows if item["seed"] == seed),
        }
        for seed in protocol.seeds
    ]
    candidate = _mean(item["candidate"] for item in measurement_rows)
    baseline = _mean(item["baseline"] for item in measurement_rows)
    difference = _mean(item["difference"] for item in measurement_rows)
    low = high = group_differences[0]["value"]
    external = partition == "external"
    raw = {
        "schema_version": "vc.benchmark-primary-result.v1",
        "evaluation_partition": partition,
        "dataset_fingerprint": (
            protocol.external_policy.dataset_fingerprint if external else protocol.dataset.dataset_fingerprint
        ),
        "split_fingerprint": protocol.split.split_fingerprint,
        "group_set_fingerprint": (
            protocol.split.external_group_set_fingerprint if external else protocol.split.test_group_set_fingerprint
        ),
        "candidate_model_fingerprint": run.candidate_model_fingerprint,
        "baseline_fingerprint": protocol.baseline.baseline_fingerprint,
        "metric_name": protocol.primary_metric.name,
        "runtime_receipt_fingerprint": run.runtime_receipt_fingerprint,
        "candidate": candidate,
        "baseline": baseline,
        "difference": difference,
        "paired_ci": {
            "schema_version": "vc.benchmark-paired-ci.v1",
            "low": low,
            "high": high,
            "method": protocol.confidence_interval.method,
            "rng": protocol.confidence_interval.rng,
            "quantile_method": protocol.confidence_interval.quantile_method,
            "group_unit": protocol.confidence_interval.group_unit,
            "confidence_level": protocol.confidence_interval.confidence_level,
            "replicates": protocol.confidence_interval.replicates,
            "seed": protocol.confidence_interval.seed,
            "group_count": len(group_ids),
            "group_differences": group_differences,
            "group_differences_sha256": _canonical_fp(group_differences),
        },
        "measurement_rows": measurement_rows,
        "seed_results": seed_results,
    }
    return _bind(raw, "measurement_receipt_fingerprint")


def _rebind_primary_from_rows(raw: dict) -> dict:
    rows = raw["measurement_rows"]
    group_ids = sorted({item["group_id"] for item in rows})
    group_differences = [
        {
            "schema_version": "vc.benchmark-group-metric-value.v1",
            "group_id": group_id,
            "value": _mean(item["difference"] for item in rows if item["group_id"] == group_id),
        }
        for group_id in group_ids
    ]
    raw["paired_ci"]["group_differences"] = group_differences
    raw["paired_ci"]["group_differences_sha256"] = _canonical_fp(group_differences)
    bounds = paired_bootstrap_ci([item["value"] for item in group_differences])
    raw["paired_ci"].update(low=bounds["low"], high=bounds["high"])
    for summary in raw["seed_results"]:
        seed_rows = [item for item in rows if item["seed"] == summary["seed"]]
        summary.update(
            candidate=_mean(item["candidate"] for item in seed_rows),
            baseline=_mean(item["baseline"] for item in seed_rows),
            difference=_mean(item["difference"] for item in seed_rows),
        )
    raw.update(
        candidate=_mean(item["candidate"] for item in rows),
        baseline=_mean(item["baseline"] for item in rows),
        difference=_mean(item["difference"] for item in rows),
    )
    return _bind(raw, "measurement_receipt_fingerprint")


def _result_raw(
    protocol: BenchmarkProtocolV1,
    run: BenchmarkRunV1,
    *,
    primary_passing: bool = True,
    external: bool = True,
    calibration_error: float | None = 0.05,
) -> dict:
    audit = audit_group_leakage(
        _group_rows(),
        split_fingerprint=protocol.split.split_fingerprint,
        dataset_fingerprints=(
            protocol.dataset.dataset_fingerprint,
            protocol.external_policy.dataset_fingerprint,
        ),
    ).to_dict()
    validation_rows = [
        {
            "schema_version": "vc.benchmark-reliability-row.v1",
            "partition": "validation",
            "unit_id": "validation-1",
            "reliability_score": 0.9,
            "candidate_loss": 0.2,
            "baseline_loss": 0.4,
        },
        {
            "schema_version": "vc.benchmark-reliability-row.v1",
            "partition": "validation",
            "unit_id": "validation-2",
            "reliability_score": 0.5,
            "candidate_loss": 0.8,
            "baseline_loss": 0.5,
        },
    ]
    threshold_receipt = select_validation_threshold(
        validation_rows,
        policy=protocol.threshold_policy,
    ).to_dict()
    selective_rows = [
        {
            "schema_version": "vc.benchmark-reliability-row.v1",
            "partition": "test",
            "unit_id": "test-1",
            "reliability_score": 0.95,
            "candidate_loss": 0.1,
            "baseline_loss": 0.2,
        },
        {
            "schema_version": "vc.benchmark-reliability-row.v1",
            "partition": "test",
            "unit_id": "test-2",
            "reliability_score": 0.92,
            "candidate_loss": 0.1,
            "baseline_loss": 0.2,
        },
        {
            "schema_version": "vc.benchmark-reliability-row.v1",
            "partition": "test",
            "unit_id": "test-3",
            "reliability_score": 0.4,
            "candidate_loss": 0.5,
            "baseline_loss": 0.4,
        },
        {
            "schema_version": "vc.benchmark-reliability-row.v1",
            "partition": "test",
            "unit_id": "test-4",
            "reliability_score": 0.3,
            "candidate_loss": 0.5,
            "baseline_loss": 0.4,
        },
    ]
    selective_fingerprint_payload = [
        {
            "partition": item["partition"],
            "unit_id": item["unit_id"],
            "reliability_score": item["reliability_score"],
            "candidate_loss": item["candidate_loss"],
            "baseline_loss": item["baseline_loss"],
        }
        for item in selective_rows
    ]
    observed_bins = (
        [
            {
                "schema_version": "vc.benchmark-calibration-bin.v1",
                "index": 5,
                "count": 2,
                "mean_confidence": 0.6,
                "empirical_accuracy": 0.6 - calibration_error,
            },
            {
                "schema_version": "vc.benchmark-calibration-bin.v1",
                "index": 7,
                "count": 2,
                "mean_confidence": 0.8,
                "empirical_accuracy": 0.8 - calibration_error,
            },
        ]
        if calibration_error is not None
        else []
    )
    calibration_value = (
        math.fsum(item["count"] * abs(item["empirical_accuracy"] - item["mean_confidence"]) for item in observed_bins)
        / math.fsum(item["count"] for item in observed_bins)
        if observed_bins
        else None
    )
    calibration = {
        "schema_version": "vc.benchmark-scalar-capability.v1",
        "metric_name": protocol.calibration_policy.metric_name,
        "method": protocol.calibration_policy.method,
        "configured_bins": protocol.calibration_policy.bins,
        "evaluation_partition": "test",
        "dataset_fingerprint": protocol.dataset.dataset_fingerprint,
        "split_fingerprint": protocol.split.split_fingerprint,
        "group_set_fingerprint": protocol.split.test_group_set_fingerprint,
        "candidate_model_fingerprint": run.candidate_model_fingerprint,
        "runtime_receipt_fingerprint": run.runtime_receipt_fingerprint,
        "available": calibration_error is not None,
        "value": calibration_value,
        "reason": None if calibration_error is not None else "calibration_unavailable",
        "observed_bins": observed_bins,
    }
    _bind(calibration, "result_fingerprint")
    ood_results = []
    for item in protocol.ood_policy:
        ood = {
            "schema_version": "vc.benchmark-ood-result.v1",
            "axis": item.axis,
            "metric_name": item.metric_name,
            "direction": item.direction,
            "evaluation_partition": "test",
            "dataset_fingerprint": protocol.dataset.dataset_fingerprint,
            "split_fingerprint": protocol.split.split_fingerprint,
            "group_set_fingerprint": protocol.split.test_group_set_fingerprint,
            "candidate_model_fingerprint": run.candidate_model_fingerprint,
            "runtime_receipt_fingerprint": run.runtime_receipt_fingerprint,
            "available": True,
            "value": 0.2,
            "reason": None,
            "group_values": [
                {
                    "schema_version": "vc.benchmark-group-metric-value.v1",
                    "group_id": group_id,
                    "value": 0.2,
                }
                for group_id in protocol.split.test_group_ids
            ],
        }
        ood_results.append(_bind(ood, "result_fingerprint"))
    external_result = None
    if external:
        external_result = {
            "schema_version": "vc.benchmark-external-result.v1",
            "dataset_fingerprint": protocol.external_policy.dataset_fingerprint,
            "platform_fingerprint": protocol.external_policy.platform_fingerprint,
            "scope_fingerprint": protocol.external_policy.scope_fingerprint,
            "independent_dataset": True,
            "independent_platform": True,
            "adaptation_steps": 0,
            "leakage_audit": audit,
            "primary": _primary(
                protocol,
                run,
                partition="external",
                passing=primary_passing,
            ),
        }
        _bind(external_result, "evaluation_receipt_fingerprint")
    return {
        "schema_version": "vc.benchmark-result.v1",
        "result_id": (
            f"p21a-synthetic-result-{'primary-pass' if primary_passing else 'primary-fail'}-"
            f"{'external' if external else 'internal'}-"
            f"{'calibrated' if calibration_error is not None else 'uncalibrated'}"
        ),
        "protocol_fingerprint": protocol.fingerprint(),
        "run_fingerprint": run.fingerprint(),
        "candidate_model_fingerprint": run.candidate_model_fingerprint,
        "status": "completed",
        "runtime_receipt_fingerprint": run.runtime_receipt_fingerprint,
        "leakage_audit": audit,
        "threshold_receipt": threshold_receipt,
        "primary": _primary(protocol, run, partition="test", passing=primary_passing),
        "profile": {
            "schema_version": "vc.benchmark-capability-profile.v1",
            "threshold_receipt_fingerprint": ThresholdReceiptV1.from_dict(threshold_receipt).fingerprint(),
            "selective_evaluation_partition": "test",
            "dataset_fingerprint": protocol.dataset.dataset_fingerprint,
            "split_fingerprint": protocol.split.split_fingerprint,
            "group_set_fingerprint": protocol.split.test_group_set_fingerprint,
            "candidate_model_fingerprint": run.candidate_model_fingerprint,
            "runtime_receipt_fingerprint": run.runtime_receipt_fingerprint,
            "selected_threshold": threshold_receipt["threshold"],
            "selective_rows": selective_rows,
            "selective_rows_fingerprint": _canonical_fp(
                sorted(selective_fingerprint_payload, key=lambda item: item["unit_id"])
            ),
            "calibration_error": calibration,
            "coverage": 0.5,
            "selective_risk": 0.1,
            "wrong_accept_rate": 0.0,
            "unnecessary_abstain_rate": 0.0,
            "ood_results": ood_results,
            "composite_score": None,
        },
        "external": external_result,
        "tuning_after_test_external": False,
        "failure_reason_codes": [],
    }


def _result(protocol: BenchmarkProtocolV1, run: BenchmarkRunV1, **updates) -> BenchmarkResultV1:
    return BenchmarkResultV1.from_dict(_result_raw(protocol, run, **updates))


def _derive(
    protocol: BenchmarkProtocolV1,
    run: BenchmarkRunV1,
    result: BenchmarkResultV1,
):
    return derive_evidence(
        protocol,
        run,
        result,
        trusted_p21b_execution_fingerprint=(
            compute_p21b_execution_fingerprint(run, result) if run.evidence_class == "authorized_candidate" else None
        ),
    )


def _bundle(
    protocol: BenchmarkProtocolV1,
    run: BenchmarkRunV1,
    result: BenchmarkResultV1,
) -> BenchmarkEvidenceBundleV1:
    return BenchmarkEvidenceBundleV1.from_components(
        protocol,
        run,
        result,
    )


def test_protocol_is_strict_frozen_and_contains_no_candidate_result():
    protocol = _protocol()
    assert protocol.candidate_result_observed is False
    assert protocol.frozen is True
    assert protocol.composite_score is None
    assert protocol.fingerprint() == _protocol().fingerprint()

    with pytest.raises(ValidationError):
        protocol.protocol_id = "changed"

    for field, value in (
        ("candidate_result_observed", True),
        ("frozen", False),
        ("composite_score", 1.0),
    ):
        raw = _protocol_raw()
        raw[field] = value
        with pytest.raises(ValueError):
            BenchmarkProtocolV1.from_dict(raw)

    raw = _protocol_raw()
    raw["unknown"] = "rejected"
    with pytest.raises(ValueError):
        BenchmarkProtocolV1.from_dict(raw)


def test_protocol_rejects_random_split_nonvalidation_threshold_and_adaptation():
    raw = _protocol_raw()
    raw["split"]["random_split"] = True
    with pytest.raises(ValueError):
        BenchmarkProtocolV1.from_dict(raw)

    raw = _protocol_raw()
    raw["threshold_policy"]["selection_partition"] = "test"
    with pytest.raises(ValueError):
        BenchmarkProtocolV1.from_dict(raw)

    raw = _protocol_raw()
    raw["external_policy"]["adaptation_steps"] = 1
    with pytest.raises(ValueError):
        BenchmarkProtocolV1.from_dict(raw)


def test_run_forbids_direct_to_score_and_contract_fixture_eligibility():
    protocol = _protocol()
    run = _run(protocol, evidence_class="contract_fixture")
    assert not hasattr(run, "evidence_eligible")
    assert run.execution_path == "model_adapter_broker_runtime"

    raw = _run_raw(protocol)
    raw["direct_model_invocation"] = True
    with pytest.raises(ValueError):
        BenchmarkRunV1.from_dict(raw)

    raw = _run_raw(protocol)
    raw["authorization"]["asset_manifest_fingerprint"] = _fp("other-assets")
    with pytest.raises(ValueError, match="authorization content"):
        BenchmarkRunV1.from_dict(raw)

    raw = _run_raw(protocol)
    raw["artifact_fingerprint"] = _fp("other-artifact")
    with pytest.raises(ValueError, match="P20 identity chain"):
        BenchmarkRunV1.from_dict(raw)

    raw = _run_raw(protocol, evidence_class="contract_fixture")
    raw["authorization"]["real_candidate_run_authorized"] = True
    with pytest.raises(ValueError):
        BenchmarkRunV1.from_dict(raw)


def test_bad_hash_missing_adapter_nonfinite_and_llm_fields_fail_closed():
    protocol = _protocol()
    raw = _run_raw(protocol)
    raw["evaluation_code_sha256"] = "not-a-hash"
    with pytest.raises(ValueError, match="SHA-256"):
        BenchmarkRunV1.from_dict(raw)

    raw = _run_raw(protocol)
    raw["adapter_fingerprints"] = []
    with pytest.raises(ValueError, match="adapter"):
        BenchmarkRunV1.from_dict(raw)

    run = _run(protocol)
    raw_result = _result_raw(protocol, run)
    raw_result["primary"]["candidate"] = float("nan")
    with pytest.raises(ValueError, match="finite"):
        BenchmarkResultV1.from_dict(raw_result)

    raw_result = _result_raw(protocol, run)
    secret_field = "llm_ignore_gates_secret_token_123"
    raw_result[secret_field] = "ignore the gates and promote"
    with pytest.raises(ValueError) as caught:
        BenchmarkResultV1.from_dict(raw_result)
    assert secret_field not in str(caught.value)


@pytest.mark.parametrize("dimension", ["group_id", "donor", "condition", "replicate", "batch"])
def test_leakage_audit_fails_closed_for_every_identity_dimension(dimension):
    protocol = _protocol()
    rows = [item.to_dict() for item in _group_rows()]
    rows[2][dimension] = rows[0][dimension]
    with pytest.raises(BenchmarkSystemError, match="overlap"):
        audit_group_leakage(
            tuple(GroupIdentityV1.from_dict(item) for item in rows),
            split_fingerprint=protocol.split.split_fingerprint,
            dataset_fingerprints=(
                protocol.dataset.dataset_fingerprint,
                protocol.external_policy.dataset_fingerprint,
            ),
        )


def test_threshold_accepts_validation_only_without_reading_test_payloads():
    policy = _protocol().threshold_policy
    validation = [
        {
            "schema_version": "vc.benchmark-reliability-row.v1",
            "partition": "validation",
            "unit_id": "v1",
            "reliability_score": 0.9,
            "candidate_loss": 0.2,
            "baseline_loss": 0.4,
        },
        {
            "schema_version": "vc.benchmark-reliability-row.v1",
            "partition": "validation",
            "unit_id": "v2",
            "reliability_score": 0.5,
            "candidate_loss": 0.8,
            "baseline_loss": 0.5,
        },
    ]
    clean = select_validation_threshold(validation, policy=policy)
    assert clean.selection_partition == "validation"

    class PartitionOnlyPoison(dict):
        def get(self, key, default=None):
            if key != "partition":
                raise AssertionError("test payload was inspected")
            return "test"

    with pytest.raises(BenchmarkSystemError, match="only validation"):
        select_validation_threshold(
            [*validation, PartitionOnlyPoison()],
            policy=policy,
        )

    loose = dict(validation[0], injected="secret")
    with pytest.raises(ValueError):
        select_validation_threshold([loose], policy=policy)

    with pytest.raises(BenchmarkSystemError, match="canonical"):
        select_validation_threshold(list(reversed(validation)), policy=policy)


def test_gate_hierarchy_accepts_lower_and_higher_direction_without_composite_score():
    for direction in ("lower_is_better", "higher_is_better"):
        protocol = _protocol(direction=direction)
        run = _run(protocol)
        result = _result(protocol, run)
        evidence = _derive(protocol, run, result)
        assert evidence.validation_evidence.benchmark_passed is True
        assert evidence.validation_evidence.scientifically_validated is True
        assert evidence.validation_evidence.promotion_eligible is True
        assert evidence.evidence_grade == "promotion_eligible"
        assert not hasattr(evidence, "production_promoted")

        injected = evidence.to_dict()
        injected["production_promoted"] = True
        with pytest.raises(ValueError):
            type(evidence).from_dict(injected)


def test_authorization_trust_is_out_of_band_and_untrusted_bundles_stay_negative():
    protocol = _protocol()
    run = _run(protocol)
    result = _result(protocol, run)

    unverified = derive_evidence(protocol, run, result)
    assert unverified.validation_evidence.benchmark_passed is False
    assert unverified.validation_evidence.scientifically_validated is False
    assert unverified.validation_evidence.promotion_eligible is False
    assert "p21b_execution_not_verified" in unverified.reason_codes
    with pytest.raises(BenchmarkSystemError, match="trusted P21B execution"):
        derive_evidence(
            protocol,
            run,
            result,
            trusted_p21b_execution_fingerprint=_fp("wrong-execution"),
        )

    verified = _derive(protocol, run, result)
    bundle = _bundle(protocol, run, result)
    assert bundle.evidence == unverified
    trusted_execution = compute_p21b_execution_fingerprint(run, result)
    assert (
        bundle.derive_with_p21b_execution(
            trusted_p21b_execution_fingerprint=trusted_execution,
        )
        == verified
    )
    raw = bundle.to_dict()
    assert "trusted_p21b_execution_fingerprint" not in raw

    raw["evidence"] = verified.to_dict()
    with pytest.raises(ValueError, match="reproducible"):
        BenchmarkEvidenceBundleV1.from_dict(raw)
    raw = bundle.to_dict()
    raw["trusted_p21b_execution_fingerprint"] = trusted_execution
    with pytest.raises(ValueError):
        BenchmarkEvidenceBundleV1.from_dict(raw)

    negative = _result(protocol, run, primary_passing=False)
    with pytest.raises(BenchmarkSystemError, match="trusted P21B execution"):
        derive_evidence(
            protocol,
            run,
            result,
            trusted_p21b_execution_fingerprint=compute_p21b_execution_fingerprint(run, negative),
        )

    replayed_raw = _run_raw(protocol)
    replayed_raw["evaluation_code_sha256"] = _fp("changed-evaluation-code")
    replayed_raw["runtime_receipt_fingerprint"] = _fp("changed-runtime")
    _rebind_run_authorization(replayed_raw)
    replayed = BenchmarkRunV1.from_dict(replayed_raw)
    replayed_result = _result(protocol, replayed)
    with pytest.raises(BenchmarkSystemError, match="trusted P21B execution"):
        derive_evidence(
            protocol,
            replayed,
            replayed_result,
            trusted_p21b_execution_fingerprint=trusted_execution,
        )


def test_internal_pass_does_not_claim_science_or_promotion_without_external():
    protocol = _protocol()
    run = _run(protocol)
    evidence = _derive(protocol, run, _result(protocol, run, external=False))
    assert evidence.validation_evidence.benchmark_passed is True
    assert evidence.validation_evidence.scientifically_validated is False
    assert evidence.validation_evidence.promotion_eligible is False
    assert "external_result_missing" in evidence.reason_codes


def test_equality_and_ci_boundary_preserve_negative_evidence():
    protocol = _protocol()
    run = _run(protocol)
    result = _result(protocol, run, primary_passing=False)
    evidence = _derive(protocol, run, result)
    assert evidence.validation_evidence.benchmark_passed is False
    assert evidence.validation_evidence.scientifically_validated is False
    assert evidence.validation_evidence.promotion_eligible is False
    assert "primary_not_strictly_better" in evidence.reason_codes
    assert "primary_ci_does_not_support_improvement" in evidence.reason_codes


def test_capability_failure_blocks_only_promotion_after_external_validation():
    protocol = _protocol()
    run = _run(protocol)
    result = _result(protocol, run, calibration_error=None)
    evidence = _derive(protocol, run, result)
    assert evidence.validation_evidence.benchmark_passed is True
    assert evidence.validation_evidence.scientifically_validated is True
    assert evidence.validation_evidence.promotion_eligible is False
    assert "calibration_unavailable" in evidence.reason_codes


def test_ood_unavailable_blocks_only_promotion_and_is_not_silently_filled():
    protocol = _protocol()
    run = _run(protocol)
    raw = _result_raw(protocol, run)
    raw["profile"]["ood_results"][0].update(
        available=False,
        value=None,
        reason="perturbation_ood_unavailable",
        group_values=[],
    )
    _bind(raw["profile"]["ood_results"][0], "result_fingerprint")
    evidence = _derive(protocol, run, BenchmarkResultV1.from_dict(raw))
    assert evidence.validation_evidence.benchmark_passed is True
    assert evidence.validation_evidence.scientifically_validated is True
    assert evidence.validation_evidence.promotion_eligible is False
    assert "perturbation_ood_unavailable" in evidence.reason_codes


def test_wrong_external_scope_and_adaptation_cannot_validate_science():
    protocol = _protocol()
    run = _run(protocol)
    raw = _result_raw(protocol, run)
    raw["external"]["scope_fingerprint"] = _fp("wrong-scope")
    raw["external"]["adaptation_steps"] = 1
    _bind(raw["external"], "evaluation_receipt_fingerprint")
    evidence = _derive(protocol, run, BenchmarkResultV1.from_dict(raw))
    assert evidence.validation_evidence.benchmark_passed is True
    assert evidence.validation_evidence.scientifically_validated is False
    assert evidence.validation_evidence.promotion_eligible is False
    assert "external_scope_mismatch" in evidence.reason_codes
    assert "external_adaptation_not_zero" in evidence.reason_codes


def test_compatibility_state_is_separate_from_benchmark_and_science():
    protocol = _protocol()
    raw = _run_raw(protocol)
    raw["compatibility_passed"] = False
    _rebind_run_authorization(raw)
    run = BenchmarkRunV1.from_dict(raw)
    evidence = _derive(protocol, run, _result(protocol, run))
    assert evidence.validation_evidence.benchmark_passed is False
    assert evidence.validation_evidence.scientifically_validated is False
    assert evidence.validation_evidence.promotion_eligible is False
    assert "compatibility_failed" in evidence.reason_codes


def test_threshold_receipt_is_recomputed_and_bound_to_the_frozen_policy():
    protocol = _protocol()
    run = _run(protocol)
    raw = _result_raw(protocol, run)
    raw["threshold_receipt"]["threshold"] = -999.0
    with pytest.raises(ValueError, match="does not reproduce"):
        BenchmarkResultV1.from_dict(raw)

    raw = _result_raw(protocol, run)
    raw["threshold_receipt"]["policy_fingerprint"] = _fp("other-policy")
    raw["profile"]["threshold_receipt_fingerprint"] = ThresholdReceiptV1.from_dict(
        raw["threshold_receipt"]
    ).fingerprint()
    with pytest.raises(BenchmarkSystemError, match="threshold selection"):
        _derive(protocol, run, BenchmarkResultV1.from_dict(raw))

    raw = _result_raw(protocol, run)
    raw["threshold_receipt"]["selection_rows"][0]["candidate_loss"] = 0.3
    with pytest.raises(ValueError, match="validation rows"):
        BenchmarkResultV1.from_dict(raw)


def test_capability_profile_must_bind_the_exact_threshold_receipt():
    protocol = _protocol()
    run = _run(protocol)
    raw = _result_raw(protocol, run)
    raw["profile"]["threshold_receipt_fingerprint"] = _fp("different-threshold-receipt")
    with pytest.raises(ValueError, match="frozen threshold receipt"):
        BenchmarkResultV1.from_dict(raw)

    raw = _result_raw(protocol, run)
    raw["profile"].update(
        selected_threshold=0.3,
        coverage=1.0,
        selective_risk=0.3,
        wrong_accept_rate=1.0,
        unnecessary_abstain_rate=0.0,
    )
    with pytest.raises(ValueError, match="selected validation threshold"):
        BenchmarkResultV1.from_dict(raw)

    raw = _result_raw(protocol, run)
    raw["profile"]["selective_rows"].reverse()
    with pytest.raises(ValueError, match="canonical unit-ID order"):
        BenchmarkResultV1.from_dict(raw)


def test_calibration_and_ood_receipts_recompute_and_bind_context():
    protocol = _protocol()
    run = _run(protocol)

    raw = _result_raw(protocol, run)
    raw["profile"]["calibration_error"]["value"] = 0.01
    with pytest.raises(ValueError, match="calibration value"):
        BenchmarkResultV1.from_dict(raw)

    raw = _result_raw(protocol, run)
    calibration = raw["profile"]["calibration_error"]
    calibration["dataset_fingerprint"] = _fp("other-calibration-dataset")
    _bind(calibration, "result_fingerprint")
    with pytest.raises(BenchmarkSystemError, match="calibration result"):
        _derive(protocol, run, BenchmarkResultV1.from_dict(raw))

    raw = _result_raw(protocol, run)
    raw["profile"]["ood_results"][0]["value"] = 0.1
    with pytest.raises(ValueError, match="biological-group mean"):
        BenchmarkResultV1.from_dict(raw)

    raw = _result_raw(protocol, run)
    ood = raw["profile"]["ood_results"][0]
    ood["metric_name"] = "other_metric"
    _bind(ood, "result_fingerprint")
    with pytest.raises(BenchmarkSystemError, match="OOD result"):
        _derive(protocol, run, BenchmarkResultV1.from_dict(raw))


def test_primary_and_leakage_receipts_reject_stale_or_overlapping_content():
    protocol = _protocol()
    run = _run(protocol)
    raw = _result_raw(protocol, run, primary_passing=False)
    stale_receipt = raw["primary"]["measurement_receipt_fingerprint"]
    raw["primary"] = _primary(protocol, run, partition="test", passing=True)
    raw["primary"]["measurement_receipt_fingerprint"] = stale_receipt
    with pytest.raises(ValueError, match="measurement receipt fingerprint"):
        BenchmarkResultV1.from_dict(raw)

    raw = _result_raw(protocol, run)
    records = raw["leakage_audit"]["records"]
    train = next(item for item in records if item["partition"] == "train")
    test = next(item for item in records if item["partition"] == "test")
    test["donor"] = train["donor"]
    raw["leakage_audit"]["records_fingerprint"] = _canonical_fp(records)
    with pytest.raises(ValueError, match="overlaps benchmark partitions"):
        BenchmarkResultV1.from_dict(raw)


def test_primary_decisions_use_one_canonical_float_recomputation_path():
    protocol = _protocol()
    run = _run(protocol)
    raw = _result_raw(protocol, run)
    primary = raw["primary"]
    for index, row in enumerate(primary["measurement_rows"]):
        row["candidate"] = 0.11 + index * 0.007
        row["baseline"] = 0.91 + (index % 4) * 0.003
        row["difference"] = row["candidate"] - row["baseline"]
    _rebind_primary_from_rows(primary)
    result = BenchmarkResultV1.from_dict(raw)
    assert _derive(protocol, run, result).validation_evidence.benchmark_passed is True

    raw = _result_raw(protocol, run, primary_passing=False)
    primary = raw["primary"]
    tiny_candidate = 1.0 - 5e-13
    tiny_difference = tiny_candidate - 1.0
    primary.update(candidate=tiny_candidate, baseline=1.0, difference=tiny_difference)
    for summary in primary["seed_results"]:
        summary.update(candidate=tiny_candidate, baseline=1.0, difference=tiny_difference)
    primary["paired_ci"].update(low=-5e-16, high=-5e-16)
    _bind(primary, "measurement_receipt_fingerprint")
    with pytest.raises(ValueError, match="paired CI bounds"):
        BenchmarkResultV1.from_dict(raw)


def test_leakage_audit_content_is_bound_to_the_frozen_protocol():
    protocol = _protocol()
    run = _run(protocol)
    raw = _result_raw(protocol, run)
    for audit in (raw["leakage_audit"], raw["external"]["leakage_audit"]):
        target = next(item for item in audit["records"] if item["group_id"] == "test-1")
        target["donor"] = "fresh-nonoverlapping-donor"
        audit["records_fingerprint"] = _canonical_fp(audit["records"])
    _bind(raw["external"], "evaluation_receipt_fingerprint")
    result = BenchmarkResultV1.from_dict(raw)
    with pytest.raises(BenchmarkSystemError, match="leakage audit"):
        _derive(protocol, run, result)


def test_derive_revalidates_frozen_models_after_model_copy_bypass():
    protocol = _protocol()
    valid = _run(protocol)
    bypassed = valid.model_copy(update={"direct_model_invocation": True})
    result = _result(protocol, bypassed)
    with pytest.raises(ValueError):
        _derive(protocol, bypassed, result)


def test_contract_fixture_can_never_become_benchmark_or_scientific_evidence():
    protocol = _protocol()
    run = _run(protocol, evidence_class="contract_fixture")
    evidence = _derive(protocol, run, _result(protocol, run))
    assert evidence.validation_evidence.benchmark_passed is False
    assert evidence.validation_evidence.scientifically_validated is False
    assert evidence.validation_evidence.promotion_eligible is False
    assert "contract_fixture_not_evidence_eligible" in evidence.reason_codes


def test_cross_binding_and_seed_drift_fail_closed():
    protocol = _protocol()
    run = _run(protocol)
    result = _result(protocol, run)

    other = _protocol()
    other = other.model_copy(update={"protocol_id": "other"})
    with pytest.raises(BenchmarkSystemError, match="protocol"):
        _derive(other, run, result)

    raw = _run_raw(protocol)
    raw["seeds"] = [11, 23]
    _rebind_run_authorization(raw)
    drifted = BenchmarkRunV1.from_dict(raw)
    drifted_result = _result(protocol, drifted)
    with pytest.raises(BenchmarkSystemError, match="seeds"):
        _derive(protocol, drifted, drifted_result)

    raw_result = _result_raw(protocol, run)
    primary = raw_result["primary"]
    for item in primary["measurement_rows"]:
        item["group_id"] = f"other-{item['group_id']}"
    for item in primary["paired_ci"]["group_differences"]:
        item["group_id"] = f"other-{item['group_id']}"
    primary["group_set_fingerprint"] = _canonical_fp(sorted({item["group_id"] for item in primary["measurement_rows"]}))
    primary["paired_ci"]["group_differences_sha256"] = _canonical_fp(primary["paired_ci"]["group_differences"])
    _bind(primary, "measurement_receipt_fingerprint")
    with pytest.raises(BenchmarkSystemError, match="measurement binding"):
        _derive(protocol, run, BenchmarkResultV1.from_dict(raw_result))

    raw_result = _result_raw(protocol, run)
    raw_result["primary"]["paired_ci"]["group_count"] = 1
    with pytest.raises(ValueError, match="group_count"):
        BenchmarkResultV1.from_dict(raw_result)


def test_evidence_bundle_recomputes_summary_and_rejects_forgery():
    protocol = _protocol()
    run = _run(protocol)
    result = _result(protocol, run, primary_passing=False)
    bundle = _bundle(protocol, run, result)
    raw = bundle.to_dict()
    raw["evidence"]["reason_codes"].append("self_asserted_without_bundle")
    with pytest.raises(ValueError, match="reproducible"):
        BenchmarkEvidenceBundleV1.from_dict(raw)


def test_abstained_leakage_failure_is_preserved_as_negative_evidence(tmp_path):
    protocol = _protocol()
    run = _run(protocol)
    raw = _result_raw(protocol, run)
    raw.update(
        result_id="p21a-synthetic-leakage-abstain",
        status="abstained",
        leakage_audit=None,
        threshold_receipt=None,
        primary=None,
        profile=None,
        external=None,
        failure_reason_codes=["leakage_overlap_detected_before_evaluation"],
    )
    result = BenchmarkResultV1.from_dict(raw)
    bundle = _bundle(protocol, run, result)
    assert bundle.evidence.validation_evidence.benchmark_passed is False
    assert bundle.evidence.validation_evidence.scientifically_validated is False
    assert bundle.evidence.validation_evidence.promotion_eligible is False
    assert "leakage_overlap_detected_before_evaluation" in bundle.evidence.reason_codes

    ledger = BenchmarkEvidenceLedger.create((tmp_path / "ledger").resolve())
    stored = ledger.append(bundle)
    assert stored.entry.record == bundle
    assert ledger.verify()[0].entry.record == bundle


def test_append_only_content_addressed_ledger_retains_negative_history(tmp_path):
    protocol = _protocol()
    run = _run(protocol)
    negative_result = _result(protocol, run, primary_passing=False)
    negative = _bundle(protocol, run, negative_result)
    p9 = replay_checked_in_benchmarks(_ROOT)[1]

    ledger = BenchmarkEvidenceLedger.create((tmp_path / "ledger").resolve())
    first = ledger.append(negative)
    first_bytes = first.path.read_bytes()
    second = ledger.append(p9)
    assert first.path.read_bytes() == first_bytes
    assert first.sequence == 1
    assert second.sequence == 2
    assert second.previous_entry_fingerprint == first.entry_fingerprint
    assert tuple(item.record_fingerprint for item in ledger.verify()) == (
        negative.fingerprint(),
        p9.fingerprint(),
    )
    assert ledger.append(negative).entry_fingerprint == first.entry_fingerprint

    positive_result = _result(protocol, run)
    positive = _bundle(protocol, run, positive_result).model_copy(
        update={"evidence": _derive(protocol, run, positive_result)}
    )
    with pytest.raises(BenchmarkSystemError, match="promotion-eligible"):
        ledger.append(positive)
    with pytest.raises(TypeError):
        ledger.append(negative.evidence)
    with pytest.raises(BenchmarkSystemError, match="exact P9"):
        ledger.append(replay_checked_in_benchmarks(_ROOT)[0])
    altered_p9 = p9.model_copy(update={"reason_codes": (*p9.reason_codes, "altered_legacy_reason")})
    with pytest.raises(BenchmarkSystemError, match="exact P9"):
        ledger.append(altered_p9)

    fixture_run = _run(protocol, evidence_class="contract_fixture")
    fixture_bundle = _bundle(
        protocol,
        fixture_run,
        _result(protocol, fixture_run, primary_passing=False),
    )
    with pytest.raises(BenchmarkSystemError, match="contract-only"):
        ledger.append(fixture_bundle)

    second_result = _result(protocol, run, calibration_error=None)
    same_run_negative = _bundle(
        protocol,
        run,
        second_result,
    )
    with pytest.raises(BenchmarkSystemError, match="run"):
        ledger.append(same_run_negative)

    second_run_raw = _run_raw(protocol)
    second_run_raw["run_id"] = "p21a-synthetic-run-v2"
    with pytest.raises(ValueError, match="does not bind run"):
        BenchmarkRunV1.from_dict(second_run_raw)


def test_ledger_is_write_new_and_detects_tampering_and_symlink_roots(tmp_path):
    root = (tmp_path / "ledger").resolve()
    ledger = BenchmarkEvidenceLedger.create(root)
    with pytest.raises(BenchmarkSystemError, match="write-new"):
        BenchmarkEvidenceLedger.create(root)

    protocol = _protocol()
    run = _run(protocol)
    stored = ledger.append(
        _bundle(
            protocol,
            run,
            _result(protocol, run, primary_passing=False),
        )
    )
    stored.path.write_bytes(stored.path.read_bytes() + b" ")
    with pytest.raises(BenchmarkSystemError):
        ledger.verify()

    truncation_ledger = BenchmarkEvidenceLedger.create((tmp_path / "truncation-ledger").resolve())
    truncation_ledger.append(
        _bundle(
            protocol,
            run,
            _result(protocol, run, primary_passing=False),
        )
    )
    tail = truncation_ledger.append(replay_checked_in_benchmarks(_ROOT)[1])
    tail.path.unlink()
    with pytest.raises(BenchmarkSystemError, match="truncation"):
        truncation_ledger.verify()

    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(BenchmarkSystemError, match="symlink"):
        BenchmarkEvidenceLedger.open(link)


def test_ledger_publish_collision_and_partial_failure_never_overwrite(tmp_path, monkeypatch):
    protocol = _protocol()
    run = _run(protocol)
    evidence = _bundle(
        protocol,
        run,
        _result(protocol, run, primary_passing=False),
    )

    collision_ledger = BenchmarkEvidenceLedger.create((tmp_path / "collision").resolve())
    original_link = os.link
    competing = b"competing-entry\n"

    def collide(source, destination, **kwargs):
        (collision_ledger.root / "entries" / destination).write_bytes(competing)
        return original_link(source, destination, **kwargs)

    monkeypatch.setattr(os, "link", collide)
    with pytest.raises(BenchmarkSystemError, match="collision"):
        collision_ledger.append(evidence)
    visible = tuple(path for path in (collision_ledger.root / "entries").iterdir() if not path.name.startswith("."))
    assert len(visible) == 1
    assert visible[0].read_bytes() == competing

    monkeypatch.setattr(os, "link", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("injected")))
    partial_ledger = BenchmarkEvidenceLedger.create((tmp_path / "partial").resolve())
    with pytest.raises(BenchmarkSystemError, match="append"):
        partial_ledger.append(evidence)
    assert tuple((partial_ledger.root / "entries").iterdir()) == ()


def test_ledger_holds_layout_and_lock_identities(tmp_path):
    protocol = _protocol()
    run = _run(protocol)
    evidence = _bundle(
        protocol,
        run,
        _result(protocol, run, primary_passing=False),
    )
    root = (tmp_path / "ledger").resolve()
    ledger = BenchmarkEvidenceLedger.create(root)
    original_entries = tmp_path / "original-entries"
    (root / "entries").rename(original_entries)
    (root / "entries").mkdir()
    with pytest.raises(BenchmarkSystemError, match="entries identity"):
        ledger.verify()

    restored = (tmp_path / "lock-ledger").resolve()
    lock_ledger = BenchmarkEvidenceLedger.create(restored)
    original_lock = restored / ".original-lock"
    (restored / ".ledger.lock").rename(original_lock)
    (restored / ".ledger.lock").write_bytes(b"")
    with pytest.raises(BenchmarkSystemError, match="lock identity"):
        lock_ledger.append(evidence)


def test_partial_ledger_initialization_keeps_final_target_absent(tmp_path, monkeypatch):
    root = (tmp_path / "partial-create").resolve()
    original_open = os.open

    def fail_lock(path, flags, mode=0o777, *, dir_fd=None):
        if Path(path).name == ".ledger.lock":
            raise OSError("injected lock creation failure")
        return original_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "open", fail_lock)
    with pytest.raises(BenchmarkSystemError, match="initialize"):
        BenchmarkEvidenceLedger.create(root)
    assert not root.exists()


def test_checked_in_p8_p9_replay_preserves_null_and_negative_states(tmp_path):
    receipts = replay_checked_in_benchmarks(_ROOT)
    assert len(receipts) == 2
    p8, p9 = receipts
    assert p8.receipt_id == "p8-golden-norman-artifact-manifest"
    assert p8.available is None
    assert p8.benchmark_passed is None
    assert p8.scientifically_validated is False
    assert p8.promotion_eligible is None
    assert p9.receipt_id == "p9-external-validation-negative"
    assert p9.available is False
    assert p9.benchmark_passed is False
    assert p9.scientifically_validated is False
    assert p9.promotion_eligible is False
    assert p9.reason_codes[:2] == (
        "primary_not_better_than_baseline",
        "primary_ci_not_below_zero",
    )
    assert all(not Path(item.source_path).is_absolute() for item in receipts)

    copied = tmp_path / "repository"
    for relative in (
        "praxis_virtualcell/tests/fixtures/model_registry_v2/legacy_migration.json",
        "data/golden/norman_2019/artifact-manifest.json",
        "data/benchmarks/p9/external-validation.json",
        "data/benchmarks/p9/ood-manifest.json",
    ):
        source = _ROOT / relative
        target = copied / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    target = copied / "data/benchmarks/p9/external-validation.json"
    target.write_bytes(target.read_bytes().replace(b'"available": false', b'"available": true '))
    with pytest.raises(BenchmarkSystemError, match="identity"):
        replay_checked_in_benchmarks(copied.resolve())
