"""P28E typed multi-agent contracts with deterministic value-free abstention.

The current repository has zero request-specific model modules that are both
executable, scientifically validated, and production promoted.  This module
therefore exposes only advisory conformance records and an authoritative empty
compilation.  It does not reuse the mutable legacy MessageBus, invoke tools or
LLMs, execute models, create evidence/policy, or perform external I/O.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Literal, TypeVar

from pydantic import ConfigDict, ValidationError, field_validator, model_validator

from praxis_virtualcell.experiment_design import ReplayResultV1, VirtualExperimentV1
from praxis_virtualcell.model_zoo.adapter_sdk import (
    _Contract as _AdapterContract,
)
from praxis_virtualcell.model_zoo.adapter_sdk import (
    _fingerprint as _canonical_fingerprint,
)
from praxis_virtualcell.model_zoo.adapter_sdk import (
    _reject_model_type_drift,
    _reject_undeclared_model_fields,
    _strict_fingerprint,
    _strict_text,
)
from praxis_virtualcell.virtual_experiment import VirtualExperimentCompilationV1

_CONTENT_ID = re.compile(r"^[a-z][a-z0-9_]*_[0-9a-f]{24}$")
_ROLE_ID = re.compile(r"^[a-z][a-z0-9_-]{2,63}$")
_ROLE_KINDS = (
    "cell_advisory",
    "drug_advisory",
    "literature_advisory",
    "md_advisory",
    "metabolism_advisory",
    "microbiome_advisory",
    "rule_advisory",
)
_INPUT_SCHEMAS = (
    "vc.multi-agent-value-free-handoff.v1",
    "vc.replay-result.v1",
    "vc.virtual-experiment-compilation.v1",
    "vc.virtual-experiment.v1",
)
_PERMISSIONS = (
    "emit_value_free_handoff",
    "read_bound_immutable_identity",
)
_ABSTAIN_REASONS = (
    "insufficient_exact_executable_validated_promoted_model_modules",
    "p27_historical_shadow_prospective_evidence_unavailable",
    "p28_real_execution_not_authorized",
)


class MultiAgentBiologyContractError(ValueError):
    """A P28E record crossed its strict contract or trust boundary."""


class _P28Contract(_AdapterContract):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    @classmethod
    def from_dict(cls, value: dict[str, Any]):
        if type(value) is not dict:
            raise MultiAgentBiologyContractError(f"{cls.__name__} must be an exact JSON object")
        try:
            return cls.model_validate(value)
        except (TypeError, ValidationError, ValueError) as exc:
            raise MultiAgentBiologyContractError(f"invalid {cls.__name__}: {exc}") from exc


_ModelT = TypeVar("_ModelT", bound=_P28Contract)


def _normalize_exact(value: Any, cls: type[_ModelT], field: str) -> _ModelT:
    try:
        _reject_undeclared_model_fields(value, field)
        if type(value) is not cls:
            raise TypeError(f"{field} must be exact {cls.__name__}")
        normalized = cls.model_validate(value.to_dict())
        _reject_model_type_drift(value, normalized, field)
        return normalized
    except (TypeError, ValidationError, ValueError) as exc:
        raise MultiAgentBiologyContractError(f"invalid {field}: {exc}") from exc


def _normalize_external(value: Any, cls: type[Any], field: str):
    try:
        _reject_undeclared_model_fields(value, field)
        if type(value) is not cls:
            raise TypeError(f"{field} must be exact {cls.__name__}")
        normalized = cls.from_dict(value.to_dict())
        _reject_model_type_drift(value, normalized, field)
        return normalized
    except (TypeError, ValidationError, ValueError) as exc:
        raise MultiAgentBiologyContractError(f"invalid {field}: {exc}") from exc


def _content_id(prefix: str, value: dict[str, Any]) -> str:
    return f"{prefix}{_canonical_fingerprint(value)[:24]}"


def _exact_array(value: Any, expected: tuple[str, ...], field: str) -> tuple[str, ...]:
    if type(value) is not list or tuple(value) != expected:
        raise ValueError(f"{field} must equal {list(expected)}")
    return expected


def _empty_array(value: Any, field: str) -> tuple[Any, ...]:
    if type(value) is not list or value:
        raise ValueError(f"{field} must be an empty array")
    return ()


class MultiAgentRolePolicyV1(_P28Contract):
    """A fixed local advisory role with no numerical or external authority."""

    schema_version: Literal["vc.multi-agent-role-policy.v1"]
    role_id: str
    role_kind: Literal[
        "cell_advisory",
        "drug_advisory",
        "literature_advisory",
        "md_advisory",
        "metabolism_advisory",
        "microbiome_advisory",
        "rule_advisory",
    ]
    accepted_input_schema_versions: tuple[str, ...]
    output_schema_version: Literal["vc.multi-agent-value-free-handoff.v1"]
    permissions: tuple[str, ...]
    max_handoffs: Literal[4]
    timeout_ms: Literal[1000]
    retry_limit: Literal[0]
    max_concurrency: Literal[1]
    resource_class: Literal["local_cpu_contract_only"]
    cancellation_required: Literal[True]
    network_access_allowed: Literal[False]
    filesystem_write_allowed: Literal[False]
    subprocess_allowed: Literal[False]
    device_access_allowed: Literal[False]
    external_action_allowed: Literal[False]
    dynamic_tool_invocation_allowed: Literal[False]
    numerical_output_allowed: Literal[False]
    advisory_only: Literal[True]
    counts_for_real_acceptance: Literal[False]
    scientifically_validated: Literal[False]
    production_promoted: Literal[False]
    record_role: Literal["p28e_synthetic_advisory_conformance"]

    @field_validator("role_id", mode="before")
    @classmethod
    def _role_id(cls, value):
        value = _strict_text(value, "role_id")
        if not _ROLE_ID.fullmatch(value):
            raise ValueError("role_id is malformed")
        return value

    @field_validator("role_kind", mode="before")
    @classmethod
    def _role_kind(cls, value):
        value = _strict_text(value, "role_kind")
        if value not in _ROLE_KINDS:
            raise ValueError("role_kind is not registered")
        return value

    @field_validator("accepted_input_schema_versions", mode="before")
    @classmethod
    def _inputs(cls, value):
        return _exact_array(value, _INPUT_SCHEMAS, "accepted_input_schema_versions")

    @field_validator("permissions", mode="before")
    @classmethod
    def _permissions(cls, value):
        return _exact_array(value, _PERMISSIONS, "permissions")


class MultiAgentHandoffV1(_P28Contract):
    """A typed handoff that carries one identity and no value or narrative payload."""

    schema_version: Literal["vc.multi-agent-handoff.v1"]
    handoff_id: str
    sender_role_id: str
    receiver_role_id: str
    sender_policy_fingerprint: str
    receiver_policy_fingerprint: str
    input_schema_version: str
    input_fingerprint: str
    output_schema_version: Literal["vc.multi-agent-value-free-handoff.v1"]
    output_fingerprint: None
    prediction: None
    numerical_result: None
    evidence_fingerprint: None
    policy_fingerprint: None
    status: Literal["not_run_contract_only"]
    executable: Literal[False]
    execution_performed: Literal[False]
    external_action_performed: Literal[False]
    advisory_only: Literal[True]
    counts_for_real_acceptance: Literal[False]
    abstain: Literal[True]
    record_role: Literal["p28e_value_free_handoff"]

    @field_validator("handoff_id", mode="before")
    @classmethod
    def _handoff_id(cls, value):
        value = _strict_text(value, "handoff_id")
        if not _CONTENT_ID.fullmatch(value) or not value.startswith("handoff_"):
            raise ValueError("handoff_id is malformed")
        return value

    @field_validator("sender_role_id", "receiver_role_id", mode="before")
    @classmethod
    def _roles(cls, value, info):
        value = _strict_text(value, info.field_name)
        if not _ROLE_ID.fullmatch(value):
            raise ValueError(f"{info.field_name} is malformed")
        return value

    @field_validator(
        "sender_policy_fingerprint",
        "receiver_policy_fingerprint",
        "input_fingerprint",
        mode="before",
    )
    @classmethod
    def _fingerprints(cls, value, info):
        return _strict_fingerprint(value, info.field_name)

    @field_validator("input_schema_version", mode="before")
    @classmethod
    def _input_schema(cls, value):
        value = _strict_text(value, "input_schema_version")
        if value not in _INPUT_SCHEMAS:
            raise ValueError("input_schema_version is not registered")
        return value

    @model_validator(mode="after")
    def _closure(self):
        if self.sender_role_id == self.receiver_role_id:
            raise ValueError("handoff cannot be self-referential")
        identity = self.model_dump(mode="json", exclude={"handoff_id"})
        if self.handoff_id != _content_id("handoff_", identity):
            raise ValueError("handoff_id is stale")
        return self


def _topological_order(
    role_ids: tuple[str, ...],
    handoffs: tuple[MultiAgentHandoffV1, ...],
) -> tuple[str, ...]:
    indegree = {role_id: 0 for role_id in role_ids}
    targets: dict[str, set[str]] = defaultdict(set)
    for handoff in handoffs:
        if handoff.receiver_role_id not in targets[handoff.sender_role_id]:
            targets[handoff.sender_role_id].add(handoff.receiver_role_id)
            indegree[handoff.receiver_role_id] += 1
    ready = sorted(role_id for role_id, count in indegree.items() if count == 0)
    ordered: list[str] = []
    while ready:
        role_id = ready.pop(0)
        ordered.append(role_id)
        for target in sorted(targets[role_id]):
            indegree[target] -= 1
            if indegree[target] == 0:
                ready.append(target)
                ready.sort()
    if len(ordered) != len(role_ids):
        raise ValueError("multi-agent handoff graph must be acyclic")
    return tuple(ordered)


class MultiAgentDAGV1(_P28Contract):
    """A deterministic advisory-only DAG; it never becomes an execution plan."""

    schema_version: Literal["vc.multi-agent-dag.v1"]
    p17_compilation_fingerprint: str
    p27_experiment_fingerprint: str
    p27_replay_result_fingerprint: str
    roles: tuple[MultiAgentRolePolicyV1, ...]
    handoffs: tuple[MultiAgentHandoffV1, ...]
    topological_role_ids: tuple[str, ...]
    execution_steps: tuple[str, ...]
    executable: Literal[False]
    counts_for_real_acceptance: Literal[False]
    record_role: Literal["p28e_advisory_only_dag"]

    @field_validator(
        "p17_compilation_fingerprint",
        "p27_experiment_fingerprint",
        "p27_replay_result_fingerprint",
        mode="before",
    )
    @classmethod
    def _fingerprints(cls, value, info):
        return _strict_fingerprint(value, info.field_name)

    @field_validator("roles", "handoffs", mode="before")
    @classmethod
    def _record_arrays(cls, value, info):
        if type(value) is not list:
            raise ValueError(f"{info.field_name} must be an array")
        return tuple(value)

    @field_validator("topological_role_ids", mode="before")
    @classmethod
    def _topological_ids(cls, value):
        if type(value) is not list:
            raise ValueError("topological_role_ids must be an array")
        values = tuple(_strict_text(item, "topological_role_ids") for item in value)
        if len(set(values)) != len(values):
            raise ValueError("topological_role_ids must be unique")
        return values

    @field_validator("execution_steps", mode="before")
    @classmethod
    def _no_steps(cls, value):
        return _empty_array(value, "execution_steps")

    @model_validator(mode="after")
    def _closure(self):
        roles = tuple(_normalize_exact(item, MultiAgentRolePolicyV1, "role") for item in self.roles)
        handoffs = tuple(_normalize_exact(item, MultiAgentHandoffV1, "handoff") for item in self.handoffs)
        if tuple(role.role_id for role in roles) != tuple(sorted(role.role_id for role in roles)):
            raise ValueError("roles must use canonical role_id order")
        if len({role.role_id for role in roles}) != len(roles):
            raise ValueError("roles must be unique")
        if tuple(item.handoff_id for item in handoffs) != tuple(sorted(item.handoff_id for item in handoffs)):
            raise ValueError("handoffs must use canonical handoff_id order")
        if len({item.handoff_id for item in handoffs}) != len(handoffs):
            raise ValueError("handoffs must be unique")
        by_id = {role.role_id: role for role in roles}
        exact_external_inputs = {
            "vc.virtual-experiment-compilation.v1": self.p17_compilation_fingerprint,
            "vc.virtual-experiment.v1": self.p27_experiment_fingerprint,
            "vc.replay-result.v1": self.p27_replay_result_fingerprint,
        }
        by_fingerprint = {item.fingerprint(): item for item in handoffs}
        sent: dict[str, int] = defaultdict(int)
        for handoff in handoffs:
            sender = by_id.get(handoff.sender_role_id)
            receiver = by_id.get(handoff.receiver_role_id)
            if sender is None or receiver is None:
                raise ValueError("handoff references an undeclared role")
            if handoff.sender_policy_fingerprint != sender.fingerprint():
                raise ValueError("handoff sender policy identity is stale")
            if handoff.receiver_policy_fingerprint != receiver.fingerprint():
                raise ValueError("handoff receiver policy identity is stale")
            if handoff.input_schema_version not in sender.accepted_input_schema_versions:
                raise ValueError("sender does not accept the handoff input schema")
            if handoff.output_schema_version not in receiver.accepted_input_schema_versions:
                raise ValueError("receiver does not accept the handoff output schema")
            expected_input = exact_external_inputs.get(handoff.input_schema_version)
            if expected_input is not None and handoff.input_fingerprint != expected_input:
                raise ValueError("handoff input identity is stale for the bound DAG input")
            if handoff.input_schema_version == "vc.multi-agent-value-free-handoff.v1":
                predecessor = by_fingerprint.get(handoff.input_fingerprint)
                if predecessor is None or predecessor.receiver_role_id != handoff.sender_role_id:
                    raise ValueError("handoff input is not a declared predecessor")
            sent[sender.role_id] += 1
            if sent[sender.role_id] > sender.max_handoffs:
                raise ValueError("role handoff budget exceeded")
        expected_order = _topological_order(tuple(by_id), handoffs)
        if self.topological_role_ids != expected_order:
            raise ValueError("topological_role_ids are stale")
        return self


class MultiAgentTraceEventV1(_P28Contract):
    """One hash-chained statement that a typed handoff was not executed."""

    schema_version: Literal["vc.multi-agent-trace-event.v1"]
    event_id: str
    event_index: int
    previous_event_fingerprint: str
    dag_fingerprint: str
    handoff_fingerprint: str
    event_type: Literal["handoff_not_run_contract_only"]
    status: Literal["not_run"]
    prediction: None
    result: None
    tool_output: None
    evidence_fingerprint: None
    policy_fingerprint: None
    execution_performed: Literal[False]
    external_action_performed: Literal[False]
    record_role: Literal["p28e_value_free_trace_event"]

    @field_validator("event_id", mode="before")
    @classmethod
    def _event_id(cls, value):
        value = _strict_text(value, "event_id")
        if not _CONTENT_ID.fullmatch(value) or not value.startswith("event_"):
            raise ValueError("event_id is malformed")
        return value

    @field_validator("event_index", mode="before")
    @classmethod
    def _event_index(cls, value):
        if type(value) is not int or value < 0:
            raise ValueError("event_index must be a non-negative integer")
        return value

    @field_validator(
        "previous_event_fingerprint",
        "dag_fingerprint",
        "handoff_fingerprint",
        mode="before",
    )
    @classmethod
    def _fingerprints(cls, value, info):
        return _strict_fingerprint(value, info.field_name)

    @model_validator(mode="after")
    def _closure(self):
        identity = self.model_dump(mode="json", exclude={"event_id"})
        if self.event_id != _content_id("event_", identity):
            raise ValueError("event_id is stale")
        return self


class MultiAgentTraceV1(_P28Contract):
    """A deterministic predecessor chain with no executed event or value."""

    schema_version: Literal["vc.multi-agent-trace.v1"]
    trace_id: str
    dag_fingerprint: str
    root_fingerprint: str
    handoff_fingerprints: tuple[str, ...]
    events: tuple[MultiAgentTraceEventV1, ...]
    event_fingerprints: tuple[str, ...]
    last_event_fingerprint: str
    status: Literal["not_run_contract_only"]
    execution_performed: Literal[False]
    external_action_performed: Literal[False]
    replayable_contract_trace: Literal[True]
    record_role: Literal["p28e_value_free_trace"]

    @field_validator("trace_id", mode="before")
    @classmethod
    def _trace_id(cls, value):
        value = _strict_text(value, "trace_id")
        if not _CONTENT_ID.fullmatch(value) or not value.startswith("trace_"):
            raise ValueError("trace_id is malformed")
        return value

    @field_validator("dag_fingerprint", "root_fingerprint", "last_event_fingerprint", mode="before")
    @classmethod
    def _fingerprints(cls, value, info):
        return _strict_fingerprint(value, info.field_name)

    @field_validator("handoff_fingerprints", "event_fingerprints", mode="before")
    @classmethod
    def _fingerprint_arrays(cls, value, info):
        if type(value) is not list:
            raise ValueError(f"{info.field_name} must be an array")
        values = tuple(_strict_fingerprint(item, info.field_name) for item in value)
        if len(set(values)) != len(values):
            raise ValueError(f"{info.field_name} must be unique")
        return values

    @field_validator("events", mode="before")
    @classmethod
    def _events(cls, value):
        if type(value) is not list:
            raise ValueError("events must be an array")
        return tuple(value)

    @model_validator(mode="after")
    def _closure(self):
        events = tuple(_normalize_exact(item, MultiAgentTraceEventV1, "trace event") for item in self.events)
        expected_root = _canonical_fingerprint(
            {"schema_version": "vc.multi-agent-trace-root.v1", "dag_fingerprint": self.dag_fingerprint}
        )
        if self.root_fingerprint != expected_root:
            raise ValueError("trace root identity is stale")
        previous = expected_root
        observed_event_fingerprints: list[str] = []
        for index, event in enumerate(events):
            if event.event_index != index or event.previous_event_fingerprint != previous:
                raise ValueError("trace predecessor chain is broken")
            if event.dag_fingerprint != self.dag_fingerprint:
                raise ValueError("trace event DAG identity is stale")
            if event.handoff_fingerprint not in self.handoff_fingerprints:
                raise ValueError("trace event references an undeclared handoff")
            observed = event.fingerprint()
            observed_event_fingerprints.append(observed)
            previous = observed
        if tuple(event.handoff_fingerprint for event in events) != self.handoff_fingerprints:
            raise ValueError("trace must contain exactly one canonical event per handoff")
        if tuple(observed_event_fingerprints) != self.event_fingerprints:
            raise ValueError("event_fingerprints are stale")
        if self.last_event_fingerprint != previous:
            raise ValueError("last_event_fingerprint is stale")
        identity = self.model_dump(mode="json", exclude={"trace_id"})
        if self.trace_id != _content_id("trace_", identity):
            raise ValueError("trace_id is stale")
        return self


class MultiAgentBiologyCompilationV1(_P28Contract):
    """Authoritative P28E output: exact inputs, empty graph, zero modules, no value."""

    schema_version: Literal["vc.multi-agent-biology-compilation.v1"]
    compilation_id: str
    p17_compilation_fingerprint: str
    p17_request_fingerprint: str
    p27_experiment_fingerprint: str
    p27_request_fingerprint: str
    p27_replay_result_fingerprint: str
    p27_replay_maturity: Literal["synthetic_conformance_only"]
    p27_historical_replay_status: Literal["replay_not_run_asset_pending"]
    p27_shadow_reviewed: Literal[False]
    p27_prospective_pilot: Literal[False]
    orchestration_dag: MultiAgentDAGV1
    orchestration_dag_fingerprint: str
    trace: MultiAgentTraceV1
    trace_fingerprint: str
    role_policy_fingerprints: tuple[str, ...]
    handoff_fingerprints: tuple[str, ...]
    qualifying_module_fingerprints: tuple[str, ...]
    qualifying_module_count: Literal[0]
    required_qualifying_module_count: Literal[3]
    registry_snapshot_fingerprint: None
    compatibility_reports_verified: Literal[False]
    comparison_protocol_fingerprint: None
    comparison_performed: Literal[False]
    ablation_performed: Literal[False]
    prediction: None
    result: None
    tool_output: None
    conflict_status: Literal["not_evaluated_no_execution"]
    partial_failure_status: Literal["not_evaluated_no_execution"]
    executable: Literal[False]
    execution_performed: Literal[False]
    external_action_performed: Literal[False]
    scientifically_validated: Literal[False]
    promotion_eligible: Literal[False]
    production_promoted: Literal[False]
    product_policy_status: Literal["no_new_decision"]
    abstain: Literal[True]
    abstain_reasons: tuple[str, ...]
    record_role: Literal["p28e_contract_only_zero_qualifying_modules"]

    @field_validator("compilation_id", mode="before")
    @classmethod
    def _compilation_id(cls, value):
        value = _strict_text(value, "compilation_id")
        if not _CONTENT_ID.fullmatch(value) or not value.startswith("ma_comp_"):
            raise ValueError("compilation_id is malformed")
        return value

    @field_validator(
        "p17_compilation_fingerprint",
        "p17_request_fingerprint",
        "p27_experiment_fingerprint",
        "p27_request_fingerprint",
        "p27_replay_result_fingerprint",
        "orchestration_dag_fingerprint",
        "trace_fingerprint",
        mode="before",
    )
    @classmethod
    def _fingerprints(cls, value, info):
        return _strict_fingerprint(value, info.field_name)

    @field_validator(
        "role_policy_fingerprints",
        "handoff_fingerprints",
        "qualifying_module_fingerprints",
        mode="before",
    )
    @classmethod
    def _empty_identities(cls, value, info):
        return _empty_array(value, info.field_name)

    @field_validator("abstain_reasons", mode="before")
    @classmethod
    def _reasons(cls, value):
        return _exact_array(value, _ABSTAIN_REASONS, "abstain_reasons")

    @model_validator(mode="after")
    def _closure(self):
        dag = _normalize_exact(self.orchestration_dag, MultiAgentDAGV1, "orchestration_dag")
        trace = validate_value_free_trace(dag, self.trace)
        if self.p17_request_fingerprint != self.p27_request_fingerprint:
            raise ValueError("P17 and P27 request identities differ")
        if not (
            dag.p17_compilation_fingerprint == self.p17_compilation_fingerprint
            and dag.p27_experiment_fingerprint == self.p27_experiment_fingerprint
            and dag.p27_replay_result_fingerprint == self.p27_replay_result_fingerprint
            and self.orchestration_dag_fingerprint == dag.fingerprint()
            and self.trace_fingerprint == trace.fingerprint()
            and trace.dag_fingerprint == dag.fingerprint()
        ):
            raise ValueError("P17/P27/DAG/trace identities are not closed")
        if dag.roles or dag.handoffs or trace.events or trace.handoff_fingerprints:
            raise ValueError("authoritative P28E compilation must keep roles/handoffs/events empty")
        identity = self.model_dump(mode="json", exclude={"compilation_id"})
        if self.compilation_id != _content_id("ma_comp_", identity):
            raise ValueError("compilation_id is stale")
        return self


def build_advisory_role(role_id: str, role_kind: str) -> MultiAgentRolePolicyV1:
    """Create one fixed synthetic advisory policy; it cannot count for P28."""

    return MultiAgentRolePolicyV1.from_dict(
        {
            "schema_version": "vc.multi-agent-role-policy.v1",
            "role_id": role_id,
            "role_kind": role_kind,
            "accepted_input_schema_versions": list(_INPUT_SCHEMAS),
            "output_schema_version": "vc.multi-agent-value-free-handoff.v1",
            "permissions": list(_PERMISSIONS),
            "max_handoffs": 4,
            "timeout_ms": 1000,
            "retry_limit": 0,
            "max_concurrency": 1,
            "resource_class": "local_cpu_contract_only",
            "cancellation_required": True,
            "network_access_allowed": False,
            "filesystem_write_allowed": False,
            "subprocess_allowed": False,
            "device_access_allowed": False,
            "external_action_allowed": False,
            "dynamic_tool_invocation_allowed": False,
            "numerical_output_allowed": False,
            "advisory_only": True,
            "counts_for_real_acceptance": False,
            "scientifically_validated": False,
            "production_promoted": False,
            "record_role": "p28e_synthetic_advisory_conformance",
        }
    )


def build_value_free_handoff(
    sender: MultiAgentRolePolicyV1,
    receiver: MultiAgentRolePolicyV1,
    *,
    input_schema_version: str,
    input_fingerprint: str,
) -> MultiAgentHandoffV1:
    """Bind two exact advisory policies without accepting a free-form payload."""

    sender = _normalize_exact(sender, MultiAgentRolePolicyV1, "sender")
    receiver = _normalize_exact(receiver, MultiAgentRolePolicyV1, "receiver")
    identity = {
        "schema_version": "vc.multi-agent-handoff.v1",
        "sender_role_id": sender.role_id,
        "receiver_role_id": receiver.role_id,
        "sender_policy_fingerprint": sender.fingerprint(),
        "receiver_policy_fingerprint": receiver.fingerprint(),
        "input_schema_version": input_schema_version,
        "input_fingerprint": input_fingerprint,
        "output_schema_version": "vc.multi-agent-value-free-handoff.v1",
        "output_fingerprint": None,
        "prediction": None,
        "numerical_result": None,
        "evidence_fingerprint": None,
        "policy_fingerprint": None,
        "status": "not_run_contract_only",
        "executable": False,
        "execution_performed": False,
        "external_action_performed": False,
        "advisory_only": True,
        "counts_for_real_acceptance": False,
        "abstain": True,
        "record_role": "p28e_value_free_handoff",
    }
    return MultiAgentHandoffV1.from_dict({"handoff_id": _content_id("handoff_", identity), **identity})


def build_advisory_dag(
    *,
    p17_compilation_fingerprint: str,
    p27_experiment_fingerprint: str,
    p27_replay_result_fingerprint: str,
    roles: tuple[MultiAgentRolePolicyV1, ...] = (),
    handoffs: tuple[MultiAgentHandoffV1, ...] = (),
) -> MultiAgentDAGV1:
    """Build a canonical acyclic conformance graph with no execution steps."""

    normalized_roles = tuple(
        sorted(
            (_normalize_exact(role, MultiAgentRolePolicyV1, "role") for role in roles),
            key=lambda item: item.role_id,
        )
    )
    normalized_handoffs = tuple(
        sorted(
            (_normalize_exact(item, MultiAgentHandoffV1, "handoff") for item in handoffs),
            key=lambda item: item.handoff_id,
        )
    )
    role_ids = tuple(role.role_id for role in normalized_roles)
    declared = set(role_ids)
    if len(declared) != len(role_ids):
        raise MultiAgentBiologyContractError("roles must be unique")
    if any(
        item.sender_role_id not in declared or item.receiver_role_id not in declared for item in normalized_handoffs
    ):
        raise MultiAgentBiologyContractError("handoff references an undeclared role")
    try:
        order = _topological_order(role_ids, normalized_handoffs)
    except (KeyError, ValueError) as exc:
        raise MultiAgentBiologyContractError(str(exc)) from exc
    return MultiAgentDAGV1.from_dict(
        {
            "schema_version": "vc.multi-agent-dag.v1",
            "p17_compilation_fingerprint": p17_compilation_fingerprint,
            "p27_experiment_fingerprint": p27_experiment_fingerprint,
            "p27_replay_result_fingerprint": p27_replay_result_fingerprint,
            "roles": [role.to_dict() for role in normalized_roles],
            "handoffs": [handoff.to_dict() for handoff in normalized_handoffs],
            "topological_role_ids": list(order),
            "execution_steps": [],
            "executable": False,
            "counts_for_real_acceptance": False,
            "record_role": "p28e_advisory_only_dag",
        }
    )


def build_value_free_trace(dag: MultiAgentDAGV1) -> MultiAgentTraceV1:
    """Create a predecessor chain recording that each advisory handoff was not run."""

    dag = _normalize_exact(dag, MultiAgentDAGV1, "dag")
    dag_fingerprint = dag.fingerprint()
    root = _canonical_fingerprint(
        {"schema_version": "vc.multi-agent-trace-root.v1", "dag_fingerprint": dag_fingerprint}
    )
    previous = root
    events: list[MultiAgentTraceEventV1] = []
    for index, handoff in enumerate(dag.handoffs):
        identity = {
            "schema_version": "vc.multi-agent-trace-event.v1",
            "event_index": index,
            "previous_event_fingerprint": previous,
            "dag_fingerprint": dag_fingerprint,
            "handoff_fingerprint": handoff.fingerprint(),
            "event_type": "handoff_not_run_contract_only",
            "status": "not_run",
            "prediction": None,
            "result": None,
            "tool_output": None,
            "evidence_fingerprint": None,
            "policy_fingerprint": None,
            "execution_performed": False,
            "external_action_performed": False,
            "record_role": "p28e_value_free_trace_event",
        }
        event = MultiAgentTraceEventV1.from_dict({"event_id": _content_id("event_", identity), **identity})
        events.append(event)
        previous = event.fingerprint()
    identity = {
        "schema_version": "vc.multi-agent-trace.v1",
        "dag_fingerprint": dag_fingerprint,
        "root_fingerprint": root,
        "handoff_fingerprints": [item.fingerprint() for item in dag.handoffs],
        "events": [event.to_dict() for event in events],
        "event_fingerprints": [event.fingerprint() for event in events],
        "last_event_fingerprint": previous,
        "status": "not_run_contract_only",
        "execution_performed": False,
        "external_action_performed": False,
        "replayable_contract_trace": True,
        "record_role": "p28e_value_free_trace",
    }
    trace = MultiAgentTraceV1.from_dict({"trace_id": _content_id("trace_", identity), **identity})
    return validate_value_free_trace(dag, trace)


def validate_value_free_trace(
    dag: MultiAgentDAGV1,
    trace: MultiAgentTraceV1,
) -> MultiAgentTraceV1:
    """Cross-check a trace against the exact DAG rather than trusting a content hash."""

    dag = _normalize_exact(dag, MultiAgentDAGV1, "dag")
    trace = _normalize_exact(trace, MultiAgentTraceV1, "trace")
    expected_handoffs = tuple(item.fingerprint() for item in dag.handoffs)
    if trace.dag_fingerprint != dag.fingerprint() or trace.handoff_fingerprints != expected_handoffs:
        raise MultiAgentBiologyContractError("trace is not bound to the exact DAG handoff set")
    return trace


def compile_multi_agent_biology(
    p17_compilation: VirtualExperimentCompilationV1,
    p27_experiment: VirtualExperimentV1,
    p27_replay_result: ReplayResultV1,
) -> MultiAgentBiologyCompilationV1:
    """Compile the current exact P17/P27 identities into a zero-module abstention."""

    p17 = _normalize_external(
        p17_compilation,
        VirtualExperimentCompilationV1,
        "p17_compilation",
    )
    experiment = _normalize_external(p27_experiment, VirtualExperimentV1, "p27_experiment")
    replay = _normalize_external(p27_replay_result, ReplayResultV1, "p27_replay_result")
    if p17.dag.request_fingerprint != experiment.request_fingerprint:
        raise MultiAgentBiologyContractError("P17 and P27 must bind the same exact request")
    dag = build_advisory_dag(
        p17_compilation_fingerprint=p17.fingerprint(),
        p27_experiment_fingerprint=experiment.fingerprint(),
        p27_replay_result_fingerprint=replay.fingerprint(),
    )
    trace = build_value_free_trace(dag)
    identity = {
        "schema_version": "vc.multi-agent-biology-compilation.v1",
        "p17_compilation_fingerprint": p17.fingerprint(),
        "p17_request_fingerprint": p17.dag.request_fingerprint,
        "p27_experiment_fingerprint": experiment.fingerprint(),
        "p27_request_fingerprint": experiment.request_fingerprint,
        "p27_replay_result_fingerprint": replay.fingerprint(),
        "p27_replay_maturity": "synthetic_conformance_only",
        "p27_historical_replay_status": "replay_not_run_asset_pending",
        "p27_shadow_reviewed": False,
        "p27_prospective_pilot": False,
        "orchestration_dag": dag.to_dict(),
        "orchestration_dag_fingerprint": dag.fingerprint(),
        "trace": trace.to_dict(),
        "trace_fingerprint": trace.fingerprint(),
        "role_policy_fingerprints": [],
        "handoff_fingerprints": [],
        "qualifying_module_fingerprints": [],
        "qualifying_module_count": 0,
        "required_qualifying_module_count": 3,
        "registry_snapshot_fingerprint": None,
        "compatibility_reports_verified": False,
        "comparison_protocol_fingerprint": None,
        "comparison_performed": False,
        "ablation_performed": False,
        "prediction": None,
        "result": None,
        "tool_output": None,
        "conflict_status": "not_evaluated_no_execution",
        "partial_failure_status": "not_evaluated_no_execution",
        "executable": False,
        "execution_performed": False,
        "external_action_performed": False,
        "scientifically_validated": False,
        "promotion_eligible": False,
        "production_promoted": False,
        "product_policy_status": "no_new_decision",
        "abstain": True,
        "abstain_reasons": list(_ABSTAIN_REASONS),
        "record_role": "p28e_contract_only_zero_qualifying_modules",
    }
    return MultiAgentBiologyCompilationV1.from_dict({"compilation_id": _content_id("ma_comp_", identity), **identity})
