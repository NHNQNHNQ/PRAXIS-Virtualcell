"""simulate_intervention:对 BacterialCellState 施加已知基因型干预,产出新状态。

用途(D4 干预一致性):把"ompK36 缺失/ampC 去阻遏/mexAB 过表达/oprD 缺失"等
可控扰动映射到状态维度的定向改动,再喂给下游 SIR 预测,检验状态确实朝已知
生物学方向移动(falsifiability.run_intervention_consistency 断言)。
"""
from __future__ import annotations

from dataclasses import dataclass

from .cell_state import STATE_DIMENSIONS, BacterialCellState


@dataclass(frozen=True)
class Intervention:
    name: str
    effects: dict[str, float]  # 维度 -> 定向增量
    expected_direction: dict[str, str]  # 维度 -> "up"/"down"(供一致性断言)
    biology: str


def _mk(name, effects, biology) -> Intervention:
    direction = {d: ("up" if v > 0 else "down") for d, v in effects.items()}
    for d in effects:
        assert d in STATE_DIMENSIONS, f"干预 {name} 目标维度 {d} 非法"
    return Intervention(name=name, effects=effects, expected_direction=direction, biology=biology)


KNOWN_INTERVENTIONS: dict[str, Intervention] = {
    "ompK36_knockout": _mk(
        "ompK36_knockout",
        {"outer_membrane_permeability": -0.35},
        "OmpK36 孔蛋白缺失 → 外膜对碳青霉烯/头孢通透性下降 → 药物入胞减少。",
    ),
    "oprD_knockout": _mk(
        "oprD_knockout",
        {"outer_membrane_permeability": -0.40},
        "OprD 缺失 → 铜绿假单胞菌碳青霉烯特异通道丢失 → 亚胺培南入胞减少。",
    ),
    "ampC_derepression": _mk(
        "ampC_derepression",
        {"beta_lactamase_activity": +0.35},
        "ampC 去阻遏(ampD/ampR 突变)→ AmpC 高产 → 三代头孢/头孢西丁水解增强。",
    ),
    "mexAB_overexpression": _mk(
        "mexAB_overexpression",
        {"efflux_activity": +0.40},
        "MexAB-OprM 过表达(nalB/mexR 突变)→ RND 外排增强 → 胞内药物浓度下降。",
    ),
    "adeABC_overexpression": _mk(
        "adeABC_overexpression",
        {"efflux_activity": +0.40},
        "AdeABC 过表达(adeRS 突变)→ 鲍曼不动杆菌多药外排增强。",
    ),
    "gyrA_qrdr_mutation": _mk(
        "gyrA_qrdr_mutation",
        {"dna_gyrase_sensitivity": -0.35},
        "GyrA QRDR(S83L 等)突变 → 氟喹诺酮靶点亲和力下降 → 敏感性降低。",
    ),
    "carbapenemase_acquisition": _mk(
        "carbapenemase_acquisition",
        {"beta_lactamase_activity": +0.45},
        "获得 KPC/NDM 等碳青霉烯酶 → β-内酰胺(含碳青霉烯)水解通量大增。",
    ),
}


def simulate_intervention(
    state: BacterialCellState, intervention: str
) -> BacterialCellState:
    """对 state 施加命名干预,返回新状态(纯函数);未知干预抛 KeyError。"""
    iv = KNOWN_INTERVENTIONS[intervention]  # 未知 -> KeyError(可证伪:不容默默 no-op)
    overrides = {}
    cur = dict(zip(STATE_DIMENSIONS, state.to_vector()))
    for dim, inc in iv.effects.items():
        overrides[dim] = cur[dim] + inc
    out = state.copy_with(**overrides)
    out.provenance.append(f"intervention:{intervention}")
    return out
