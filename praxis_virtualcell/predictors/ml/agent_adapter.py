"""M2:把真 donor ML predictor 包成 communicative PredictorAgent(接 Week 2 骨架)。

继承 core `PredictorAgent`:retrieve-before-predict 门 + `assess_applicability`(brain) + `prepare_input` + `run_prediction`。
`prepare_input` 做 **schema→tensor 适配**(request.targets → esm2 pert_emb + norman control)。
`run_prediction` 调真 donor `model.predict`。仅远端 virtualcell 环境(import torch + donor)。
"""  # noqa: E501
from __future__ import annotations

import sys

_DONOR = "/home/zkyd/data1/mzy/Virtual cell"
if _DONOR not in sys.path:
    sys.path.insert(0, _DONOR)

from praxis_virtualcell.predictors.base import PredictorAgent  # noqa: E402


class MLBackedPredictorAgent(PredictorAgent):
    """真 ML 模型驱动的 predictor-agent(替代 Week 2 的 mock)。"""

    model_version = "donor_ml"   # 类属性兜底;__init__ 覆盖为反映具体 donor 模型类型
    # C2 Gate A per-call hash 完整性硬门要求每个被采纳 predictor 声明 model_version,否则
    # models_used 缺 version → fail-closed 误伤对外 abstain。真 ML 路径(远端 .53)须诚实声明。

    def __init__(self, donor_model, *, control, pert_table, pert_dim, name=None):
        self.model = donor_model.eval()
        self.name = name or f"ML{type(donor_model).__name__}"
        self.model_version = f"donor_ml:{type(donor_model).__name__}"   # 诚实反映真实 donor 模型类型
        self._control = control
        self._pert_table = pert_table
        self._pert_dim = pert_dim

    def prepare_input(self, request: dict, brain_context: dict) -> dict:
        """schema→tensor:request.perturbation_targets → esm2 pert_emb;复用 norman control baseline。"""
        from bench.vcbench.loader import _pert_emb_for

        targets = list(request.get("perturbation_targets", []))
        pname = "+".join(targets) if targets else "control"
        pert_emb = _pert_emb_for(pname, self._pert_table, self._pert_dim)
        return {"control": self._control, "pert_emb": pert_emb, "targets": tuple(targets)}

    def run_prediction(self, model_input: dict) -> dict:
        from praxis_virtualcell.predictors.ml.ml_predictor_agent import MLPredictorAgent

        targets = model_input["targets"]
        kind = "gene_combo" if len(targets) > 1 else "gene_ko"
        mean = MLPredictorAgent(self.model).predict_tensor(
            model_input["control"], model_input["pert_emb"], kind=kind, targets=targets)
        # delta 向量(预测 - control);EnsembleCoordinator 按 element-wise 聚合 prediction["delta"]
        delta = (mean.squeeze(0) - model_input["control"]).detach().cpu().tolist()
        return {"prediction": {"delta": delta, "n_genes": len(delta)},
                "uncertainty": {"std": float(mean.std())}}


def make_ml_agent(donor_model, *, norman_ds=None, name=None) -> MLBackedPredictorAgent:
    """从 norman dataset 取 control baseline + pert_table 初始化(测试/workflow 用)。"""
    from praxis_virtualcell.predictors.ml.donor_bridge import load_norman

    ds = norman_ds if norman_ds is not None else load_norman(split="test", max_perts=2, max_cells=2)
    return MLBackedPredictorAgent(donor_model, control=ds[0].control, pert_table=ds.pert_table,
                                  pert_dim=ds.pert_dim, name=name)
