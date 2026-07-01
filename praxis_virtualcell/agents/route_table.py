"""W1.2(v0.4):route table + applicability rules。

据归一后的请求(见 species_schema.normalize_request)决定路由到哪个引擎,并给出 reliability
disposition。这是**声明式能力图**(presence-absence),不下性能结论;真值由下游引擎跑出。

引擎:
  donor_predictor  哺乳类 scRNA delta-expression predictor(human 原生 / mouse ortholog 迁移)
  gem_fba          基因组尺度代谢模型 / FBA(bacteria/yeast growth·flux 的机制模型)
  embedding        药物/配体扰动的 signature / embedding 模型(CPA/LINCS 等,下游多为 data-gated)
  reject           无适用引擎 → 拒绝/弃权

disposition:accept(直接用)/ caution(带告警用,如 ortholog)/ downgrade(降级:引擎在但
证据/数据不足,不可全信)/ abstain(弃权:无适用引擎)。

applicability 铁律:哺乳类 predictor **不得**用于 bacteria/yeast growth → 路由 gem_fba 或 abstain;
细菌/酵母的 expression/state 无适用 scRNA predictor → abstain(negative transfer)。
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict

ENGINES = ("donor_predictor", "gem_fba", "embedding", "reject")

_MAMMAL = {"human", "mouse"}
_MICROBE = {"bacteria", "yeast"}
_GENE_LIKE = {"gene", "gene_combination"}
_METABOLIC = {"growth", "flux"}


@dataclass
class RouteDecision:
    engine: str
    disposition: str                       # accept / caution / downgrade / abstain
    reason: str
    caution_flags: list[str] = field(default_factory=list)
    data_gated: bool = False               # 引擎存在但下游数据/模型未就位(真跑前必为降级/弃权)

    def to_dict(self) -> dict:
        return asdict(self)


def route(req: dict) -> RouteDecision:
    """把归一请求映射到路由决策(纯声明式,不跑模型)。"""
    sp = req["species"]
    obj = req["perturbation_object"]
    out = req["target_output"]

    # --- 代谢型输出(growth/flux):机制模型领地 ---
    if out in _METABOLIC:
        if sp in _MICROBE and (obj in _GENE_LIKE or obj == "medium"):
            return RouteDecision("gem_fba", "accept",
                                 reason=f"{sp}_metabolic_gem_fba")
        if sp in _MAMMAL:
            # 哺乳类 flux 需 scFEA/Compass,尚未接入 → 不假装
            return RouteDecision("gem_fba", "downgrade",
                                 reason="mammalian_flux_model_not_wired",
                                 data_gated=True)
        # 其余(如 medium 改变的 growth)暂无接入
        return RouteDecision("reject", "abstain",
                             reason="no_metabolic_engine_for_request")

    # --- 药物扰动:LINCS L1000 签名 DB 已接入(W3.1)→ 非 data-gated,但签名噪声大故 caution ---
    if obj == "drug":
        return RouteDecision("embedding", "caution",
                             reason="drug_signature_db_wired", data_gated=False)
    # --- 配体扰动:signature/communication 模型未接入 → data-gated ---
    if obj == "ligand":
        return RouteDecision("embedding", "downgrade",
                             reason="ligand_signature_model_data_gated", data_gated=True)

    # --- 基因扰动 → 表达/状态:哺乳类 scRNA predictor 领地 ---
    if obj in _GENE_LIKE and out in ("expression", "state"):
        if sp == "human":
            return RouteDecision("donor_predictor", "accept",
                                 reason="human_native_scrna_predictor")
        if sp == "mouse":
            # human predictor 迁 mouse:applicable 但需 ortholog(§7.3),带 caution 降级
            return RouteDecision("donor_predictor", "caution",
                                 reason="human_predictor_transfer_to_mouse_requires_ortholog",
                                 caution_flags=["ortholog_required"])
        if sp in _MICROBE:
            # 铁律:哺乳类 scRNA predictor 不适用于微生物 → abstain
            return RouteDecision("reject", "abstain",
                                 reason="mammalian_scrna_predictor_not_applicable")

    # --- communication 等其余:暂无接入引擎 ---
    if out == "communication":
        return RouteDecision("embedding", "downgrade",
                             reason="communication_model_data_gated",
                             data_gated=True)

    return RouteDecision("reject", "abstain", reason="no_applicable_engine")
