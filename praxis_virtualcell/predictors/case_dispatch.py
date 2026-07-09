"""engine→真实 run_*_case 分发 + CaseReport→delta 映射。B1 实现 gem_fba 的 gene→growth,
B2 Task1 加 gem_fba 的 medium(碳源切换)→growth(bacteria only)。
其余 engine / gem_fba 的 drug 等子路径由后续增量 task 往这里加分支。"""
from __future__ import annotations

from praxis_virtualcell.core.exceptions import UnsupportedEngine

# 已接入真实预测的 engine(单一真源;被 agents.model_applicability 直接 import,不镜像)
REAL_ENGINES = frozenset({"gem_fba"})

# 与 agents.route_table._GENE_LIKE 对齐:单基因/多基因联合敲除同属 gem_fba gene→growth
_GENE_LIKE = frozenset({"gene", "gene_combination"})


def dispatch_runner(engine: str, raw_req: dict):
    """engine + 请求上下文 → 具体 run_*_case(返回可调用,签名 (raw_req, ...) → (CaseReport, RouteDecision))。"""
    species = raw_req.get("species")
    obj = raw_req.get("perturbation_object")
    if engine == "gem_fba":
        if obj in _GENE_LIKE:
            if species == "bacteria":
                from praxis_virtualcell.predictors.mechanistic.ecoli_gem import run_ecoli_growth_case
                return run_ecoli_growth_case
            if species == "yeast":
                from praxis_virtualcell.predictors.mechanistic.yeast_gem import run_yeast_growth_case
                return run_yeast_growth_case
        elif obj == "medium" and species == "bacteria":
            # medium 切换目前只有 bacteria(EcoliGEM)重建;yeast 无对应 runner → 诚实 UnsupportedEngine。
            from praxis_virtualcell.predictors.mechanistic.medium_shift import run_medium_shift_case
            return run_medium_shift_case
    raise UnsupportedEngine(f"B 未接入 case runner: engine={engine} object={obj} species={species}")


def map_case_delta(engine: str, report) -> list[float]:
    """CaseReport.raw_output → delta 向量(确定性,继承 raw_output 的 round)。按 raw_output 判别键选映射。"""
    raw = report.raw_output
    if engine == "gem_fba":
        if "knockouts" in raw:
            # 每个 KO 基因 growth 相对 WT 的变化:ratio-1(essential ratio0→-1.0;无效应 1.0→0)。
            # ratio None(基因不在 GEM)→跳过,不虚构(disposition 已 abstain/caution 表达)。
            return [round(k["ratio"] - 1.0, 4) for k in raw["knockouts"] if k["ratio"] is not None]
        if "carbon_sources" in raw:
            # 每个碳源 growth 相对 glucose 参照的变化:ratio_vs_glucose-1。
            # in_model=False(碳源不在模型 exchange)→跳过,不虚构。
            return [round(r["ratio_vs_glucose"] - 1.0, 4) for r in raw["carbon_sources"] if r["in_model"]]
        raise UnsupportedEngine(f"gem_fba map_case_delta 未支持 raw_output 形状: {sorted(raw)}")
    raise UnsupportedEngine(f"map_case_delta 未支持 engine={engine}")
