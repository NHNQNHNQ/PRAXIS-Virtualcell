"""engine→真实 run_*_case 分发 + CaseReport→delta 映射。B1 实现 gem_fba 的 gene→growth,
B2 Task1 加 gem_fba 的 medium(碳源切换)→growth,Task2 加 gem_fba 的 drug(抗生素靶抑制)→growth
(均 bacteria only)。B3 Task1 加 embedding 的 human+drug→MOA 签名(LINCS,human-guarded;
route 亦把 ligand 判 embedding 但未接模型,故 embedding 分支再加 obj==drug 守卫,ligand 落诚实 abstain)。
B3 Task3 加 state_scoring 的 human+IFN-β→cell_state(Kang 2018 ISG 激活评分,复用 B2 的
_is_ifn_beta 窄门;非 IFN-β/mouse 是状态刻画类别错误,诚实 abstain,不冒充扰动预测)。
其余 engine 子路径由后续增量 task 往这里加分支。"""
from __future__ import annotations

import os

from praxis_virtualcell.core.exceptions import UnsupportedEngine

# 已接入真实预测的 engine(单一真源;被 agents.model_applicability 直接 import,不镜像)
REAL_ENGINES = frozenset({"gem_fba", "pathway_scoring", "embedding", "state_scoring"})


def _gears_importable() -> bool:
    """torch + gears 是否可 import(轻量探测,不载 ckpt/不跑推理)。Mac 无 torch → False。"""
    import importlib.util
    return (importlib.util.find_spec("torch") is not None
            and importlib.util.find_spec("gears") is not None)


def gears_available() -> bool:
    """donor_predictor 是否可走真实 GEARS:GEARS_CKPT 环境变量非空 且 torch+gears 可 import。
    确定性、无副作用。Mac(无 torch)恒 False → donor_predictor 落回 mock;.53(ckpt+torch)→ True。"""
    return bool(os.environ.get("GEARS_CKPT")) and _gears_importable()

# 与 agents.route_table._GENE_LIKE 对齐:单基因/多基因联合敲除同属 gem_fba gene→growth
_GENE_LIKE = frozenset({"gene", "gene_combination"})

# metabolic_tendency 只覆盖 human Kang 2018 IFN-β 刺激场景。
# IFN-β 精确别名白名单(strip().lower() 后精确匹配,非子串——避免 IFNB2[IL-6 历史别名]、
# "interferon binding protein" 等自由文本/别名碰撞被误判为 IFN-β 而张冠李戴到 Kang 数据);
# 故 IFN-γ/α、IFNB2/IL-6、任意基因/非 human 物种 → 落 UnsupportedEngine → 诚实 abstain,不虚构固定 IFN-β 数值。
_IFN_BETA_ALIASES = frozenset({
    "ifnb1", "ifnb", "ifn-b1", "ifnβ", "ifn-β", "ifn-beta", "ifnbeta",
    "interferon beta", "interferon-beta", "interferon β", "interferon beta 1", "interferon-beta-1",
})


def _is_ifn_beta(targets) -> bool:
    # 非空且**全部** target 都是 IFN-β 别名才算 IFN-β 场景(固定 Kang IFN-β 数据无法建模含其它扰动的组合;
    # 混入非 IFN-β target 若仍用 any() 放行会静默吞掉其它组分,只覆盖数据的一半却冒充完整预测)。
    ts = [str(t).strip().lower() for t in (targets or [])]
    return bool(ts) and all(t in _IFN_BETA_ALIASES for t in ts)


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
        elif obj == "drug" and species == "bacteria":
            # 抗生素靶抑制目前只有 bacteria(iML1515)接入;非 bacteria 无对应 runner → 诚实 UnsupportedEngine。
            from praxis_virtualcell.predictors.mechanistic.antibiotic import run_antibiotic_case
            return run_antibiotic_case
    elif engine == "pathway_scoring":
        if species == "human" and _is_ifn_beta(raw_req.get("perturbation_targets")):
            from praxis_virtualcell.predictors.state.metabolic_tendency import run_metabolic_tendency_case
            return run_metabolic_tendency_case
        # 非 human 或非 IFN-β:metabolic_tendency 只有 human Kang IFN-β 数据 → 落末尾 UnsupportedEngine → 诚实 abstain
    elif engine == "embedding":
        if raw_req.get("species") == "human" and obj == "drug":
            if raw_req.get("perturbation_dose") is not None:
                # 请求带 perturbation_dose(主链 asdict 保留的字段)→ 剂量响应意图 → drug_dose
                # (LINCS 剂量子集,Spearman 单调性)
                from praxis_virtualcell.predictors.embedding.drug_dose import run_drug_dose_case
                return run_drug_dose_case
            from praxis_virtualcell.predictors.embedding.drug_signature import run_drug_response_case
            return run_drug_response_case
        # 非 human 或非 drug(如 ligand,route 判 embedding 但 data_gated 未接模型)→ 落末尾
        # UnsupportedEngine → 诚实 abstain(不把 ligand 当药名去查 DrugSignatureDB 而误标 drug_not_in_db)
    elif engine == "state_scoring":
        if raw_req.get("species") == "human" and _is_ifn_beta(raw_req.get("perturbation_targets")):
            from praxis_virtualcell.predictors.state.cell_state import run_cellstate_case
            return run_cellstate_case
        # 非 human 或非 IFN-β(emt 的 gene→state、fate 的 mouse state)→ 落 UnsupportedEngine →
        # 诚实 abstain(cell_state 只有固定 Kang human IFN-β 数据,不接刻画类工具冒充扰动预测)
    elif engine == "donor_predictor":
        # M2:human gene→expression 真实 GEARS(.53 gated)。dispatch 层也校验 gears_available()
        # (defense-in-depth:GEARS 不可用即诚实 UnsupportedEngine,不声称 applicable 后失败)。
        if (species == "human" and obj in _GENE_LIKE
                and raw_req.get("target_output") == "expression" and gears_available()):
            from praxis_virtualcell.predictors.ml.gears_case import run_gears_case
            return run_gears_case
        # 非 human/非 gene/非 expression/GEARS 不可用 → 落末尾 UnsupportedEngine → 诚实 abstain/reject
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
        if "antibiotics" in raw:
            # 每个抗生素靶抑制后 growth 相对 WT 的变化:ratio_vs_wt-1。
            # 非代谢靶/未知抗生素/靶反应不在模型 → 无 ratio_vs_wt → 跳过,不虚构。
            return [round(r["ratio_vs_wt"] - 1.0, 4) for r in raw["antibiotics"]
                    if r.get("in_model") and r.get("ratio_vs_wt") is not None]
        raise UnsupportedEngine(f"gem_fba map_case_delta 未支持 raw_output 形状: {sorted(raw)}")
    if engine == "pathway_scoring":  # 代谢通路 tendency:各通路 Cohen's d 效应量作 delta 分量
        return [round(s["cohens_d"], 4) for s in report.raw_output["pathway_shifts"]]
    if engine == "embedding":
        if "per_drug" in raw:
            # 每个在库药物的 MOA 富集比作 delta 分量;不在库(in_db=False)→无 moa_enrichment,跳过不虚构。
            return [round(d["moa_enrichment"], 4) for d in raw["per_drug"]
                    if d.get("in_db") and d.get("moa_enrichment") is not None]
        if "dose_response" in raw:   # drug_dose:剂量-recall 单调性 Spearman
            # 药不在剂量库 → dose_response=None → 空 delta(→abstain,不虚构),不对 None 下标
            dr = raw["dose_response"]
            return [round(dr["spearman"], 4)] if dr is not None else []
        raise UnsupportedEngine(f"embedding map_case_delta 未支持 raw_output 形状: {sorted(raw)}")
    if engine == "state_scoring":
        if "per_cell_type" in report.raw_output:   # cell_state:整体 ISG 组间 Cohen's d
            return [round(report.raw_output["cohens_d"], 4)]
        raise UnsupportedEngine(f"state_scoring map_case_delta 未支持 raw_output 形状: {sorted(report.raw_output)}")
    if engine == "donor_predictor":
        if "gears_delta" in raw:   # GEARS-内部 delta(已在 wrapper round 定点)
            return list(raw["gears_delta"])
        raise UnsupportedEngine(f"donor_predictor map_case_delta 未支持 raw_output 形状: {sorted(raw)}")
    raise UnsupportedEngine(f"map_case_delta 未支持 engine={engine}")
