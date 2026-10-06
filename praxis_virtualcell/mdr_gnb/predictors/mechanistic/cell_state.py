"""BacterialCellState:契约锁定的 8 维细菌机理状态向量。

设计原则(D4):
- 每一维都对应可独立监督的生物学量(外排活性、β-内酰胺酶水解等),
  不是无解释的 latent;所以带 DIMENSION_BIOLOGY 说明,并在 falsifiability
  里被独立数据校验。
- 取值域统一 [0,1](0=该功能关闭/敏感,1=该功能全开/耐受),便于干预算子
  与下游特征拼接;构造时自动钳制,避免越界污染下游。
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields

# 契约锁定:维度名 + 顺序(to_vector/from_vector 依赖此顺序)
STATE_DIMENSIONS: tuple[str, ...] = (
    "cell_wall_stress",
    "outer_membrane_permeability",
    "efflux_activity",
    "beta_lactamase_activity",
    "ribosome_target_sensitivity",
    "dna_gyrase_sensitivity",
    "oxidative_stress_response",
    "biofilm_state",
)

# 每一维的生物学锚点(供报告与独立监督校验;禁止空洞措辞)
DIMENSION_BIOLOGY: dict[str, str] = {
    "cell_wall_stress": "肽聚糖合成受扰程度(PBP 抑制/自溶);高=细胞壁应激强,利于 β-内酰胺杀伤。",
    "outer_membrane_permeability": "外膜对亲水抗生素的通透性(孔蛋白 OmpK35/36、OprD 等);低=药物难入胞。",
    "efflux_activity": "RND 外排泵主动外排活性(AdeABC/MexAB-OprM/AcrAB-TolC);高=胞内药物浓度被泵低。",
    "beta_lactamase_activity": "β-内酰胺酶水解通量(ESBL/AmpC/KPC/NDM 等);高=β-内酰胺被降解。",
    "ribosome_target_sensitivity": "30S/50S 核糖体靶点对氨基糖苷/四环素/大环内酯的敏感性;低=靶点保护/甲基化。",
    "dna_gyrase_sensitivity": "GyrA/ParC 对氟喹诺酮的敏感性;低=QRDR 突变致靶点脱敏。",
    "oxidative_stress_response": "氧化应激/SOS 应答激活度;影响杀菌抗生素次级致死与突变率。",
    "biofilm_state": "生物膜形成程度;高=表型耐受、药物渗透受限。",
}


def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else float(x)


@dataclass
class BacterialCellState:
    """8 维机理状态向量;所有维度构造后钳制到 [0,1]。"""

    species: str
    cell_wall_stress: float = 0.5
    outer_membrane_permeability: float = 0.5
    efflux_activity: float = 0.5
    beta_lactamase_activity: float = 0.5
    ribosome_target_sensitivity: float = 0.5
    dna_gyrase_sensitivity: float = 0.5
    oxidative_stress_response: float = 0.5
    biofilm_state: float = 0.5
    # 溯源:该状态由哪些证据/规则/模型产生(供 trace 与报告)
    provenance: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        for name in STATE_DIMENSIONS:
            object.__setattr__(self, name, _clamp01(getattr(self, name)))

    def to_vector(self) -> list[float]:
        return [getattr(self, name) for name in STATE_DIMENSIONS]

    @classmethod
    def from_vector(cls, species: str, vec: list[float]) -> "BacterialCellState":
        if len(vec) != len(STATE_DIMENSIONS):
            raise ValueError(
                f"状态向量维度须为 {len(STATE_DIMENSIONS)},收到 {len(vec)}"
            )
        kwargs = {name: float(v) for name, v in zip(STATE_DIMENSIONS, vec)}
        return cls(species=species, **kwargs)

    def copy_with(self, **overrides: float) -> "BacterialCellState":
        """返回改若干维度后的新状态(干预算子用,不原地改)。"""
        base = {name: getattr(self, name) for name in STATE_DIMENSIONS}
        base.update({k: v for k, v in overrides.items() if k in STATE_DIMENSIONS})
        prov = list(self.provenance)
        return BacterialCellState(species=self.species, provenance=prov, **base)

    def delta_to(self, other: "BacterialCellState") -> dict[str, float]:
        """只报告发生变化的维度差值(other - self)。"""
        out: dict[str, float] = {}
        for name in STATE_DIMENSIONS:
            d = getattr(other, name) - getattr(self, name)
            if abs(d) > 1e-9:
                out[name] = d
        return out


# 快速自检:字段与契约一致(catch 手误)
_declared = {f.name for f in fields(BacterialCellState)} - {"species", "provenance"}
assert _declared == set(STATE_DIMENSIONS), "BacterialCellState 字段与 STATE_DIMENSIONS 不一致"
