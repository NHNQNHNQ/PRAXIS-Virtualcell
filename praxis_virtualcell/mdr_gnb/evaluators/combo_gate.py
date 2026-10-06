"""逐 species×drug go/no-go 归类(G2)。

判定序:
  1) n_strains < min_strains 且 n_st_with_R < min_st_with_R → excluded(不入回归/建模)
  2) 有量但 ST_R 不足以做 ST 级显著检验(或无检验统计) → abstain_only(仅弃权主导)
  3) 有检验但未显著优于规则(effect_size > -min 或 p ≥ alpha) → degrade_classification(降级为规则/迁移分类)
  4) 显著优于规则(effect_size ≤ -min 且 p < alpha) → pass

契约字段(ComboGateResult)锁定,G0 依赖其默认值。
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class ComboGateResult:
    """一个 species×drug 组合的门控结论(字段锁定)。"""

    species: str
    drug: str
    status: str  # pass | degrade_classification | abstain_only | excluded
    n_strains: int
    vme_model: float | None = None
    vme_rule: float | None = None
    effect_size: float | None = None
    note: str = ""


@dataclass
class GatePrereg:
    """锚点门预注册参数(与 preregistration.yaml 对齐)。"""

    min_effect_size: float
    alpha: float
    min_st_with_R: int
    min_strains: int


def evaluate_combo_gate(
    species: str, drug: str, *, n_strains: int, n_st_with_R: int,
    vme_model: float | None, vme_rule: float | None,
    effect_size: float | None, p_value: float | None,
    prereg: GatePrereg,
) -> ComboGateResult:
    """按预注册效应量与样本量归类组合。"""
    def _mk(status: str, note: str) -> ComboGateResult:
        return ComboGateResult(species, drug, status, n_strains, vme_model, vme_rule, effect_size, note)

    if n_strains < prereg.min_strains and n_st_with_R < prereg.min_st_with_R:
        return _mk("excluded", f"数据不足(n={n_strains}, ST_R={n_st_with_R}),不进入建模")

    if n_st_with_R < prereg.min_st_with_R or effect_size is None or p_value is None:
        return _mk("abstain_only", f"ST_R={n_st_with_R} 不足以做 ST 级显著检验,仅弃权主导")

    significant = (effect_size <= -prereg.min_effect_size) and (p_value < prereg.alpha)
    if significant:
        return _mk("pass", f"显著优于规则:Δ={effect_size:.3f}, p={p_value:.4f}")
    return _mk(
        "degrade_classification",
        f"未显著优于规则(Δ={effect_size:.3f}, p={p_value:.4f}),降级为规则/迁移分类",
    )


def write_gate_report(result: ComboGateResult, out_dir: Path) -> Path:
    """写 reports/gates/<species>_<drug>.md。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{result.species}_{result.drug}.md"
    lines = [
        f"# Go/No-Go 门:{result.species} × {result.drug}",
        "",
        "> 仅科研筛选工具,非临床用药决策。",
        "",
        f"- 判定:**{result.status}**",
        f"- 菌株数 n_strains:{result.n_strains}",
        f"- VME(model):{result.vme_model}",
        f"- VME(rule):{result.vme_rule}",
        f"- 效应量(model-rule VME):{result.effect_size}",
        f"- 说明:{result.note}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
