"""ModelWrapper:model zoo 的统一模型契约。extends PredictorAgent(保留 fail-closed +
retrieve-before-predict 门),补两个显式治理方法:

- declare_scope() -> dict:声明该模型适用的 species/module/task/perturbation 边界,供治理读。
- estimate_uncertainty(model_input, prediction) -> dict:显式不确定性。默认从 run_prediction 的
  uncertainty 提取;若无(run_prediction 未产 uncertainty)→ available=False(诚实,不假造)。

超出 scope 的输入由继承的 assess_applicability/handle 走 rejected,不硬预测。
"""
from __future__ import annotations

from abc import abstractmethod

from praxis_virtualcell.predictors.base import PredictorAgent


class ModelWrapper(PredictorAgent):
    name = "ModelWrapper"

    @abstractmethod
    def declare_scope(self) -> dict:
        """返回 {species: list, module: str, task: list, perturbation?: list}。治理据此判 in/out of scope。"""

    def estimate_uncertainty(self, model_input: dict, prediction: dict | None) -> dict:
        """默认:调 run_prediction 取 uncertainty(可能为 None → available=False,不假造)。
        子类可覆写为更显式的估计(如 bootstrap CI / ensemble disagreement)。"""
        try:
            out = self.run_prediction(model_input)
        except Exception as e:  # noqa: BLE001 — 不确定性估计失败视为不可用,fail-closed
            return {"available": False, "reason": f"uncertainty_estimation_failed: {e}"}
        unc = out.get("uncertainty")
        if unc is None:
            return {"available": False, "reason": "model_reports_no_uncertainty"}
        return {"available": True, "uncertainty": unc}

    def declare_provenance(self) -> dict:
        """返回模型级 provenance(静态模型卡:训练数据/指标锚点/远端坐标/可分发性)。
        默认空(机制模型如 GEM 无训练锚点);ML wrapper(GEARS/scGPT)覆写返回真锚点。
        与运行时 PredictorResultMessage.provenance 正交(那是逐次预测的证据链)。"""
        return {}
