"""predictor-agent 契约:能不能/为什么/用了什么/输出/不确定性/失败原因。
执行前强制 retrieve-before-predict 门(bus 里须已有 brain_retrieved)。无 torch。"""
from __future__ import annotations

from abc import abstractmethod
from dataclasses import asdict

from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.exceptions import RetrieveBeforePredictError
from praxis_virtualcell.core.message import AgentMessage, PredictorResultMessage


class PredictorAgent(BaseAgent):
    name = "PredictorAgent"

    def assess_applicability(self, request: dict, brain_context: dict) -> tuple[float, str | None]:
        """返回 (score, rejection_reason)。reason 非 None 表示拒。"""
        rules = (brain_context.get("model_applicability") or {}).get(self.name, {})
        if not rules:
            return 0.0, f"{self.name} 不在 {brain_context.get('species')} brain 的 model_applicability"
        if request.get("species") not in rules.get("supported_species", []):
            return 0.0, "unsupported_species"
        if request.get("input_modality") not in rules.get("supported_modalities", []):
            return 0.0, "unsupported_modality"
        if request.get("task_type") not in rules.get("supported_tasks", []):
            return 0.0, "unsupported_task"
        return 1.0, None

    def prepare_input(self, request: dict, brain_context: dict) -> dict:
        return {"targets": request.get("perturbation_targets", [])}

    @abstractmethod
    def run_prediction(self, model_input: dict) -> dict:
        """返回 {prediction, uncertainty}。"""

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        if not bus.has_message_type("brain_retrieved"):
            raise RetrieveBeforePredictError(
                f"{self.name} 在 brain 检索前被调用(retrieve-before-predict 门)")
        req = message.payload["request"]
        bc = message.payload["brain_context"]
        score, reject = self.assess_applicability(req, bc)
        if reject is not None:
            self._emit(bus, message, PredictorResultMessage(
                agent_name=self.name, status="rejected", prediction=None, uncertainty=None,
                applicability_score=score, evidence=[reject], rejection_reason=reject,
                provenance={"rules": bc.get("rules_referenced", [])}))
            return
        try:
            out = self.run_prediction(self.prepare_input(req, bc))
        except Exception as e:  # noqa: BLE001 — mock 阶段把异常归为 failed
            self._emit(bus, message, PredictorResultMessage(
                agent_name=self.name, status="failed", prediction=None, uncertainty=None,
                applicability_score=score, evidence=[], rejection_reason=None,
                provenance={"error": str(e)}))
            return
        self._emit(bus, message, PredictorResultMessage(
            agent_name=self.name, status="success", prediction=out["prediction"],
            uncertainty=out.get("uncertainty"), applicability_score=score, evidence=["mock"],
            rejection_reason=None, provenance={"mock": True}))

    def _emit(self, bus: MessageBus, src: AgentMessage, result: PredictorResultMessage) -> None:
        bus.send(AgentMessage(
            message_id=src.message_id + f":{self.name}",
            sender=self.name, receiver="EnsembleCoordinator",
            message_type="predictor_result", payload=asdict(result),
            timestamp=src.timestamp, parent_message_id=src.message_id))
