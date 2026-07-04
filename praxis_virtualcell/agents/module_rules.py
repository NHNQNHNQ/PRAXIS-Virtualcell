"""module 确定性规则(决策 M1/M3):把归一请求映射到 primary/secondary module + mismatch query。

纯函数,零 LLM、零副作用。primary 规则与 route_table 的 engine 归属 + MODULES[mid]["engines"] 对齐。
这是 OFFLINE module 路由的确定性内核;LLM 版(Phase 4)只是换 primary/secondary 的产生方式,
但必须过滤成本模块的合法输出(复用"只能从候选选"约束)。
"""
from __future__ import annotations

# module id 常量(∈ MODULE_ORDER)
_M2 = "genetic_hub"
_M3 = "mitochondrial_energy_metabolism"
_M4 = "cytoplasmic_metabolism"
_M6 = "cytoskeletal_framework"
_M7 = "stress_processor"
_M8 = "degradation_machinery"

_METABOLIC = {"growth", "flux"}
_GENE_LIKE = {"gene", "gene_combination"}


def pick_primary(req: dict) -> str:
    """决策 M1:(perturbation_object, target_output) → primary module。全确定性。"""
    obj = req["perturbation_object"]
    out = req["target_output"]
    if out in _METABOLIC:
        return _M4                        # growth/flux → 胞质代谢(gem_fba/pathway_scoring)
    if out == "expression":
        if obj in _GENE_LIKE:
            return _M2                    # 基因扰动→表达 → 基因枢纽(donor_predictor)
        return _M7                        # 药物/配体→表达 → 应激(embedding 签名)
    if out == "state":
        if obj == "medium" and str(req.get("medium", "")).lower() == "niche":
            return _M6                    # niche 微环境→状态 → 细胞骨架/空间(spatial_niche)
        return _M7                        # 其余状态 → 应激(state_scoring)
    if out == "communication":
        return _M7                        # 通讯暂归应激/信号(待确认:是否新增通讯语义归属)
    return _M7                            # 兜底(理论不达;保守归应激)


def pick_secondary(req: dict, primary: str) -> list[str]:
    """决策 M1 secondary:最小确定性集。哺乳类 growth/flux 加 M3 能量代谢为 secondary。"""
    out = req["target_output"]
    species = req["species"]
    sec: list[str] = []
    if out in _METABOLIC and species in ("human", "mouse"):
        sec.append(_M3)
    return [m for m in sec if m != primary]   # 排除 primary


def mismatch_query_for(req: dict, module: str) -> str | None:
    """决策 M3:从 (species, module) 推 biological_mismatch query。命中交 registry 判 verdict。"""
    species = req["species"]
    if species == "bacteria" and module == _M8:
        return "bacteria_autophagy"        # 原核无真核自噬
    if species == "yeast" and module == _M6:
        return "tissue_spatial_niche"      # 单细胞真菌无组织 niche
    return None
