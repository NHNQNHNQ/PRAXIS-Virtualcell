"""Strict, system-only Phase 21A benchmark contracts.

This module freezes benchmark inputs, binds execution receipts, derives
evidence states, and stores immutable negative records.  It reads only the
small checked-in P8/P9 historical identity/status files for compatibility;
it never reads raw/test labels, external assets, or weights, invokes a model,
scores a candidate, or creates operator policy.
"""

from __future__ import annotations

import ctypes
import errno
import fcntl
import hashlib
import json
import math
import os
import re
import stat
import sys
import tempfile
from collections.abc import Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator

from praxis_virtualcell.benchmarks.ood_validation import (
    OODValidationError,
    load_validation_artifact,
    select_threshold,
    selective_metrics,
)
from praxis_virtualcell.model_zoo.registry_v2 import LegacyMigrationReceipt, ValidationEvidence

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PARTITIONS = ("train", "validation", "test", "external")
_LEAKAGE_DIMENSIONS = ("donor", "condition", "replicate", "batch")
_AUDITED_IDENTITIES = ("group_id", *_LEAKAGE_DIMENSIONS)
_LEDGER_MARKER = ".benchmark-evidence-ledger.v1"
_LEDGER_MARKER_BYTES = b'{"schema_version":"vc.benchmark-evidence-ledger.v1"}\n'
_LEDGER_HEAD = ".ledger.head"
_MAX_CONTRACT_BYTES = 2 * 1024 * 1024
_STAGING_NAME = re.compile(r"^\.staging-[0-9a-f]{32}\.tmp$")
_HEAD_STAGING_NAME = re.compile(r"^\.head-staging-[0-9a-f]{32}\.tmp$")
_LEGACY_FIXTURE = PurePosixPath("praxis_virtualcell/tests/fixtures/model_registry_v2/legacy_migration.json")
_LEGACY_FIXTURE_SIZE = 2197
_LEGACY_FIXTURE_SHA256 = "bfb8ac5c730d1ea5a42e5155b98ffcc12bc884b05ef20aeccdef9a34cb06f4e3"
_P8_PATH = PurePosixPath("data/golden/norman_2019/artifact-manifest.json")
_P8_SIZE = 3864
_P8_SHA256 = "724b701beda574ad344b764de09dafb86648e49c9a327df717212aaf25cc71ac"
_P9_PATH = PurePosixPath("data/benchmarks/p9/external-validation.json")
_P9_SIZE = 10119
_P9_SHA256 = "abd1145c434fd4e48ac9d72e94e8e19d14a5b4011f03d05db4823dd91760da6e"
_P9_MANIFEST_PATH = PurePosixPath("data/benchmarks/p9/ood-manifest.json")
_P9_MANIFEST_SIZE = 5357
_P9_MANIFEST_SHA256 = "6134bd89510f461fbd73d7640fa3c4e30260ed04bf0182c9ebc682dac18933bf"
_P9_RECEIPT_FINGERPRINT = "a03d455b97994c27fb7f0b5e1b2f31d4014993a46d503a8c15826def7f6fab62"


class BenchmarkSystemError(ValueError):
    """A frozen benchmark identity, gate, or ledger check failed closed."""


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
        raise BenchmarkSystemError(f"value is not canonical JSON: {exc}") from exc


def _canonical_fingerprint(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _duplicate_rejecting_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise BenchmarkSystemError(f"duplicate JSON key: {key!r}")
        value[key] = item
    return value


def _reject_nonfinite(value):
    raise BenchmarkSystemError(f"non-finite JSON number is forbidden: {value}")


def _json_object_bytes(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_duplicate_rejecting_object,
            parse_constant=_reject_nonfinite,
        )
    except BenchmarkSystemError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BenchmarkSystemError(f"{label} is not strict UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise BenchmarkSystemError(f"{label} root must be a JSON object")
    return value


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise ValueError(f"{field} must be a non-empty string without surrounding whitespace")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError(f"{field} must be valid UTF-8 text") from exc
    return value


def _texts(value: Any, field: str, *, minimum: int = 1) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{field} must be an array")
    values = tuple(_text(item, field) for item in value)
    if len(values) < minimum:
        raise ValueError(f"{field} must contain at least {minimum} item(s)")
    if len(set(values)) != len(values):
        raise ValueError(f"{field} must not contain duplicates")
    return values


def _fingerprint(value: Any, field: str) -> str:
    value = _text(value, field)
    if not _SHA256.fullmatch(value):
        raise ValueError(f"{field} must be a lowercase SHA-256 fingerprint")
    return value


def _fingerprints(value: Any, field: str, *, minimum: int = 1) -> tuple[str, ...]:
    values = _texts(value, field, minimum=minimum)
    return tuple(_fingerprint(item, field) for item in values)


def _finite(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{field} must be a finite number")
    return result


def _canonical_mean(values: Sequence[float], field: str) -> float:
    values = tuple(values)
    if not values:
        raise ValueError(f"{field} must contain at least one value")
    result = math.fsum(values) / len(values)
    if not math.isfinite(result):
        raise ValueError(f"{field} mean must be finite")
    return result


def _paired_ci_bounds(values: Sequence[float]) -> tuple[float, float]:
    try:
        from praxis_virtualcell.benchmarks.golden_norman import paired_bootstrap_ci

        reproduced = paired_bootstrap_ci(tuple(values))
    except (ImportError, OSError, ValueError) as exc:
        raise ValueError(f"paired CI cannot be reproduced: {exc}") from exc
    return reproduced["low"], reproduced["high"]


def _unit_interval(value: Any, field: str, *, include_zero: bool = True) -> float:
    result = _finite(value, field)
    lower_ok = result >= 0 if include_zero else result > 0
    if not lower_ok or result > 1:
        boundary = "[0, 1]" if include_zero else "(0, 1]"
        raise ValueError(f"{field} must be in {boundary}")
    return result


def _positive_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field} must be a positive integer")
    return value


def _nonnegative_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    return value


class _Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    @classmethod
    def from_dict(cls, value: dict[str, Any]):
        if not isinstance(value, dict):
            raise ValueError(f"{cls.__name__} must be a JSON object")
        try:
            return cls.model_validate(value)
        except ValidationError as exc:
            messages = []
            for error in exc.errors(
                include_url=False,
                include_context=False,
                include_input=False,
            ):
                location = ".".join(
                    str(item)
                    if isinstance(item, int) or (isinstance(item, str) and item in cls.model_fields)
                    else "<field>"
                    for item in error["loc"]
                )
                messages.append(f"{location}: {error['msg']}")
            raise ValueError(f"{cls.__name__} validation failed: {'; '.join(messages)}") from None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def fingerprint(self) -> str:
        return _canonical_fingerprint(self.to_dict())


class BenchmarkScopeV1(_Contract):
    schema_version: Literal["vc.benchmark-scope.v1"]
    organism: str
    cell_type: str
    intervention: str
    endpoint: str

    @field_validator("organism", "cell_type", "intervention", "endpoint", mode="before")
    @classmethod
    def _valid_text(cls, value, info):
        return _text(value, info.field_name)


class DatasetBindingV1(_Contract):
    schema_version: Literal["vc.benchmark-dataset-binding.v1"]
    dataset_fingerprint: str
    platform_fingerprint: str

    @field_validator("dataset_fingerprint", "platform_fingerprint", mode="before")
    @classmethod
    def _valid_fingerprint(cls, value, info):
        return _fingerprint(value, info.field_name)


class BenchmarkSplitV1(_Contract):
    schema_version: Literal["vc.benchmark-split.v1"]
    split_fingerprint: str
    partitions: tuple[str, ...]
    group_unit: str
    leakage_dimensions: tuple[str, ...]
    leakage_record_count: int
    leakage_records_fingerprint: str
    fit_partitions: tuple[str, ...]
    tuning_partitions: tuple[str, ...]
    threshold_selection_partition: Literal["validation"]
    evaluation_partitions: tuple[str, ...]
    validation_group_ids: tuple[str, ...]
    validation_group_set_fingerprint: str
    validation_group_count: int
    test_group_ids: tuple[str, ...]
    test_group_set_fingerprint: str
    test_group_count: int
    external_group_ids: tuple[str, ...]
    external_group_set_fingerprint: str
    external_group_count: int
    random_split: Literal[False]

    @field_validator(
        "split_fingerprint",
        "leakage_records_fingerprint",
        mode="before",
    )
    @classmethod
    def _valid_fingerprint(cls, value, info):
        return _fingerprint(value, info.field_name)

    @field_validator(
        "validation_group_set_fingerprint",
        "test_group_set_fingerprint",
        "external_group_set_fingerprint",
        mode="before",
    )
    @classmethod
    def _valid_group_set_fingerprint(cls, value, info):
        return _fingerprint(value, info.field_name)

    @field_validator(
        "validation_group_count",
        "test_group_count",
        "external_group_count",
        "leakage_record_count",
        mode="before",
    )
    @classmethod
    def _valid_group_count(cls, value, info):
        return _positive_int(value, info.field_name)

    @field_validator("group_unit", mode="before")
    @classmethod
    def _valid_group_unit(cls, value):
        return _text(value, "group_unit")

    @field_validator(
        "partitions",
        "leakage_dimensions",
        "fit_partitions",
        "tuning_partitions",
        "evaluation_partitions",
        "validation_group_ids",
        "test_group_ids",
        "external_group_ids",
        mode="before",
    )
    @classmethod
    def _valid_arrays(cls, value, info):
        return _texts(value, info.field_name)

    @model_validator(mode="after")
    def _frozen_partition_policy(self):
        expected = {
            "partitions": _PARTITIONS,
            "leakage_dimensions": _LEAKAGE_DIMENSIONS,
            "fit_partitions": ("train",),
            "tuning_partitions": ("train", "validation"),
            "evaluation_partitions": ("test", "external"),
        }
        for field, value in expected.items():
            if getattr(self, field) != value:
                raise ValueError(f"{field} must be exactly {list(value)}")
        for label in ("validation", "test", "external"):
            group_ids = getattr(self, f"{label}_group_ids")
            if len(group_ids) != getattr(self, f"{label}_group_count"):
                raise ValueError(f"{label} group count does not match group IDs")
            if _canonical_fingerprint(sorted(group_ids)) != getattr(
                self,
                f"{label}_group_set_fingerprint",
            ):
                raise ValueError(f"{label} group-set fingerprint does not bind group IDs")
        return self


class BenchmarkBaselineV1(_Contract):
    schema_version: Literal["vc.benchmark-baseline.v1"]
    baseline_id: str
    baseline_fingerprint: str
    kind: Literal["no_change", "global_mean", "declared_simple"]
    fit_partition: Literal["train"]
    simple: Literal[True]

    @field_validator("baseline_id", mode="before")
    @classmethod
    def _valid_id(cls, value):
        return _text(value, "baseline_id")

    @field_validator("baseline_fingerprint", mode="before")
    @classmethod
    def _valid_fingerprint(cls, value):
        return _fingerprint(value, "baseline_fingerprint")


class BenchmarkMetricV1(_Contract):
    schema_version: Literal["vc.benchmark-metric.v1"]
    name: str
    direction: Literal["lower_is_better", "higher_is_better"]
    aggregation: Literal["biological_group_macro"]
    difference: Literal["candidate_minus_baseline"]

    @field_validator("name", mode="before")
    @classmethod
    def _valid_name(cls, value):
        return _text(value, "metric.name")


class PairedCIPolicyV1(_Contract):
    schema_version: Literal["vc.benchmark-ci-policy.v1"]
    method: Literal["paired_group_percentile"]
    rng: Literal["numpy.PCG64"]
    quantile_method: Literal["linear"]
    group_unit: str
    confidence_level: float
    replicates: int
    seed: int

    @field_validator("group_unit", mode="before")
    @classmethod
    def _valid_group_unit(cls, value):
        return _text(value, "ci.group_unit")

    @field_validator("confidence_level", mode="before")
    @classmethod
    def _valid_confidence(cls, value):
        result = _unit_interval(value, "confidence_level", include_zero=False)
        if result >= 1:
            raise ValueError("confidence_level must be below 1")
        return result

    @field_validator("replicates", mode="before")
    @classmethod
    def _valid_replicates(cls, value):
        value = _positive_int(value, "replicates")
        if value < 100:
            raise ValueError("replicates must be at least 100")
        return value

    @field_validator("seed", mode="before")
    @classmethod
    def _valid_seed(cls, value):
        return _nonnegative_int(value, "seed")

    @model_validator(mode="after")
    def _frozen_statistics(self):
        if self.confidence_level != 0.95 or self.replicates != 2000 or self.seed != 0:
            raise ValueError("CI policy must use the frozen P8/P9 0.95/2000/seed-0 settings")
        return self


class ThresholdPolicyV1(_Contract):
    schema_version: Literal["vc.benchmark-threshold-policy.v1"]
    selection_partition: Literal["validation"]
    reliability_name: str
    minimum_coverage: float
    objective: Literal["minimize_candidate_risk"]
    tie_break: Literal["higher_coverage_then_higher_threshold"]

    @field_validator("reliability_name", mode="before")
    @classmethod
    def _valid_name(cls, value):
        return _text(value, "reliability_name")

    @field_validator("minimum_coverage", mode="before")
    @classmethod
    def _valid_coverage(cls, value):
        return _unit_interval(value, "minimum_coverage", include_zero=False)


class OODGateV1(_Contract):
    schema_version: Literal["vc.benchmark-ood-gate.v1"]
    axis: str
    metric_name: str
    direction: Literal["lower_is_better", "higher_is_better"]
    threshold: float

    @field_validator("axis", "metric_name", mode="before")
    @classmethod
    def _valid_text(cls, value, info):
        return _text(value, info.field_name)

    @field_validator("threshold", mode="before")
    @classmethod
    def _valid_threshold(cls, value):
        return _finite(value, "ood.threshold")


class CalibrationPolicyV1(_Contract):
    schema_version: Literal["vc.benchmark-calibration-policy.v1"]
    metric_name: Literal["expected_calibration_error"]
    method: Literal["equal_width"]
    bins: int
    evaluation_partition: Literal["test"]

    @field_validator("bins", mode="before")
    @classmethod
    def _valid_bins(cls, value):
        value = _positive_int(value, "calibration bins")
        if value < 2:
            raise ValueError("calibration bins must be at least two")
        return value


class ExternalPolicyV1(_Contract):
    schema_version: Literal["vc.benchmark-external-policy.v1"]
    required: Literal[True]
    dataset_fingerprint: str
    platform_fingerprint: str
    scope_fingerprint: str
    independent_dataset: Literal[True]
    independent_platform: Literal[True]
    adaptation_steps: Literal[0]

    @field_validator("dataset_fingerprint", "platform_fingerprint", "scope_fingerprint", mode="before")
    @classmethod
    def _valid_fingerprint(cls, value, info):
        return _fingerprint(value, info.field_name)


class PromotionGateV1(_Contract):
    schema_version: Literal["vc.benchmark-promotion-gate.v1"]
    maximum_calibration_error: float
    minimum_coverage: float
    maximum_selective_risk: float
    maximum_wrong_accept_rate: float
    maximum_unnecessary_abstain_rate: float

    @field_validator(
        "maximum_calibration_error",
        "minimum_coverage",
        "maximum_wrong_accept_rate",
        "maximum_unnecessary_abstain_rate",
        mode="before",
    )
    @classmethod
    def _valid_rate(cls, value, info):
        return _unit_interval(value, info.field_name)

    @field_validator("maximum_selective_risk", mode="before")
    @classmethod
    def _valid_risk(cls, value):
        value = _finite(value, "maximum_selective_risk")
        if value < 0:
            raise ValueError("maximum_selective_risk must be non-negative")
        return value


class BenchmarkProtocolV1(_Contract):
    schema_version: Literal["vc.benchmark-protocol.v1"]
    protocol_id: str
    task: str
    scope: BenchmarkScopeV1
    pack_fingerprint: str
    dataset: DatasetBindingV1
    feature_contract_fingerprint: str
    output_contract_fingerprint: str
    split: BenchmarkSplitV1
    baseline: BenchmarkBaselineV1
    primary_metric: BenchmarkMetricV1
    confidence_interval: PairedCIPolicyV1
    seeds: tuple[int, ...]
    threshold_policy: ThresholdPolicyV1
    calibration_policy: CalibrationPolicyV1
    ood_policy: tuple[OODGateV1, ...]
    external_policy: ExternalPolicyV1
    promotion_gate: PromotionGateV1
    candidate_result_observed: Literal[False]
    frozen: Literal[True]
    composite_score: None

    @field_validator("protocol_id", "task", mode="before")
    @classmethod
    def _valid_text(cls, value, info):
        return _text(value, info.field_name)

    @field_validator("pack_fingerprint", "feature_contract_fingerprint", "output_contract_fingerprint", mode="before")
    @classmethod
    def _valid_fingerprint(cls, value, info):
        return _fingerprint(value, info.field_name)

    @field_validator("seeds", mode="before")
    @classmethod
    def _valid_seeds(cls, value):
        if not isinstance(value, (list, tuple)):
            raise ValueError("seeds must be an array")
        seeds = tuple(_nonnegative_int(item, "seeds") for item in value)
        if len(seeds) < 3 or len(set(seeds)) != len(seeds):
            raise ValueError("seeds must contain at least three unique values")
        return seeds

    @field_validator("ood_policy", mode="before")
    @classmethod
    def _valid_ood(cls, value):
        if not isinstance(value, (list, tuple)) or not value:
            raise ValueError("ood_policy must be a non-empty array")
        return tuple(value)

    @model_validator(mode="after")
    def _cross_bound_policy(self):
        if self.confidence_interval.group_unit != self.split.group_unit:
            raise ValueError("CI group_unit must match split group_unit")
        if self.external_policy.scope_fingerprint != self.scope.fingerprint():
            raise ValueError("external scope_fingerprint must match frozen scope")
        if self.external_policy.dataset_fingerprint == self.dataset.dataset_fingerprint:
            raise ValueError("external dataset must be independent")
        if self.external_policy.platform_fingerprint == self.dataset.platform_fingerprint:
            raise ValueError("external platform must be independent")
        axes = tuple(item.axis for item in self.ood_policy)
        if len(set(axes)) != len(axes):
            raise ValueError("OOD axes must be unique")
        return self


class BenchmarkRunAuthorizationV1(_Contract):
    schema_version: Literal["vc.benchmark-run-authorization.v1"]
    authorization_id: str
    authorized_run_id: str
    authorized_run_payload_fingerprint: str
    authorization_kind: Literal["contract_fixture", "p21b_single_candidate"]
    authorization_record_sha256: str
    protocol_fingerprint: str
    scope_fingerprint: str
    candidate_model_fingerprint: str
    asset_manifest_fingerprint: str
    output_root_identity_fingerprint: str
    real_candidate_run_authorized: bool
    test_external_access_authorized: bool

    @field_validator("authorization_id", "authorized_run_id", mode="before")
    @classmethod
    def _valid_id(cls, value, info):
        return _text(value, info.field_name)

    @field_validator(
        "authorization_record_sha256",
        "authorized_run_payload_fingerprint",
        "protocol_fingerprint",
        "scope_fingerprint",
        "candidate_model_fingerprint",
        "asset_manifest_fingerprint",
        "output_root_identity_fingerprint",
        mode="before",
    )
    @classmethod
    def _valid_fingerprint(cls, value, info):
        return _fingerprint(value, info.field_name)

    @model_validator(mode="after")
    def _authorization_boundary(self):
        authorized = self.authorization_kind == "p21b_single_candidate"
        if self.real_candidate_run_authorized != authorized or (self.test_external_access_authorized != authorized):
            raise ValueError("only an exact P21B authorization may permit candidate/test/external access")
        payload = self.to_dict()
        payload.pop("authorization_record_sha256")
        if self.authorization_record_sha256 != _canonical_fingerprint(payload):
            raise ValueError("authorization_record_sha256 does not bind the authorization content")
        return self


class BenchmarkRunV1(_Contract):
    schema_version: Literal["vc.benchmark-run.v1"]
    run_id: str
    protocol_fingerprint: str
    training_job_fingerprint: str
    training_result_fingerprint: str
    checkpoint_fingerprint: str
    artifact_fingerprint: str
    model_card_fingerprint: str
    candidate_model_fingerprint: str
    model_identity_fingerprint: str
    factory_registration_fingerprint: str
    pack_fingerprint: str
    feature_contract_fingerprint: str
    output_contract_fingerprint: str
    trainer_revision: str
    trainer_source_sha256: str
    training_environment_fingerprint: str
    candidate_provenance_fingerprint: str
    adapter_fingerprints: tuple[str, ...]
    evaluation_environment_fingerprint: str
    evaluation_code_sha256: str
    compatibility_report_fingerprints: tuple[str, ...]
    compatibility_passed: bool
    seeds: tuple[int, ...]
    candidate_registry_state: Literal["candidate_cataloged_contract_only", "candidate_cataloged"]
    candidate_identity_immutable: Literal[True]
    execution_path: Literal["model_adapter_broker_runtime"]
    broker_contract_fingerprint: str
    runtime_receipt_fingerprint: str
    direct_model_invocation: Literal[False]
    direct_asset_access: Literal[False]
    fit_partition: Literal["train"]
    threshold_partition: Literal["validation"]
    evaluation_partitions: tuple[str, ...]
    evidence_class: Literal["contract_fixture", "authorized_candidate"]
    authorization: BenchmarkRunAuthorizationV1

    @field_validator("run_id", mode="before")
    @classmethod
    def _valid_id(cls, value):
        return _text(value, "run_id")

    @field_validator(
        "protocol_fingerprint",
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
        "trainer_source_sha256",
        "training_environment_fingerprint",
        "candidate_provenance_fingerprint",
        "evaluation_environment_fingerprint",
        "evaluation_code_sha256",
        "broker_contract_fingerprint",
        "runtime_receipt_fingerprint",
        mode="before",
    )
    @classmethod
    def _valid_fingerprint(cls, value, info):
        return _fingerprint(value, info.field_name)

    @field_validator("trainer_revision", mode="before")
    @classmethod
    def _valid_trainer_revision(cls, value):
        return _text(value, "trainer_revision")

    @field_validator("adapter_fingerprints", "compatibility_report_fingerprints", mode="before")
    @classmethod
    def _valid_fingerprints(cls, value, info):
        return _fingerprints(value, info.field_name)

    @field_validator("seeds", mode="before")
    @classmethod
    def _valid_seeds(cls, value):
        if not isinstance(value, (list, tuple)):
            raise ValueError("seeds must be an array")
        seeds = tuple(_nonnegative_int(item, "seeds") for item in value)
        if not seeds or len(set(seeds)) != len(seeds):
            raise ValueError("seeds must be non-empty and unique")
        return seeds

    @field_validator("evaluation_partitions", mode="before")
    @classmethod
    def _valid_partitions(cls, value):
        return _texts(value, "evaluation_partitions")

    @model_validator(mode="after")
    def _evidence_boundary(self):
        if self.evaluation_partitions != ("test", "external"):
            raise ValueError("evaluation_partitions must be exactly test/external")
        if (
            self.authorization.authorized_run_id != self.run_id
            or self.authorization.protocol_fingerprint != self.protocol_fingerprint
            or self.authorization.candidate_model_fingerprint != self.candidate_model_fingerprint
        ):
            raise ValueError("run authorization does not bind run/protocol/candidate")
        if self.evidence_class == "contract_fixture":
            if (
                self.authorization.authorization_kind != "contract_fixture"
                or self.candidate_registry_state != "candidate_cataloged_contract_only"
            ):
                raise ValueError("contract_fixture must remain contract-only")
        elif (
            self.authorization.authorization_kind != "p21b_single_candidate"
            or self.candidate_registry_state != "candidate_cataloged"
        ):
            raise ValueError("authorized_candidate requires an exact P21B single-candidate authorization")
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
        expected = _canonical_fingerprint({field: getattr(self, field) for field in provenance_fields})
        if self.candidate_provenance_fingerprint != expected:
            raise ValueError("candidate provenance fingerprint does not bind the P20 identity chain")
        run_payload = self.to_dict()
        run_payload.pop("authorization")
        if self.authorization.authorized_run_payload_fingerprint != _canonical_fingerprint(run_payload):
            raise ValueError("run authorization does not bind the exact frozen run payload")
        return self


class GroupIdentityV1(_Contract):
    schema_version: Literal["vc.benchmark-group-identity.v1"]
    partition: Literal["train", "validation", "test", "external"]
    group_id: str
    donor: str
    condition: str
    replicate: str
    batch: str

    @field_validator("group_id", "donor", "condition", "replicate", "batch", mode="before")
    @classmethod
    def _valid_identity(cls, value, info):
        return _text(value, info.field_name)


class LeakageAuditV1(_Contract):
    schema_version: Literal["vc.benchmark-leakage-audit.v1"]
    checked_before_evaluation: Literal[True]
    group_unit: str
    split_fingerprint: str
    dataset_fingerprints: tuple[str, ...]
    audited_dimensions: tuple[str, ...]
    partitions: tuple[str, ...]
    records: tuple[GroupIdentityV1, ...]
    record_count: int
    records_fingerprint: str
    overlaps: tuple[str, ...]
    passed: Literal[True]

    @field_validator("group_unit", mode="before")
    @classmethod
    def _valid_group_unit(cls, value):
        return _text(value, "group_unit")

    @field_validator("audited_dimensions", "partitions", mode="before")
    @classmethod
    def _valid_arrays(cls, value, info):
        return _texts(value, info.field_name)

    @field_validator("records", mode="before")
    @classmethod
    def _valid_records(cls, value):
        if not isinstance(value, (list, tuple)) or not value:
            raise ValueError("leakage audit records must be a non-empty array")
        return tuple(value)

    @field_validator("record_count", mode="before")
    @classmethod
    def _valid_count(cls, value):
        return _positive_int(value, "record_count")

    @field_validator("split_fingerprint", "records_fingerprint", mode="before")
    @classmethod
    def _valid_fingerprint(cls, value, info):
        return _fingerprint(value, info.field_name)

    @field_validator("dataset_fingerprints", mode="before")
    @classmethod
    def _valid_dataset_fingerprints(cls, value):
        return _fingerprints(value, "dataset_fingerprints", minimum=2)

    @field_validator("overlaps", mode="before")
    @classmethod
    def _valid_overlaps(cls, value):
        return _texts(value, "overlaps", minimum=0)

    @model_validator(mode="after")
    def _complete_audit(self):
        if self.audited_dimensions != _AUDITED_IDENTITIES or self.partitions != _PARTITIONS:
            raise ValueError("leakage audit dimensions and partitions must be complete")
        if self.overlaps:
            raise ValueError("a passing leakage audit cannot contain overlaps")
        ordered = tuple(
            sorted(
                self.records,
                key=lambda item: (
                    _PARTITIONS.index(item.partition),
                    item.group_id,
                ),
            )
        )
        if self.records != ordered or self.record_count != len(ordered):
            raise ValueError("leakage records must be canonical and match record_count")
        if {item.partition for item in ordered} != set(_PARTITIONS):
            raise ValueError("leakage records must cover every partition")
        if self.records_fingerprint != _canonical_fingerprint([item.to_dict() for item in ordered]):
            raise ValueError("leakage records fingerprint does not bind records")
        for dimension in _AUDITED_IDENTITIES:
            seen: dict[str, str] = {}
            for item in ordered:
                identity = getattr(item, dimension)
                previous = seen.get(identity)
                if previous is not None and previous != item.partition:
                    raise ValueError(f"{dimension} overlaps benchmark partitions")
                seen[identity] = item.partition
        return self


def audit_group_leakage(
    records: Sequence[GroupIdentityV1],
    *,
    split_fingerprint: str,
    dataset_fingerprints: Sequence[str],
) -> LeakageAuditV1:
    """Audit all biological identities before any test/external evaluation."""

    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)) or not records:
        raise BenchmarkSystemError("group identity records must be a non-empty sequence")
    values = tuple(records)
    if any(type(item) is not GroupIdentityV1 for item in values):
        raise BenchmarkSystemError("group identity records must be strict GroupIdentityV1 values")
    if {item.partition for item in values} != set(_PARTITIONS):
        raise BenchmarkSystemError("group identities must cover train, validation, test, and external")
    for dimension in _AUDITED_IDENTITIES:
        seen: dict[str, str] = {}
        for item in values:
            identity = getattr(item, dimension)
            previous = seen.get(identity)
            if previous is not None and previous != item.partition:
                raise BenchmarkSystemError(f"{dimension} overlap across {previous}/{item.partition}: {identity!r}")
            seen[identity] = item.partition
    ordered = sorted(
        (item.to_dict() for item in values),
        key=lambda item: (_PARTITIONS.index(item["partition"]), item["group_id"]),
    )
    return LeakageAuditV1(
        schema_version="vc.benchmark-leakage-audit.v1",
        checked_before_evaluation=True,
        group_unit="biological_condition",
        split_fingerprint=_fingerprint(split_fingerprint, "split_fingerprint"),
        dataset_fingerprints=_fingerprints(
            dataset_fingerprints,
            "dataset_fingerprints",
            minimum=2,
        ),
        audited_dimensions=_AUDITED_IDENTITIES,
        partitions=_PARTITIONS,
        records=tuple(GroupIdentityV1.from_dict(item) for item in ordered),
        record_count=len(values),
        records_fingerprint=_canonical_fingerprint(ordered),
        overlaps=(),
        passed=True,
    )


class ReliabilityRowV1(_Contract):
    schema_version: Literal["vc.benchmark-reliability-row.v1"]
    partition: Literal["validation", "test", "external"]
    unit_id: str
    reliability_score: float
    candidate_loss: float
    baseline_loss: float

    @field_validator("unit_id", mode="before")
    @classmethod
    def _valid_id(cls, value):
        return _text(value, "unit_id")

    @field_validator("reliability_score", "candidate_loss", "baseline_loss", mode="before")
    @classmethod
    def _valid_number(cls, value, info):
        result = _finite(value, info.field_name)
        if info.field_name.endswith("loss") and result < 0:
            raise ValueError(f"{info.field_name} must be non-negative")
        return result


class ThresholdReceiptV1(_Contract):
    schema_version: Literal["vc.benchmark-threshold-receipt.v1"]
    selection_partition: Literal["validation"]
    policy_fingerprint: str
    minimum_coverage: float
    selection_rows: tuple[ReliabilityRowV1, ...]
    group_set_fingerprint: str
    selection_rows_fingerprint: str
    threshold: float
    selected_before_test_external: Literal[True]
    accepted_units: int
    total_units: int
    coverage: float
    candidate_risk: float

    @field_validator(
        "policy_fingerprint",
        "group_set_fingerprint",
        "selection_rows_fingerprint",
        mode="before",
    )
    @classmethod
    def _valid_fingerprint(cls, value, info):
        return _fingerprint(value, info.field_name)

    @field_validator("minimum_coverage", mode="before")
    @classmethod
    def _valid_minimum_coverage(cls, value):
        return _unit_interval(value, "minimum_coverage", include_zero=False)

    @field_validator("selection_rows", mode="before")
    @classmethod
    def _valid_rows(cls, value):
        if not isinstance(value, (list, tuple)) or not value:
            raise ValueError("selection_rows must be a non-empty array")
        return tuple(value)

    @field_validator("threshold", "candidate_risk", mode="before")
    @classmethod
    def _valid_number(cls, value, info):
        result = _finite(value, info.field_name)
        if info.field_name == "candidate_risk" and result < 0:
            raise ValueError("candidate_risk must be non-negative")
        return result

    @field_validator("accepted_units", "total_units", mode="before")
    @classmethod
    def _valid_count(cls, value, info):
        return _positive_int(value, info.field_name)

    @field_validator("coverage", mode="before")
    @classmethod
    def _valid_coverage(cls, value):
        return _unit_interval(value, "coverage", include_zero=False)

    @model_validator(mode="after")
    def _consistent_counts(self):
        if self.accepted_units > self.total_units or self.coverage != self.accepted_units / self.total_units:
            raise ValueError("threshold coverage and counts disagree")
        if any(item.partition != "validation" for item in self.selection_rows):
            raise ValueError("threshold receipt may contain only validation rows")
        unit_ids = [item.unit_id for item in self.selection_rows]
        if len(set(unit_ids)) != len(unit_ids):
            raise ValueError("threshold selection rows must have unique unit IDs")
        if unit_ids != sorted(unit_ids):
            raise ValueError("threshold selection rows must use canonical unit-ID order")
        if self.group_set_fingerprint != _canonical_fingerprint(sorted(unit_ids)):
            raise ValueError("threshold group-set fingerprint does not bind validation units")
        payload = [
            {
                "partition": item.partition,
                "unit_id": item.unit_id,
                "reliability_score": item.reliability_score,
                "candidate_loss": item.candidate_loss,
                "baseline_loss": item.baseline_loss,
            }
            for item in self.selection_rows
        ]
        expected_rows = _canonical_fingerprint(payload)
        if self.selection_rows_fingerprint != expected_rows:
            raise ValueError("selection_rows_fingerprint does not bind validation rows")
        try:
            selected = select_threshold(payload, self.minimum_coverage)
        except OODValidationError as exc:
            raise ValueError(f"threshold receipt cannot be reproduced: {exc}") from exc
        expected = (
            selected["threshold"],
            selected["accepted_units"],
            selected["total_units"],
            selected["coverage"],
            selected["candidate_risk"],
        )
        actual = (
            self.threshold,
            self.accepted_units,
            self.total_units,
            self.coverage,
            self.candidate_risk,
        )
        if actual != expected:
            raise ValueError("threshold receipt does not reproduce from its validation rows")
        return self


def select_validation_threshold(
    records: Sequence[Mapping[str, Any] | ReliabilityRowV1],
    *,
    policy: ThresholdPolicyV1,
) -> ThresholdReceiptV1:
    """Select a threshold from strict validation rows; reject all other partitions."""

    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)) or not records:
        raise BenchmarkSystemError("reliability rows must be a non-empty sequence")
    values = []
    for item in records:
        if type(item) is ReliabilityRowV1:
            if item.partition != "validation":
                raise BenchmarkSystemError("threshold selection accepts only validation rows")
            values.append(item)
        elif isinstance(item, dict):
            if item.get("partition") != "validation":
                raise BenchmarkSystemError("threshold selection accepts only validation rows")
            values.append(ReliabilityRowV1.from_dict(item))
        else:
            raise BenchmarkSystemError("reliability rows must be strict JSON objects")
    unit_ids = [item.unit_id for item in values]
    if len(set(unit_ids)) != len(unit_ids):
        raise BenchmarkSystemError("reliability unit_id values must be unique")
    if unit_ids != sorted(unit_ids):
        raise BenchmarkSystemError("reliability rows must use canonical unit-ID order")
    if type(policy) is not ThresholdPolicyV1:
        raise TypeError("policy must be exact ThresholdPolicyV1")
    policy = ThresholdPolicyV1.from_dict(policy.to_dict())
    minimum = policy.minimum_coverage
    validation = tuple(values)
    payload = [
        {
            "partition": item.partition,
            "unit_id": item.unit_id,
            "reliability_score": item.reliability_score,
            "candidate_loss": item.candidate_loss,
            "baseline_loss": item.baseline_loss,
        }
        for item in validation
    ]
    try:
        selected = select_threshold(payload, minimum)
    except OODValidationError as exc:
        raise BenchmarkSystemError(f"validation threshold selection failed: {exc}") from exc
    return ThresholdReceiptV1(
        schema_version="vc.benchmark-threshold-receipt.v1",
        selection_partition="validation",
        policy_fingerprint=policy.fingerprint(),
        minimum_coverage=minimum,
        selection_rows=validation,
        group_set_fingerprint=_canonical_fingerprint(sorted(unit_ids)),
        selection_rows_fingerprint=_canonical_fingerprint(payload),
        threshold=selected["threshold"],
        selected_before_test_external=True,
        accepted_units=selected["accepted_units"],
        total_units=selected["total_units"],
        coverage=selected["coverage"],
        candidate_risk=selected["candidate_risk"],
    )


class SeedResultV1(_Contract):
    schema_version: Literal["vc.benchmark-seed-result.v1"]
    seed: int
    candidate: float
    baseline: float
    difference: float

    @field_validator("seed", mode="before")
    @classmethod
    def _valid_seed(cls, value):
        return _nonnegative_int(value, "seed")

    @field_validator("candidate", "baseline", "difference", mode="before")
    @classmethod
    def _valid_number(cls, value, info):
        return _finite(value, info.field_name)

    @model_validator(mode="after")
    def _consistent_difference(self):
        if not math.isclose(
            self.difference,
            self.candidate - self.baseline,
            rel_tol=1e-12,
            abs_tol=1e-15,
        ):
            raise ValueError("seed difference must equal candidate minus baseline")
        return self


class GroupMetricValueV1(_Contract):
    schema_version: Literal["vc.benchmark-group-metric-value.v1"]
    group_id: str
    value: float

    @field_validator("group_id", mode="before")
    @classmethod
    def _valid_group_id(cls, value):
        return _text(value, "group_id")

    @field_validator("value", mode="before")
    @classmethod
    def _valid_value(cls, value):
        return _finite(value, "group metric value")


class PrimaryMeasurementRowV1(_Contract):
    schema_version: Literal["vc.benchmark-primary-measurement-row.v1"]
    group_id: str
    seed: int
    candidate: float
    baseline: float
    difference: float

    @field_validator("group_id", mode="before")
    @classmethod
    def _valid_group_id(cls, value):
        return _text(value, "group_id")

    @field_validator("seed", mode="before")
    @classmethod
    def _valid_seed(cls, value):
        return _nonnegative_int(value, "seed")

    @field_validator("candidate", "baseline", "difference", mode="before")
    @classmethod
    def _valid_number(cls, value, info):
        return _finite(value, info.field_name)

    @model_validator(mode="after")
    def _consistent_difference(self):
        if self.difference != self.candidate - self.baseline:
            raise ValueError("measurement difference must equal candidate minus baseline")
        return self


class PairedCIResultV1(_Contract):
    schema_version: Literal["vc.benchmark-paired-ci.v1"]
    low: float
    high: float
    method: Literal["paired_group_percentile"]
    rng: Literal["numpy.PCG64"]
    quantile_method: Literal["linear"]
    group_unit: str
    confidence_level: float
    replicates: int
    seed: int
    group_count: int
    group_differences: tuple[GroupMetricValueV1, ...]
    group_differences_sha256: str

    @field_validator("low", "high", mode="before")
    @classmethod
    def _valid_bound(cls, value, info):
        return _finite(value, info.field_name)

    @field_validator("group_unit", mode="before")
    @classmethod
    def _valid_group_unit(cls, value):
        return _text(value, "group_unit")

    @field_validator("confidence_level", mode="before")
    @classmethod
    def _valid_confidence(cls, value):
        value = _unit_interval(value, "confidence_level", include_zero=False)
        if value >= 1:
            raise ValueError("confidence_level must be below 1")
        return value

    @field_validator("replicates", "group_count", mode="before")
    @classmethod
    def _valid_positive(cls, value, info):
        return _positive_int(value, info.field_name)

    @field_validator("seed", mode="before")
    @classmethod
    def _valid_seed(cls, value):
        return _nonnegative_int(value, "seed")

    @field_validator("group_differences_sha256", mode="before")
    @classmethod
    def _valid_fingerprint(cls, value):
        return _fingerprint(value, "group_differences_sha256")

    @field_validator("group_differences", mode="before")
    @classmethod
    def _valid_group_differences(cls, value):
        if not isinstance(value, (list, tuple)) or not value:
            raise ValueError("group_differences must be a non-empty array")
        return tuple(value)

    @model_validator(mode="after")
    def _ordered_bounds(self):
        if self.low > self.high:
            raise ValueError("paired CI low must not exceed high")
        if self.group_count != len(self.group_differences):
            raise ValueError("paired CI group_count does not match group_differences")
        group_ids = [item.group_id for item in self.group_differences]
        if len(set(group_ids)) != len(group_ids) or group_ids != sorted(group_ids):
            raise ValueError("paired CI group differences must have unique canonical group IDs")
        if self.group_differences_sha256 != _canonical_fingerprint([item.to_dict() for item in self.group_differences]):
            raise ValueError("group_differences_sha256 does not bind the paired values")
        if self.confidence_level != 0.95 or self.replicates != 2000 or self.seed != 0:
            raise ValueError("paired CI must use the frozen P8/P9 bootstrap settings")
        if (self.low, self.high) != _paired_ci_bounds([item.value for item in self.group_differences]):
            raise ValueError("paired CI bounds do not reproduce from group differences")
        return self


class PrimaryResultV1(_Contract):
    schema_version: Literal["vc.benchmark-primary-result.v1"]
    evaluation_partition: Literal["test", "external"]
    dataset_fingerprint: str
    split_fingerprint: str
    group_set_fingerprint: str
    candidate_model_fingerprint: str
    baseline_fingerprint: str
    metric_name: str
    runtime_receipt_fingerprint: str
    measurement_receipt_fingerprint: str
    candidate: float
    baseline: float
    difference: float
    paired_ci: PairedCIResultV1
    measurement_rows: tuple[PrimaryMeasurementRowV1, ...]
    seed_results: tuple[SeedResultV1, ...]

    @field_validator(
        "dataset_fingerprint",
        "split_fingerprint",
        "group_set_fingerprint",
        "candidate_model_fingerprint",
        "baseline_fingerprint",
        "runtime_receipt_fingerprint",
        "measurement_receipt_fingerprint",
        mode="before",
    )
    @classmethod
    def _valid_fingerprint(cls, value, info):
        return _fingerprint(value, info.field_name)

    @field_validator("metric_name", mode="before")
    @classmethod
    def _valid_metric_name(cls, value):
        return _text(value, "metric_name")

    @field_validator("candidate", "baseline", "difference", mode="before")
    @classmethod
    def _valid_number(cls, value, info):
        return _finite(value, info.field_name)

    @field_validator("measurement_rows", "seed_results", mode="before")
    @classmethod
    def _valid_measurement_arrays(cls, value, info):
        if not isinstance(value, (list, tuple)) or not value:
            raise ValueError(f"{info.field_name} must be a non-empty array")
        return tuple(value)

    @model_validator(mode="after")
    def _consistent_summary(self):
        if len({item.seed for item in self.seed_results}) != len(self.seed_results):
            raise ValueError("seed_results must contain unique seeds")
        ordered_rows = tuple(
            sorted(
                self.measurement_rows,
                key=lambda item: (item.group_id, item.seed),
            )
        )
        if self.measurement_rows != ordered_rows or len({(item.group_id, item.seed) for item in ordered_rows}) != len(
            ordered_rows
        ):
            raise ValueError("primary measurement rows must be canonical and unique")
        group_ids = tuple(sorted({item.group_id for item in ordered_rows}))
        if self.group_set_fingerprint != _canonical_fingerprint(list(group_ids)):
            raise ValueError("primary group-set fingerprint does not bind measurement rows")
        ci_by_group = {item.group_id: item.value for item in self.paired_ci.group_differences}
        if tuple(ci_by_group) != group_ids:
            raise ValueError("paired CI groups do not match primary measurement rows")
        seeds = tuple(item.seed for item in self.seed_results)
        expected_seed_set = set(seeds)
        for group_id in group_ids:
            if {item.seed for item in ordered_rows if item.group_id == group_id} != expected_seed_set:
                raise ValueError("each biological group must contain every preregistered seed")
            values = [item.difference for item in ordered_rows if item.group_id == group_id]
            expected_group = _canonical_mean(values, "paired group differences")
            if ci_by_group[group_id] != expected_group:
                raise ValueError("paired group difference does not reproduce from measurement rows")
        seed_by_id = {item.seed: item for item in self.seed_results}
        for seed in seeds:
            rows = [item for item in ordered_rows if item.seed == seed]
            expected_candidate = _canonical_mean(
                [item.candidate for item in rows],
                "seed candidate measurements",
            )
            expected_baseline = _canonical_mean(
                [item.baseline for item in rows],
                "seed baseline measurements",
            )
            expected_difference = _canonical_mean(
                [item.difference for item in rows],
                "seed paired differences",
            )
            observed = seed_by_id[seed]
            if (
                observed.candidate,
                observed.baseline,
                observed.difference,
            ) != (
                expected_candidate,
                expected_baseline,
                expected_difference,
            ):
                raise ValueError("seed summary does not reproduce from measurement rows")
        candidate = _canonical_mean(
            [item.candidate for item in ordered_rows],
            "primary candidate measurements",
        )
        baseline = _canonical_mean(
            [item.baseline for item in ordered_rows],
            "primary baseline measurements",
        )
        difference = _canonical_mean(
            [item.difference for item in ordered_rows],
            "primary paired differences",
        )
        if (self.candidate, self.baseline, self.difference) != (
            candidate,
            baseline,
            difference,
        ):
            raise ValueError("primary summary does not reproduce from canonical measurement rows")
        payload = self.to_dict()
        payload.pop("measurement_receipt_fingerprint")
        if self.measurement_receipt_fingerprint != _canonical_fingerprint(payload):
            raise ValueError("measurement receipt fingerprint does not bind primary content")
        return self


class CalibrationBinV1(_Contract):
    schema_version: Literal["vc.benchmark-calibration-bin.v1"]
    index: int
    count: int
    mean_confidence: float
    empirical_accuracy: float

    @field_validator("index", mode="before")
    @classmethod
    def _valid_index(cls, value):
        return _nonnegative_int(value, "calibration bin index")

    @field_validator("count", mode="before")
    @classmethod
    def _valid_count(cls, value):
        return _positive_int(value, "calibration bin count")

    @field_validator("mean_confidence", "empirical_accuracy", mode="before")
    @classmethod
    def _valid_rate(cls, value, info):
        return _unit_interval(value, info.field_name)


class ScalarCapabilityV1(_Contract):
    schema_version: Literal["vc.benchmark-scalar-capability.v1"]
    metric_name: Literal["expected_calibration_error"]
    method: Literal["equal_width"]
    configured_bins: int
    evaluation_partition: Literal["test"]
    dataset_fingerprint: str
    split_fingerprint: str
    group_set_fingerprint: str
    candidate_model_fingerprint: str
    runtime_receipt_fingerprint: str
    available: bool
    value: float | None
    reason: str | None
    observed_bins: tuple[CalibrationBinV1, ...]
    result_fingerprint: str

    @field_validator(
        "dataset_fingerprint",
        "split_fingerprint",
        "group_set_fingerprint",
        "candidate_model_fingerprint",
        "runtime_receipt_fingerprint",
        "result_fingerprint",
        mode="before",
    )
    @classmethod
    def _valid_fingerprint(cls, value, info):
        return _fingerprint(value, info.field_name)

    @field_validator("configured_bins", mode="before")
    @classmethod
    def _valid_configured_bins(cls, value):
        value = _positive_int(value, "configured_bins")
        if value < 2:
            raise ValueError("configured_bins must be at least two")
        return value

    @field_validator("observed_bins", mode="before")
    @classmethod
    def _valid_bins(cls, value):
        if not isinstance(value, (list, tuple)):
            raise ValueError("observed_bins must be an array")
        return tuple(value)

    @field_validator("value", mode="before")
    @classmethod
    def _valid_value(cls, value):
        return None if value is None else _finite(value, "value")

    @field_validator("reason", mode="before")
    @classmethod
    def _valid_reason(cls, value):
        return None if value is None else _text(value, "reason")

    @model_validator(mode="after")
    def _available_or_explained(self):
        if self.available != (self.value is not None):
            raise ValueError("capability availability must agree with value presence")
        if self.available and self.reason is not None:
            raise ValueError("available capability cannot contain an unavailable reason")
        if not self.available and self.reason is None:
            raise ValueError("unavailable capability requires a reason")
        if self.available:
            if not self.observed_bins:
                raise ValueError("available calibration requires observed bins")
            indices = [item.index for item in self.observed_bins]
            if len(set(indices)) != len(indices) or any(index >= self.configured_bins for index in indices):
                raise ValueError("calibration bin indices must be unique and configured")
            if indices != sorted(indices):
                raise ValueError("calibration bins must use canonical index order")
            total = math.fsum(item.count for item in self.observed_bins)
            expected = (
                math.fsum(
                    item.count * abs(item.empirical_accuracy - item.mean_confidence) for item in self.observed_bins
                )
                / total
            )
            if self.value is None or self.value != expected:
                raise ValueError("calibration value does not reproduce from observed bins")
        elif self.observed_bins:
            raise ValueError("unavailable calibration cannot contain observed bins")
        payload = self.to_dict()
        payload.pop("result_fingerprint")
        if self.result_fingerprint != _canonical_fingerprint(payload):
            raise ValueError("calibration result fingerprint does not bind its content")
        return self


class OODResultV1(_Contract):
    schema_version: Literal["vc.benchmark-ood-result.v1"]
    axis: str
    metric_name: str
    direction: Literal["lower_is_better", "higher_is_better"]
    evaluation_partition: Literal["test"]
    dataset_fingerprint: str
    split_fingerprint: str
    group_set_fingerprint: str
    candidate_model_fingerprint: str
    runtime_receipt_fingerprint: str
    available: bool
    value: float | None
    reason: str | None
    group_values: tuple[GroupMetricValueV1, ...]
    result_fingerprint: str

    @field_validator(
        "dataset_fingerprint",
        "split_fingerprint",
        "group_set_fingerprint",
        "candidate_model_fingerprint",
        "runtime_receipt_fingerprint",
        "result_fingerprint",
        mode="before",
    )
    @classmethod
    def _valid_fingerprint(cls, value, info):
        return _fingerprint(value, info.field_name)

    @field_validator("axis", "metric_name", mode="before")
    @classmethod
    def _valid_text(cls, value, info):
        return _text(value, info.field_name)

    @field_validator("group_values", mode="before")
    @classmethod
    def _valid_group_values(cls, value):
        if not isinstance(value, (list, tuple)):
            raise ValueError("group_values must be an array")
        return tuple(value)

    @field_validator("value", mode="before")
    @classmethod
    def _valid_value(cls, value):
        return None if value is None else _finite(value, "value")

    @field_validator("reason", mode="before")
    @classmethod
    def _valid_reason(cls, value):
        return None if value is None else _text(value, "reason")

    @model_validator(mode="after")
    def _available_or_explained(self):
        if self.available != (self.value is not None):
            raise ValueError("OOD availability must agree with value presence")
        if self.available and self.reason is not None:
            raise ValueError("available OOD result cannot contain a reason")
        if not self.available and self.reason is None:
            raise ValueError("unavailable OOD result requires a reason")
        if self.available:
            if not self.group_values:
                raise ValueError("available OOD result requires biological-group values")
            group_ids = [item.group_id for item in self.group_values]
            if len(set(group_ids)) != len(group_ids) or group_ids != sorted(group_ids):
                raise ValueError("OOD group values must have unique canonical group IDs")
            if self.group_set_fingerprint != _canonical_fingerprint(group_ids):
                raise ValueError("OOD group-set fingerprint does not bind group values")
            expected = _canonical_mean(
                [item.value for item in self.group_values],
                "OOD biological-group values",
            )
            if self.value is None or self.value != expected:
                raise ValueError("OOD value must equal the biological-group mean")
        elif self.group_values:
            raise ValueError("unavailable OOD result cannot contain group values")
        payload = self.to_dict()
        payload.pop("result_fingerprint")
        if self.result_fingerprint != _canonical_fingerprint(payload):
            raise ValueError("OOD result fingerprint does not bind its content")
        return self


class BenchmarkCapabilityProfileV1(_Contract):
    schema_version: Literal["vc.benchmark-capability-profile.v1"]
    threshold_receipt_fingerprint: str
    selective_evaluation_partition: Literal["test"]
    dataset_fingerprint: str
    split_fingerprint: str
    group_set_fingerprint: str
    candidate_model_fingerprint: str
    runtime_receipt_fingerprint: str
    selected_threshold: float
    selective_rows: tuple[ReliabilityRowV1, ...]
    selective_rows_fingerprint: str
    calibration_error: ScalarCapabilityV1
    coverage: float
    selective_risk: float
    wrong_accept_rate: float
    unnecessary_abstain_rate: float
    ood_results: tuple[OODResultV1, ...]
    composite_score: None

    @field_validator(
        "threshold_receipt_fingerprint",
        "dataset_fingerprint",
        "split_fingerprint",
        "group_set_fingerprint",
        "candidate_model_fingerprint",
        "runtime_receipt_fingerprint",
        "selective_rows_fingerprint",
        mode="before",
    )
    @classmethod
    def _valid_fingerprint(cls, value, info):
        return _fingerprint(value, info.field_name)

    @field_validator("selected_threshold", mode="before")
    @classmethod
    def _valid_selected_threshold(cls, value):
        return _finite(value, "selected_threshold")

    @field_validator("selective_rows", mode="before")
    @classmethod
    def _valid_selective_rows(cls, value):
        if not isinstance(value, (list, tuple)) or not value:
            raise ValueError("selective_rows must be a non-empty array")
        return tuple(value)

    @field_validator("coverage", "wrong_accept_rate", "unnecessary_abstain_rate", mode="before")
    @classmethod
    def _valid_rate(cls, value, info):
        return _unit_interval(value, info.field_name)

    @field_validator("selective_risk", mode="before")
    @classmethod
    def _valid_risk(cls, value):
        value = _finite(value, "selective_risk")
        if value < 0:
            raise ValueError("selective_risk must be non-negative")
        return value

    @field_validator("ood_results", mode="before")
    @classmethod
    def _valid_ood(cls, value):
        if not isinstance(value, (list, tuple)) or not value:
            raise ValueError("ood_results must be a non-empty array")
        return tuple(value)

    @model_validator(mode="after")
    def _unique_axes(self):
        axes = [item.axis for item in self.ood_results]
        if len(set(axes)) != len(axes):
            raise ValueError("OOD result axes must be unique")
        if any(item.partition != "test" for item in self.selective_rows):
            raise ValueError("selective profile may contain only test rows")
        unit_ids = [item.unit_id for item in self.selective_rows]
        if len(set(unit_ids)) != len(unit_ids):
            raise ValueError("selective rows must have unique unit IDs")
        if unit_ids != sorted(unit_ids):
            raise ValueError("selective rows must use canonical unit-ID order")
        if self.group_set_fingerprint != _canonical_fingerprint(sorted(unit_ids)):
            raise ValueError("selective group-set fingerprint does not bind test rows")
        payload = [
            {
                "partition": item.partition,
                "unit_id": item.unit_id,
                "reliability_score": item.reliability_score,
                "candidate_loss": item.candidate_loss,
                "baseline_loss": item.baseline_loss,
            }
            for item in self.selective_rows
        ]
        if self.selective_rows_fingerprint != _canonical_fingerprint(payload):
            raise ValueError("selective_rows_fingerprint does not bind test rows")
        try:
            reproduced = selective_metrics(payload, self.selected_threshold)
        except OODValidationError as exc:
            raise ValueError(f"selective metrics cannot be reproduced: {exc}") from exc
        expected = (
            reproduced["coverage"],
            reproduced["accepted_risk"],
            reproduced["wrong_accept_rate"],
            reproduced["unnecessary_abstain_rate"],
        )
        if any(value is None for value in expected):
            raise ValueError("selective metrics are unavailable for the supplied test rows")
        actual = (
            self.coverage,
            self.selective_risk,
            self.wrong_accept_rate,
            self.unnecessary_abstain_rate,
        )
        if actual != expected:
            raise ValueError("selective metrics do not reproduce from test rows")
        return self


class ExternalResultV1(_Contract):
    schema_version: Literal["vc.benchmark-external-result.v1"]
    dataset_fingerprint: str
    platform_fingerprint: str
    scope_fingerprint: str
    independent_dataset: bool
    independent_platform: bool
    adaptation_steps: int
    evaluation_receipt_fingerprint: str
    leakage_audit: LeakageAuditV1
    primary: PrimaryResultV1

    @field_validator(
        "dataset_fingerprint",
        "platform_fingerprint",
        "scope_fingerprint",
        "evaluation_receipt_fingerprint",
        mode="before",
    )
    @classmethod
    def _valid_fingerprint(cls, value, info):
        return _fingerprint(value, info.field_name)

    @field_validator("adaptation_steps", mode="before")
    @classmethod
    def _valid_steps(cls, value):
        return _nonnegative_int(value, "adaptation_steps")

    @model_validator(mode="after")
    def _receipt_is_bound(self):
        payload = self.to_dict()
        payload.pop("evaluation_receipt_fingerprint")
        if self.evaluation_receipt_fingerprint != _canonical_fingerprint(payload):
            raise ValueError("external evaluation receipt does not bind its content")
        return self


class BenchmarkResultV1(_Contract):
    schema_version: Literal["vc.benchmark-result.v1"]
    result_id: str
    protocol_fingerprint: str
    run_fingerprint: str
    candidate_model_fingerprint: str
    status: Literal["completed", "failed", "abstained"]
    runtime_receipt_fingerprint: str
    leakage_audit: LeakageAuditV1 | None
    threshold_receipt: ThresholdReceiptV1 | None
    primary: PrimaryResultV1 | None
    profile: BenchmarkCapabilityProfileV1 | None
    external: ExternalResultV1 | None
    tuning_after_test_external: Literal[False]
    failure_reason_codes: tuple[str, ...]

    @field_validator("result_id", mode="before")
    @classmethod
    def _valid_id(cls, value):
        return _text(value, "result_id")

    @field_validator(
        "protocol_fingerprint",
        "run_fingerprint",
        "candidate_model_fingerprint",
        "runtime_receipt_fingerprint",
        mode="before",
    )
    @classmethod
    def _valid_fingerprint(cls, value, info):
        return _fingerprint(value, info.field_name)

    @field_validator("failure_reason_codes", mode="before")
    @classmethod
    def _valid_reasons(cls, value):
        return _texts(value, "failure_reason_codes", minimum=0)

    @model_validator(mode="after")
    def _complete_or_failed(self):
        measurements = (self.leakage_audit, self.threshold_receipt, self.primary, self.profile)
        if self.status == "completed":
            if any(item is None for item in measurements):
                raise ValueError("completed result requires all internal measurements")
            assert self.threshold_receipt is not None and self.profile is not None
            if self.profile.threshold_receipt_fingerprint != self.threshold_receipt.fingerprint():
                raise ValueError("capability profile must bind the frozen threshold receipt")
            if self.profile.selected_threshold != self.threshold_receipt.threshold:
                raise ValueError("capability profile must use the selected validation threshold")
        elif any(item is not None for item in (*measurements, self.external)):
            raise ValueError("failed or abstained result cannot contain scientific measurements")
        elif not self.failure_reason_codes:
            raise ValueError("failed or abstained result requires reason codes")
        return self


class BenchmarkPromotionEvidenceV1(_Contract):
    """Evidence-only gate result; operator production policy is intentionally absent."""

    schema_version: Literal["vc.benchmark-promotion-evidence.v1"]
    evidence_id: str
    protocol_fingerprint: str
    run_fingerprint: str
    result_fingerprint: str
    profile_fingerprint: str
    validation_evidence: ValidationEvidence
    evidence_grade: Literal[
        "contract_only",
        "negative",
        "internal_benchmark",
        "external_validation",
        "promotion_eligible",
    ]
    reason_codes: tuple[str, ...]

    @field_validator("evidence_id", mode="before")
    @classmethod
    def _valid_id(cls, value):
        return _text(value, "evidence_id")

    @field_validator(
        "protocol_fingerprint",
        "run_fingerprint",
        "result_fingerprint",
        "profile_fingerprint",
        mode="before",
    )
    @classmethod
    def _valid_fingerprint(cls, value, info):
        return _fingerprint(value, info.field_name)

    @field_validator("reason_codes", mode="before")
    @classmethod
    def _valid_reasons(cls, value):
        return _texts(value, "reason_codes")

    @model_validator(mode="after")
    def _consistent_summary(self):
        evidence = self.validation_evidence
        if not self.evidence_id.startswith("p21a:") or not evidence.evidence_id.startswith("benchmark:"):
            raise ValueError("benchmark evidence IDs must use their reserved prefixes")
        if self.evidence_id.removeprefix("p21a:") != evidence.evidence_id.removeprefix("benchmark:"):
            raise ValueError("top-level and registry evidence IDs must bind one result")
        if evidence.protocol_fingerprint != self.protocol_fingerprint:
            raise ValueError("validation evidence protocol binding is stale")
        if evidence.result_sha256 != self.result_fingerprint:
            raise ValueError("validation evidence result binding is stale")
        expected_grade = (
            "promotion_eligible"
            if evidence.promotion_eligible
            else "external_validation"
            if evidence.scientifically_validated
            else "internal_benchmark"
            if evidence.benchmark_passed
            else "contract_only"
            if "contract_fixture_not_evidence_eligible" in self.reason_codes
            else "negative"
        )
        if self.evidence_grade != expected_grade:
            raise ValueError("evidence_grade contradicts validation states")
        return self


def _check_audit_binding(protocol: BenchmarkProtocolV1, audit: LeakageAuditV1, label: str) -> None:
    if (
        audit.group_unit != protocol.split.group_unit
        or audit.split_fingerprint != protocol.split.split_fingerprint
        or audit.dataset_fingerprints
        != (
            protocol.dataset.dataset_fingerprint,
            protocol.external_policy.dataset_fingerprint,
        )
        or audit.audited_dimensions != ("group_id", *protocol.split.leakage_dimensions)
        or audit.partitions != protocol.split.partitions
        or audit.record_count != protocol.split.leakage_record_count
        or audit.records_fingerprint != protocol.split.leakage_records_fingerprint
    ):
        raise BenchmarkSystemError(f"{label} leakage audit does not match frozen protocol")
    for partition in ("validation", "test", "external"):
        observed = tuple(sorted(item.group_id for item in audit.records if item.partition == partition))
        if observed != tuple(sorted(getattr(protocol.split, f"{partition}_group_ids"))):
            raise BenchmarkSystemError(f"{label} leakage audit does not cover frozen {partition} groups")


def _primary_reasons(
    protocol: BenchmarkProtocolV1,
    run: BenchmarkRunV1,
    primary: PrimaryResultV1,
    *,
    partition: Literal["test", "external"],
) -> tuple[str, ...]:
    prefix = "" if partition == "test" else "external_"
    policy = protocol.confidence_interval
    ci = primary.paired_ci
    expected_dataset = (
        protocol.dataset.dataset_fingerprint if partition == "test" else protocol.external_policy.dataset_fingerprint
    )
    expected_group_set = (
        protocol.split.test_group_set_fingerprint
        if partition == "test"
        else protocol.split.external_group_set_fingerprint
    )
    expected_group_count = (
        protocol.split.test_group_count if partition == "test" else protocol.split.external_group_count
    )
    if (
        primary.evaluation_partition != partition
        or primary.dataset_fingerprint != expected_dataset
        or primary.split_fingerprint != protocol.split.split_fingerprint
        or primary.group_set_fingerprint != expected_group_set
        or primary.candidate_model_fingerprint != run.candidate_model_fingerprint
        or primary.baseline_fingerprint != protocol.baseline.baseline_fingerprint
        or primary.metric_name != protocol.primary_metric.name
        or primary.runtime_receipt_fingerprint != run.runtime_receipt_fingerprint
        or ci.group_count != expected_group_count
        or tuple(item.group_id for item in ci.group_differences)
        != tuple(sorted(protocol.split.test_group_ids if partition == "test" else protocol.split.external_group_ids))
    ):
        raise BenchmarkSystemError(f"{prefix}primary measurement binding drifted from protocol/run")
    if (
        ci.method != policy.method
        or ci.rng != policy.rng
        or ci.quantile_method != policy.quantile_method
        or ci.group_unit != policy.group_unit
        or ci.confidence_level != policy.confidence_level
        or ci.replicates != policy.replicates
        or ci.seed != policy.seed
    ):
        raise BenchmarkSystemError(f"{prefix}paired CI does not match frozen protocol")
    if tuple(item.seed for item in primary.seed_results) != protocol.seeds:
        raise BenchmarkSystemError(f"{prefix}primary seeds do not match frozen protocol")
    paired_difference = _canonical_mean(
        [item.difference for item in primary.measurement_rows],
        f"{prefix}primary paired measurements",
    )
    reproduced_low, reproduced_high = _paired_ci_bounds([item.value for item in ci.group_differences])
    if protocol.primary_metric.direction == "lower_is_better":
        better = paired_difference < 0
        supported = reproduced_high < 0
    else:
        better = paired_difference > 0
        supported = reproduced_low > 0
    reasons = []
    if not better:
        reasons.append(f"{prefix}primary_not_strictly_better")
    if not supported:
        reasons.append(f"{prefix}primary_ci_does_not_support_improvement")
    return tuple(reasons)


def _profile_reasons(
    protocol: BenchmarkProtocolV1,
    run: BenchmarkRunV1,
    profile: BenchmarkCapabilityProfileV1,
) -> tuple[str, ...]:
    if (
        profile.dataset_fingerprint != protocol.dataset.dataset_fingerprint
        or profile.split_fingerprint != protocol.split.split_fingerprint
        or profile.group_set_fingerprint != protocol.split.test_group_set_fingerprint
        or tuple(sorted(item.unit_id for item in profile.selective_rows))
        != tuple(sorted(protocol.split.test_group_ids))
        or len(profile.selective_rows) != protocol.split.test_group_count
        or profile.candidate_model_fingerprint != run.candidate_model_fingerprint
        or profile.runtime_receipt_fingerprint != run.runtime_receipt_fingerprint
    ):
        raise BenchmarkSystemError("capability profile does not bind the frozen test evaluation")
    gate = protocol.promotion_gate
    reasons = []
    calibration = profile.calibration_error
    calibration_policy = protocol.calibration_policy
    if (
        calibration.metric_name != calibration_policy.metric_name
        or calibration.method != calibration_policy.method
        or calibration.configured_bins != calibration_policy.bins
        or calibration.evaluation_partition != calibration_policy.evaluation_partition
        or calibration.dataset_fingerprint != protocol.dataset.dataset_fingerprint
        or calibration.split_fingerprint != protocol.split.split_fingerprint
        or calibration.group_set_fingerprint != protocol.split.test_group_set_fingerprint
        or calibration.candidate_model_fingerprint != run.candidate_model_fingerprint
        or calibration.runtime_receipt_fingerprint != run.runtime_receipt_fingerprint
        or (
            calibration.available
            and sum(item.count for item in calibration.observed_bins) != protocol.split.test_group_count
        )
    ):
        raise BenchmarkSystemError("calibration result does not bind its frozen policy/evaluation")
    if not calibration.available:
        reasons.append(calibration.reason or "calibration_unavailable")
    elif calibration.value is None or calibration.value > gate.maximum_calibration_error:
        reasons.append("calibration_gate_failed")
    if profile.coverage < gate.minimum_coverage:
        reasons.append("coverage_gate_failed")
    if profile.selective_risk > gate.maximum_selective_risk:
        reasons.append("selective_risk_gate_failed")
    if profile.wrong_accept_rate > gate.maximum_wrong_accept_rate:
        reasons.append("wrong_accept_gate_failed")
    if profile.unnecessary_abstain_rate > gate.maximum_unnecessary_abstain_rate:
        reasons.append("unnecessary_abstain_gate_failed")

    policy_by_axis = {item.axis: item for item in protocol.ood_policy}
    result_by_axis = {item.axis: item for item in profile.ood_results}
    if set(policy_by_axis) != set(result_by_axis):
        raise BenchmarkSystemError("OOD result axes do not match frozen protocol")
    for axis, policy in policy_by_axis.items():
        result = result_by_axis[axis]
        if (
            result.metric_name != policy.metric_name
            or result.direction != policy.direction
            or result.evaluation_partition != "test"
            or result.dataset_fingerprint != protocol.dataset.dataset_fingerprint
            or result.split_fingerprint != protocol.split.split_fingerprint
            or result.group_set_fingerprint != protocol.split.test_group_set_fingerprint
            or (
                result.available
                and tuple(item.group_id for item in result.group_values) != tuple(sorted(protocol.split.test_group_ids))
            )
            or result.candidate_model_fingerprint != run.candidate_model_fingerprint
            or result.runtime_receipt_fingerprint != run.runtime_receipt_fingerprint
            or (result.available and len(result.group_values) != protocol.split.test_group_count)
        ):
            raise BenchmarkSystemError(f"OOD result {axis!r} does not bind its frozen policy/evaluation")
        if not result.available:
            reasons.append(result.reason or f"ood_{axis}_unavailable")
            continue
        assert result.value is not None
        passed = (
            result.value <= policy.threshold
            if policy.direction == "lower_is_better"
            else result.value >= policy.threshold
        )
        if not passed:
            reasons.append(f"ood_{axis}_gate_failed")
    return tuple(reasons)


def compute_p21b_execution_fingerprint(
    run: BenchmarkRunV1,
    result: BenchmarkResultV1,
) -> str:
    """Compute an identity for external trust lookup; this does not confer trust."""

    if type(run) is not BenchmarkRunV1 or type(result) is not BenchmarkResultV1:
        raise TypeError("run/result must be exact P21A contracts")
    run = BenchmarkRunV1.from_dict(run.to_dict())
    result = BenchmarkResultV1.from_dict(result.to_dict())
    if result.run_fingerprint != run.fingerprint():
        raise BenchmarkSystemError("P21B execution result does not bind its run")
    return _canonical_fingerprint(
        {
            "schema_version": "vc.p21b-execution-identity.v1",
            "authorization_fingerprint": run.authorization.fingerprint(),
            "run_fingerprint": run.fingerprint(),
            "result_fingerprint": result.fingerprint(),
        }
    )


def derive_evidence(
    protocol: BenchmarkProtocolV1,
    run: BenchmarkRunV1,
    result: BenchmarkResultV1,
    *,
    trusted_p21b_execution_fingerprint: str | None = None,
) -> BenchmarkPromotionEvidenceV1:
    """Derive benchmark/science/eligibility states without creating product policy."""

    if type(protocol) is not BenchmarkProtocolV1:
        raise TypeError("protocol must be exact BenchmarkProtocolV1")
    if type(run) is not BenchmarkRunV1:
        raise TypeError("run must be exact BenchmarkRunV1")
    if type(result) is not BenchmarkResultV1:
        raise TypeError("result must be exact BenchmarkResultV1")
    protocol = BenchmarkProtocolV1.from_dict(protocol.to_dict())
    run = BenchmarkRunV1.from_dict(run.to_dict())
    result = BenchmarkResultV1.from_dict(result.to_dict())
    protocol_fingerprint = protocol.fingerprint()
    run_fingerprint = run.fingerprint()
    result_fingerprint = result.fingerprint()
    if run.protocol_fingerprint != protocol_fingerprint:
        raise BenchmarkSystemError("run protocol fingerprint is stale")
    if run.authorization.scope_fingerprint != protocol.scope.fingerprint():
        raise BenchmarkSystemError("run authorization scope is stale")
    if run.pack_fingerprint != protocol.pack_fingerprint:
        raise BenchmarkSystemError("run Pack does not match frozen protocol")
    if (
        run.feature_contract_fingerprint != protocol.feature_contract_fingerprint
        or run.output_contract_fingerprint != protocol.output_contract_fingerprint
    ):
        raise BenchmarkSystemError("run feature/output contracts do not match frozen protocol")
    if run.seeds != protocol.seeds:
        raise BenchmarkSystemError("run seeds do not match frozen protocol")
    if result.protocol_fingerprint != protocol_fingerprint:
        raise BenchmarkSystemError("result protocol fingerprint is stale")
    if result.run_fingerprint != run_fingerprint:
        raise BenchmarkSystemError("result run fingerprint is stale")
    if result.candidate_model_fingerprint != run.candidate_model_fingerprint:
        raise BenchmarkSystemError("result candidate identity is stale")
    if result.runtime_receipt_fingerprint != run.runtime_receipt_fingerprint:
        raise BenchmarkSystemError("result runtime receipt is stale")

    reasons: list[str] = []

    def add(values: Sequence[str]) -> None:
        for value in values:
            if value not in reasons:
                reasons.append(value)

    if trusted_p21b_execution_fingerprint is not None:
        trusted_p21b_execution_fingerprint = _fingerprint(
            trusted_p21b_execution_fingerprint,
            "trusted_p21b_execution_fingerprint",
        )
    if run.evidence_class == "authorized_candidate":
        expected_execution = compute_p21b_execution_fingerprint(run, result)
        if trusted_p21b_execution_fingerprint is None:
            add(("p21b_execution_not_verified",))
        elif trusted_p21b_execution_fingerprint != expected_execution:
            raise BenchmarkSystemError("trusted P21B execution does not match exact authorization/run/result")
    elif trusted_p21b_execution_fingerprint is not None:
        raise BenchmarkSystemError("contract fixtures cannot consume a trusted P21B execution")

    if not run.compatibility_passed:
        add(("compatibility_failed",))

    if result.status != "completed":
        add(result.failure_reason_codes)
        add(("benchmark_run_not_completed",))
        benchmark_passed = False
    else:
        assert result.leakage_audit is not None
        assert result.threshold_receipt is not None
        assert result.primary is not None
        assert result.profile is not None
        _check_audit_binding(protocol, result.leakage_audit, "internal")
        if (
            result.threshold_receipt.selection_partition != protocol.threshold_policy.selection_partition
            or result.threshold_receipt.policy_fingerprint != protocol.threshold_policy.fingerprint()
            or result.threshold_receipt.minimum_coverage != protocol.threshold_policy.minimum_coverage
            or result.threshold_receipt.group_set_fingerprint != protocol.split.validation_group_set_fingerprint
            or result.threshold_receipt.total_units != protocol.split.validation_group_count
            or tuple(sorted(item.unit_id for item in result.threshold_receipt.selection_rows))
            != tuple(sorted(protocol.split.validation_group_ids))
        ):
            raise BenchmarkSystemError("threshold selection partition drifted from protocol")
        if result.threshold_receipt.coverage < protocol.threshold_policy.minimum_coverage:
            add(("threshold_minimum_coverage_not_met",))
        add(_primary_reasons(protocol, run, result.primary, partition="test"))
        add(result.failure_reason_codes)
        benchmark_passed = not reasons

    if run.evidence_class == "contract_fixture":
        add(("contract_fixture_not_evidence_eligible",))
        benchmark_passed = False

    external_reasons: list[str] = []
    if not benchmark_passed:
        external_reasons.append("benchmark_not_passed")
    if result.external is None:
        external_reasons.append("external_result_missing")
    else:
        external = result.external
        policy = protocol.external_policy
        _check_audit_binding(protocol, external.leakage_audit, "external")
        if external.dataset_fingerprint != policy.dataset_fingerprint:
            external_reasons.append("external_dataset_mismatch")
        if external.platform_fingerprint != policy.platform_fingerprint:
            external_reasons.append("external_platform_mismatch")
        if external.scope_fingerprint != policy.scope_fingerprint:
            external_reasons.append("external_scope_mismatch")
        if not external.independent_dataset:
            external_reasons.append("external_dataset_not_independent")
        if not external.independent_platform:
            external_reasons.append("external_platform_not_independent")
        if external.adaptation_steps != 0:
            external_reasons.append("external_adaptation_not_zero")
        if result.leakage_audit is not None and (
            external.leakage_audit.fingerprint() != result.leakage_audit.fingerprint()
        ):
            external_reasons.append("external_leakage_audit_mismatch")
        external_reasons.extend(_primary_reasons(protocol, run, external.primary, partition="external"))
    add(external_reasons)
    scientifically_validated = benchmark_passed and not external_reasons

    profile_reasons: tuple[str, ...] = ()
    if result.profile is not None:
        if result.profile.selected_threshold != result.threshold_receipt.threshold:
            raise BenchmarkSystemError("capability profile threshold drifted from validation receipt")
        profile_reasons = _profile_reasons(protocol, run, result.profile)
    else:
        profile_reasons = ("capability_profile_missing",)
    add(profile_reasons)
    if not scientifically_validated:
        add(("scientific_validation_not_passed",))
    promotion_eligible = scientifically_validated and not profile_reasons

    if not reasons:
        reasons.append("all_frozen_gates_passed")
    grade = (
        "promotion_eligible"
        if promotion_eligible
        else "external_validation"
        if scientifically_validated
        else "internal_benchmark"
        if benchmark_passed
        else "contract_only"
        if run.evidence_class == "contract_fixture"
        else "negative"
    )
    validation = ValidationEvidence(
        schema_version="vc.model-validation-evidence.v1",
        evidence_id=f"benchmark:{result.result_id}",
        pack_fingerprint=protocol.pack_fingerprint,
        model_fingerprint=run.candidate_model_fingerprint,
        environment_fingerprint=run.evaluation_environment_fingerprint,
        adapter_fingerprints=run.adapter_fingerprints,
        protocol_fingerprint=protocol_fingerprint,
        baseline_fingerprint=protocol.baseline.baseline_fingerprint,
        metric_name=protocol.primary_metric.name,
        metric_direction=protocol.primary_metric.direction,
        result_sha256=result_fingerprint,
        benchmark_passed=benchmark_passed,
        scientifically_validated=scientifically_validated,
        promotion_eligible=promotion_eligible,
        legacy_incomplete=False,
        binding_errors=(),
    )
    return BenchmarkPromotionEvidenceV1(
        schema_version="vc.benchmark-promotion-evidence.v1",
        evidence_id=f"p21a:{result.result_id}",
        protocol_fingerprint=protocol_fingerprint,
        run_fingerprint=run_fingerprint,
        result_fingerprint=result_fingerprint,
        profile_fingerprint=(
            result.profile.fingerprint() if result.profile is not None else _canonical_fingerprint(None)
        ),
        validation_evidence=validation,
        evidence_grade=grade,
        reason_codes=tuple(reasons),
    )


class BenchmarkEvidenceBundleV1(_Contract):
    """Self-contained untrusted bundle; authorization trust stays out-of-band."""

    schema_version: Literal["vc.benchmark-evidence-bundle.v1"]
    protocol: BenchmarkProtocolV1
    run: BenchmarkRunV1
    result: BenchmarkResultV1
    evidence: BenchmarkPromotionEvidenceV1

    @model_validator(mode="after")
    def _evidence_is_reproducible(self):
        expected = derive_evidence(
            self.protocol,
            self.run,
            self.result,
        )
        if self.evidence.fingerprint() != expected.fingerprint():
            raise ValueError("bundle evidence is not reproducible from protocol/run/result")
        return self

    @classmethod
    def from_components(
        cls,
        protocol: BenchmarkProtocolV1,
        run: BenchmarkRunV1,
        result: BenchmarkResultV1,
    ) -> BenchmarkEvidenceBundleV1:
        evidence = derive_evidence(protocol, run, result)
        return cls(
            schema_version="vc.benchmark-evidence-bundle.v1",
            protocol=BenchmarkProtocolV1.from_dict(protocol.to_dict()),
            run=BenchmarkRunV1.from_dict(run.to_dict()),
            result=BenchmarkResultV1.from_dict(result.to_dict()),
            evidence=evidence,
        )

    def derive_with_p21b_execution(
        self,
        *,
        trusted_p21b_execution_fingerprint: str,
    ) -> BenchmarkPromotionEvidenceV1:
        """Verify exact run/result identities pinned independently by the P21B consumer."""

        return derive_evidence(
            self.protocol,
            self.run,
            self.result,
            trusted_p21b_execution_fingerprint=trusted_p21b_execution_fingerprint,
        )


class BenchmarkLedgerEntryV1(_Contract):
    schema_version: Literal["vc.benchmark-evidence-ledger-entry.v1"]
    sequence: int
    previous_entry_fingerprint: str | None
    record_fingerprint: str
    record: BenchmarkEvidenceBundleV1 | LegacyMigrationReceipt

    @field_validator("sequence", mode="before")
    @classmethod
    def _valid_sequence(cls, value):
        return _positive_int(value, "sequence")

    @field_validator("previous_entry_fingerprint", mode="before")
    @classmethod
    def _valid_previous(cls, value):
        return None if value is None else _fingerprint(value, "previous_entry_fingerprint")

    @field_validator("record_fingerprint", mode="before")
    @classmethod
    def _valid_record_fingerprint(cls, value):
        return _fingerprint(value, "record_fingerprint")

    @model_validator(mode="after")
    def _record_is_bound(self):
        if self.record.fingerprint() != self.record_fingerprint:
            raise ValueError("ledger record fingerprint is stale")
        if (self.sequence == 1) != (self.previous_entry_fingerprint is None):
            raise ValueError("only the first ledger entry may omit its predecessor")
        return self


class BenchmarkLedgerHeadV1(_Contract):
    schema_version: Literal["vc.benchmark-evidence-ledger-head.v1"]
    entry_count: int
    last_entry_fingerprint: str | None

    @field_validator("entry_count", mode="before")
    @classmethod
    def _valid_count(cls, value):
        return _nonnegative_int(value, "entry_count")

    @field_validator("last_entry_fingerprint", mode="before")
    @classmethod
    def _valid_last(cls, value):
        return None if value is None else _fingerprint(value, "last_entry_fingerprint")

    @model_validator(mode="after")
    def _consistent_empty_state(self):
        if (self.entry_count == 0) != (self.last_entry_fingerprint is None):
            raise ValueError("empty ledger head must be the only head without a tail")
        return self


def _ledger_record_id(record: BenchmarkEvidenceBundleV1 | LegacyMigrationReceipt) -> str:
    return record.evidence.evidence_id if type(record) is BenchmarkEvidenceBundleV1 else record.receipt_id


def _validated_negative_record(
    record: BenchmarkEvidenceBundleV1 | LegacyMigrationReceipt,
) -> BenchmarkEvidenceBundleV1 | LegacyMigrationReceipt:
    if type(record) is BenchmarkEvidenceBundleV1:
        if record.evidence.validation_evidence.promotion_eligible:
            raise BenchmarkSystemError("negative ledger rejects promotion-eligible evidence")
        value = BenchmarkEvidenceBundleV1.from_dict(record.to_dict())
        if value.run.evidence_class != "authorized_candidate":
            raise BenchmarkSystemError("negative ledger rejects contract-only fixtures")
        return value
    if type(record) is LegacyMigrationReceipt:
        value = LegacyMigrationReceipt.from_dict(record.to_dict())
        if value.fingerprint() != _P9_RECEIPT_FINGERPRINT:
            raise BenchmarkSystemError("negative ledger accepts only the exact P9 legacy negative receipt")
        return value
    raise TypeError("record must be an exact benchmark bundle or P9 legacy negative receipt")


@dataclass(frozen=True)
class StoredBenchmarkEvidence:
    entry: BenchmarkLedgerEntryV1
    path: Path

    @property
    def sequence(self) -> int:
        return self.entry.sequence

    @property
    def previous_entry_fingerprint(self) -> str | None:
        return self.entry.previous_entry_fingerprint

    @property
    def record_fingerprint(self) -> str:
        return self.entry.record_fingerprint

    @property
    def entry_fingerprint(self) -> str:
        return self.entry.fingerprint()


def _read_regular(path: Path, *, label: str, max_bytes: int = _MAX_CONTRACT_BYTES) -> bytes:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise BenchmarkSystemError(f"cannot read {label} as a regular non-symlink file") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size > max_bytes:
            raise BenchmarkSystemError(f"{label} must be a bounded regular file")
        payload = _read_descriptor(descriptor, max_bytes=max_bytes)
        after = os.fstat(descriptor)
        if len(payload) != before.st_size or (
            before.st_dev,
            before.st_ino,
            before.st_size,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
        ):
            raise BenchmarkSystemError(f"{label} changed while being read")
        return payload
    finally:
        os.close(descriptor)


def _read_descriptor(descriptor: int, *, max_bytes: int) -> bytes:
    chunks = []
    remaining = max_bytes + 1
    while remaining:
        chunk = os.read(descriptor, min(65536, remaining))
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    payload = b"".join(chunks)
    if len(payload) > max_bytes:
        raise BenchmarkSystemError("contract file exceeds its byte ceiling")
    return payload


def _read_regular_at(
    parent_descriptor: int,
    name: str,
    *,
    label: str,
    max_bytes: int = _MAX_CONTRACT_BYTES,
) -> bytes:
    if not isinstance(name, str) or not name or "/" in name or "\x00" in name:
        raise BenchmarkSystemError(f"{label} name is not a safe basename")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(name, flags, dir_fd=parent_descriptor)
    except OSError as exc:
        raise BenchmarkSystemError(f"cannot read {label} as a regular non-symlink file") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size > max_bytes:
            raise BenchmarkSystemError(f"{label} must be a bounded regular file")
        payload = _read_descriptor(descriptor, max_bytes=max_bytes)
        after = os.fstat(descriptor)
        if len(payload) != before.st_size or (
            before.st_dev,
            before.st_ino,
            before.st_size,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
        ):
            raise BenchmarkSystemError(f"{label} changed while being read")
        return payload
    finally:
        os.close(descriptor)


def _read_identity(path: Path, *, size: int, sha256: str, label: str) -> bytes:
    payload = _read_regular(path, label=label)
    if len(payload) != size or hashlib.sha256(payload).hexdigest() != sha256:
        raise BenchmarkSystemError(f"{label} identity does not match the checked-in contract")
    return payload


def _atomic_publish_directory(
    source: Path,
    target: Path,
    *,
    parent_descriptor: int,
    source_descriptor: int,
    source_identity: tuple[int, int],
) -> None:
    held = os.fstat(source_descriptor)
    try:
        named = os.stat(
            source.name,
            dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
    except OSError as exc:
        raise BenchmarkSystemError("ledger staging directory is unavailable") from exc
    if (
        source.parent != target.parent
        or not stat.S_ISDIR(held.st_mode)
        or not stat.S_ISDIR(named.st_mode)
        or (held.st_dev, held.st_ino) != source_identity
        or (named.st_dev, named.st_ino) != source_identity
    ):
        raise BenchmarkSystemError("ledger staging directory identity changed")
    libc = ctypes.CDLL(None, use_errno=True)
    source_bytes = os.fsencode(source.name)
    target_bytes = os.fsencode(target.name)
    if sys.platform == "darwin":
        try:
            operation = libc.renameatx_np
        except AttributeError as exc:  # pragma: no cover - unsupported Darwin runtime
            raise BenchmarkSystemError("atomic no-replace ledger creation is unavailable") from exc
        operation.argtypes = (
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        )
        operation.restype = ctypes.c_int
        result = operation(
            parent_descriptor,
            source_bytes,
            parent_descriptor,
            target_bytes,
            0x00000004,
        )
    elif sys.platform.startswith("linux"):
        try:
            operation = libc.renameat2
        except AttributeError as exc:  # pragma: no cover - old libc fails closed
            raise BenchmarkSystemError("atomic no-replace ledger creation is unavailable") from exc
        operation.argtypes = (
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        )
        operation.restype = ctypes.c_int
        result = operation(
            parent_descriptor,
            source_bytes,
            parent_descriptor,
            target_bytes,
            1,
        )
    else:  # pragma: no cover - unsupported platforms fail closed
        raise BenchmarkSystemError("atomic no-replace ledger creation is unavailable")
    if result == 0:
        try:
            published = os.stat(
                target.name,
                dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
        except OSError as exc:
            raise BenchmarkSystemError("published ledger root is unavailable") from exc
        if not stat.S_ISDIR(published.st_mode) or (published.st_dev, published.st_ino) != source_identity:
            raise BenchmarkSystemError("published ledger root identity changed")
        return
    error = ctypes.get_errno()
    if error in {errno.EEXIST, errno.ENOTEMPTY}:
        raise BenchmarkSystemError("ledger root must be write-new")
    raise BenchmarkSystemError("atomic ledger creation failed") from OSError(
        error,
        os.strerror(error),
    )


class BenchmarkEvidenceLedger:
    """Write-new, content-addressed, append-only storage for negative evidence."""

    def __init__(self, root: Path) -> None:
        if not isinstance(root, Path) or not root.is_absolute():
            raise BenchmarkSystemError("ledger root must be an explicit absolute Path")
        if root.is_symlink():
            raise BenchmarkSystemError("ledger root must not be a symlink")
        try:
            resolved = root.resolve(strict=True)
            root_stat = root.stat()
        except OSError as exc:
            raise BenchmarkSystemError("ledger root does not exist") from exc
        if resolved != root or not stat.S_ISDIR(root_stat.st_mode):
            raise BenchmarkSystemError("ledger root must be a canonical real directory")
        entries = root / "entries"
        if entries.is_symlink():
            raise BenchmarkSystemError("ledger entries directory must not be a symlink")
        try:
            entries_stat = entries.stat()
        except OSError as exc:
            raise BenchmarkSystemError("ledger entries directory is unavailable") from exc
        if not stat.S_ISDIR(entries_stat.st_mode) or entries.resolve(strict=True).parent != root:
            raise BenchmarkSystemError("ledger entries directory escapes its root")
        marker = _read_regular(root / _LEDGER_MARKER, label="ledger marker")
        if marker != _LEDGER_MARKER_BYTES:
            raise BenchmarkSystemError("ledger marker is invalid")
        head_payload = _read_regular(root / _LEDGER_HEAD, label="ledger head")
        head = BenchmarkLedgerHeadV1.from_dict(_json_object_bytes(head_payload, "ledger head"))
        if head_payload != _canonical_bytes(head.to_dict()) + b"\n":
            raise BenchmarkSystemError("ledger head is not canonical")
        lock_path = root / ".ledger.lock"
        if lock_path.is_symlink():
            raise BenchmarkSystemError("ledger lock must not be a symlink")
        try:
            lock_stat = lock_path.stat()
        except OSError as exc:
            raise BenchmarkSystemError("ledger lock is unavailable") from exc
        if not stat.S_ISREG(lock_stat.st_mode):
            raise BenchmarkSystemError("ledger lock must be a regular file")
        self.root = root
        self._root_identity = (root_stat.st_dev, root_stat.st_ino)
        self._entries_identity = (entries_stat.st_dev, entries_stat.st_ino)
        self._lock_identity = (lock_stat.st_dev, lock_stat.st_ino)

    @classmethod
    def create(cls, root: str | Path) -> BenchmarkEvidenceLedger:
        path = Path(root)
        if not path.is_absolute():
            raise BenchmarkSystemError("ledger root must be an explicit absolute path")
        parent = path.parent
        if parent.is_symlink():
            raise BenchmarkSystemError("ledger parent must not be a symlink")
        try:
            if parent.resolve(strict=True) != parent or not parent.is_dir() or path.resolve(strict=False) != path:
                raise BenchmarkSystemError("ledger parent must be canonical")
            if path.exists() or path.is_symlink():
                raise BenchmarkSystemError("ledger root must be write-new")
        except BenchmarkSystemError:
            raise
        except OSError as exc:
            raise BenchmarkSystemError("ledger parent is unavailable") from exc
        directory_flags = os.O_RDONLY
        if hasattr(os, "O_DIRECTORY"):
            directory_flags |= os.O_DIRECTORY
        if hasattr(os, "O_NOFOLLOW"):
            directory_flags |= os.O_NOFOLLOW
        try:
            parent_descriptor = os.open(parent, directory_flags)
        except OSError as exc:
            raise BenchmarkSystemError("ledger parent cannot be held safely") from exc
        staging = None
        staging_descriptor = None
        staging_identity = None
        try:
            staging = Path(
                tempfile.mkdtemp(
                    prefix=f".{path.name}.benchmark-ledger-",
                    dir=parent,
                )
            )
            created = staging.lstat()
            staging_identity = (created.st_dev, created.st_ino)
            staging_descriptor = os.open(staging, directory_flags)
            held = os.fstat(staging_descriptor)
            named = os.stat(
                staging.name,
                dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
            if (
                not stat.S_ISDIR(created.st_mode)
                or (held.st_dev, held.st_ino) != staging_identity
                or (named.st_dev, named.st_ino) != staging_identity
            ):
                raise BenchmarkSystemError("ledger staging directory identity is unstable")
            os.mkdir("entries", mode=0o700, dir_fd=staging_descriptor)
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            descriptor = os.open(
                _LEDGER_MARKER,
                flags,
                0o600,
                dir_fd=staging_descriptor,
            )
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(_LEDGER_MARKER_BYTES)
                stream.flush()
                os.fsync(stream.fileno())
            head = BenchmarkLedgerHeadV1(
                schema_version="vc.benchmark-evidence-ledger-head.v1",
                entry_count=0,
                last_entry_fingerprint=None,
            )
            descriptor = os.open(
                _LEDGER_HEAD,
                flags,
                0o600,
                dir_fd=staging_descriptor,
            )
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(_canonical_bytes(head.to_dict()) + b"\n")
                stream.flush()
                os.fsync(stream.fileno())
            lock_descriptor = os.open(
                ".ledger.lock",
                flags,
                0o600,
                dir_fd=staging_descriptor,
            )
            try:
                os.fsync(lock_descriptor)
            finally:
                os.close(lock_descriptor)
            entries_descriptor = os.open(
                "entries",
                directory_flags,
                dir_fd=staging_descriptor,
            )
            try:
                os.fsync(entries_descriptor)
            finally:
                os.close(entries_descriptor)
            os.fsync(staging_descriptor)
            os.fsync(parent_descriptor)
            _atomic_publish_directory(
                staging,
                path,
                parent_descriptor=parent_descriptor,
                source_descriptor=staging_descriptor,
                source_identity=staging_identity,
            )
            try:
                os.fsync(parent_descriptor)
            except OSError:
                pass
        except BenchmarkSystemError:
            raise
        except OSError as exc:
            raise BenchmarkSystemError("cannot initialize ledger") from exc
        finally:
            if staging_descriptor is not None:
                os.close(staging_descriptor)
            os.close(parent_descriptor)
        ledger = cls(path.resolve(strict=True))
        if staging_identity is None or ledger._root_identity != staging_identity:
            raise BenchmarkSystemError("published ledger root no longer matches held staging identity")
        return ledger

    @classmethod
    def open(cls, root: str | Path) -> BenchmarkEvidenceLedger:
        path = Path(root)
        if not path.is_absolute():
            raise BenchmarkSystemError("ledger root must be an explicit absolute path")
        if path.is_symlink():
            raise BenchmarkSystemError("ledger root must not be a symlink")
        try:
            resolved = path.resolve(strict=True)
        except OSError as exc:
            raise BenchmarkSystemError("ledger root does not exist") from exc
        return cls(resolved)

    @property
    def _entries(self) -> Path:
        return self.root / "entries"

    @contextmanager
    def _held_layout(self):
        directory_flags = os.O_RDONLY
        if hasattr(os, "O_DIRECTORY"):
            directory_flags |= os.O_DIRECTORY
        if hasattr(os, "O_NOFOLLOW"):
            directory_flags |= os.O_NOFOLLOW
        try:
            root_descriptor = os.open(self.root, directory_flags)
        except OSError as exc:
            raise BenchmarkSystemError("ledger root cannot be held safely") from exc
        entries_descriptor = None
        try:
            root_stat = os.fstat(root_descriptor)
            if (root_stat.st_dev, root_stat.st_ino) != self._root_identity:
                raise BenchmarkSystemError("ledger root identity changed")
            entries_descriptor = os.open("entries", directory_flags, dir_fd=root_descriptor)
            entries_stat = os.fstat(entries_descriptor)
            if (entries_stat.st_dev, entries_stat.st_ino) != self._entries_identity:
                raise BenchmarkSystemError("ledger entries identity changed")
            marker = _read_regular_at(root_descriptor, _LEDGER_MARKER, label="ledger marker")
            if marker != _LEDGER_MARKER_BYTES:
                raise BenchmarkSystemError("ledger marker changed")
            yield root_descriptor, entries_descriptor
        finally:
            if entries_descriptor is not None:
                os.close(entries_descriptor)
            os.close(root_descriptor)

    def _load_head_at(self, root_descriptor: int) -> BenchmarkLedgerHeadV1:
        payload = _read_regular_at(
            root_descriptor,
            _LEDGER_HEAD,
            label="ledger head",
        )
        head = BenchmarkLedgerHeadV1.from_dict(_json_object_bytes(payload, "ledger head"))
        if payload != _canonical_bytes(head.to_dict()) + b"\n":
            raise BenchmarkSystemError("ledger head bytes are not canonical")
        return head

    def _write_head_at(
        self,
        root_descriptor: int,
        head: BenchmarkLedgerHeadV1,
    ) -> None:
        head = BenchmarkLedgerHeadV1.from_dict(head.to_dict())
        payload = _canonical_bytes(head.to_dict()) + b"\n"
        temporary_name = f".head-staging-{os.urandom(16).hex()}.tmp"
        if not _HEAD_STAGING_NAME.fullmatch(temporary_name):  # pragma: no cover
            raise BenchmarkSystemError("ledger head staging name is invalid")
        flags = os.O_RDWR | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = None
        try:
            descriptor = os.open(
                temporary_name,
                flags,
                0o600,
                dir_fd=root_descriptor,
            )
            with os.fdopen(os.dup(descriptor), "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            held = os.fstat(descriptor)
            os.lseek(descriptor, 0, os.SEEK_SET)
            if _read_descriptor(descriptor, max_bytes=_MAX_CONTRACT_BYTES) != payload:
                raise BenchmarkSystemError("staged ledger head changed")
            named = os.stat(
                temporary_name,
                dir_fd=root_descriptor,
                follow_symlinks=False,
            )
            if not stat.S_ISREG(held.st_mode) or (named.st_dev, named.st_ino, named.st_size) != (
                held.st_dev,
                held.st_ino,
                held.st_size,
            ):
                raise BenchmarkSystemError("staged ledger head identity changed")
            os.replace(
                temporary_name,
                _LEDGER_HEAD,
                src_dir_fd=root_descriptor,
                dst_dir_fd=root_descriptor,
            )
            if self._load_head_at(root_descriptor) != head:
                raise BenchmarkSystemError("published ledger head identity changed")
            try:
                os.fsync(root_descriptor)
            except OSError as exc:
                raise BenchmarkSystemError("ledger head committed but directory durability is uncertain") from exc
        except BenchmarkSystemError:
            raise
        except OSError as exc:
            raise BenchmarkSystemError("cannot update ledger head") from exc
        finally:
            if descriptor is not None:
                os.close(descriptor)
            try:
                os.unlink(temporary_name, dir_fd=root_descriptor)
            except FileNotFoundError:
                pass

    def _load_entry_at(self, entries_descriptor: int, name: str) -> StoredBenchmarkEvidence:
        payload = _read_regular_at(entries_descriptor, name, label="ledger entry")
        raw = _json_object_bytes(payload, "ledger entry")
        entry = BenchmarkLedgerEntryV1.from_dict(raw)
        canonical = _canonical_bytes(entry.to_dict()) + b"\n"
        if payload != canonical:
            raise BenchmarkSystemError("ledger entry bytes are not canonical")
        expected = f"{entry.sequence:08d}-{entry.fingerprint()}.json"
        if name != expected:
            raise BenchmarkSystemError("ledger entry filename and content identity disagree")
        return StoredBenchmarkEvidence(entry=entry, path=self._entries / name)

    def _verify_held(
        self,
        root_descriptor: int,
        entries_descriptor: int,
        *,
        recover_unanchored_tail: bool = False,
    ) -> tuple[StoredBenchmarkEvidence, ...]:
        names = []
        for name in os.listdir(entries_descriptor):
            try:
                metadata = os.stat(name, dir_fd=entries_descriptor, follow_symlinks=False)
            except OSError as exc:
                raise BenchmarkSystemError("ledger entry metadata is unavailable") from exc
            if name.startswith(".staging-"):
                if not _STAGING_NAME.fullmatch(name) or not stat.S_ISREG(metadata.st_mode):
                    raise BenchmarkSystemError("ledger contains an invalid staging path")
                continue
            if not name.endswith(".json") or not stat.S_ISREG(metadata.st_mode):
                raise BenchmarkSystemError("ledger entries contain an unexpected path")
            names.append(name)
        stored = tuple(self._load_entry_at(entries_descriptor, name) for name in sorted(names))
        previous = None
        logical_ids = set()
        nested_ids = set()
        result_fingerprints = set()
        run_fingerprints = set()
        authorization_fingerprints = set()
        protocol_identities: dict[str, str] = {}
        run_identities: dict[str, str] = {}
        authorization_identities: dict[str, str] = {}
        record_fingerprints = set()
        for sequence, item in enumerate(stored, start=1):
            if item.sequence != sequence or item.previous_entry_fingerprint != previous:
                raise BenchmarkSystemError("ledger sequence or predecessor chain is broken")
            record = _validated_negative_record(item.entry.record)
            logical_id = _ledger_record_id(record)
            if logical_id in logical_ids:
                raise BenchmarkSystemError("ledger contains conflicting logical IDs")
            if item.record_fingerprint in record_fingerprints:
                raise BenchmarkSystemError("ledger contains a duplicate evidence record")
            if type(record) is BenchmarkEvidenceBundleV1:
                nested_id = record.evidence.validation_evidence.evidence_id
                result_fingerprint = record.result.fingerprint()
                run_fingerprint = record.run.fingerprint()
                protocol_fingerprint = record.protocol.fingerprint()
                authorization = record.run.authorization
                authorization_fingerprint = authorization.fingerprint()
                if nested_id in nested_ids or result_fingerprint in result_fingerprints:
                    raise BenchmarkSystemError("ledger contains a duplicate result identity")
                if run_fingerprint in run_fingerprints:
                    raise BenchmarkSystemError("one benchmark run cannot bind multiple results")
                for identities, logical_id, fingerprint, label in (
                    (
                        protocol_identities,
                        record.protocol.protocol_id,
                        protocol_fingerprint,
                        "protocol",
                    ),
                    (run_identities, record.run.run_id, run_fingerprint, "run"),
                    (
                        authorization_identities,
                        authorization.authorization_id,
                        authorization_fingerprint,
                        "authorization",
                    ),
                ):
                    previous_identity = identities.get(logical_id)
                    if previous_identity is not None and previous_identity != fingerprint:
                        raise BenchmarkSystemError(f"ledger {label} ID binds conflicting content")
                    identities[logical_id] = fingerprint
                if authorization_fingerprint in authorization_fingerprints:
                    raise BenchmarkSystemError("one P21B authorization cannot bind multiple runs")
                nested_ids.add(nested_id)
                result_fingerprints.add(result_fingerprint)
                run_fingerprints.add(run_fingerprint)
                authorization_fingerprints.add(authorization_fingerprint)
            logical_ids.add(logical_id)
            record_fingerprints.add(item.record_fingerprint)
            previous = item.entry_fingerprint
        head = self._load_head_at(root_descriptor)
        expected_tail = stored[-1].entry_fingerprint if stored else None
        if head.entry_count != len(stored) or head.last_entry_fingerprint != expected_tail:
            prior_tail = stored[-2].entry_fingerprint if len(stored) > 1 else None
            if not (
                recover_unanchored_tail
                and head.entry_count == len(stored) - 1
                and head.last_entry_fingerprint == prior_tail
            ):
                raise BenchmarkSystemError("ledger head detects truncation or an unanchored tail")
            self._write_head_at(
                root_descriptor,
                BenchmarkLedgerHeadV1(
                    schema_version="vc.benchmark-evidence-ledger-head.v1",
                    entry_count=len(stored),
                    last_entry_fingerprint=expected_tail,
                ),
            )
        return stored

    def verify(self) -> tuple[StoredBenchmarkEvidence, ...]:
        with self._held_layout() as (root_descriptor, entries_descriptor):
            return self._verify_held(root_descriptor, entries_descriptor)

    def append(
        self,
        record: BenchmarkEvidenceBundleV1 | LegacyMigrationReceipt,
    ) -> StoredBenchmarkEvidence:
        record = _validated_negative_record(record)
        flags = os.O_RDWR
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        with self._held_layout() as (root_descriptor, entries_descriptor):
            try:
                descriptor = os.open(".ledger.lock", flags, dir_fd=root_descriptor)
            except OSError as exc:
                raise BenchmarkSystemError("ledger lock is unavailable") from exc
            with os.fdopen(descriptor, "a+b") as lock:
                if not stat.S_ISREG(os.fstat(lock.fileno()).st_mode):
                    raise BenchmarkSystemError("ledger lock must be a regular file")
                lock_stat = os.fstat(lock.fileno())
                if (lock_stat.st_dev, lock_stat.st_ino) != self._lock_identity:
                    raise BenchmarkSystemError("ledger lock identity changed")
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
                held_entries = os.fstat(entries_descriptor)
                if (held_entries.st_dev, held_entries.st_ino) != self._entries_identity:
                    raise BenchmarkSystemError("ledger entries identity changed while locked")
                stored = self._verify_held(
                    root_descriptor,
                    entries_descriptor,
                    recover_unanchored_tail=True,
                )
                record_fingerprint = record.fingerprint()
                for item in stored:
                    if item.record_fingerprint == record_fingerprint:
                        os.fsync(entries_descriptor)
                        return item
                    if _ledger_record_id(item.entry.record) == _ledger_record_id(record):
                        raise BenchmarkSystemError("logical record ID already binds different bytes")
                    if (
                        type(record) is BenchmarkEvidenceBundleV1
                        and type(item.entry.record) is BenchmarkEvidenceBundleV1
                    ):
                        existing = item.entry.record
                        if (
                            existing.evidence.validation_evidence.evidence_id
                            == record.evidence.validation_evidence.evidence_id
                            or existing.result.fingerprint() == record.result.fingerprint()
                        ):
                            raise BenchmarkSystemError("result identity already exists")
                        if existing.run.fingerprint() == record.run.fingerprint():
                            raise BenchmarkSystemError("benchmark run already has a result")
                        if (
                            existing.protocol.protocol_id == record.protocol.protocol_id
                            and existing.protocol.fingerprint() != record.protocol.fingerprint()
                        ):
                            raise BenchmarkSystemError("protocol ID already binds different content")
                        if (
                            existing.run.run_id == record.run.run_id
                            and existing.run.fingerprint() != record.run.fingerprint()
                        ):
                            raise BenchmarkSystemError("run ID already binds different content")
                        existing_authorization = existing.run.authorization
                        authorization = record.run.authorization
                        if (
                            existing_authorization.authorization_id == authorization.authorization_id
                            and existing_authorization.fingerprint() != authorization.fingerprint()
                        ):
                            raise BenchmarkSystemError("authorization ID already binds different content")
                        if existing_authorization.fingerprint() == authorization.fingerprint():
                            raise BenchmarkSystemError("P21B authorization already binds another run")
                previous = stored[-1].entry_fingerprint if stored else None
                entry = BenchmarkLedgerEntryV1(
                    schema_version="vc.benchmark-evidence-ledger-entry.v1",
                    sequence=len(stored) + 1,
                    previous_entry_fingerprint=previous,
                    record_fingerprint=record_fingerprint,
                    record=record,
                )
                payload = _canonical_bytes(entry.to_dict()) + b"\n"
                target_name = f"{entry.sequence:08d}-{entry.fingerprint()}.json"
                temporary_name = f".staging-{os.urandom(16).hex()}.tmp"
                temporary_flags = os.O_RDWR | os.O_CREAT | os.O_EXCL
                if hasattr(os, "O_NOFOLLOW"):
                    temporary_flags |= os.O_NOFOLLOW
                temporary_descriptor = None
                try:
                    temporary_descriptor = os.open(
                        temporary_name,
                        temporary_flags,
                        0o600,
                        dir_fd=entries_descriptor,
                    )
                    with os.fdopen(os.dup(temporary_descriptor), "wb") as stream:
                        stream.write(payload)
                        stream.flush()
                        os.fsync(stream.fileno())
                    held = os.fstat(temporary_descriptor)
                    os.lseek(temporary_descriptor, 0, os.SEEK_SET)
                    if (
                        _read_descriptor(
                            temporary_descriptor,
                            max_bytes=_MAX_CONTRACT_BYTES,
                        )
                        != payload
                    ):
                        raise BenchmarkSystemError("staged ledger entry changed")
                    named = os.stat(
                        temporary_name,
                        dir_fd=entries_descriptor,
                        follow_symlinks=False,
                    )
                    if not stat.S_ISREG(held.st_mode) or (named.st_dev, named.st_ino, named.st_size) != (
                        held.st_dev,
                        held.st_ino,
                        held.st_size,
                    ):
                        raise BenchmarkSystemError("staged ledger entry identity changed")
                    try:
                        os.link(
                            temporary_name,
                            target_name,
                            src_dir_fd=entries_descriptor,
                            dst_dir_fd=entries_descriptor,
                            follow_symlinks=False,
                        )
                    except FileExistsError as exc:
                        raise BenchmarkSystemError("ledger destination collision was not overwritten") from exc
                    except OSError as exc:
                        raise BenchmarkSystemError("cannot append benchmark evidence") from exc
                    published = os.stat(
                        target_name,
                        dir_fd=entries_descriptor,
                        follow_symlinks=False,
                    )
                    if not stat.S_ISREG(published.st_mode) or (
                        published.st_dev,
                        published.st_ino,
                        published.st_size,
                    ) != (held.st_dev, held.st_ino, held.st_size):
                        raise BenchmarkSystemError("published ledger entry identity changed")
                    try:
                        os.fsync(entries_descriptor)
                    except OSError as exc:
                        raise BenchmarkSystemError(
                            "ledger entry committed but directory durability is uncertain"
                        ) from exc
                    self._write_head_at(
                        root_descriptor,
                        BenchmarkLedgerHeadV1(
                            schema_version="vc.benchmark-evidence-ledger-head.v1",
                            entry_count=entry.sequence,
                            last_entry_fingerprint=entry.fingerprint(),
                        ),
                    )
                finally:
                    if temporary_descriptor is not None:
                        os.close(temporary_descriptor)
                    try:
                        os.unlink(temporary_name, dir_fd=entries_descriptor)
                    except FileNotFoundError:
                        pass
                loaded = self._load_entry_at(entries_descriptor, target_name)
                if loaded.entry_fingerprint != entry.fingerprint():
                    raise BenchmarkSystemError("published ledger entry identity changed")
                return loaded


def _repository_root(value: str | Path) -> Path:
    root = Path(value)
    if not root.is_absolute():
        raise BenchmarkSystemError("repository root must be an explicit absolute path")
    if root.is_symlink():
        raise BenchmarkSystemError("repository root must not be a symlink")
    try:
        resolved = root.resolve(strict=True)
    except OSError as exc:
        raise BenchmarkSystemError("repository root does not exist") from exc
    if resolved != root or not root.is_dir():
        raise BenchmarkSystemError("repository root must be a canonical real directory")
    return root


def replay_checked_in_benchmarks(repository_root: str | Path) -> tuple[LegacyMigrationReceipt, ...]:
    """Replay only the checked-in P8 inventory and frozen P9 negative receipt."""

    root = _repository_root(repository_root)
    fixture_payload = _read_identity(
        root / _LEGACY_FIXTURE,
        size=_LEGACY_FIXTURE_SIZE,
        sha256=_LEGACY_FIXTURE_SHA256,
        label="legacy replay fixture",
    )
    fixture = _json_object_bytes(fixture_payload, "legacy replay fixture")
    if fixture.get("schema_version") != "vc.model-registry-legacy-migration-fixture.v1":
        raise BenchmarkSystemError("legacy replay fixture schema is unsupported")
    raw_receipts = fixture.get("receipts")
    if not isinstance(raw_receipts, list) or len(raw_receipts) != 2:
        raise BenchmarkSystemError("legacy replay fixture must contain exactly P8 and P9 receipts")
    receipts = tuple(LegacyMigrationReceipt.from_dict(item) for item in raw_receipts)
    if tuple(item.source_path for item in receipts) != (str(_P8_PATH), str(_P9_PATH)):
        raise BenchmarkSystemError("legacy replay sources are not the frozen P8/P9 pair")

    p8, p9 = receipts
    p8_payload = _read_identity(root / _P8_PATH, size=_P8_SIZE, sha256=_P8_SHA256, label="P8 manifest")
    p9_payload = _read_identity(root / _P9_PATH, size=_P9_SIZE, sha256=_P9_SHA256, label="P9 result")
    p9_manifest_payload = _read_identity(
        root / _P9_MANIFEST_PATH,
        size=_P9_MANIFEST_SIZE,
        sha256=_P9_MANIFEST_SHA256,
        label="P9 manifest",
    )
    if (p8.size_bytes, p8.sha256, p9.size_bytes, p9.sha256) != (
        _P8_SIZE,
        _P8_SHA256,
        _P9_SIZE,
        _P9_SHA256,
    ):
        raise BenchmarkSystemError("legacy receipt identity does not match its checked-in source")

    p8_source = _json_object_bytes(p8_payload, "P8 manifest")
    if (
        p8_source.get("schema_version") != "vc.golden-artifact-manifest.v1"
        or not isinstance(p8_source.get("pack"), dict)
        or p8.declared_pack_fingerprint != p8_source["pack"].get("fingerprint")
        or not isinstance(p8_source.get("states"), dict)
        or p8_source["states"].get("scientifically_validated") is not False
        or p8.available is not None
        or p8.benchmark_passed is not None
        or p8.scientifically_validated is not False
        or p8.promotion_eligible is not None
    ):
        raise BenchmarkSystemError("P8 replay must remain an unbound historical inventory")

    try:
        p9_source = load_validation_artifact(
            root / _P9_PATH,
            manifest_path=root / _P9_MANIFEST_PATH,
        )
    except (OODValidationError, OSError, ValueError) as exc:
        raise BenchmarkSystemError(f"P9 negative replay failed strict validation: {exc}") from exc
    if (
        _read_identity(
            root / _P9_PATH,
            size=_P9_SIZE,
            sha256=_P9_SHA256,
            label="P9 result",
        )
        != p9_payload
        or _read_identity(
            root / _P9_MANIFEST_PATH,
            size=_P9_MANIFEST_SIZE,
            sha256=_P9_MANIFEST_SHA256,
            label="P9 manifest",
        )
        != p9_manifest_payload
    ):
        raise BenchmarkSystemError("P9 replay files changed during validation")
    status = p9_source.get("status")
    if (
        not isinstance(status, dict)
        or status.get("available") is not False
        or status.get("scientifically_validated") is not False
        or status.get("reason_codes") != ["primary_not_better_than_baseline", "primary_ci_not_below_zero"]
        or p9.available is not False
        or p9.benchmark_passed is not False
        or p9.scientifically_validated is not False
        or p9.promotion_eligible is not False
        or p9.reason_codes[:2] != tuple(status["reason_codes"])
    ):
        raise BenchmarkSystemError("P9 replay must preserve the frozen negative result")
    if hashlib.sha256(p9_payload).hexdigest() != p9.sha256:
        raise BenchmarkSystemError("P9 replay bytes changed")
    return receipts
