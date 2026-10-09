"""P29E strict empty-graph contracts for a limited biological world model.

The current P28 compilation has zero qualifying executable, scientifically
validated, production-promoted model modules.  P29E therefore records missing
state/action/observation/time identities and an empty graph that is explicitly
not connected.  It does not load assets, invent biological nodes, execute a
model, or create scientific evidence or product policy.
"""

from __future__ import annotations

import re
from typing import Any, Literal, TypeVar

from pydantic import ConfigDict, ValidationError, field_validator, model_validator

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
from praxis_virtualcell.multi_agent_biology import MultiAgentBiologyCompilationV1

_CONTENT_ID = re.compile(r"^[a-z][a-z0-9_]*_[0-9a-f]{24}$")
_ABSTAIN_REASONS = (
    "p28_has_no_qualifying_executable_model_modules",
    "state_action_observation_time_identity_unavailable",
    "real_connected_adjacent_scale_subgraph_unavailable",
    "p29_real_data_model_benchmark_not_authorized",
)


class LimitedWorldModelContractError(ValueError):
    """A P29E record crossed its strict empty-graph trust boundary."""


class _P29Contract(_AdapterContract):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    @classmethod
    def from_dict(cls, value: dict[str, Any]):
        if type(value) is not dict:
            raise LimitedWorldModelContractError(f"{cls.__name__} must be an exact JSON object")
        try:
            return cls.model_validate(value)
        except (TypeError, ValidationError, ValueError) as exc:
            raise LimitedWorldModelContractError(f"invalid {cls.__name__}: {exc}") from exc


_ModelT = TypeVar("_ModelT", bound=_P29Contract)


def _normalize_exact(value: Any, cls: type[_ModelT], field: str) -> _ModelT:
    try:
        _reject_undeclared_model_fields(value, field)
        if type(value) is not cls:
            raise TypeError(f"{field} must be exact {cls.__name__}")
        normalized = cls.from_dict(value.to_dict())
        _reject_model_type_drift(value, normalized, field)
        return normalized
    except (TypeError, ValidationError, ValueError) as exc:
        raise LimitedWorldModelContractError(f"invalid {field}: {exc}") from exc


def _normalize_p28(value: Any) -> MultiAgentBiologyCompilationV1:
    try:
        _reject_undeclared_model_fields(value, "p28_compilation")
        if type(value) is not MultiAgentBiologyCompilationV1:
            raise TypeError("p28_compilation must be exact MultiAgentBiologyCompilationV1")
        normalized = MultiAgentBiologyCompilationV1.from_dict(value.to_dict())
        _reject_model_type_drift(value, normalized, "p28_compilation")
        return normalized
    except (TypeError, ValidationError, ValueError) as exc:
        raise LimitedWorldModelContractError(f"invalid p28_compilation: {exc}") from exc


def _empty_array(value: Any, field: str) -> tuple[Any, ...]:
    if type(value) is not list or value:
        raise ValueError(f"{field} must be an empty array")
    return ()


class StateActionObservationTimeRequirementV1(_P29Contract):
    """The unavailable real identities required before a P29 graph can exist."""

    schema_version: Literal["vc.state-action-observation-time-requirement.v1"]
    p28_compilation_fingerprint: str
    scope_identity_fingerprint: None
    state_identity_fingerprint: None
    action_identity_fingerprint: None
    observation_identity_fingerprint: None
    time_identity_fingerprint: None
    longitudinal_data_fingerprint: None
    intervention_data_fingerprint: None
    requirement_status: Literal["unavailable_zero_qualifying_biological_nodes"]
    real_identities_available: Literal[False]
    record_role: Literal["p29e_unavailable_real_requirement"]

    @field_validator("p28_compilation_fingerprint", mode="before")
    @classmethod
    def _fingerprint(cls, value):
        return _strict_fingerprint(value, "p28_compilation_fingerprint")


class ConnectedTypedSubgraphV1(_P29Contract):
    """An authoritative empty graph; empty is deliberately not connected."""

    schema_version: Literal["vc.connected-typed-subgraph.v1"]
    p28_compilation_fingerprint: str
    requirement_fingerprint: str
    nodes: tuple[Any, ...]
    edges: tuple[Any, ...]
    scales: tuple[Any, ...]
    qualifying_biological_node_count: Literal[0]
    adjacent_scale_edge_count: Literal[0]
    connected: Literal[False]
    connectivity_status: Literal["empty_not_connected"]
    real_biological_subgraph: Literal[False]
    executable: Literal[False]
    record_role: Literal["p29e_authoritative_empty_subgraph"]

    @field_validator("p28_compilation_fingerprint", "requirement_fingerprint", mode="before")
    @classmethod
    def _fingerprints(cls, value, info):
        return _strict_fingerprint(value, info.field_name)

    @field_validator("nodes", "edges", "scales", mode="before")
    @classmethod
    def _empty_graph_arrays(cls, value, info):
        return _empty_array(value, info.field_name)


class LimitedWorldModelCompilationV1(_P29Contract):
    """Authoritative P29E result: zero nodes, no value and no execution."""

    schema_version: Literal["vc.limited-world-model-compilation.v1"]
    compilation_id: str
    p28_compilation_fingerprint: str
    requirement: StateActionObservationTimeRequirementV1
    requirement_fingerprint: str
    subgraph: ConnectedTypedSubgraphV1
    subgraph_fingerprint: str
    qualifying_biological_node_count: Literal[0]
    real_candidate_status: Literal["blocked_zero_qualifying_biological_nodes"]
    standalone_replay_result_request_bound: Literal[False]
    data_fingerprint: None
    weight_fingerprint: None
    model_fingerprint: None
    environment_fingerprint: None
    adapter_fingerprint: None
    compute_fingerprint: None
    benchmark_protocol_fingerprint: None
    evidence_fingerprint: None
    policy_fingerprint: None
    result_fingerprint: None
    benchmark_status: Literal["not_run"]
    prediction: None
    result: None
    tool_output: None
    rollout: None
    calibration: None
    ood: None
    conservation: None
    counterfactual_consistency: None
    executable: Literal[False]
    execution_performed: Literal[False]
    external_action_performed: Literal[False]
    scientifically_validated: Literal[False]
    promotion_eligible: Literal[False]
    production_promoted: Literal[False]
    product_policy_status: Literal["no_new_decision"]
    abstain: Literal[True]
    abstain_reasons: tuple[str, ...]
    record_role: Literal["p29e_contract_only_zero_qualifying_biological_nodes"]

    @field_validator("compilation_id", mode="before")
    @classmethod
    def _compilation_id(cls, value):
        value = _strict_text(value, "compilation_id")
        if not _CONTENT_ID.fullmatch(value) or not value.startswith("world_comp_"):
            raise ValueError("compilation_id is malformed")
        return value

    @field_validator(
        "p28_compilation_fingerprint",
        "requirement_fingerprint",
        "subgraph_fingerprint",
        mode="before",
    )
    @classmethod
    def _fingerprints(cls, value, info):
        return _strict_fingerprint(value, info.field_name)

    @field_validator("abstain_reasons", mode="before")
    @classmethod
    def _reasons(cls, value):
        if type(value) is not list or tuple(value) != _ABSTAIN_REASONS:
            raise ValueError(f"abstain_reasons must equal {list(_ABSTAIN_REASONS)}")
        return _ABSTAIN_REASONS

    @model_validator(mode="after")
    def _closure(self):
        requirement = _normalize_exact(
            self.requirement,
            StateActionObservationTimeRequirementV1,
            "requirement",
        )
        subgraph = _normalize_exact(self.subgraph, ConnectedTypedSubgraphV1, "subgraph")
        if not (
            requirement.p28_compilation_fingerprint == self.p28_compilation_fingerprint
            and subgraph.p28_compilation_fingerprint == self.p28_compilation_fingerprint
            and self.requirement_fingerprint == requirement.fingerprint()
            and subgraph.requirement_fingerprint == requirement.fingerprint()
            and self.subgraph_fingerprint == subgraph.fingerprint()
        ):
            raise ValueError("P28/requirement/subgraph identities are not closed")
        if subgraph.nodes or subgraph.edges or subgraph.scales or subgraph.connected:
            raise ValueError("authoritative P29E subgraph must remain empty and not connected")
        identity = self.model_dump(mode="json", exclude={"compilation_id"})
        expected = f"world_comp_{_canonical_fingerprint(identity)[:24]}"
        if self.compilation_id != expected:
            raise ValueError("compilation_id is stale")
        return self


def compile_limited_biological_world_model(
    p28_compilation: MultiAgentBiologyCompilationV1,
) -> LimitedWorldModelCompilationV1:
    """Compile the exact zero-module P28 result into P29E abstention."""

    p28 = _normalize_p28(p28_compilation)
    requirement = StateActionObservationTimeRequirementV1.from_dict(
        {
            "schema_version": "vc.state-action-observation-time-requirement.v1",
            "p28_compilation_fingerprint": p28.fingerprint(),
            "scope_identity_fingerprint": None,
            "state_identity_fingerprint": None,
            "action_identity_fingerprint": None,
            "observation_identity_fingerprint": None,
            "time_identity_fingerprint": None,
            "longitudinal_data_fingerprint": None,
            "intervention_data_fingerprint": None,
            "requirement_status": "unavailable_zero_qualifying_biological_nodes",
            "real_identities_available": False,
            "record_role": "p29e_unavailable_real_requirement",
        }
    )
    subgraph = ConnectedTypedSubgraphV1.from_dict(
        {
            "schema_version": "vc.connected-typed-subgraph.v1",
            "p28_compilation_fingerprint": p28.fingerprint(),
            "requirement_fingerprint": requirement.fingerprint(),
            "nodes": [],
            "edges": [],
            "scales": [],
            "qualifying_biological_node_count": 0,
            "adjacent_scale_edge_count": 0,
            "connected": False,
            "connectivity_status": "empty_not_connected",
            "real_biological_subgraph": False,
            "executable": False,
            "record_role": "p29e_authoritative_empty_subgraph",
        }
    )
    identity = {
        "schema_version": "vc.limited-world-model-compilation.v1",
        "p28_compilation_fingerprint": p28.fingerprint(),
        "requirement": requirement.to_dict(),
        "requirement_fingerprint": requirement.fingerprint(),
        "subgraph": subgraph.to_dict(),
        "subgraph_fingerprint": subgraph.fingerprint(),
        "qualifying_biological_node_count": 0,
        "real_candidate_status": "blocked_zero_qualifying_biological_nodes",
        "standalone_replay_result_request_bound": False,
        "data_fingerprint": None,
        "weight_fingerprint": None,
        "model_fingerprint": None,
        "environment_fingerprint": None,
        "adapter_fingerprint": None,
        "compute_fingerprint": None,
        "benchmark_protocol_fingerprint": None,
        "evidence_fingerprint": None,
        "policy_fingerprint": None,
        "result_fingerprint": None,
        "benchmark_status": "not_run",
        "prediction": None,
        "result": None,
        "tool_output": None,
        "rollout": None,
        "calibration": None,
        "ood": None,
        "conservation": None,
        "counterfactual_consistency": None,
        "executable": False,
        "execution_performed": False,
        "external_action_performed": False,
        "scientifically_validated": False,
        "promotion_eligible": False,
        "production_promoted": False,
        "product_policy_status": "no_new_decision",
        "abstain": True,
        "abstain_reasons": list(_ABSTAIN_REASONS),
        "record_role": "p29e_contract_only_zero_qualifying_biological_nodes",
    }
    return LimitedWorldModelCompilationV1.from_dict(
        {
            "compilation_id": f"world_comp_{_canonical_fingerprint(identity)[:24]}",
            **identity,
        }
    )
