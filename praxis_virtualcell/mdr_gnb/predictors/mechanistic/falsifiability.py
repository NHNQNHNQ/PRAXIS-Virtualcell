"""机理层可证伪三支柱(D4 / Gate G3)。

1. run_ablation:对比"有机理特征 vs 去机理特征"的下游 SIR 性能(VME 为主判据),
   只有去掉后性能显著变差,才判定机理层"真做功";否则诚实报告机理主张不成立。
2. run_intervention_consistency:施加已知干预,断言状态朝 intervention 声明的
   expected_direction 移动;可选与真实株表型对照。任一方向错 -> 整体不一致。
3. correlate_mechanism_supervision:有外排活性/β-内酰胺酶水解等独立功能数据时,
   算 predicted 与 measured 的相关性;数据缺失记 "unverified"(不跳过、不假装通过)。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .cell_state import BacterialCellState
from .intervention import KNOWN_INTERVENTIONS, simulate_intervention


# ---------- 支柱 1:消融 ----------
@dataclass
class AblationResult:
    with_mechanism: dict
    without_mechanism: dict
    vme_delta: float  # without - with(正=去掉后更差=机理有用)
    major_error_delta: float
    mechanism_helps: bool
    conclusion: str
    evidence: list[dict] = field(default_factory=list)


def run_ablation(
    with_mechanism: dict,
    without_mechanism: dict,
    *,
    vme_worsen_threshold: float = 0.03,
) -> AblationResult:
    """with/without 需含键 vme、major_error、n_strains。"""
    vme_delta = float(without_mechanism["vme"]) - float(with_mechanism["vme"])
    me_delta = float(without_mechanism["major_error"]) - float(
        with_mechanism["major_error"]
    )
    helps = vme_delta >= vme_worsen_threshold
    if helps:
        conclusion = (
            f"机理层真做功:去掉后 VME 上升 {vme_delta:.3f} "
            f"(≥阈值 {vme_worsen_threshold}),机理特征提升了下游预测。"
        )
    else:
        conclusion = (
            f"机理层未做功:去掉后 VME 仅变化 {vme_delta:.3f} "
            f"(<阈值 {vme_worsen_threshold}),'机理可解释'主张不成立,"
            f"报告须降级为'仅代谢靶 FBA + 其余 abstain',不得用机理话术包装 latent。"
        )
    return AblationResult(
        with_mechanism=with_mechanism,
        without_mechanism=without_mechanism,
        vme_delta=vme_delta,
        major_error_delta=me_delta,
        mechanism_helps=helps,
        conclusion=conclusion,
        evidence=[{"kind": "ablation", "vme_worsen_threshold": vme_worsen_threshold}],
    )


# ---------- 支柱 2:干预一致性 ----------
def run_intervention_consistency(
    base_state: BacterialCellState,
    interventions: list[str],
    *,
    apply_fn=simulate_intervention,
    genotype_phenotype_refs: dict | None = None,
) -> dict:
    """对每个干预断言状态朝声明方向移动;可与已知基因型-表型对照。

    genotype_phenotype_refs:可选 {intervention_name: {"dim": str, "direction": "up"/"down"}}
    表示真实株观察到的表型方向,用于额外对照(缺失则只做算子内部一致性)。
    """
    checks = []
    for name in interventions:
        iv = KNOWN_INTERVENTIONS[name]
        after = apply_fn(base_state, name)
        delta = base_state.delta_to(after)
        ok = True
        detail = {}
        for dim, expected in iv.expected_direction.items():
            moved = delta.get(dim, 0.0)
            dir_ok = (moved > 0 and expected == "up") or (
                moved < 0 and expected == "down"
            )
            detail[dim] = {"delta": moved, "expected": expected, "ok": dir_ok}
            ok = ok and dir_ok
        # 与真实表型对照(如提供)
        ref_ok = None
        if genotype_phenotype_refs and name in genotype_phenotype_refs:
            ref = genotype_phenotype_refs[name]
            moved = delta.get(ref["dim"], 0.0)
            ref_ok = (moved > 0 and ref["direction"] == "up") or (
                moved < 0 and ref["direction"] == "down"
            )
            ok = ok and ref_ok
        checks.append(
            {
                "intervention": name,
                "consistent": ok,
                "dims": detail,
                "phenotype_ref_ok": ref_ok,
                "biology": iv.biology,
            }
        )
    return {"all_consistent": all(c["consistent"] for c in checks), "checks": checks}


# ---------- 支柱 3:独立机理监督相关性 ----------
def _spearman(a: list[float], b: list[float]) -> float:
    """无 scipy 依赖的 Spearman:先转秩再算 Pearson。"""
    n = len(a)
    if n < 2:
        return 0.0

    def _rank(x):
        order = sorted(range(len(x)), key=lambda i: x[i])
        r = [0.0] * len(x)
        i = 0
        while i < len(x):
            j = i
            while j + 1 < len(x) and x[order[j + 1]] == x[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r

    ra, rb = _rank(a), _rank(b)
    ma = sum(ra) / n
    mb = sum(rb) / n
    num = sum((ra[i] - ma) * (rb[i] - mb) for i in range(n))
    da = sum((ra[i] - ma) ** 2 for i in range(n)) ** 0.5
    db = sum((rb[i] - mb) ** 2 for i in range(n)) ** 0.5
    return 0.0 if da == 0 or db == 0 else num / (da * db)


def correlate_mechanism_supervision(
    predicted: dict[str, list[float]],
    measured: dict[str, list[float]],
    *,
    verify_threshold: float = 0.5,
) -> dict:
    """对每个有独立功能数据的维度算相关性;无数据记 unverified。"""
    out: dict[str, dict] = {}
    for dim, pred in predicted.items():
        meas = measured.get(dim)
        if not meas or len(meas) != len(pred) or len(pred) < 2:
            out[dim] = {
                "status": "unverified",
                "note": "缺独立机理功能数据(外排活性/β-内酰胺酶水解等),记为未验证而非跳过",
            }
            continue
        rho = _spearman(list(pred), list(meas))
        out[dim] = {
            "status": "verified" if rho >= verify_threshold else "verified_but_weak",
            "spearman": rho,
            "n": len(pred),
        }
    return out
