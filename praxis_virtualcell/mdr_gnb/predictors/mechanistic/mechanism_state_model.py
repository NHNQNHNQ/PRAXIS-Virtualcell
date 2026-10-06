"""MechanismStateModel:把非代谢靶耐药机制的基因型映射到 8 维状态维度。

两条通道:
1. 规则通道(默认、可解释、无需数据):声明式 GENE/MUTATION/PORIN/EFFLUX 规则表,
   每条规则指定 (维度, 方向, 强度)。已知基因型 → 状态朝生物学正确方向移动。
2. 学习通道(可选):若某 species 存在 learned artifact(基因型 one-hot → 状态回归),
   则用其覆盖对应维度;artifact 缺失/schema 不匹配自动退回规则通道(fail-closed)。

关键红线(D4):未知基因型不得扰动状态(否则制造假机理);每条被触发的规则写入
provenance,供 falsifiability 干预一致性核对。
"""
from __future__ import annotations

from dataclasses import dataclass

from .cell_state import STATE_DIMENSIONS, BacterialCellState


@dataclass(frozen=True)
class MechRule:
    dim: str  # 目标状态维度(须属 STATE_DIMENSIONS)
    delta: float  # 相对中点 0.5 的推动量(正=上调,负=下调)
    label: str  # 机制标签,写入 provenance


# 基因存在 -> 规则(基因名匹配用前缀,兼容等位后缀 -1/-2 等)
GENE_RULES: dict[str, MechRule] = {
    "blaKPC": MechRule("beta_lactamase_activity", +0.40, "carbapenemase_KPC"),
    "blaNDM": MechRule("beta_lactamase_activity", +0.45, "carbapenemase_NDM_MBL"),
    "blaOXA-48": MechRule("beta_lactamase_activity", +0.35, "carbapenemase_OXA48"),
    "blaVIM": MechRule("beta_lactamase_activity", +0.42, "carbapenemase_VIM_MBL"),
    "blaIMP": MechRule("beta_lactamase_activity", +0.42, "carbapenemase_IMP_MBL"),
    "blaCTX-M": MechRule("beta_lactamase_activity", +0.30, "ESBL_CTXM"),
    "blaCMY": MechRule("beta_lactamase_activity", +0.28, "AmpC_CMY"),
    "blaampC": MechRule("beta_lactamase_activity", +0.25, "AmpC_derepressed"),
    "armA": MechRule("ribosome_target_sensitivity", -0.40, "16S_methyltransferase_armA"),
    "rmtB": MechRule("ribosome_target_sensitivity", -0.40, "16S_methyltransferase_rmtB"),
    "tetA": MechRule("ribosome_target_sensitivity", -0.20, "tet_efflux_ribosome_protect"),
}

# 点突变 -> 规则(QRDR / 靶点脱敏)
MUTATION_RULES: dict[str, MechRule] = {
    "gyrA_S83L": MechRule("dna_gyrase_sensitivity", -0.35, "QRDR_gyrA_S83L"),
    "gyrA_D87N": MechRule("dna_gyrase_sensitivity", -0.30, "QRDR_gyrA_D87N"),
    "parC_S80I": MechRule("dna_gyrase_sensitivity", -0.25, "QRDR_parC_S80I"),
}

# 孔蛋白缺失 -> 外膜通透下降
PORIN_RULES: dict[str, MechRule] = {
    "ompK36": MechRule("outer_membrane_permeability", -0.35, "porin_loss_ompK36"),
    "ompK35": MechRule("outer_membrane_permeability", -0.25, "porin_loss_ompK35"),
    "oprD": MechRule("outer_membrane_permeability", -0.40, "porin_loss_oprD"),
    "ompC": MechRule("outer_membrane_permeability", -0.25, "porin_loss_ompC"),
    "ompF": MechRule("outer_membrane_permeability", -0.25, "porin_loss_ompF"),
}

# 外排过表达 -> 外排活性上升
EFFLUX_RULES: dict[str, MechRule] = {
    "adeABC": MechRule("efflux_activity", +0.40, "efflux_overexpr_adeABC"),
    "adeIJK": MechRule("efflux_activity", +0.30, "efflux_overexpr_adeIJK"),
    "mexAB": MechRule("efflux_activity", +0.40, "efflux_overexpr_mexAB_OprM"),
    "mexXY": MechRule("efflux_activity", +0.30, "efflux_overexpr_mexXY"),
    "acrAB": MechRule("efflux_activity", +0.35, "efflux_overexpr_acrAB_TolC"),
}


def _match_prefix(token: str, table: dict[str, MechRule]) -> MechRule | None:
    for key, rule in table.items():
        if token.lower().startswith(key.lower()):
            return rule
    return None


class MechanismStateModel:
    def __init__(self, learned_registry=None) -> None:
        # learned_registry:可选,提供 .get_state_regressor(species) -> callable|None
        self._learned = learned_registry

    def apply(
        self, state: BacterialCellState, *, amr_profile: dict
    ) -> BacterialCellState:
        """规则通道优先构建状态;若有 learned 覆盖则叠加(缺失自动退回规则)。"""
        deltas: dict[str, float] = {name: 0.0 for name in STATE_DIMENSIONS}
        fired: list[str] = []

        def _accumulate(tokens, table):
            for tok in tokens or []:
                rule = _match_prefix(str(tok), table)
                if rule is not None:
                    deltas[rule.dim] += rule.delta
                    fired.append(f"{tok}->{rule.label}")

        _accumulate(amr_profile.get("genes"), GENE_RULES)
        _accumulate(amr_profile.get("mutations"), MUTATION_RULES)
        _accumulate(amr_profile.get("porin_loss"), PORIN_RULES)
        _accumulate(amr_profile.get("efflux_overexpression"), EFFLUX_RULES)

        overrides = {
            name: state_val + deltas[name]
            for name, state_val in zip(STATE_DIMENSIONS, state.to_vector())
            if abs(deltas[name]) > 1e-9
        }
        new_state = state.copy_with(**overrides)
        new_state.provenance.extend(f"rule:{f}" for f in fired)

        # 学习通道覆盖(可选;fail-closed)
        if self._learned is not None:
            try:
                reg = self._learned.get_state_regressor(state.species)
            except Exception:  # noqa: BLE001
                reg = None
            if reg is not None:
                try:
                    learned_vec = reg(amr_profile)  # -> list[float] 长 8
                    ns = BacterialCellState.from_vector(state.species, learned_vec)
                    ns.provenance = list(new_state.provenance) + ["learned_state_regressor"]
                    return ns
                except Exception:  # noqa: BLE001 - 覆盖失败退回规则结果
                    new_state.provenance.append("learned_override_failed_fallback_rule")
        return new_state
