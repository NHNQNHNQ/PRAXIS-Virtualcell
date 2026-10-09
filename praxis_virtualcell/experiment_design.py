"""P27A-E experiment-design contracts and a synthetic replay harness.

The authoritative product action space is currently empty: this module does not
turn synthetic replay rows into executable experiments.  Its replay API is split
into selection and evaluation so selectors cannot receive outcome values.  The
only implemented maturity is deterministic ``SYNTHETIC_CONFORMANCE_ONLY``;
canonical historical replay, shadow review, prospective work, and external
actions remain unavailable.
"""

from __future__ import annotations

import hashlib
import re
from decimal import Decimal, InvalidOperation
from typing import Any, Literal, TypeVar

from pydantic import ConfigDict, ValidationError, field_validator, model_validator

from praxis_virtualcell.core.request_v2 import VirtualCellRequestV2
from praxis_virtualcell.model_zoo.adapter_sdk import _Contract as _AdapterContract
from praxis_virtualcell.model_zoo.adapter_sdk import (
    _fingerprint,
    _reject_model_type_drift,
    _reject_undeclared_model_fields,
    _strict_fingerprint,
    _strict_text,
)

_EXPERIMENT_ID = re.compile(r"^experiment_[0-9a-f]{24}$")
_PROTOCOL_ID = re.compile(r"^replay_protocol_[0-9a-f]{24}$")
_RECEIPT_ID = re.compile(r"^replay_receipt_[0-9a-f]{24}$")
_RESULT_ID = re.compile(r"^replay_result_[0-9a-f]{24}$")
_DECIMAL = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")

_STRATEGIES = (
    "active_heuristic",
    "random",
    "uncertainty_only",
    "diversity",
    "expert_rule",
)
_ABSTAIN_REASONS = (
    "no_exact_validated_promoted_action_space",
    "historical_replay_asset_unavailable",
    "human_approval_required",
)
_ACTION_FEASIBILITY_REASONS = (
    "synthetic_fixture_not_real_model_domain",
    "external_execution_not_authorized",
)
_DESIGN_FEASIBILITY_REASONS = (
    "validated_model_domain_unavailable",
    "external_execution_not_authorized",
)


class ExperimentDesignContractError(ValueError):
    """A P27A-E contract is malformed or crosses a trust boundary."""


class _P27Contract(_AdapterContract):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    @classmethod
    def from_dict(cls, value: dict[str, Any]):
        if type(value) is not dict:
            raise ExperimentDesignContractError(f"{cls.__name__} must be an exact JSON object")
        try:
            return cls.model_validate(value)
        except (TypeError, ValidationError, ValueError) as exc:
            raise ExperimentDesignContractError(f"invalid {cls.__name__}: {exc}") from exc


_ModelT = TypeVar("_ModelT", bound=_P27Contract)


def _normalize_exact(value: Any, cls: type[_ModelT], field: str) -> _ModelT:
    try:
        _reject_undeclared_model_fields(value, field)
        if type(value) is not cls:
            raise TypeError(f"{field} must be exact {cls.__name__}")
        normalized = cls.model_validate(value.to_dict())
        _reject_model_type_drift(value, normalized, field)
        return normalized
    except (TypeError, ValidationError, ValueError) as exc:
        raise ExperimentDesignContractError(f"invalid {field}: {exc}") from exc


def _normalize_request(value: Any) -> VirtualCellRequestV2:
    try:
        _reject_undeclared_model_fields(value, "request")
        if type(value) is not VirtualCellRequestV2:
            raise TypeError("request must be exact VirtualCellRequestV2")
        normalized = VirtualCellRequestV2.from_dict(value.to_dict())
        _reject_model_type_drift(value, normalized, "request")
        return normalized
    except (TypeError, ValidationError, ValueError) as exc:
        raise ExperimentDesignContractError(f"invalid request: {exc}") from exc


def _text_array(value: Any, field: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if type(value) is not list or (not value and not allow_empty):
        raise ValueError(f"{field} must be a JSON array{' (possibly empty)' if allow_empty else ''}")
    values = tuple(_strict_text(item, field) for item in value)
    if len(set(values)) != len(values):
        raise ValueError(f"{field} must contain unique values")
    return values


def _canonical_decimal(
    value: Any,
    field: str,
    *,
    minimum: Decimal | None = None,
    maximum: Decimal | None = None,
    strictly_positive: bool = False,
) -> str:
    if type(value) is not str or not _DECIMAL.fullmatch(value):
        raise ValueError(f"{field} must be a canonical finite decimal string")
    try:
        number = Decimal(value)
    except InvalidOperation as exc:  # pragma: no cover - guarded by the regex
        raise ValueError(f"{field} must be a decimal") from exc
    if not number.is_finite():
        raise ValueError(f"{field} must be finite")
    canonical = format(number.normalize(), "f")
    if canonical == "-0":
        canonical = "0"
    if value != canonical:
        raise ValueError(f"{field} must not be silently normalized")
    if strictly_positive and number <= 0:
        raise ValueError(f"{field} must be positive")
    if minimum is not None and number < minimum:
        raise ValueError(f"{field} is below its declared range")
    if maximum is not None and number > maximum:
        raise ValueError(f"{field} exceeds its declared range")
    return value


def _decimal_text(value: Decimal) -> str:
    text = format(value.normalize(), "f")
    return "0" if text == "-0" else text


def _content_id(prefix: str, value: dict[str, Any]) -> str:
    return f"{prefix}{_fingerprint(value)[:24]}"


def _outcome_contract_fingerprint(selection_view: ReplaySelectionViewV1) -> str:
    return _fingerprint(
        {
            "schema_version": "vc.replay-outcome-contract.v1",
            "pool_id": selection_view.pool_id,
            "manifest_fingerprint": selection_view.manifest_fingerprint,
            "group_split_fingerprint": selection_view.group_split_fingerprint,
            "action_catalog_fingerprint": selection_view.action_catalog_fingerprint,
            "action_group_bindings": [[row.action.action_id, row.group_id] for row in selection_view.rows],
            "primary_metric": "synthetic_realized_utility",
            "metric_unit": "dimensionless",
        }
    )


class ExperimentActionV1(_P27Contract):
    """One synthetic-only catalog action; never a dispatchable experiment."""

    schema_version: Literal["vc.experiment-action.v1"]
    action_id: str
    request_fingerprint: str
    cell_scope_fingerprint: str
    model_scope_fingerprint: str
    pack_fingerprint: str
    compatibility_fingerprint: str
    execution_step_fingerprint: str
    evidence_fingerprint: str
    calibration_fingerprint: str
    ood_fingerprint: str
    perturbation_id: str
    control_id: str
    replicate_count: int
    batch_ids: tuple[str, ...]
    endpoint: str
    endpoint_unit: Literal["log2_fold_change"]
    planned_cost: str
    cost_unit: Literal["synthetic_cost_unit"]
    constraints: tuple[str, ...]
    feasibility_status: Literal["synthetic_conformance_only"]
    feasibility_reasons: tuple[str, ...]
    synthetic_catalog_eligible: Literal[True]
    real_model_domain_verified: Literal[False]
    scientifically_validated: Literal[False]
    production_promoted: Literal[False]
    external_execution_allowed: Literal[False]
    record_role: Literal["synthetic_conformance_action"]

    @field_validator(
        "request_fingerprint",
        "cell_scope_fingerprint",
        "model_scope_fingerprint",
        "pack_fingerprint",
        "compatibility_fingerprint",
        "execution_step_fingerprint",
        "evidence_fingerprint",
        "calibration_fingerprint",
        "ood_fingerprint",
        mode="before",
    )
    @classmethod
    def _fingerprints(cls, value, info):
        return _strict_fingerprint(value, info.field_name)

    @field_validator(
        "action_id",
        "perturbation_id",
        "control_id",
        "endpoint",
        mode="before",
    )
    @classmethod
    def _texts(cls, value, info):
        return _strict_text(value, info.field_name)

    @field_validator("batch_ids", "constraints", mode="before")
    @classmethod
    def _arrays(cls, value, info):
        return _text_array(value, info.field_name)

    @field_validator("feasibility_reasons", mode="before")
    @classmethod
    def _feasibility_reasons(cls, value):
        if type(value) is not list or tuple(value) != _ACTION_FEASIBILITY_REASONS:
            raise ValueError("feasibility_reasons must equal the synthetic-only reasons")
        return _ACTION_FEASIBILITY_REASONS

    @field_validator("replicate_count", mode="before")
    @classmethod
    def _replicates(cls, value):
        if type(value) is not int or value <= 0:
            raise ValueError("replicate_count must be a positive integer")
        return value

    @field_validator("planned_cost", mode="before")
    @classmethod
    def _cost(cls, value):
        return _canonical_decimal(value, "planned_cost", strictly_positive=True)

    @model_validator(mode="after")
    def _design_shape(self):
        if self.perturbation_id == self.control_id:
            raise ValueError("perturbation and control must be distinct")
        if self.replicate_count < len(self.batch_ids):
            raise ValueError("replicate_count cannot be smaller than the batch count")
        return self


class VirtualExperimentV1(_P27Contract):
    """The current authoritative P27 design: explicit, empty, and non-executable."""

    schema_version: Literal["vc.virtual-experiment.v1"]
    experiment_id: str
    question: str
    hypothesis: str
    request_id: str
    request_fingerprint: str
    cell_scope_fingerprint: str
    model_scope_fingerprint: None
    pack_fingerprint: None
    evidence_fingerprint: None
    policy_fingerprint: None
    perturbation_fingerprint: str
    perturbation_ids: tuple[str, ...]
    control_id: None
    replicate_count: None
    batch_ids: tuple[str, ...]
    endpoint: str
    endpoint_unit: str | None
    cost_limit: None
    cost_unit: None
    constraints_fingerprint: str
    action_catalog_fingerprint: None
    selected_action_ids: tuple[str, ...]
    feasibility_status: Literal["unavailable_no_validated_action_space"]
    feasibility_reasons: tuple[str, ...]
    human_approval_required: Literal[True]
    human_approval_status: Literal["required_not_granted"]
    executable: Literal[False]
    execution_performed: Literal[False]
    external_action_allowed: Literal[False]
    shadow_reviewed: Literal[False]
    prospective_pilot: Literal[False]
    autonomous_experiment: Literal[False]
    abstain: Literal[True]
    abstain_reasons: tuple[str, ...]
    scientifically_validated: Literal[False]
    production_promoted: Literal[False]
    record_role: Literal["p27ae_contract_only_missing_action_space"]

    @field_validator("experiment_id", mode="before")
    @classmethod
    def _id(cls, value):
        if type(value) is not str or not _EXPERIMENT_ID.fullmatch(value):
            raise ValueError("experiment_id is malformed")
        return value

    @field_validator(
        "request_fingerprint",
        "cell_scope_fingerprint",
        "perturbation_fingerprint",
        "constraints_fingerprint",
        mode="before",
    )
    @classmethod
    def _fingerprints(cls, value, info):
        return _strict_fingerprint(value, info.field_name)

    @field_validator(
        "question",
        "hypothesis",
        "request_id",
        "endpoint",
        mode="before",
    )
    @classmethod
    def _texts(cls, value, info):
        return _strict_text(value, info.field_name)

    @field_validator("perturbation_ids", mode="before")
    @classmethod
    def _perturbations(cls, value):
        return _text_array(value, "perturbation_ids")

    @field_validator("batch_ids", mode="before")
    @classmethod
    def _no_batches(cls, value):
        if type(value) is not list or value:
            raise ValueError("batch_ids must be empty until an action space is validated")
        return ()

    @field_validator("selected_action_ids", mode="before")
    @classmethod
    def _no_actions(cls, value):
        if type(value) is not list or value:
            raise ValueError("P27A-E authoritative selected_action_ids must be empty")
        return ()

    @field_validator("abstain_reasons", mode="before")
    @classmethod
    def _reasons(cls, value):
        if type(value) is not list or tuple(value) != _ABSTAIN_REASONS:
            raise ValueError("abstain_reasons must equal the canonical P27A-E reasons")
        return _ABSTAIN_REASONS

    @field_validator("feasibility_reasons", mode="before")
    @classmethod
    def _feasibility_reasons(cls, value):
        if type(value) is not list or tuple(value) != _DESIGN_FEASIBILITY_REASONS:
            raise ValueError("feasibility_reasons must equal the unavailable-domain reasons")
        return _DESIGN_FEASIBILITY_REASONS

    @field_validator("endpoint_unit", mode="before")
    @classmethod
    def _endpoint_unit(cls, value):
        if value is None:
            return None
        return _strict_text(value, "endpoint_unit")

    @model_validator(mode="after")
    def _closure(self):
        identity = self.model_dump(mode="json", exclude={"experiment_id"})
        if self.experiment_id != _content_id("experiment_", identity):
            raise ValueError("experiment_id is stale")
        return self


class ReplaySelectionRowV1(_P27Contract):
    schema_version: Literal["vc.replay-selection-row.v1"]
    action: ExperimentActionV1
    group_id: str
    heuristic_score: str
    uncertainty_score: str
    diversity_group: str
    expert_priority: int

    @field_validator("group_id", "diversity_group", mode="before")
    @classmethod
    def _texts(cls, value, info):
        return _strict_text(value, info.field_name)

    @field_validator("heuristic_score", "uncertainty_score", mode="before")
    @classmethod
    def _scores(cls, value, info):
        return _canonical_decimal(value, info.field_name, minimum=Decimal("0"), maximum=Decimal("1"))

    @field_validator("expert_priority", mode="before")
    @classmethod
    def _priority(cls, value):
        if type(value) is not int or value <= 0:
            raise ValueError("expert_priority must be a positive integer")
        return value

    @model_validator(mode="after")
    def _action_closure(self):
        _normalize_exact(self.action, ExperimentActionV1, "action")
        return self


class ReplaySelectionViewV1(_P27Contract):
    schema_version: Literal["vc.replay-selection-view.v1"]
    pool_id: str
    manifest_fingerprint: str
    group_split_fingerprint: str
    action_catalog_fingerprint: str
    rows: tuple[ReplaySelectionRowV1, ...]
    split_method: Literal["synthetic_group_partition_conformance"]
    selection_partition: Literal["synthetic_candidate_pool"]
    outcome_partition: Literal["synthetic_hidden_outcome_fixture"]
    leakage_audit_status: Literal["unavailable_synthetic_conformance"]
    outcome_fields_available: Literal[False]
    historical_asset_used: Literal[False]
    record_role: Literal["synthetic_conformance_selection_view"]

    @field_validator("pool_id", mode="before")
    @classmethod
    def _pool(cls, value):
        return _strict_text(value, "pool_id")

    @field_validator(
        "manifest_fingerprint",
        "group_split_fingerprint",
        "action_catalog_fingerprint",
        mode="before",
    )
    @classmethod
    def _fingerprints(cls, value, info):
        return _strict_fingerprint(value, info.field_name)

    @field_validator("rows", mode="before")
    @classmethod
    def _rows(cls, value):
        if type(value) is not list or not value:
            raise ValueError("selection view requires a non-empty JSON row array")
        return tuple(value)

    @model_validator(mode="after")
    def _catalog_closure(self):
        rows = tuple(_normalize_exact(row, ReplaySelectionRowV1, "selection row") for row in self.rows)
        action_ids = tuple(row.action.action_id for row in rows)
        if len(set(action_ids)) != len(action_ids):
            raise ValueError("selection action IDs must be unique")
        invariant_fields = (
            "cell_scope_fingerprint",
            "model_scope_fingerprint",
            "pack_fingerprint",
            "evidence_fingerprint",
            "calibration_fingerprint",
            "ood_fingerprint",
            "endpoint",
            "endpoint_unit",
            "cost_unit",
        )
        for field in invariant_fields:
            if len({getattr(row.action, field) for row in rows}) != 1:
                raise ValueError(f"selection actions mix comparator domain field {field}")
        expected = _fingerprint([row.action.fingerprint() for row in rows])
        if self.action_catalog_fingerprint != expected:
            raise ValueError("action_catalog_fingerprint is stale")
        return self


OutcomeStatus = Literal["observed", "failed", "unavailable"]


class ReplayOutcomeRowV1(_P27Contract):
    schema_version: Literal["vc.replay-outcome-row.v1"]
    action_id: str
    group_id: str
    status: OutcomeStatus
    realized_utility: str | None
    realized_cost: str | None

    @field_validator("action_id", "group_id", mode="before")
    @classmethod
    def _texts(cls, value, info):
        return _strict_text(value, info.field_name)

    @field_validator("realized_utility", mode="before")
    @classmethod
    def _utility(cls, value):
        if value is None:
            return None
        return _canonical_decimal(value, "realized_utility", minimum=Decimal("-1"), maximum=Decimal("1"))

    @field_validator("realized_cost", mode="before")
    @classmethod
    def _cost(cls, value):
        if value is None:
            return None
        return _canonical_decimal(value, "realized_cost", strictly_positive=True)

    @model_validator(mode="after")
    def _status_shape(self):
        if self.status == "observed" and (self.realized_utility is None or self.realized_cost is None):
            raise ValueError("observed outcomes require utility and cost")
        if self.status == "failed" and (self.realized_utility is not None or self.realized_cost is None):
            raise ValueError("failed outcomes require cost and no utility")
        if self.status == "unavailable" and (self.realized_utility is not None or self.realized_cost is not None):
            raise ValueError("unavailable outcomes cannot contain values")
        return self


class ReplayOutcomeLedgerV1(_P27Contract):
    schema_version: Literal["vc.replay-outcome-ledger.v1"]
    pool_id: str
    manifest_fingerprint: str
    group_split_fingerprint: str
    action_catalog_fingerprint: str
    selection_view_fingerprint: str
    outcome_contract_fingerprint: str
    rows: tuple[ReplayOutcomeRowV1, ...]
    historical_asset_used: Literal[False]
    record_role: Literal["synthetic_conformance_outcome_ledger"]

    @field_validator("pool_id", mode="before")
    @classmethod
    def _pool(cls, value):
        return _strict_text(value, "pool_id")

    @field_validator(
        "manifest_fingerprint",
        "group_split_fingerprint",
        "action_catalog_fingerprint",
        "selection_view_fingerprint",
        "outcome_contract_fingerprint",
        mode="before",
    )
    @classmethod
    def _fingerprints(cls, value, info):
        return _strict_fingerprint(value, info.field_name)

    @field_validator("rows", mode="before")
    @classmethod
    def _rows(cls, value):
        if type(value) is not list or not value:
            raise ValueError("outcome ledger rows must be a non-empty JSON array")
        return tuple(value)

    @model_validator(mode="after")
    def _rows_unique(self):
        rows = tuple(_normalize_exact(row, ReplayOutcomeRowV1, "outcome row") for row in self.rows)
        action_ids = tuple(row.action_id for row in rows)
        if len(set(action_ids)) != len(action_ids):
            raise ValueError("outcome action IDs must be unique")
        return self


class ReplayProtocolV1(_P27Contract):
    schema_version: Literal["vc.replay-protocol.v1"]
    protocol_id: str
    pool_id: str
    manifest_fingerprint: str
    group_split_fingerprint: str
    action_catalog_fingerprint: str
    selection_view_fingerprint: str
    outcome_contract_fingerprint: str
    strategies: tuple[str, ...]
    budget_count: int
    random_seed: int
    tie_breaker: Literal["canonical_action_id"]
    primary_metric: Literal["synthetic_realized_utility"]
    metric_direction: Literal["higher_is_better"]
    outcome_access_policy: Literal["rank_then_reveal_after_all_receipts_frozen"]
    selector_outcome_access_allowed: Literal[False]
    historical_replay_status: Literal["replay_not_run_asset_pending"]
    record_role: Literal["p27ae_synthetic_replay_protocol"]

    @field_validator("protocol_id", mode="before")
    @classmethod
    def _id(cls, value):
        if type(value) is not str or not _PROTOCOL_ID.fullmatch(value):
            raise ValueError("protocol_id is malformed")
        return value

    @field_validator("pool_id", mode="before")
    @classmethod
    def _pool(cls, value):
        return _strict_text(value, "pool_id")

    @field_validator(
        "manifest_fingerprint",
        "group_split_fingerprint",
        "action_catalog_fingerprint",
        "selection_view_fingerprint",
        "outcome_contract_fingerprint",
        mode="before",
    )
    @classmethod
    def _fingerprints(cls, value, info):
        return _strict_fingerprint(value, info.field_name)

    @field_validator("strategies", mode="before")
    @classmethod
    def _strategies(cls, value):
        if type(value) is not list or tuple(value) != _STRATEGIES:
            raise ValueError("strategies must equal the canonical five-strategy order")
        return _STRATEGIES

    @field_validator("budget_count", mode="before")
    @classmethod
    def _budget(cls, value):
        if type(value) is not int or value <= 0:
            raise ValueError("budget_count must be a positive integer")
        return value

    @field_validator("random_seed", mode="before")
    @classmethod
    def _seed(cls, value):
        if type(value) is not int or value < 0:
            raise ValueError("random_seed must be a non-negative integer")
        return value

    @model_validator(mode="after")
    def _identity(self):
        identity = self.model_dump(mode="json", exclude={"protocol_id"})
        if self.protocol_id != _content_id("replay_protocol_", identity):
            raise ValueError("protocol_id is stale")
        return self


class ReplaySelectionReceiptV1(_P27Contract):
    schema_version: Literal["vc.replay-selection-receipt.v1"]
    receipt_id: str
    strategy: str
    protocol_fingerprint: str
    selection_view_fingerprint: str
    outcome_contract_fingerprint: str
    action_catalog_fingerprint: str
    selected_action_ids: tuple[str, ...]
    selected_action_fingerprints: tuple[str, ...]
    selected_uncertainty_scores: tuple[str, ...]
    total_planned_cost: str
    outcome_accessed: Literal[False]
    record_role: Literal["synthetic_pre_outcome_selection_receipt"]

    @field_validator("receipt_id", mode="before")
    @classmethod
    def _id(cls, value):
        if type(value) is not str or not _RECEIPT_ID.fullmatch(value):
            raise ValueError("receipt_id is malformed")
        return value

    @field_validator("strategy", mode="before")
    @classmethod
    def _strategy(cls, value):
        value = _strict_text(value, "strategy")
        if value not in _STRATEGIES:
            raise ValueError("strategy is not registered")
        return value

    @field_validator(
        "protocol_fingerprint",
        "selection_view_fingerprint",
        "outcome_contract_fingerprint",
        "action_catalog_fingerprint",
        mode="before",
    )
    @classmethod
    def _fingerprints(cls, value, info):
        return _strict_fingerprint(value, info.field_name)

    @field_validator("selected_action_ids", mode="before")
    @classmethod
    def _actions(cls, value):
        return _text_array(value, "selected_action_ids")

    @field_validator("selected_action_fingerprints", mode="before")
    @classmethod
    def _action_fingerprints(cls, value):
        if type(value) is not list or not value:
            raise ValueError("selected_action_fingerprints must be a non-empty JSON array")
        values = tuple(_strict_fingerprint(item, "selected_action_fingerprints") for item in value)
        if len(set(values)) != len(values):
            raise ValueError("selected_action_fingerprints must be unique")
        return values

    @field_validator("selected_uncertainty_scores", mode="before")
    @classmethod
    def _uncertainties(cls, value):
        if type(value) is not list or not value:
            raise ValueError("selected_uncertainty_scores must be a non-empty JSON array")
        return tuple(
            _canonical_decimal(item, "selected_uncertainty_scores", minimum=Decimal("0"), maximum=Decimal("1"))
            for item in value
        )

    @field_validator("total_planned_cost", mode="before")
    @classmethod
    def _cost(cls, value):
        return _canonical_decimal(value, "total_planned_cost", strictly_positive=True)

    @model_validator(mode="after")
    def _identity(self):
        if not (
            len(self.selected_action_ids)
            == len(self.selected_action_fingerprints)
            == len(self.selected_uncertainty_scores)
        ):
            raise ValueError("selected action identity arrays must have equal length")
        identity = self.model_dump(mode="json", exclude={"receipt_id"})
        if self.receipt_id != _content_id("replay_receipt_", identity):
            raise ValueError("receipt_id is stale")
        return self


class ReplayStrategySummaryV1(_P27Contract):
    schema_version: Literal["vc.replay-strategy-summary.v1"]
    strategy: str
    receipt_fingerprint: str
    selected_action_ids: tuple[str, ...]
    observed_count: int
    failed_count: int
    unavailable_count: int
    failed_action_ids: tuple[str, ...]
    unavailable_action_ids: tuple[str, ...]
    mean_realized_utility: str | None
    total_realized_cost: str | None
    mean_selected_uncertainty: str
    missing_values_imputed: Literal[False]
    comparison_verdict: Literal["not_scientific"]

    @field_validator("strategy", mode="before")
    @classmethod
    def _strategy(cls, value):
        value = _strict_text(value, "strategy")
        if value not in _STRATEGIES:
            raise ValueError("summary strategy is not registered")
        return value

    @field_validator("receipt_fingerprint", mode="before")
    @classmethod
    def _fingerprint_value(cls, value):
        return _strict_fingerprint(value, "receipt_fingerprint")

    @field_validator("selected_action_ids", "failed_action_ids", "unavailable_action_ids", mode="before")
    @classmethod
    def _arrays(cls, value, info):
        return _text_array(value, info.field_name, allow_empty=True)

    @field_validator("observed_count", "failed_count", "unavailable_count", mode="before")
    @classmethod
    def _counts(cls, value, info):
        if type(value) is not int or value < 0:
            raise ValueError(f"{info.field_name} must be a non-negative integer")
        return value

    @field_validator("mean_realized_utility", mode="before")
    @classmethod
    def _utility(cls, value):
        if value is None:
            return None
        return _canonical_decimal(value, "mean_realized_utility", minimum=Decimal("-1"), maximum=Decimal("1"))

    @field_validator("total_realized_cost", mode="before")
    @classmethod
    def _cost(cls, value):
        if value is None:
            return None
        return _canonical_decimal(value, "total_realized_cost", strictly_positive=True)

    @field_validator("mean_selected_uncertainty", mode="before")
    @classmethod
    def _uncertainty(cls, value):
        return _canonical_decimal(
            value,
            "mean_selected_uncertainty",
            minimum=Decimal("0"),
            maximum=Decimal("1"),
        )

    @model_validator(mode="after")
    def _counts_match(self):
        if self.observed_count + self.failed_count + self.unavailable_count != len(self.selected_action_ids):
            raise ValueError("summary counts must cover every selected action")
        if self.failed_count != len(self.failed_action_ids):
            raise ValueError("failed_count does not match failed_action_ids")
        if self.unavailable_count != len(self.unavailable_action_ids):
            raise ValueError("unavailable_count does not match unavailable_action_ids")
        selected = set(self.selected_action_ids)
        failed = set(self.failed_action_ids)
        unavailable = set(self.unavailable_action_ids)
        if failed & unavailable or not failed.issubset(selected) or not unavailable.issubset(selected):
            raise ValueError("failed/unavailable action identities must partition selected actions")
        if (self.observed_count == 0) != (self.mean_realized_utility is None):
            raise ValueError("utility must be unavailable exactly when no outcome was observed")
        return self


class ReplayResultV1(_P27Contract):
    schema_version: Literal["vc.replay-result.v1"]
    result_id: str
    protocol_fingerprint: str
    selection_view_fingerprint: str
    outcome_ledger_fingerprint: str
    outcome_contract_fingerprint: str
    receipt_fingerprints: tuple[str, ...]
    summaries: tuple[ReplayStrategySummaryV1, ...]
    primary_strategy: Literal["active_heuristic"]
    primary_passed: None
    replay_maturity: Literal["synthetic_conformance_only"]
    historical_replay_status: Literal["replay_not_run_asset_pending"]
    outcome_revealed_after_all_receipts_frozen: Literal[True]
    negative_results_preserved: Literal[True]
    implicit_zero_fill_allowed: Literal[False]
    human_approval_required: Literal[True]
    execution_performed: Literal[False]
    external_action_performed: Literal[False]
    shadow_reviewed: Literal[False]
    prospective_pilot: Literal[False]
    autonomous_experiment: Literal[False]
    scientifically_validated: Literal[False]
    promotion_eligible: Literal[False]
    production_promoted: Literal[False]
    record_role: Literal["p27ae_synthetic_replay_result"]

    @field_validator("result_id", mode="before")
    @classmethod
    def _id(cls, value):
        if type(value) is not str or not _RESULT_ID.fullmatch(value):
            raise ValueError("result_id is malformed")
        return value

    @field_validator(
        "protocol_fingerprint",
        "selection_view_fingerprint",
        "outcome_ledger_fingerprint",
        "outcome_contract_fingerprint",
        mode="before",
    )
    @classmethod
    def _fingerprints(cls, value, info):
        return _strict_fingerprint(value, info.field_name)

    @field_validator("receipt_fingerprints", mode="before")
    @classmethod
    def _receipt_fingerprints(cls, value):
        if type(value) is not list or len(value) != len(_STRATEGIES):
            raise ValueError("receipt_fingerprints must contain exactly five values")
        values = tuple(_strict_fingerprint(item, "receipt_fingerprints") for item in value)
        if len(set(values)) != len(values):
            raise ValueError("receipt_fingerprints must be unique")
        return values

    @field_validator("summaries", mode="before")
    @classmethod
    def _summaries(cls, value):
        if type(value) is not list or len(value) != len(_STRATEGIES):
            raise ValueError("summaries must contain exactly five values")
        return tuple(value)

    @model_validator(mode="after")
    def _identity(self):
        summaries = tuple(_normalize_exact(item, ReplayStrategySummaryV1, "summary") for item in self.summaries)
        if tuple(item.strategy for item in summaries) != _STRATEGIES:
            raise ValueError("summaries must preserve canonical strategy order")
        if tuple(item.receipt_fingerprint for item in summaries) != self.receipt_fingerprints:
            raise ValueError("summaries do not match receipt fingerprints")
        identity = self.model_dump(mode="json", exclude={"result_id"})
        if self.result_id != _content_id("replay_result_", identity):
            raise ValueError("result_id is stale")
        return self


def compile_contract_only_experiment(
    *,
    request: VirtualCellRequestV2,
    question: str,
    hypothesis: str,
) -> VirtualExperimentV1:
    """Freeze an honest P27A-E design with no executable product action."""

    frozen_request = _normalize_request(request)
    if len(frozen_request.task.requested_outputs) != 1:
        raise ExperimentDesignContractError("P27A-E requires exactly one requested endpoint")
    cell_scope = {
        "species": frozen_request.species.to_dict(),
        "cell_context": frozen_request.cell_context.to_dict(),
        "input_modality": frozen_request.input_modality.to_dict(),
        "output_modality": frozen_request.output_modality.to_dict(),
        "task": frozen_request.task.to_dict(),
    }
    payload: dict[str, Any] = {
        "schema_version": "vc.virtual-experiment.v1",
        "question": question,
        "hypothesis": hypothesis,
        "request_id": frozen_request.request_id,
        "request_fingerprint": _fingerprint(frozen_request.to_dict()),
        "cell_scope_fingerprint": _fingerprint(cell_scope),
        "model_scope_fingerprint": None,
        "pack_fingerprint": None,
        "evidence_fingerprint": None,
        "policy_fingerprint": None,
        "perturbation_fingerprint": _fingerprint(frozen_request.perturbation.to_dict()),
        "perturbation_ids": list(frozen_request.perturbation.targets),
        "control_id": None,
        "replicate_count": None,
        "batch_ids": [],
        "endpoint": frozen_request.task.requested_outputs[0],
        "endpoint_unit": frozen_request.output_modality.unit,
        "cost_limit": None,
        "cost_unit": None,
        "constraints_fingerprint": _fingerprint(frozen_request.constraints),
        "action_catalog_fingerprint": None,
        "selected_action_ids": [],
        "feasibility_status": "unavailable_no_validated_action_space",
        "feasibility_reasons": list(_DESIGN_FEASIBILITY_REASONS),
        "human_approval_required": True,
        "human_approval_status": "required_not_granted",
        "executable": False,
        "execution_performed": False,
        "external_action_allowed": False,
        "shadow_reviewed": False,
        "prospective_pilot": False,
        "autonomous_experiment": False,
        "abstain": True,
        "abstain_reasons": list(_ABSTAIN_REASONS),
        "scientifically_validated": False,
        "production_promoted": False,
        "record_role": "p27ae_contract_only_missing_action_space",
    }
    payload["experiment_id"] = _content_id("experiment_", payload)
    return VirtualExperimentV1.from_dict(payload)


def freeze_replay_protocol(
    selection_view: ReplaySelectionViewV1,
    *,
    budget_count: int,
    random_seed: int,
) -> ReplayProtocolV1:
    """Freeze selector-visible protocol identity without outcome values."""

    view = _normalize_exact(selection_view, ReplaySelectionViewV1, "selection_view")
    payload: dict[str, Any] = {
        "schema_version": "vc.replay-protocol.v1",
        "pool_id": view.pool_id,
        "manifest_fingerprint": view.manifest_fingerprint,
        "group_split_fingerprint": view.group_split_fingerprint,
        "action_catalog_fingerprint": view.action_catalog_fingerprint,
        "selection_view_fingerprint": view.fingerprint(),
        "outcome_contract_fingerprint": _outcome_contract_fingerprint(view),
        "strategies": list(_STRATEGIES),
        "budget_count": budget_count,
        "random_seed": random_seed,
        "tie_breaker": "canonical_action_id",
        "primary_metric": "synthetic_realized_utility",
        "metric_direction": "higher_is_better",
        "outcome_access_policy": "rank_then_reveal_after_all_receipts_frozen",
        "selector_outcome_access_allowed": False,
        "historical_replay_status": "replay_not_run_asset_pending",
        "record_role": "p27ae_synthetic_replay_protocol",
    }
    payload["protocol_id"] = _content_id("replay_protocol_", payload)
    return ReplayProtocolV1.from_dict(payload)


def _diversity_order(rows: tuple[ReplaySelectionRowV1, ...]) -> list[ReplaySelectionRowV1]:
    groups: dict[str, list[ReplaySelectionRowV1]] = {}
    for row in rows:
        groups.setdefault(row.diversity_group, []).append(row)
    for values in groups.values():
        values.sort(key=lambda row: (-Decimal(row.heuristic_score), row.action.action_id))
    ordered: list[ReplaySelectionRowV1] = []
    while any(groups.values()):
        for group in sorted(groups):
            if groups[group]:
                ordered.append(groups[group].pop(0))
    return ordered


def _strategy_order(
    strategy: str,
    rows: tuple[ReplaySelectionRowV1, ...],
    seed: int,
) -> list[ReplaySelectionRowV1]:
    if strategy == "active_heuristic":
        return sorted(rows, key=lambda row: (-Decimal(row.heuristic_score), row.action.action_id))
    if strategy == "random":
        return sorted(
            rows,
            key=lambda row: hashlib.sha256(f"{seed}:{row.action.action_id}".encode()).hexdigest(),
        )
    if strategy == "uncertainty_only":
        return sorted(rows, key=lambda row: (-Decimal(row.uncertainty_score), row.action.action_id))
    if strategy == "diversity":
        return _diversity_order(rows)
    if strategy == "expert_rule":
        return sorted(rows, key=lambda row: (row.expert_priority, row.action.action_id))
    raise ExperimentDesignContractError(f"unknown replay strategy: {strategy}")


def select_replay_actions(
    protocol: ReplayProtocolV1,
    selection_view: ReplaySelectionViewV1,
) -> tuple[ReplaySelectionReceiptV1, ...]:
    """Freeze all five selections.  No outcome object is accepted by this API."""

    frozen_protocol = _normalize_exact(protocol, ReplayProtocolV1, "protocol")
    view = _normalize_exact(selection_view, ReplaySelectionViewV1, "selection_view")
    if not (
        frozen_protocol.pool_id == view.pool_id
        and frozen_protocol.manifest_fingerprint == view.manifest_fingerprint
        and frozen_protocol.group_split_fingerprint == view.group_split_fingerprint
        and frozen_protocol.action_catalog_fingerprint == view.action_catalog_fingerprint
        and frozen_protocol.selection_view_fingerprint == view.fingerprint()
    ):
        raise ExperimentDesignContractError("protocol does not match the selection view")
    if frozen_protocol.outcome_contract_fingerprint != _outcome_contract_fingerprint(view):
        raise ExperimentDesignContractError("protocol outcome contract is stale")
    if frozen_protocol.budget_count > len(view.rows):
        raise ExperimentDesignContractError("budget_count exceeds the frozen action pool")

    receipts: list[ReplaySelectionReceiptV1] = []
    for strategy in _STRATEGIES:
        selected = _strategy_order(strategy, view.rows, frozen_protocol.random_seed)[: frozen_protocol.budget_count]
        payload: dict[str, Any] = {
            "schema_version": "vc.replay-selection-receipt.v1",
            "strategy": strategy,
            "protocol_fingerprint": frozen_protocol.fingerprint(),
            "selection_view_fingerprint": view.fingerprint(),
            "outcome_contract_fingerprint": frozen_protocol.outcome_contract_fingerprint,
            "action_catalog_fingerprint": view.action_catalog_fingerprint,
            "selected_action_ids": [row.action.action_id for row in selected],
            "selected_action_fingerprints": [row.action.fingerprint() for row in selected],
            "selected_uncertainty_scores": [row.uncertainty_score for row in selected],
            "total_planned_cost": _decimal_text(
                sum((Decimal(row.action.planned_cost) for row in selected), Decimal("0"))
            ),
            "outcome_accessed": False,
            "record_role": "synthetic_pre_outcome_selection_receipt",
        }
        payload["receipt_id"] = _content_id("replay_receipt_", payload)
        receipts.append(ReplaySelectionReceiptV1.from_dict(payload))
    return tuple(receipts)


def evaluate_replay(
    protocol: ReplayProtocolV1,
    selection_view: ReplaySelectionViewV1,
    receipts: tuple[ReplaySelectionReceiptV1, ...],
    outcome_ledger: ReplayOutcomeLedgerV1,
) -> ReplayResultV1:
    """Reveal synthetic outcomes only after all canonical receipts exist."""

    frozen_protocol = _normalize_exact(protocol, ReplayProtocolV1, "protocol")
    view = _normalize_exact(selection_view, ReplaySelectionViewV1, "selection_view")
    ledger = _normalize_exact(outcome_ledger, ReplayOutcomeLedgerV1, "outcome_ledger")
    if type(receipts) is not tuple or len(receipts) != len(_STRATEGIES):
        raise ExperimentDesignContractError("all five receipts must be frozen before evaluation")
    frozen_receipts = tuple(_normalize_exact(receipt, ReplaySelectionReceiptV1, "receipt") for receipt in receipts)
    if tuple(receipt.strategy for receipt in frozen_receipts) != _STRATEGIES:
        raise ExperimentDesignContractError("receipt order must match the frozen strategy order")
    expected_receipts = select_replay_actions(frozen_protocol, view)
    if tuple(receipt.to_dict() for receipt in frozen_receipts) != tuple(
        receipt.to_dict() for receipt in expected_receipts
    ):
        raise ExperimentDesignContractError("receipt was not produced by the frozen selector")
    if not (
        ledger.pool_id == frozen_protocol.pool_id
        and ledger.manifest_fingerprint == frozen_protocol.manifest_fingerprint
        and ledger.group_split_fingerprint == frozen_protocol.group_split_fingerprint
        and ledger.action_catalog_fingerprint == frozen_protocol.action_catalog_fingerprint
        and ledger.selection_view_fingerprint == frozen_protocol.selection_view_fingerprint
        and ledger.outcome_contract_fingerprint == frozen_protocol.outcome_contract_fingerprint
    ):
        raise ExperimentDesignContractError("outcome ledger does not match the frozen protocol")
    expected_outcome_contract = _outcome_contract_fingerprint(view)
    if frozen_protocol.outcome_contract_fingerprint != expected_outcome_contract:
        raise ExperimentDesignContractError("outcome contract is stale")
    for receipt in frozen_receipts:
        if not (
            receipt.protocol_fingerprint == frozen_protocol.fingerprint()
            and receipt.selection_view_fingerprint == frozen_protocol.selection_view_fingerprint
            and receipt.outcome_contract_fingerprint == frozen_protocol.outcome_contract_fingerprint
            and receipt.action_catalog_fingerprint == frozen_protocol.action_catalog_fingerprint
            and len(receipt.selected_action_ids) == frozen_protocol.budget_count
        ):
            raise ExperimentDesignContractError("receipt does not match the frozen protocol")

    by_action = {row.action_id: row for row in ledger.rows}
    expected_groups = {row.action.action_id: row.group_id for row in view.rows}
    if set(by_action) != set(expected_groups):
        raise ExperimentDesignContractError("outcome ledger must cover the exact catalog; use explicit unavailable")
    if any(by_action[action_id].group_id != group_id for action_id, group_id in expected_groups.items()):
        raise ExperimentDesignContractError("outcome group binding does not match the selection view")

    summaries: list[ReplayStrategySummaryV1] = []
    for receipt in frozen_receipts:
        selected_outcomes = [by_action[action_id] for action_id in receipt.selected_action_ids]
        observed = [row for row in selected_outcomes if row.status == "observed"]
        failed = [row for row in selected_outcomes if row.status == "failed"]
        unavailable = [row for row in selected_outcomes if row.status == "unavailable"]
        utilities = [Decimal(row.realized_utility) for row in observed if row.realized_utility is not None]
        costs = [Decimal(row.realized_cost) for row in selected_outcomes if row.realized_cost is not None]
        uncertainties = [Decimal(value) for value in receipt.selected_uncertainty_scores]
        summary = ReplayStrategySummaryV1.from_dict(
            {
                "schema_version": "vc.replay-strategy-summary.v1",
                "strategy": receipt.strategy,
                "receipt_fingerprint": receipt.fingerprint(),
                "selected_action_ids": list(receipt.selected_action_ids),
                "observed_count": len(observed),
                "failed_count": len(failed),
                "unavailable_count": len(unavailable),
                "failed_action_ids": [row.action_id for row in failed],
                "unavailable_action_ids": [row.action_id for row in unavailable],
                "mean_realized_utility": (
                    _decimal_text(sum(utilities, Decimal("0")) / len(utilities)) if utilities else None
                ),
                "total_realized_cost": _decimal_text(sum(costs, Decimal("0"))) if costs else None,
                "mean_selected_uncertainty": _decimal_text(sum(uncertainties, Decimal("0")) / len(uncertainties)),
                "missing_values_imputed": False,
                "comparison_verdict": "not_scientific",
            }
        )
        summaries.append(summary)

    payload: dict[str, Any] = {
        "schema_version": "vc.replay-result.v1",
        "protocol_fingerprint": frozen_protocol.fingerprint(),
        "selection_view_fingerprint": frozen_protocol.selection_view_fingerprint,
        "outcome_ledger_fingerprint": ledger.fingerprint(),
        "outcome_contract_fingerprint": frozen_protocol.outcome_contract_fingerprint,
        "receipt_fingerprints": [receipt.fingerprint() for receipt in frozen_receipts],
        "summaries": [summary.to_dict() for summary in summaries],
        "primary_strategy": "active_heuristic",
        "primary_passed": None,
        "replay_maturity": "synthetic_conformance_only",
        "historical_replay_status": "replay_not_run_asset_pending",
        "outcome_revealed_after_all_receipts_frozen": True,
        "negative_results_preserved": True,
        "implicit_zero_fill_allowed": False,
        "human_approval_required": True,
        "execution_performed": False,
        "external_action_performed": False,
        "shadow_reviewed": False,
        "prospective_pilot": False,
        "autonomous_experiment": False,
        "scientifically_validated": False,
        "promotion_eligible": False,
        "production_promoted": False,
        "record_role": "p27ae_synthetic_replay_result",
    }
    payload["result_id"] = _content_id("replay_result_", payload)
    return ReplayResultV1.from_dict(payload)


__all__ = [
    "ExperimentActionV1",
    "ExperimentDesignContractError",
    "ReplayOutcomeLedgerV1",
    "ReplayOutcomeRowV1",
    "ReplayProtocolV1",
    "ReplayResultV1",
    "ReplaySelectionReceiptV1",
    "ReplaySelectionRowV1",
    "ReplaySelectionViewV1",
    "ReplayStrategySummaryV1",
    "VirtualExperimentV1",
    "compile_contract_only_experiment",
    "evaluate_replay",
    "freeze_replay_protocol",
    "select_replay_actions",
]
