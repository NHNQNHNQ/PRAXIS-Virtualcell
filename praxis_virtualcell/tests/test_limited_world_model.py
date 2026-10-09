from __future__ import annotations

import inspect

import pytest

from praxis_virtualcell.limited_world_model import (
    ConnectedTypedSubgraphV1,
    LimitedWorldModelCompilationV1,
    LimitedWorldModelContractError,
    StateActionObservationTimeRequirementV1,
    compile_limited_biological_world_model,
)
from praxis_virtualcell.model_zoo.adapter_sdk import _fingerprint
from praxis_virtualcell.multi_agent_biology import (
    MultiAgentBiologyCompilationV1,
    compile_multi_agent_biology,
)
from praxis_virtualcell.tests.test_multi_agent_biology import _exact_inputs


def _p28(*, p17_participant_count: int = 0, secret_prose: bool = False):
    return compile_multi_agent_biology(
        *_exact_inputs(
            p17_participant_count=p17_participant_count,
            secret_prose=secret_prose,
        )
    )


def _resign(raw: dict[str, object]) -> None:
    payload = {key: value for key, value in raw.items() if key != "compilation_id"}
    raw["compilation_id"] = "world_comp_" + _fingerprint(payload)[:24]


def test_compilation_is_deterministic_empty_not_connected_and_value_free() -> None:
    first = compile_limited_biological_world_model(_p28(secret_prose=True))
    second = compile_limited_biological_world_model(_p28(secret_prose=True))

    assert first == second
    assert first.fingerprint() == second.fingerprint()
    assert first.requirement.real_identities_available is False
    assert (
        first.requirement.scope_identity_fingerprint
        is first.requirement.state_identity_fingerprint
        is first.requirement.action_identity_fingerprint
        is first.requirement.observation_identity_fingerprint
        is first.requirement.time_identity_fingerprint
        is first.requirement.longitudinal_data_fingerprint
        is first.requirement.intervention_data_fingerprint
        is None
    )
    assert first.subgraph.nodes == first.subgraph.edges == first.subgraph.scales == ()
    assert first.subgraph.connected is False
    assert first.subgraph.connectivity_status == "empty_not_connected"
    assert first.subgraph.real_biological_subgraph is False
    assert first.standalone_replay_result_request_bound is False
    assert first.qualifying_biological_node_count == 0
    assert (
        first.data_fingerprint
        is first.weight_fingerprint
        is first.model_fingerprint
        is first.environment_fingerprint
        is first.adapter_fingerprint
        is first.compute_fingerprint
        is first.benchmark_protocol_fingerprint
        is first.evidence_fingerprint
        is first.policy_fingerprint
        is first.result_fingerprint
        is first.prediction
        is first.result
        is first.tool_output
        is None
    )
    assert first.executable is first.execution_performed is False
    assert first.scientifically_validated is first.production_promoted is False
    assert first.abstain is True
    assert LimitedWorldModelCompilationV1.from_dict(first.to_dict()) == first


def test_p28_advisory_or_synthetic_participants_never_become_biological_nodes() -> None:
    p28 = _p28(p17_participant_count=3)
    assert p28.qualifying_module_count == 0

    compilation = compile_limited_biological_world_model(p28)

    assert compilation.qualifying_biological_node_count == 0
    assert compilation.subgraph.nodes == ()
    assert compilation.subgraph.edges == ()
    assert compilation.subgraph.adjacent_scale_edge_count == 0


def test_compiler_requires_exact_recursively_revalidated_p28_input() -> None:
    p28 = _p28()

    class EvilP28(MultiAgentBiologyCompilationV1):
        invented_node: str = "organism"

    evil = EvilP28.model_construct(**p28.__dict__, invented_node="organism")
    with pytest.raises(LimitedWorldModelContractError, match="exact MultiAgentBiologyCompilationV1"):
        compile_limited_biological_world_model(evil)

    forged = p28.to_dict()
    forged["qualifying_module_count"] = 1
    bypassed = MultiAgentBiologyCompilationV1.model_construct(**forged)
    with pytest.raises(LimitedWorldModelContractError, match="p28_compilation"):
        compile_limited_biological_world_model(bypassed)


def test_nested_requirement_and_subgraph_type_drift_is_rejected() -> None:
    compilation = compile_limited_biological_world_model(_p28())

    class EvilRequirement(StateActionObservationTimeRequirementV1):
        invented_scope: str = "organism"

    evil_requirement = EvilRequirement.model_construct(
        **compilation.requirement.__dict__,
        invented_scope="organism",
    )
    raw = compilation.to_dict()
    raw["requirement"] = evil_requirement
    _resign(raw)
    with pytest.raises(LimitedWorldModelContractError, match="exact StateActionObservationTimeRequirementV1"):
        LimitedWorldModelCompilationV1.from_dict(raw)

    class EvilSubgraph(ConnectedTypedSubgraphV1):
        placeholder_chain: tuple[str, ...] = ("molecule", "organism")

    evil_subgraph = EvilSubgraph.model_construct(
        **compilation.subgraph.__dict__,
        placeholder_chain=("molecule", "organism"),
    )
    raw = compilation.to_dict()
    raw["subgraph"] = evil_subgraph
    _resign(raw)
    with pytest.raises(LimitedWorldModelContractError, match="exact ConnectedTypedSubgraphV1"):
        LimitedWorldModelCompilationV1.from_dict(raw)

    bypassed = StateActionObservationTimeRequirementV1.model_construct(
        **compilation.requirement.__dict__,
    )
    bypassed.__dict__["hidden_identity"] = _fingerprint({"hidden": "scope"})
    raw = compilation.to_dict()
    raw["requirement"] = bypassed
    with pytest.raises(LimitedWorldModelContractError, match="unknown fields"):
        LimitedWorldModelCompilationV1.from_dict(raw)


def test_compiler_has_no_candidate_asset_path_registry_or_llm_surface() -> None:
    assert tuple(inspect.signature(compile_limited_biological_world_model).parameters) == ("p28_compilation",)

    class Bomb:
        def __iter__(self):
            raise AssertionError("candidate must not be inspected")

        def __repr__(self):
            raise AssertionError("candidate must not be rendered")

    for field in ("nodes", "asset_path", "registry", "llm_candidate"):
        with pytest.raises(TypeError):
            compile_limited_biological_world_model(_p28(), **{field: Bomb()})


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("state_identity_fingerprint", _fingerprint({"invented": "state"})),
        ("scope_identity_fingerprint", _fingerprint({"invented": "scope"})),
        ("action_identity_fingerprint", _fingerprint({"invented": "action"})),
        ("observation_identity_fingerprint", _fingerprint({"invented": "observation"})),
        ("time_identity_fingerprint", _fingerprint({"invented": "time"})),
        ("longitudinal_data_fingerprint", _fingerprint({"invented": "longitudinal"})),
        ("intervention_data_fingerprint", _fingerprint({"invented": "intervention"})),
        ("requirement_status", "available"),
        ("real_identities_available", True),
    ),
)
def test_requirement_cannot_be_resigned_into_available_real_identity(
    field: str,
    value: object,
) -> None:
    raw = compile_limited_biological_world_model(_p28()).requirement.to_dict()
    raw[field] = value

    with pytest.raises(LimitedWorldModelContractError):
        StateActionObservationTimeRequirementV1.from_dict(raw)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("nodes", [{"scale": "molecule", "kind": "model"}]),
        ("edges", [{"source": "molecule", "target": "organism"}]),
        ("scales", ["molecule", "organism"]),
        ("qualifying_biological_node_count", 1),
        ("adjacent_scale_edge_count", 1),
        ("connected", True),
        ("connectivity_status", "connected"),
        ("real_biological_subgraph", True),
        ("executable", True),
    ),
)
def test_empty_subgraph_cannot_gain_nodes_edges_scales_or_connected_status(
    field: str,
    value: object,
) -> None:
    raw = compile_limited_biological_world_model(_p28()).subgraph.to_dict()
    raw[field] = value

    with pytest.raises(LimitedWorldModelContractError):
        ConnectedTypedSubgraphV1.from_dict(raw)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("prediction", {"value": 1.0}),
        ("result", {"world_model": "success"}),
        ("tool_output", {"tool": "success"}),
        ("data_fingerprint", _fingerprint({"invented": "data"})),
        ("weight_fingerprint", _fingerprint({"invented": "weight"})),
        ("model_fingerprint", _fingerprint({"invented": "model"})),
        ("environment_fingerprint", _fingerprint({"invented": "environment"})),
        ("adapter_fingerprint", _fingerprint({"invented": "adapter"})),
        ("compute_fingerprint", _fingerprint({"invented": "compute"})),
        ("benchmark_protocol_fingerprint", _fingerprint({"invented": "benchmark"})),
        ("evidence_fingerprint", _fingerprint({"invented": "evidence"})),
        ("policy_fingerprint", _fingerprint({"invented": "policy"})),
        ("result_fingerprint", _fingerprint({"invented": "result"})),
        ("rollout", {"status": "passed"}),
        ("calibration", {"status": "passed"}),
        ("ood", {"status": "passed"}),
        ("conservation", {"status": "passed"}),
        ("counterfactual_consistency", {"status": "passed"}),
        ("benchmark_status", "passed"),
        ("executable", True),
        ("execution_performed", True),
        ("external_action_performed", True),
        ("scientifically_validated", True),
        ("promotion_eligible", True),
        ("production_promoted", True),
        ("product_policy_status", "approved"),
        ("real_candidate_status", "ready"),
    ),
)
def test_resigned_compilation_cannot_gain_values_execution_science_or_policy(
    field: str,
    value: object,
) -> None:
    raw = compile_limited_biological_world_model(_p28()).to_dict()
    raw[field] = value
    _resign(raw)

    with pytest.raises(LimitedWorldModelContractError):
        LimitedWorldModelCompilationV1.from_dict(raw)


def test_reason_order_identity_closure_and_public_bytes_are_fail_closed() -> None:
    compilation = compile_limited_biological_world_model(_p28(secret_prose=True))
    assert compilation.abstain_reasons == (
        "p28_has_no_qualifying_executable_model_modules",
        "state_action_observation_time_identity_unavailable",
        "real_connected_adjacent_scale_subgraph_unavailable",
        "p29_real_data_model_benchmark_not_authorized",
    )

    reordered = compilation.to_dict()
    reordered["abstain_reasons"] = list(reversed(reordered["abstain_reasons"]))
    _resign(reordered)
    with pytest.raises(LimitedWorldModelContractError, match="abstain_reasons"):
        LimitedWorldModelCompilationV1.from_dict(reordered)

    stale = compilation.to_dict()
    stale["requirement_fingerprint"] = _fingerprint({"stale": "requirement"})
    _resign(stale)
    with pytest.raises(LimitedWorldModelContractError, match="identities are not closed"):
        LimitedWorldModelCompilationV1.from_dict(stale)

    request_claim = compilation.to_dict()
    request_claim["p28_request_fingerprint"] = _fingerprint({"invented": "request"})
    _resign(request_claim)
    with pytest.raises(LimitedWorldModelContractError, match="extra"):
        LimitedWorldModelCompilationV1.from_dict(request_claim)

    public = str(compilation.to_dict())
    assert "secret-P28" not in public and "/private" not in public
    assert "molecule" not in public and "organism" not in public
    assert not set(compilation.to_dict()).intersection(
        {"path", "asset", "payload", "prose", "candidate", "registry", "llm", "model_nodes"}
    )
