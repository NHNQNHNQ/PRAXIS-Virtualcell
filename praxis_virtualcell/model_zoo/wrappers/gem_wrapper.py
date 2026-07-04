"""GemWrapper:把真实 GemModel(predictors/mechanistic/gem_model.py)包成 ModelWrapper。

证明 model_zoo 契约在**真机制模型**上跑通。默认 e_coli_core(cobra 自带 textbook,无外部数据)。
缺 cobra → 构造时抛(继承 handle 归 failed);缺 SBML → GemModel 构造抛。基因不在 GEM →
knockout 返 in_model=False(不虚构生长)。GEM 是确定性 FBA,estimate_uncertainty 声明 deterministic。
"""
from __future__ import annotations

from praxis_virtualcell.model_zoo.wrappers.base import ModelWrapper


class GemWrapper(ModelWrapper):
    name = "GemWrapper"

    def __init__(self, sbml_path: str | None = None) -> None:
        # lazy:仅在实例化时载模型;缺 cobra/SBML → 抛 → 上层 fail-closed
        from praxis_virtualcell.predictors.mechanistic.ecoli_gem import EcoliGEM
        from praxis_virtualcell.predictors.mechanistic.gem_model import GemModel

        self._gem = GemModel(sbml_path) if sbml_path else EcoliGEM()

    def declare_scope(self) -> dict:
        return {
            "species": ["bacteria", "yeast"],   # GEM 覆盖微生物 KO growth
            "module": "cytoplasmic_metabolism", # M4(与 registry.yaml ecoli_gem.module 一致)
            "task": ["growth"],
            "perturbation": ["gene"],
        }

    def run_prediction(self, model_input: dict) -> dict:
        """真跑 cobra FBA KO。返回 {prediction: {wt_growth, knockouts:[...]}, uncertainty}。
        基因不在 GEM → in_model=False, growth=None(不虚构)。"""
        targets = model_input.get("targets", [])
        kos = self._gem.knockout_many(targets)
        return {
            "prediction": {
                "wt_growth": round(self._gem.wt_growth, 5),
                "knockouts": [
                    {"gene": k.gene, "in_model": k.in_model,
                     "growth": None if k.growth is None else round(k.growth, 5),
                     "ratio": None if k.ratio is None else round(k.ratio, 4),
                     "essential": k.essential}
                    for k in kos
                ],
            },
            # GEM 是确定性约束型模型:不产随机 uncertainty,如实声明 deterministic
            "uncertainty": {"method": "deterministic_fba"},
        }

    def estimate_uncertainty(self, model_input: dict, prediction: dict | None) -> dict:
        """GEM 确定性:available=True 但 method=deterministic_fba(诚实:非概率不确定性)。"""
        return {"available": True, "method": "deterministic_fba",
                "note": "constraint-based FBA is deterministic; essentiality needs wet-lab confirmation"}
