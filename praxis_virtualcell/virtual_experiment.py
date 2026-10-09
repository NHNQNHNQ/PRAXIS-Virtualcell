"""Deterministic, contract-only Virtual Experiment DAG compilation.

The compiler consumes the existing v2 capability plan and model registry.  It
does not route models, prepare wrappers, execute predictions, or let a
candidate LLM plan alter authoritative identity or policy decisions.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator

from praxis_virtualcell.core.request_v2 import VirtualCellRequestV2
from praxis_virtualcell.model_zoo.capability_registry import (
    CompatibilityReportV2,
    ExecutionPlanV2,
    ExecutionStepV2,
)
from praxis_virtualcell.model_zoo.registry_v2 import ModelRegistryV2

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PLAN_ID = re.compile(r"^plan_[0-9a-f]{24}$")


class VirtualExperimentContractError(ValueError):
    """Raised when authoritative Virtual Experiment identity is incomplete."""


def _canonical_fingerprint(value: dict[str, Any]) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise ValueError(f"{field} must be a non-empty string without surrounding whitespace")
    return value


def _fingerprint(value: Any, field: str) -> str:
    value = _text(value, field)
    if not _SHA256.fullmatch(value):
        raise ValueError(f"{field} must be a lowercase SHA-256 fingerprint")
    return value


def _fingerprints(
    value: Any,
    field: str,
    *,
    allow_empty: bool = False,
    canonical_order: bool = False,
) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{field} must be an array")
    values = tuple(_fingerprint(item, field) for item in value)
    if not allow_empty and not values:
        raise ValueError(f"{field} must not be empty")
    if len(set(values)) != len(values):
        raise ValueError(f"{field} must not contain duplicates")
    if canonical_order and values != tuple(sorted(values)):
        raise ValueError(f"{field} must use canonical fingerprint order")
    return values


class _Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    @classmethod
    def from_dict(cls, value: dict[str, Any]):
        if not isinstance(value, dict):
            raise VirtualExperimentContractError(f"{cls.__name__} must be a JSON object")
        try:
            return cls.model_validate(value)
        except ValidationError as exc:
            raise VirtualExperimentContractError(f"invalid {cls.__name__}: {exc}") from exc

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def fingerprint(self) -> str:
        return _canonical_fingerprint(self.to_dict())


class VirtualExperimentNodeV1(_Contract):
    """One registry-approved execution step with exact adapter contracts."""

    schema_version: Literal["vc.virtual-experiment-node.v1"]
    execution_step_fingerprint: str
    model_fingerprint: str
    release_fingerprint: str
    capability_fingerprint: str
    environment_fingerprint: str
    adapter_fingerprints: tuple[str, ...]
    input_contract_fingerprints: tuple[str, ...]
    output_contract_fingerprints: tuple[str, ...]

    @field_validator(
        "execution_step_fingerprint",
        "model_fingerprint",
        "release_fingerprint",
        "capability_fingerprint",
        "environment_fingerprint",
        mode="before",
    )
    @classmethod
    def _valid_fingerprint(cls, value, info):
        return _fingerprint(value, info.field_name)

    @field_validator(
        "adapter_fingerprints",
        "input_contract_fingerprints",
        "output_contract_fingerprints",
        mode="before",
    )
    @classmethod
    def _valid_fingerprints(cls, value, info):
        return _fingerprints(value, info.field_name)

    @model_validator(mode="after")
    def _aligned_adapter_contracts(self):
        if not (
            len(self.adapter_fingerprints)
            == len(self.input_contract_fingerprints)
            == len(self.output_contract_fingerprints)
        ):
            raise ValueError("adapter and input/output contract identities must align")
        return self


class VirtualExperimentEdgeV1(_Contract):
    """A typed dependency between two exact execution-step identities."""

    schema_version: Literal["vc.virtual-experiment-edge.v1"]
    source_step_fingerprint: str
    target_step_fingerprint: str
    output_contract_fingerprint: str
    input_contract_fingerprint: str

    @field_validator(
        "source_step_fingerprint",
        "target_step_fingerprint",
        "output_contract_fingerprint",
        "input_contract_fingerprint",
        mode="before",
    )
    @classmethod
    def _valid_fingerprint(cls, value, info):
        return _fingerprint(value, info.field_name)

    @model_validator(mode="after")
    def _not_self_referential(self):
        if self.source_step_fingerprint == self.target_step_fingerprint:
            raise ValueError("virtual experiment edges cannot be self-referential")
        return self


class VirtualExperimentDAGV1(_Contract):
    """The authoritative deterministic graph; candidate plans never enter it."""

    schema_version: Literal["vc.virtual-experiment-dag.v1"]
    request_id: str
    request_fingerprint: str
    cell_context_fingerprint: str
    pack_id: str
    pack_version: str
    pack_fingerprint: str
    environment_snapshot_fingerprint: str
    plan_id: str
    plan_fingerprint: str
    validated_step_fingerprints: tuple[str, ...] = ()
    participating_capability_fingerprints: tuple[str, ...] = ()
    nodes: tuple[VirtualExperimentNodeV1, ...] = ()
    edges: tuple[VirtualExperimentEdgeV1, ...] = ()

    @field_validator("request_id", "pack_id", "pack_version", mode="before")
    @classmethod
    def _valid_text(cls, value, info):
        return _text(value, info.field_name)

    @field_validator("plan_id", mode="before")
    @classmethod
    def _valid_plan_id(cls, value):
        value = _text(value, "plan_id")
        if not _PLAN_ID.fullmatch(value):
            raise ValueError("plan_id must be plan_ plus 24 lowercase hex characters")
        return value

    @field_validator(
        "request_fingerprint",
        "cell_context_fingerprint",
        "pack_fingerprint",
        "environment_snapshot_fingerprint",
        "plan_fingerprint",
        mode="before",
    )
    @classmethod
    def _valid_fingerprint(cls, value, info):
        return _fingerprint(value, info.field_name)

    @field_validator(
        "validated_step_fingerprints",
        "participating_capability_fingerprints",
        mode="before",
    )
    @classmethod
    def _valid_fingerprints(cls, value, info):
        return _fingerprints(
            value,
            info.field_name,
            allow_empty=True,
            canonical_order=True,
        )

    @field_validator("nodes", "edges", mode="before")
    @classmethod
    def _valid_arrays(cls, value, info):
        if not isinstance(value, (list, tuple)):
            raise ValueError(f"{info.field_name} must be an array")
        return tuple(value)

    @model_validator(mode="after")
    def _valid_graph(self):
        if self.plan_id != f"plan_{self.plan_fingerprint[:24]}":
            raise ValueError("plan_id does not match plan_fingerprint")
        node_ids = tuple(node.execution_step_fingerprint for node in self.nodes)
        if len(set(node_ids)) != len(node_ids):
            raise ValueError("virtual experiment nodes must have unique step identities")
        if node_ids != tuple(sorted(node_ids)):
            raise ValueError("virtual experiment nodes must use canonical step order")
        if self.nodes and not (
            node_ids == self.validated_step_fingerprints
            and tuple(sorted({node.capability_fingerprint for node in self.nodes}))
            == self.participating_capability_fingerprints
        ):
            raise ValueError("DAG nodes do not match validated participants")

        edge_keys = tuple((edge.source_step_fingerprint, edge.target_step_fingerprint) for edge in self.edges)
        if len(set(edge_keys)) != len(edge_keys):
            raise ValueError("duplicate virtual experiment edges are not allowed")
        if edge_keys != tuple(sorted(edge_keys)):
            raise ValueError("virtual experiment edges must use canonical order")

        by_id = {node.execution_step_fingerprint: node for node in self.nodes}
        for edge in self.edges:
            source = by_id.get(edge.source_step_fingerprint)
            target = by_id.get(edge.target_step_fingerprint)
            if source is None or target is None:
                raise ValueError("virtual experiment edge references an unknown node")
            if (
                edge.output_contract_fingerprint not in source.output_contract_fingerprints
                or edge.input_contract_fingerprint not in target.input_contract_fingerprints
                or edge.output_contract_fingerprint != edge.input_contract_fingerprint
            ):
                raise ValueError("virtual experiment edge contracts do not match")

        indegree = {node_id: 0 for node_id in node_ids}
        outgoing = {node_id: [] for node_id in node_ids}
        for source, target in edge_keys:
            outgoing[source].append(target)
            indegree[target] += 1
        ready = sorted(node_id for node_id, degree in indegree.items() if degree == 0)
        visited = 0
        while ready:
            current = ready.pop(0)
            visited += 1
            for target in sorted(outgoing[current]):
                indegree[target] -= 1
                if indegree[target] == 0:
                    ready.append(target)
                    ready.sort()
        if visited != len(node_ids):
            raise ValueError("virtual experiment graph must be acyclic")
        return self


class VirtualCellBrainContextV1(_Contract):
    """Immutable decision context bound to every relevant public identity."""

    schema_version: Literal["vc.virtual-cell-brain-context.v1"]
    request_id: str
    request_fingerprint: str
    cell_context_fingerprint: str
    pack_id: str
    pack_version: str
    pack_fingerprint: str
    environment_snapshot_fingerprint: str
    plan_id: str
    plan_fingerprint: str
    dag_fingerprint: str
    execution_step_fingerprints: tuple[str, ...] = ()
    participating_capability_fingerprints: tuple[str, ...] = ()
    compatibility_fingerprints: tuple[str, ...] = ()
    model_fingerprints: tuple[str, ...] = ()
    release_fingerprints: tuple[str, ...] = ()
    capability_fingerprints: tuple[str, ...] = ()
    environment_fingerprints: tuple[str, ...] = ()
    adapter_fingerprints: tuple[str, ...] = ()
    adapter_input_contract_fingerprints: tuple[str, ...] = ()
    adapter_output_contract_fingerprints: tuple[str, ...] = ()
    evidence_fingerprints: tuple[str, ...] = ()
    policy_fingerprints: tuple[str, ...] = ()

    @field_validator("request_id", "pack_id", "pack_version", mode="before")
    @classmethod
    def _valid_text(cls, value, info):
        return _text(value, info.field_name)

    @field_validator("plan_id", mode="before")
    @classmethod
    def _valid_plan_id(cls, value):
        value = _text(value, "plan_id")
        if not _PLAN_ID.fullmatch(value):
            raise ValueError("plan_id must be plan_ plus 24 lowercase hex characters")
        return value

    @field_validator(
        "request_fingerprint",
        "cell_context_fingerprint",
        "pack_fingerprint",
        "environment_snapshot_fingerprint",
        "plan_fingerprint",
        "dag_fingerprint",
        mode="before",
    )
    @classmethod
    def _valid_fingerprint(cls, value, info):
        return _fingerprint(value, info.field_name)

    @field_validator(
        "execution_step_fingerprints",
        "participating_capability_fingerprints",
        "compatibility_fingerprints",
        "model_fingerprints",
        "release_fingerprints",
        "capability_fingerprints",
        "environment_fingerprints",
        "adapter_fingerprints",
        "adapter_input_contract_fingerprints",
        "adapter_output_contract_fingerprints",
        "evidence_fingerprints",
        "policy_fingerprints",
        mode="before",
    )
    @classmethod
    def _valid_fingerprints(cls, value, info):
        return _fingerprints(
            value,
            info.field_name,
            allow_empty=True,
            canonical_order=True,
        )


class VirtualExperimentDecisionV1(_Contract):
    """Fail-closed P17 verdict; this phase authorizes no model execution."""

    schema_version: Literal["vc.virtual-experiment-decision.v1"]
    dag_fingerprint: str
    brain_fingerprint: str
    participating_capability_fingerprints: tuple[str, ...]
    participating_capability_count: int
    eligible_for_multi_model_execution: bool
    executable: Literal[False]
    execution_performed: Literal[False]
    conflict_detected: Literal[False]
    partial_failure_detected: Literal[False]
    abstain: Literal[True]
    final_verdict: Literal["abstain"]
    reason: Literal[
        "insufficient_production_promoted_capabilities",
        "contract_only_execution_not_authorized",
    ]

    @field_validator("dag_fingerprint", "brain_fingerprint", mode="before")
    @classmethod
    def _valid_fingerprint(cls, value, info):
        return _fingerprint(value, info.field_name)

    @field_validator("participating_capability_fingerprints", mode="before")
    @classmethod
    def _valid_capabilities(cls, value):
        return _fingerprints(
            value,
            "participating_capability_fingerprints",
            allow_empty=True,
            canonical_order=True,
        )

    @field_validator("participating_capability_count")
    @classmethod
    def _valid_count(cls, value):
        if value < 0:
            raise ValueError("participating_capability_count must be non-negative")
        return value

    @model_validator(mode="after")
    def _consistent_verdict(self):
        if self.participating_capability_count != len(self.participating_capability_fingerprints):
            raise ValueError("participating capability count does not match identities")
        eligible = len(self.participating_capability_fingerprints) >= 2
        if self.eligible_for_multi_model_execution != eligible:
            raise ValueError("multi-model eligibility must require two capabilities")
        expected_reason = (
            "contract_only_execution_not_authorized" if eligible else "insufficient_production_promoted_capabilities"
        )
        if self.reason != expected_reason:
            raise ValueError("virtual experiment decision reason is inconsistent")
        return self


class CandidateDAGV1(_Contract):
    """Strict, non-authoritative proposal shape accepted from an LLM boundary."""

    schema_version: Literal["vc.candidate-virtual-experiment-dag.v1"]
    request_fingerprint: str
    plan_id: str
    plan_fingerprint: str
    step_fingerprints: tuple[str, ...] = ()
    edges: tuple[VirtualExperimentEdgeV1, ...] = ()

    @field_validator("request_fingerprint", "plan_fingerprint", mode="before")
    @classmethod
    def _valid_fingerprint(cls, value, info):
        return _fingerprint(value, info.field_name)

    @field_validator("plan_id", mode="before")
    @classmethod
    def _valid_plan_id(cls, value):
        value = _text(value, "plan_id")
        if not _PLAN_ID.fullmatch(value):
            raise ValueError("plan_id must be plan_ plus 24 lowercase hex characters")
        return value

    @field_validator("step_fingerprints", mode="before")
    @classmethod
    def _valid_steps(cls, value):
        return _fingerprints(
            value,
            "step_fingerprints",
            allow_empty=True,
            canonical_order=True,
        )

    @field_validator("edges", mode="before")
    @classmethod
    def _valid_edges(cls, value):
        if not isinstance(value, (list, tuple)):
            raise ValueError("edges must be an array")
        return tuple(value)

    @model_validator(mode="after")
    def _consistent_plan_identity(self):
        if self.plan_id != f"plan_{self.plan_fingerprint[:24]}":
            raise ValueError("candidate plan_id does not match plan_fingerprint")
        edge_keys = tuple((edge.source_step_fingerprint, edge.target_step_fingerprint) for edge in self.edges)
        if len(set(edge_keys)) != len(edge_keys) or edge_keys != tuple(sorted(edge_keys)):
            raise ValueError("candidate edges must be unique and canonically ordered")
        if any(
            edge.source_step_fingerprint not in self.step_fingerprints
            or edge.target_step_fingerprint not in self.step_fingerprints
            for edge in self.edges
        ):
            raise ValueError("candidate edge references an undeclared step")
        return self


class CandidateDAGReviewV1(_Contract):
    """Non-authoritative audit status for an optional candidate LLM plan."""

    schema_version: Literal["vc.candidate-dag-review.v1"]
    status: Literal["not_provided", "matched", "rejected", "unavailable"]
    reason: Literal[
        "candidate_not_provided",
        "candidate_matched_authoritative_dag",
        "candidate_rejected_by_deterministic_validation",
        "candidate_generation_unavailable",
    ]
    authoritative_dag_changed: Literal[False] = False

    @model_validator(mode="after")
    def _consistent_status(self):
        reasons = {
            "not_provided": "candidate_not_provided",
            "matched": "candidate_matched_authoritative_dag",
            "rejected": "candidate_rejected_by_deterministic_validation",
            "unavailable": "candidate_generation_unavailable",
        }
        if self.reason != reasons[self.status]:
            raise ValueError("candidate DAG review status and reason differ")
        return self


class VirtualExperimentCompilationV1(_Contract):
    """Authoritative DAG, Brain context, verdict, and separate candidate audit."""

    schema_version: Literal["vc.virtual-experiment-compilation.v1"]
    dag: VirtualExperimentDAGV1
    brain_context: VirtualCellBrainContextV1
    decision: VirtualExperimentDecisionV1
    candidate_review: CandidateDAGReviewV1
    candidate_review_fingerprint: str

    @field_validator("candidate_review_fingerprint", mode="before")
    @classmethod
    def _valid_candidate_review_fingerprint(cls, value):
        return _fingerprint(value, "candidate_review_fingerprint")

    @model_validator(mode="after")
    def _consistent_compilation(self):
        dag_fingerprint = self.dag.fingerprint()
        brain_fingerprint = self.brain_context.fingerprint()
        if not (
            self.brain_context.request_id == self.dag.request_id
            and self.brain_context.request_fingerprint == self.dag.request_fingerprint
            and self.brain_context.cell_context_fingerprint == self.dag.cell_context_fingerprint
            and self.brain_context.pack_id == self.dag.pack_id
            and self.brain_context.pack_version == self.dag.pack_version
            and self.brain_context.pack_fingerprint == self.dag.pack_fingerprint
            and self.brain_context.environment_snapshot_fingerprint == self.dag.environment_snapshot_fingerprint
            and self.brain_context.plan_id == self.dag.plan_id
            and self.brain_context.plan_fingerprint == self.dag.plan_fingerprint
            and self.brain_context.dag_fingerprint == dag_fingerprint
        ):
            raise ValueError("Brain context does not match the authoritative DAG")
        if not (
            self.decision.dag_fingerprint == dag_fingerprint and self.decision.brain_fingerprint == brain_fingerprint
        ):
            raise ValueError("virtual experiment decision identity does not match")
        if self.candidate_review_fingerprint != self.candidate_review.fingerprint():
            raise ValueError("candidate review fingerprint does not match audit status")

        if (
            self.decision.participating_capability_fingerprints
            != self.brain_context.participating_capability_fingerprints
            or self.decision.participating_capability_fingerprints != self.dag.participating_capability_fingerprints
            or self.brain_context.execution_step_fingerprints != self.dag.validated_step_fingerprints
            or not set(self.decision.participating_capability_fingerprints).issubset(
                self.brain_context.capability_fingerprints
            )
        ):
            raise ValueError("participating capabilities do not match Brain context")
        dag_steps = tuple(sorted(node.execution_step_fingerprint for node in self.dag.nodes))
        dag_capabilities = tuple(sorted({node.capability_fingerprint for node in self.dag.nodes}))
        dag_adapters = tuple(sorted({item for node in self.dag.nodes for item in node.adapter_fingerprints}))
        dag_input_contracts = tuple(
            sorted({item for node in self.dag.nodes for item in node.input_contract_fingerprints})
        )
        dag_output_contracts = tuple(
            sorted({item for node in self.dag.nodes for item in node.output_contract_fingerprints})
        )
        if self.decision.eligible_for_multi_model_execution:
            if not (
                dag_steps == self.brain_context.execution_step_fingerprints
                and dag_capabilities == self.decision.participating_capability_fingerprints
                and set(dag_adapters).issubset(self.brain_context.adapter_fingerprints)
                and set(dag_input_contracts).issubset(self.brain_context.adapter_input_contract_fingerprints)
                and set(dag_output_contracts).issubset(self.brain_context.adapter_output_contract_fingerprints)
            ):
                raise ValueError("eligible DAG participants do not match Brain and decision")
        elif self.dag.nodes:
            raise ValueError("ineligible multi-model DAG must not expose execution nodes")
        return self

    def authoritative_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "dag": self.dag.to_dict(),
            "brain_context": self.brain_context.to_dict(),
            "decision": self.decision.to_dict(),
        }

    def authoritative_fingerprint(self) -> str:
        return _canonical_fingerprint(self.authoritative_dict())

    def fingerprint(self) -> str:
        """Candidate review is deliberately excluded from authoritative identity."""
        return self.authoritative_fingerprint()


def _canonical_contract(value, contract_type, label: str):
    if type(value) is not contract_type:
        raise VirtualExperimentContractError(f"{label} requires exact {contract_type.__name__}")
    try:
        raw = BaseModel.model_dump(value, mode="json")
        return contract_type.from_dict(raw)
    except (TypeError, ValueError) as exc:
        raise VirtualExperimentContractError(f"{label} is not a canonically valid {contract_type.__name__}") from exc


def execution_plan_fingerprint(plan: ExecutionPlanV2) -> str:
    """Hash the public-safe canonical v2 plan identity used to derive plan_id."""
    plan = _canonical_contract(plan, ExecutionPlanV2, "execution plan fingerprint")
    identity = {
        "request_id": plan.request_id,
        "request_fingerprint": plan.request_fingerprint,
        "pack_fingerprint": plan.pack_fingerprint,
        "environment_snapshot_fingerprint": plan.environment_snapshot_fingerprint,
        "reports": [report.fingerprint() for report in plan.reports],
        "steps": [step.identity_dict() for step in plan.steps],
    }
    return _canonical_fingerprint(identity)


def _registry_report_bindings(
    report: CompatibilityReportV2,
    registry: ModelRegistryV2,
    pack_fingerprint: str,
) -> None:
    if report.release_fingerprint is None:
        return
    try:
        release = registry.release(report.release_fingerprint)
        state = registry.state(report.release_fingerprint)
    except KeyError as exc:
        raise VirtualExperimentContractError("compatibility report references an unknown release") from exc

    if not (
        release.model_name == report.model_name
        and release.model_version == report.model_version
        and release.model_fingerprint == report.model_fingerprint
        and release.capability_fingerprint() == report.capability_fingerprint
        and release.artifact_fingerprints == report.artifact_fingerprints
        and release.environment_fingerprint == report.environment_fingerprint
        and release.adapter_fingerprints == report.adapter_fingerprints
        and release.evidence_fingerprints == report.evidence_fingerprints
        and release.policy_fingerprint == report.policy_fingerprint
        and state.cataloged == report.cataloged
        and state.artifact_ready == report.artifact_ready
        and state.revoked == report.revoked
        and state.superseded_by == report.superseded_by
    ):
        raise VirtualExperimentContractError("compatibility report no longer matches the model registry")

    try:
        evidence = tuple(registry.evidence(item) for item in release.evidence_fingerprints)
        policy = registry.policy(release.policy_fingerprint) if release.policy_fingerprint is not None else None
    except KeyError as exc:
        raise VirtualExperimentContractError("compatibility report has incomplete evidence or policy bindings") from exc

    evidence_present = bool(evidence and any(item.pack_fingerprint == pack_fingerprint for item in evidence))
    expected_evidence = (
        (
            all(item.benchmark_passed for item in evidence),
            all(item.scientifically_validated for item in evidence),
            all(item.promotion_eligible for item in evidence),
        )
        if evidence_present
        else (None, None, None)
    )
    if expected_evidence != (
        report.benchmark_passed,
        report.scientifically_validated,
        report.promotion_eligible,
    ):
        raise VirtualExperimentContractError("compatibility evidence state no longer matches the registry")
    if not (
        report.policy_present == (policy is not None)
        and report.production_promoted == bool(policy is not None and policy.production_promoted)
    ):
        raise VirtualExperimentContractError("compatibility policy state no longer matches the registry")


def _node_from_step(
    step: ExecutionStepV2,
    registry: ModelRegistryV2,
    pack_fingerprint: str,
) -> VirtualExperimentNodeV1:
    try:
        release = registry.release(step.release_fingerprint)
        state = registry.state(step.release_fingerprint)
        environment = registry.environment(step.environment_fingerprint)
        evidence = tuple(registry.evidence(item) for item in step.evidence_fingerprints)
        policy = registry.policy(step.policy_fingerprint)
        adapters = tuple(registry.adapter(item) for item in step.adapter_fingerprints)
    except KeyError as exc:
        raise VirtualExperimentContractError("execution step has an incomplete registry identity") from exc

    if not (
        release.migration_status == "native"
        and release.pack_fingerprints == (pack_fingerprint,)
        and release.model_name == step.model_name
        and release.model_version == step.model_version
        and release.model_fingerprint == step.model_fingerprint
        and release.capability_fingerprint() == step.capability_fingerprint
        and release.artifact_fingerprints == step.artifact_fingerprints
        and release.environment_fingerprint == step.environment_fingerprint
        and release.adapter_fingerprints == step.adapter_fingerprints
        and release.evidence_fingerprints == step.evidence_fingerprints
        and release.policy_fingerprint == step.policy_fingerprint
        and state.cataloged
        and state.artifact_ready
        and not state.revoked
        and state.superseded_by is None
        and environment.adapter_fingerprints == step.adapter_fingerprints
        and adapters
        and all(not adapter.legacy_incomplete for adapter in adapters)
        and all(
            adapter.input_contract_fingerprint is not None and adapter.output_contract_fingerprint is not None
            for adapter in adapters
        )
        and evidence
        and all(item.pack_fingerprint == pack_fingerprint for item in evidence)
        and all(item.benchmark_passed for item in evidence)
        and all(item.scientifically_validated for item in evidence)
        and all(item.promotion_eligible for item in evidence)
        and policy.capability_fingerprint == step.capability_fingerprint
        and policy.evidence_fingerprints == step.evidence_fingerprints
        and policy.production_promoted
    ):
        raise VirtualExperimentContractError("execution step does not satisfy exact production-promoted bindings")

    input_contracts = tuple(adapter.input_contract_fingerprint for adapter in adapters)
    output_contracts = tuple(adapter.output_contract_fingerprint for adapter in adapters)
    assert all(item is not None for item in input_contracts)
    assert all(item is not None for item in output_contracts)
    return VirtualExperimentNodeV1(
        schema_version="vc.virtual-experiment-node.v1",
        execution_step_fingerprint=step.fingerprint(),
        model_fingerprint=step.model_fingerprint,
        release_fingerprint=step.release_fingerprint,
        capability_fingerprint=step.capability_fingerprint,
        environment_fingerprint=step.environment_fingerprint,
        adapter_fingerprints=step.adapter_fingerprints,
        input_contract_fingerprints=input_contracts,
        output_contract_fingerprints=output_contracts,
    )


def _candidate_review(
    candidate_dag: object,
    dag: VirtualExperimentDAGV1,
) -> CandidateDAGReviewV1:
    if candidate_dag is None:
        status = "not_provided"
        reason = "candidate_not_provided"
    elif isinstance(candidate_dag, BaseException):
        status = "unavailable"
        reason = "candidate_generation_unavailable"
    else:
        try:
            candidate = CandidateDAGV1.from_dict(candidate_dag)
        except (TypeError, ValueError):
            candidate = None
        expected_steps = tuple(node.execution_step_fingerprint for node in dag.nodes)
        if candidate is not None and (
            candidate.request_fingerprint == dag.request_fingerprint
            and candidate.plan_id == dag.plan_id
            and candidate.plan_fingerprint == dag.plan_fingerprint
            and candidate.step_fingerprints == expected_steps
            and candidate.edges == dag.edges
        ):
            status = "matched"
            reason = "candidate_matched_authoritative_dag"
        else:
            status = "rejected"
            reason = "candidate_rejected_by_deterministic_validation"
    return CandidateDAGReviewV1(
        schema_version="vc.candidate-dag-review.v1",
        status=status,
        reason=reason,
        authoritative_dag_changed=False,
    )


def _sorted_unique(values) -> tuple[str, ...]:
    return tuple(sorted(set(values)))


def compile_virtual_experiment(
    request: VirtualCellRequestV2,
    plan: ExecutionPlanV2,
    registry: ModelRegistryV2,
    candidate_dag: object = None,
) -> VirtualExperimentCompilationV1:
    """Compile a replayable P17 contract without executing any model."""
    request = _canonical_contract(
        request,
        VirtualCellRequestV2,
        "Virtual Experiment request",
    )
    plan = _canonical_contract(
        plan,
        ExecutionPlanV2,
        "Virtual Experiment plan",
    )
    registry = _canonical_contract(
        registry,
        ModelRegistryV2,
        "Virtual Experiment registry",
    )

    request_fingerprint = _canonical_fingerprint(request.to_dict())
    if not (request.request_id == plan.request_id and request_fingerprint == plan.request_fingerprint):
        raise VirtualExperimentContractError("request identity does not match the execution plan")
    if plan.pack_id is None or plan.pack_version is None or plan.pack_fingerprint is None:
        raise VirtualExperimentContractError("Virtual Experiment compilation requires exact Pack identity")

    for report in plan.reports:
        _registry_report_bindings(report, registry, plan.pack_fingerprint)

    validated_nodes = tuple(
        sorted(
            (_node_from_step(step, registry, plan.pack_fingerprint) for step in plan.steps),
            key=lambda node: node.execution_step_fingerprint,
        )
    )
    validated_step_fingerprints = _sorted_unique(node.execution_step_fingerprint for node in validated_nodes)
    participating_capability_fingerprints = _sorted_unique(node.capability_fingerprint for node in validated_nodes)
    capability_count = len(participating_capability_fingerprints)
    eligible = capability_count >= 2
    authoritative_nodes = validated_nodes if eligible else ()
    plan_fingerprint = execution_plan_fingerprint(plan)
    cell_context_fingerprint = _canonical_fingerprint(request.cell_context.to_dict())

    dag = VirtualExperimentDAGV1(
        schema_version="vc.virtual-experiment-dag.v1",
        request_id=request.request_id,
        request_fingerprint=request_fingerprint,
        cell_context_fingerprint=cell_context_fingerprint,
        pack_id=plan.pack_id,
        pack_version=plan.pack_version,
        pack_fingerprint=plan.pack_fingerprint,
        environment_snapshot_fingerprint=plan.environment_snapshot_fingerprint,
        plan_id=plan.plan_id,
        plan_fingerprint=plan_fingerprint,
        validated_step_fingerprints=validated_step_fingerprints,
        participating_capability_fingerprints=(participating_capability_fingerprints),
        nodes=authoritative_nodes,
        edges=(),
    )

    adapter_fingerprints = _sorted_unique(item for report in plan.reports for item in report.adapter_fingerprints)
    adapters = tuple(registry.adapter(item) for item in adapter_fingerprints)
    brain = VirtualCellBrainContextV1(
        schema_version="vc.virtual-cell-brain-context.v1",
        request_id=request.request_id,
        request_fingerprint=request_fingerprint,
        cell_context_fingerprint=cell_context_fingerprint,
        pack_id=plan.pack_id,
        pack_version=plan.pack_version,
        pack_fingerprint=plan.pack_fingerprint,
        environment_snapshot_fingerprint=plan.environment_snapshot_fingerprint,
        plan_id=plan.plan_id,
        plan_fingerprint=plan_fingerprint,
        dag_fingerprint=dag.fingerprint(),
        execution_step_fingerprints=validated_step_fingerprints,
        participating_capability_fingerprints=(participating_capability_fingerprints),
        compatibility_fingerprints=_sorted_unique(report.fingerprint() for report in plan.reports),
        model_fingerprints=_sorted_unique(report.model_fingerprint for report in plan.reports),
        release_fingerprints=_sorted_unique(
            report.release_fingerprint for report in plan.reports if report.release_fingerprint is not None
        ),
        capability_fingerprints=_sorted_unique(
            report.capability_fingerprint for report in plan.reports if report.capability_fingerprint is not None
        ),
        environment_fingerprints=_sorted_unique(
            report.environment_fingerprint for report in plan.reports if report.environment_fingerprint is not None
        ),
        adapter_fingerprints=adapter_fingerprints,
        adapter_input_contract_fingerprints=_sorted_unique(
            adapter.input_contract_fingerprint for adapter in adapters if adapter.input_contract_fingerprint is not None
        ),
        adapter_output_contract_fingerprints=_sorted_unique(
            adapter.output_contract_fingerprint
            for adapter in adapters
            if adapter.output_contract_fingerprint is not None
        ),
        evidence_fingerprints=_sorted_unique(item for report in plan.reports for item in report.evidence_fingerprints),
        policy_fingerprints=_sorted_unique(
            report.policy_fingerprint for report in plan.reports if report.policy_fingerprint is not None
        ),
    )
    decision = VirtualExperimentDecisionV1(
        schema_version="vc.virtual-experiment-decision.v1",
        dag_fingerprint=dag.fingerprint(),
        brain_fingerprint=brain.fingerprint(),
        participating_capability_fingerprints=(participating_capability_fingerprints),
        participating_capability_count=capability_count,
        eligible_for_multi_model_execution=eligible,
        executable=False,
        execution_performed=False,
        conflict_detected=False,
        partial_failure_detected=False,
        abstain=True,
        final_verdict="abstain",
        reason=(
            "contract_only_execution_not_authorized" if eligible else "insufficient_production_promoted_capabilities"
        ),
    )
    candidate_review = _candidate_review(candidate_dag, dag)
    return VirtualExperimentCompilationV1(
        schema_version="vc.virtual-experiment-compilation.v1",
        dag=dag,
        brain_context=brain,
        decision=decision,
        candidate_review=candidate_review,
        candidate_review_fingerprint=candidate_review.fingerprint(),
    )
