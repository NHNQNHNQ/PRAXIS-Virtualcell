"""核心 fail-closed 契约：候选全部失败时不得返回空的非弃权报告。"""
from praxis_virtualcell.mdr_gnb.predictors.registry import PredictorRegistry, PredictorSpec
from praxis_virtualcell.mdr_gnb.workflows.run_mdr_query import run_mdr_query


def _always_abstain(_ctx):
    return {
        "abstained": True,
        "predictor": "unavailable_sir",
        "output_kind": "sir_class",
        "reason_code": "artifact_unavailable",
    }


def _always_fail_registry() -> PredictorRegistry:
    registry = PredictorRegistry()
    registry.register(PredictorSpec(
        name="unavailable_sir", version="test",
        species=["escherichia_coli"], drug_class=["carbapenems"],
        output_kind="sir_class", artifact_path="test://missing.joblib",
        predict=_always_abstain,
    ))
    return registry


def test_no_successful_predictor_is_a_core_hard_abstain():
    result = run_mdr_query({
        "species": "escherichia_coli",
        "drug_panel": [{"drug": "meropenem", "drug_class": "carbapenems"}],
        "requested_outputs": ["SIR"],
        "amr_profile": {"blaKPC-2": True},
    }, seed_task_id="no-success", registry=_always_fail_registry())

    report = result["report"]
    assert result["route"]["disposition"] == "accept"  # route 声明可达，运行时失败
    assert report["abstained"] is True
    assert report["output_kind"] is None
    assert report["sir"] is None
    assert report["activity"] is None
    assert report["peptide_activity"] is None
    assert report["mechanism"] is None
    assert {"no_successful_predictor", "artifact_unavailable"} <= set(report["abstain_reasons"])

    trace_by_type = {message.message_type: message for message in result["trace"]}
    final_decision = trace_by_type["final_decision_resolved"]
    assert final_decision.payload["preliminary_abstained"] is True
    assert final_decision.payload["final_abstained"] is True
    assert {"no_successful_predictor", "artifact_unavailable"} <= set(
        final_decision.payload["final_abstain_reasons"]
    )
    assert final_decision.payload["final_output_kind"] is None
    assert final_decision.payload["final_sir"] is None
    assert trace_by_type["report_built"].parent_message_id == final_decision.message_id
