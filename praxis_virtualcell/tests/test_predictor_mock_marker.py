"""Unit 4 契约:mock 标记归属正确性。

- 真预测器(run_prediction 不返回 evidence/provenance)经 handle → evidence==[] 且 provenance 无 "mock" 键
  (证:mock 标记不再由基类硬编码误标真预测器)。
- mock 预测器(自声明 evidence/provenance)经 handle → evidence 含 "mock"、provenance["mock"] is True
  (证:mock 自声明生效,OFFLINE mock 标记保留)。
"""
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.predictors.base import PredictorAgent
from praxis_virtualcell.predictors.mock_gears import MockGEARSAgent


def _bus_with_brain():
    bus = MessageBus()
    bus.send(AgentMessage("b1", "SpeciesBrain", "X", "brain_retrieved", {}, "t0"))
    return bus


def _payload(model_name):
    return {"request": {"species": "human", "input_modality": "scRNA",
                        "task_type": "predict_delta_expression", "perturbation_type": "gene",
                        "perturbation_targets": ["AHR"]},
            "brain_context": {"species": "human", "species_supported": True,
                              "model_applicability": {model_name: {"supported_species": ["human"],
                                  "supported_modalities": ["scRNA"],
                                  "supported_tasks": ["predict_delta_expression"],
                                  "supported_perturbations": ["gene"],
                                  "reject_if": ["gene_not_in_graph_vocabulary"]}},
                              "object_vocabulary": {"genes": ["AHR"]}}}


class _RealPredictor(PredictorAgent):
    """最小真预测器:run_prediction 只返回 prediction/uncertainty(不自声明 mock),
    与 MLBackedPredictorAgent / ModelWrapper 真跑返回同形。"""
    name = "RealPredictor"

    def run_prediction(self, model_input: dict) -> dict:
        return {"prediction": {"delta": [0.1]}, "uncertainty": {"sigma": 0.3}}


def test_real_predictor_not_flagged_mock():
    """真预测器 success 结果不被误标 mock:evidence 空、provenance 无 mock 键。"""
    bus = _bus_with_brain()
    _RealPredictor().handle(
        AgentMessage("m1", "X", "RealPredictor", "predict", _payload("RealPredictor"), "t1"), bus)
    out = bus.latest("predictor_result").payload
    assert out["status"] == "success"
    assert out["evidence"] == []
    assert "mock" not in out["provenance"]


def test_mock_predictor_self_declares_mock():
    """mock 预测器 success 结果保留 mock 标记(自声明):evidence 含 mock、provenance["mock"] is True。"""
    bus = _bus_with_brain()
    MockGEARSAgent().handle(
        AgentMessage("m1", "X", "MockGEARS", "predict", _payload("MockGEARS"), "t1"), bus)
    out = bus.latest("predictor_result").payload
    assert out["status"] == "success"
    assert "mock" in out["evidence"]
    assert out["provenance"]["mock"] is True
