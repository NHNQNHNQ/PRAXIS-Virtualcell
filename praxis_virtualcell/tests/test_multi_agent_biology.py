from __future__ import annotations

import inspect

import pytest

from praxis_virtualcell.experiment_design import (
    VirtualExperimentV1,
    compile_contract_only_experiment,
    evaluate_replay,
    select_replay_actions,
)
from praxis_virtualcell.model_zoo.adapter_sdk import _fingerprint
from praxis_virtualcell.multi_agent_biology import (
    MultiAgentBiologyCompilationV1,
    MultiAgentBiologyContractError,
    MultiAgentDAGV1,
    MultiAgentHandoffV1,
    MultiAgentRolePolicyV1,
    MultiAgentTraceEventV1,
    MultiAgentTraceV1,
    build_advisory_dag,
    build_advisory_role,
    build_value_free_handoff,
    build_value_free_trace,
    compile_multi_agent_biology,
    validate_value_free_trace,
)
from praxis_virtualcell.tests.test_experiment_design_replay import _ledger as _p27_ledger
from praxis_virtualcell.tests.test_experiment_design_replay import _protocol as _p27_protocol
from praxis_virtualcell.tests.test_experiment_design_replay import _request as _different_request
from praxis_virtualcell.tests.test_experiment_design_replay import _view as _p27_view
from praxis_virtualcell.tests.test_virtual_experiment import _plan as _p17_plan
from praxis_virtualcell.tests.test_virtual_experiment import _registry as _p17_registry
from praxis_virtualcell.tests.test_virtual_experiment import _registry_report as _p17_report
from praxis_virtualcell.tests.test_virtual_experiment import _request as _shared_request
from praxis_virtualcell.virtual_experiment import compile_virtual_experiment


def _fp(label: str) -> str:
    return _fingerprint({"label": label})


def _resign(raw: dict[str, object], field: str, prefix: str) -> None:
    raw[field] = f"{prefix}{_fingerprint({key: value for key, value in raw.items() if key != field})[:24]}"


def _replay_result():
    view = _p27_view()
    protocol = _p27_protocol(view)
    receipts = select_replay_actions(protocol, view)
    return evaluate_replay(protocol, view, receipts, _p27_ledger(view))


def _exact_inputs(*, p17_participant_count: int = 0, secret_prose: bool = False):
    request = _shared_request()
    registry = _p17_registry(p17_participant_count)
    reports = tuple(_p17_report(request, registry, index) for index in range(p17_participant_count))
    p17 = compile_virtual_experiment(request, _p17_plan(request, reports), registry)
    question = "secret-P28 /private/p28/input" if secret_prose else "Which action is eligible?"
    experiment = compile_contract_only_experiment(
        request=request,
        question=question,
        hypothesis="No action is eligible without exact governed model truth.",
    )
    return p17, experiment, _replay_result()


def _advisory_graph():
    p17, experiment, replay = _exact_inputs()
    cell = build_advisory_role("cell-advisory", "cell_advisory")
    literature = build_advisory_role("literature-advisory", "literature_advisory")
    handoff = build_value_free_handoff(
        cell,
        literature,
        input_schema_version="vc.virtual-experiment.v1",
        input_fingerprint=experiment.fingerprint(),
    )
    dag = build_advisory_dag(
        p17_compilation_fingerprint=p17.fingerprint(),
        p27_experiment_fingerprint=experiment.fingerprint(),
        p27_replay_result_fingerprint=replay.fingerprint(),
        roles=(literature, cell),
        handoffs=(handoff,),
    )
    return cell, literature, handoff, dag, build_value_free_trace(dag)


def test_authoritative_compilation_is_exact_empty_value_free_and_deterministic() -> None:
    p17, experiment, replay = _exact_inputs(secret_prose=True)
    first = compile_multi_agent_biology(p17, experiment, replay)
    second = compile_multi_agent_biology(p17, experiment, replay)

    assert first == second
    assert first.fingerprint() == second.fingerprint()
    assert first.qualifying_module_count == 0
    assert first.required_qualifying_module_count == 3
    assert first.role_policy_fingerprints == first.handoff_fingerprints == ()
    assert first.orchestration_dag.roles == first.orchestration_dag.handoffs == ()
    assert first.trace.events == first.trace.handoff_fingerprints == ()
    assert first.prediction is first.result is first.tool_output is None
    assert first.executable is first.execution_performed is False
    assert first.scientifically_validated is first.production_promoted is False
    assert first.abstain is True
    assert MultiAgentBiologyCompilationV1.from_dict(first.to_dict()) == first
    public = str(first.to_dict())
    assert "secret-P28" not in public and "/private" not in public


def test_p17_synthetic_participants_never_become_p28_qualifying_modules() -> None:
    p17, experiment, replay = _exact_inputs(p17_participant_count=3)
    assert p17.decision.participating_capability_count == 3

    compilation = compile_multi_agent_biology(p17, experiment, replay)

    assert compilation.qualifying_module_fingerprints == ()
    assert compilation.qualifying_module_count == 0
    assert compilation.compatibility_reports_verified is False
    assert compilation.registry_snapshot_fingerprint is None


def test_p17_and_p27_must_bind_the_same_exact_request() -> None:
    p17, _, replay = _exact_inputs()
    mismatched = compile_contract_only_experiment(
        request=_different_request(),
        question="q",
        hypothesis="h",
    )

    with pytest.raises(MultiAgentBiologyContractError, match="same exact request"):
        compile_multi_agent_biology(p17, mismatched, replay)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("network_access_allowed", True),
        ("filesystem_write_allowed", True),
        ("subprocess_allowed", True),
        ("device_access_allowed", True),
        ("external_action_allowed", True),
        ("dynamic_tool_invocation_allowed", True),
        ("numerical_output_allowed", True),
        ("counts_for_real_acceptance", True),
        ("scientifically_validated", True),
        ("production_promoted", True),
        ("retry_limit", 1),
        ("max_concurrency", 2),
    ),
)
def test_advisory_role_rejects_permission_resource_and_truth_escalation(field: str, value: object) -> None:
    role = build_advisory_role("safe-advisory", "rule_advisory")
    raw = role.to_dict()
    raw[field] = value

    with pytest.raises(MultiAgentBiologyContractError):
        MultiAgentRolePolicyV1.from_dict(raw)


def test_value_free_handoff_has_no_payload_or_numeric_authority() -> None:
    sender, receiver, handoff, _, _ = _advisory_graph()
    assert handoff.sender_policy_fingerprint == sender.fingerprint()
    assert handoff.receiver_policy_fingerprint == receiver.fingerprint()
    assert handoff.prediction is handoff.numerical_result is None
    assert handoff.counts_for_real_acceptance is False

    raw = handoff.to_dict()
    raw["payload"] = {"prediction": [1.0], "production_promoted": True}
    with pytest.raises(MultiAgentBiologyContractError):
        MultiAgentHandoffV1.from_dict(raw)


def test_advisory_dag_is_canonical_typed_and_acyclic() -> None:
    sender, receiver, handoff, dag, _ = _advisory_graph()
    assert dag.topological_role_ids == (sender.role_id, receiver.role_id)
    assert dag.execution_steps == () and dag.executable is False
    assert all(role.counts_for_real_acceptance is False for role in dag.roles)

    stale = handoff.to_dict()
    stale["sender_policy_fingerprint"] = _fp("wrong-policy")
    _resign(stale, "handoff_id", "handoff_")
    stale_handoff = MultiAgentHandoffV1.from_dict(stale)
    with pytest.raises(MultiAgentBiologyContractError, match="sender policy"):
        build_advisory_dag(
            p17_compilation_fingerprint=dag.p17_compilation_fingerprint,
            p27_experiment_fingerprint=dag.p27_experiment_fingerprint,
            p27_replay_result_fingerprint=dag.p27_replay_result_fingerprint,
            roles=dag.roles,
            handoffs=(stale_handoff,),
        )

    reverse = build_value_free_handoff(
        receiver,
        sender,
        input_schema_version="vc.multi-agent-value-free-handoff.v1",
        input_fingerprint=handoff.fingerprint(),
    )
    with pytest.raises(MultiAgentBiologyContractError, match="acyclic"):
        build_advisory_dag(
            p17_compilation_fingerprint=dag.p17_compilation_fingerprint,
            p27_experiment_fingerprint=dag.p27_experiment_fingerprint,
            p27_replay_result_fingerprint=dag.p27_replay_result_fingerprint,
            roles=dag.roles,
            handoffs=(handoff, reverse),
        )


def test_dag_rejects_unbound_external_identity_and_undeclared_roles() -> None:
    sender, receiver, _, dag, _ = _advisory_graph()
    stale = build_value_free_handoff(
        sender,
        receiver,
        input_schema_version="vc.virtual-experiment-compilation.v1",
        input_fingerprint=dag.p27_experiment_fingerprint,
    )
    with pytest.raises(MultiAgentBiologyContractError, match="input identity"):
        build_advisory_dag(
            p17_compilation_fingerprint=dag.p17_compilation_fingerprint,
            p27_experiment_fingerprint=dag.p27_experiment_fingerprint,
            p27_replay_result_fingerprint=dag.p27_replay_result_fingerprint,
            roles=(sender, receiver),
            handoffs=(stale,),
        )
    with pytest.raises(MultiAgentBiologyContractError, match="undeclared role"):
        build_advisory_dag(
            p17_compilation_fingerprint=dag.p17_compilation_fingerprint,
            p27_experiment_fingerprint=dag.p27_experiment_fingerprint,
            p27_replay_result_fingerprint=dag.p27_replay_result_fingerprint,
            roles=(sender,),
            handoffs=(stale,),
        )

    orphan = build_value_free_handoff(
        sender,
        receiver,
        input_schema_version="vc.multi-agent-value-free-handoff.v1",
        input_fingerprint=_fp("absent-predecessor"),
    )
    with pytest.raises(MultiAgentBiologyContractError, match="declared predecessor"):
        build_advisory_dag(
            p17_compilation_fingerprint=dag.p17_compilation_fingerprint,
            p27_experiment_fingerprint=dag.p27_experiment_fingerprint,
            p27_replay_result_fingerprint=dag.p27_replay_result_fingerprint,
            roles=(sender, receiver),
            handoffs=(orphan,),
        )


def test_dag_rejects_duplicate_roles_and_handoff_budget_overflow() -> None:
    sender, _, _, dag, _ = _advisory_graph()
    receivers = tuple(build_advisory_role(f"receiver-{index}", "literature_advisory") for index in range(5))
    handoffs = tuple(
        build_value_free_handoff(
            sender,
            receiver,
            input_schema_version="vc.virtual-experiment-compilation.v1",
            input_fingerprint=dag.p17_compilation_fingerprint,
        )
        for receiver in receivers
    )
    with pytest.raises(MultiAgentBiologyContractError, match="unique"):
        build_advisory_dag(
            p17_compilation_fingerprint=dag.p17_compilation_fingerprint,
            p27_experiment_fingerprint=dag.p27_experiment_fingerprint,
            p27_replay_result_fingerprint=dag.p27_replay_result_fingerprint,
            roles=(sender, sender),
        )
    with pytest.raises(MultiAgentBiologyContractError, match="budget"):
        build_advisory_dag(
            p17_compilation_fingerprint=dag.p17_compilation_fingerprint,
            p27_experiment_fingerprint=dag.p27_experiment_fingerprint,
            p27_replay_result_fingerprint=dag.p27_replay_result_fingerprint,
            roles=(sender, *receivers),
            handoffs=handoffs,
        )


def test_trace_is_complete_hash_chained_and_value_free() -> None:
    _, _, handoff, dag, trace = _advisory_graph()
    assert len(trace.events) == 1
    assert trace.handoff_fingerprints == (handoff.fingerprint(),)
    assert trace.events[0].previous_event_fingerprint == trace.root_fingerprint
    assert trace.events[0].prediction is trace.events[0].tool_output is None
    assert MultiAgentTraceV1.from_dict(trace.to_dict()) == trace

    event_raw = trace.events[0].to_dict()
    event_raw["previous_event_fingerprint"] = _fp("wrong-previous")
    _resign(event_raw, "event_id", "event_")
    event = MultiAgentTraceEventV1.from_dict(event_raw)
    broken = trace.to_dict()
    broken["events"] = [event.to_dict()]
    broken["event_fingerprints"] = [event.fingerprint()]
    broken["last_event_fingerprint"] = event.fingerprint()
    _resign(broken, "trace_id", "trace_")
    with pytest.raises(MultiAgentBiologyContractError, match="predecessor"):
        MultiAgentTraceV1.from_dict(broken)

    dropped = trace.to_dict()
    dropped["events"] = []
    dropped["event_fingerprints"] = []
    dropped["last_event_fingerprint"] = dropped["root_fingerprint"]
    _resign(dropped, "trace_id", "trace_")
    with pytest.raises(MultiAgentBiologyContractError, match="exactly one"):
        MultiAgentTraceV1.from_dict(dropped)


def test_resigned_trace_cannot_claim_a_handoff_absent_from_its_dag() -> None:
    sender, receiver, _, dag, trace = _advisory_graph()
    foreign = build_value_free_handoff(
        receiver,
        sender,
        input_schema_version="vc.virtual-experiment-compilation.v1",
        input_fingerprint=dag.p17_compilation_fingerprint,
    )
    event_raw = trace.events[0].to_dict()
    event_raw["handoff_fingerprint"] = foreign.fingerprint()
    _resign(event_raw, "event_id", "event_")
    event = MultiAgentTraceEventV1.from_dict(event_raw)
    forged = trace.to_dict()
    forged["handoff_fingerprints"] = [foreign.fingerprint()]
    forged["events"] = [event.to_dict()]
    forged["event_fingerprints"] = [event.fingerprint()]
    forged["last_event_fingerprint"] = event.fingerprint()
    _resign(forged, "trace_id", "trace_")
    resigned = MultiAgentTraceV1.from_dict(forged)

    with pytest.raises(MultiAgentBiologyContractError, match="exact DAG handoff set"):
        validate_value_free_trace(dag, resigned)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("role_policy_fingerprints", [_fp("forged-role")]),
        ("handoff_fingerprints", [_fp("forged-handoff")]),
        ("qualifying_module_fingerprints", [_fp("forged-module")]),
        ("scientifically_validated", True),
        ("promotion_eligible", True),
        ("production_promoted", True),
        ("executable", True),
        ("execution_performed", True),
        ("external_action_performed", True),
        ("prediction", {"value": [1.0]}),
        ("result", {"consensus": "success"}),
        ("product_policy_status", "approved"),
        ("conflict_status", "none"),
        ("partial_failure_status", "recovered"),
    ),
)
def test_resigned_compilation_cannot_gain_roles_values_science_or_policy(field: str, value: object) -> None:
    compilation = compile_multi_agent_biology(*_exact_inputs())
    raw = compilation.to_dict()
    raw[field] = value
    _resign(raw, "compilation_id", "ma_comp_")

    with pytest.raises(MultiAgentBiologyContractError):
        MultiAgentBiologyCompilationV1.from_dict(raw)


def test_nested_model_type_drift_is_rejected() -> None:
    p17, experiment, replay = _exact_inputs()

    class EvilExperiment(VirtualExperimentV1):
        injected_prediction: tuple[float, ...] = (1.0,)

    evil_experiment = EvilExperiment.model_construct(**experiment.__dict__, injected_prediction=(1.0,))
    with pytest.raises(MultiAgentBiologyContractError, match="exact VirtualExperimentV1"):
        compile_multi_agent_biology(p17, evil_experiment, replay)

    role = build_advisory_role("typed-advisory", "rule_advisory")

    class EvilRole(MultiAgentRolePolicyV1):
        prediction: tuple[float, ...] = (1.0,)

    evil_role = EvilRole.model_construct(**role.__dict__, prediction=(1.0,))
    with pytest.raises(MultiAgentBiologyContractError, match="exact MultiAgentRolePolicyV1"):
        build_value_free_handoff(
            evil_role,
            build_advisory_role("receiver-advisory", "literature_advisory"),
            input_schema_version="vc.virtual-experiment.v1",
            input_fingerprint=experiment.fingerprint(),
        )

    compilation = compile_multi_agent_biology(p17, experiment, replay)

    class EvilDAG(MultiAgentDAGV1):
        injected_steps: tuple[str, ...] = ("fallback",)

    evil_dag = EvilDAG.model_construct(**compilation.orchestration_dag.__dict__, injected_steps=("fallback",))
    raw = compilation.to_dict()
    raw["orchestration_dag"] = evil_dag
    raw["orchestration_dag_fingerprint"] = evil_dag.fingerprint()
    _resign(raw, "compilation_id", "ma_comp_")
    with pytest.raises(MultiAgentBiologyContractError, match="exact MultiAgentDAGV1"):
        MultiAgentBiologyCompilationV1.from_dict(raw)


def test_candidate_llm_and_dynamic_positive_module_surfaces_are_closed() -> None:
    signature = inspect.signature(compile_multi_agent_biology)
    assert tuple(signature.parameters) == (
        "p17_compilation",
        "p27_experiment",
        "p27_replay_result",
    )

    class Bomb:
        def __iter__(self):
            raise AssertionError("candidate must not be inspected")

        def __repr__(self):
            raise AssertionError("candidate must not be rendered")

    with pytest.raises(TypeError):
        compile_multi_agent_biology(*_exact_inputs(), candidate_delegation=Bomb())


def test_public_records_have_no_runtime_loader_or_free_form_payload_fields() -> None:
    _, _, _, dag, trace = _advisory_graph()
    compilation = compile_multi_agent_biology(*_exact_inputs())
    public_keys = set(compilation.to_dict()) | set(dag.to_dict()) | set(trace.to_dict())
    assert not public_keys.intersection({"path", "url", "secret", "payload", "message", "callable", "tool_locator"})
    assert compilation.comparison_performed is compilation.ablation_performed is False
    assert compilation.conflict_status == "not_evaluated_no_execution"
    assert compilation.partial_failure_status == "not_evaluated_no_execution"
