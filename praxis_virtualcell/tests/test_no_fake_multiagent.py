from praxis_virtualcell.workflows.predict_delta_expression import build_runtime

_HUMAN = {"request_id": "r1", "species": "human", "perturbation_type": "gene",
          "perturbation_targets": ["AHR"], "input_modality": "scRNA",
          "output_modality": "delta_expression", "task_type": "predict_delta_expression"}


def test_trace_has_full_chain_and_retrieve_first():
    rt = build_runtime()
    rt.run_workflow_from_dict(_HUMAN)
    types = [m.message_type for m in rt.bus.trace]
    assert "brain_retrieved" in types and "predictor_result" in types
    assert types.index("brain_retrieved") < types.index("predictor_result")

    assert any(m.receiver == "MockCPA" and m.message_type == "predict" for m in rt.bus.trace)


def test_critic_flags_injected_fake_prediction():

    from praxis_virtualcell.agents.critic import CriticAgent
    from praxis_virtualcell.core.bus import MessageBus
    from praxis_virtualcell.core.message import AgentMessage
    bus = MessageBus()
    bus.send(AgentMessage("b", "SpeciesBrain", "X", "brain_retrieved", {}, "t0"))
    bus.send(AgentMessage("pr", "MockCPA", "EnsembleCoordinator", "predictor_result",
                          {"agent_name": "MockCPA", "status": "rejected"}, "t1"))
    payload = {"results": [{"agent_name": "MockCPA", "status": "rejected"}],
               "models_used": ["MockCPA"], "reliability_decision": {"abstain": False}}
    CriticAgent().handle(AgentMessage("m", "Reliability", "Critic", "review", payload, "t2"), bus)
    v = bus.latest("critic_done").payload["critic_violations"]
    assert any("rejected_model_in_ensemble" in x for x in v)
