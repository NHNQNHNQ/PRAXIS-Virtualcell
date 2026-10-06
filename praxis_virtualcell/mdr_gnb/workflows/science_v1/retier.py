"""S6:132 组合重打 E0-E5 最终证据面(纯 CSV 聚合,science v1 证据面 capstone)。

把冻结 v0.9 面 + S2 abstain 复评 + S3 lineage holdout 三份成果聚合,给每个组合按
优先级(从高到低,取第一命中)重打 E0-E5,产 v1 最终面 + v0.9→v1 迁移 + 升级/降级诚实清单。

**v1 并存**:只产 evidence_tiers_v1.yaml,绝不回写生产 model_zoo/evidence_tiers.yaml
(生产 API 门控读那份,不动已上线的门控)。

判据(优先级从高到低,取第一命中):
  E5 external    在 S3 holdout anchor panel 且通过(该 anchor 全部 held cluster ΔVME 均值≤0)
  E4 strong/safety-pass  冻结 tier=strong / S2 upgraded_to_strong / S2 upgraded_to_safety_pass
  E3 evaluated   冻结 tier=practical 且 S2 remained_practical(做过 ST-CV 但未显著优于规则)
  E2 model_only  冻结 tier=no_baseline(有模型+确定性 E2E 预测,但规则表未收录该药、无对照基线)
  E1 artifact    冻结 tier=unevaluated(有 joblib artifact 但未做 CV)
  E0             无(132 组合都有模型;真有占位组合才 E0)

注:E5 优先于 E4(某组合既 strong 又过 holdout → E5)。

一键复现(确定性,重跑字节一致):
    .venv/bin/python -m praxis_virtualcell.mdr_gnb.workflows.science_v1.retier
"""
from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path

import yaml

from ._io import write_csv

_ROOT = Path(__file__).resolve().parents[4]
_FREEZE = _ROOT / "reports" / "antibacterial" / "mdr_gnb" / "science_v0.9_freeze" / "02_evidence_surface_132.csv"
_ABSTAIN = _ROOT / "reports" / "antibacterial" / "mdr_gnb" / "science_v1" / "abstain_m3"
_HOLDOUT = _ROOT / "reports" / "antibacterial" / "mdr_gnb" / "science_v1" / "external_holdout" / "lineage_holdout_metrics.csv"
_OUT = _ROOT / "reports" / "antibacterial" / "mdr_gnb" / "science_v1" / "evidence_tiers"

# tier_v1 语义标签 → 数字 E 级别
_TIER_LABEL = {
    "E5_external": "E5",
    "E4_strong": "E4",
    "E4_safety_pass": "E4",
    "E3_evaluated": "E3",
    "E2_model_only": "E2",
    "E1_artifact": "E1",
    "E0": "E0",
}


def _load_combo_set(path: Path) -> set[tuple[str, str]]:
    """读 CSV 取 (species,drug) 集合。"""
    with open(path) as f:
        return {(r["species"], r["drug"]) for r in csv.DictReader(f)}


def _holdout_passed() -> dict[tuple[str, str], float]:
    """按 anchor 聚合 held cluster ΔVME,均值≤0 视为通过外推。返回 {(sp,drug): mean_dvme}(仅通过者)。"""
    by_anchor: dict[tuple[str, str], list[float]] = defaultdict(list)
    with open(_HOLDOUT) as f:
        for r in csv.DictReader(f):
            by_anchor[(r["species"], r["drug"])].append(float(r["delta_vme"]))
    passed = {}
    for k, ds in by_anchor.items():
        mean = sum(ds) / len(ds)
        if mean <= 0:  # 不劣于规则
            passed[k] = round(mean, 4)
    return passed


def _classify(row: dict, up_strong: set, up_safety: set, remained: set, hd_pass: dict) -> str:
    """按优先级判 tier_v1(取第一命中)。"""
    key = (row["species"], row["drug"])
    tier = row["tier"]
    if key in hd_pass:
        return "E5_external"
    if tier == "strong" or key in up_strong:
        return "E4_strong"
    if key in up_safety:
        return "E4_safety_pass"
    if tier == "practical" and key in remained:
        return "E3_evaluated"
    if tier == "no_baseline":
        return "E2_model_only"
    if tier == "unevaluated":
        return "E1_artifact"
    return "E0"


def _direction(e0: str, e1: str) -> str:
    """E 级别数字上升=upgraded、相同=same、下降=downgraded。"""
    n0, n1 = int(e0[1]), int(e1[1])
    if n1 > n0:
        return "upgraded"
    if n1 < n0:
        return "downgraded"
    return "same"


def build() -> tuple[list[dict], list[dict]]:
    """聚合三份产物,重打 E0-E5,落盘全部 5 个产物。返回 (surface, transition)。"""
    _OUT.mkdir(parents=True, exist_ok=True)
    with open(_FREEZE) as f:
        freeze = list(csv.DictReader(f))
    up_strong = _load_combo_set(_ABSTAIN / "upgraded_to_strong.csv")
    up_safety = _load_combo_set(_ABSTAIN / "upgraded_to_safety_pass.csv")
    remained = _load_combo_set(_ABSTAIN / "remained_practical.csv")
    hd_pass = _holdout_passed()

    surface: list[dict] = []
    transition: list[dict] = []
    for r in freeze:  # 保持冻结面 132 顺序,确定性
        key = (r["species"], r["drug"])
        tier_v1 = _classify(r, up_strong, up_safety, remained, hd_pass)
        e1 = _TIER_LABEL[tier_v1]
        e0 = r["evidence_level"]
        validated = key in hd_pass
        surface.append({
            "species": r["species"],
            "drug": r["drug"],
            "tier_v0_9": r["tier"],
            "evidence_level_v0_9": e0,
            "tier_v1": tier_v1,
            "evidence_level_v1": e1,
            "holdout_validated": "true" if validated else "false",
            "delta_vme": r["delta_vme"],
            "p_value": r["p_value"],
        })
        transition.append({
            "species": r["species"],
            "drug": r["drug"],
            "evidence_level_v0_9": e0,
            "evidence_level_v1": e1,
            "direction": _direction(e0, e1),
        })

    write_csv(
        _OUT / "final_evidence_surface.csv",
        ["species", "drug", "tier_v0_9", "evidence_level_v0_9", "tier_v1",
         "evidence_level_v1", "holdout_validated", "delta_vme", "p_value"],
        surface,
    )
    write_csv(
        _OUT / "evidence_tier_transition_from_v0.9.csv",
        ["species", "drug", "evidence_level_v0_9", "evidence_level_v1", "direction"],
        transition,
    )
    _write_yaml(surface, hd_pass)
    _write_upgraded_md(surface, hd_pass, up_strong, up_safety)
    _write_downgraded_md(surface, remained)
    return surface, transition


def _num(v: str):
    """空串→None,否则 float(供 yaml 用)。"""
    return float(v) if v not in ("", None) else None


def _write_yaml(surface: list[dict], hd_pass: dict) -> None:
    """产 v1 证据分层(独立文件,格式类似生产 evidence_tiers.yaml 但绝不回写生产)。"""
    entries = []
    for r in surface:
        key = (r["species"], r["drug"])
        e = {
            "species": r["species"],
            "drug": r["drug"],
            "tier_v1": r["tier_v1"],
            "evidence_level_v1": r["evidence_level_v1"],
            "holdout_validated": r["holdout_validated"] == "true",
            "delta_vme": _num(r["delta_vme"]),
            "p_value": _num(r["p_value"]),
        }
        if key in hd_pass:  # E5:附 holdout held cluster ΔVME 均值
            e["holdout_mean_delta_vme"] = hd_pass[key]
        entries.append(e)
    header = (
        "# Science v1.0 证据分层(S6 retier 产,聚合冻结 v0.9 + S2 abstain + S3 lineage holdout)\n"
        "# v1 并存:本文件独立,绝不回写生产 model_zoo/evidence_tiers.yaml(生产 API 门控读那份)\n"
        "# tier_v1 语义:E5_external=过 holdout 外推 / E4_strong=显著优于规则或 abstain 升 strong /\n"
        "#   E4_safety_pass=abstain 在高覆盖下 covered-VME≤规则(fail-closed 安全收益) /\n"
        "#   E3_evaluated=ST-CV 过但未显著优于规则 / E2_model_only=有模型但规则表无该药、无对照基线 /\n"
        "#   E1_artifact=有 joblib 但未做 CV\n"
    )
    (_OUT / "evidence_tiers_v1.yaml").write_text(
        header + yaml.safe_dump({"evidence_tiers_v1": entries}, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def _md_table(rows: list[dict]) -> str:
    """组合小表:species | drug | v0.9 | v1 | ΔVME。"""
    out = ["| species | drug | v0.9 | v1 | ΔVME(ST-CV) |", "|---|---|:--:|:--:|--:|"]
    for r in rows:
        dv = r["delta_vme"] if r["delta_vme"] else "—"
        out.append(f"| {r['species']} | {r['drug']} | {r['evidence_level_v0_9']} | {r['evidence_level_v1']} | {dv} |")
    return "\n".join(out)


def _write_upgraded_md(surface: list[dict], hd_pass: dict, up_strong: set, up_safety: set) -> None:
    """升级组合诚实清单:strong→E5、practical→E5、practical→E4(strong-pass / safety-pass)。"""
    up = [r for r in surface if _direction(r["evidence_level_v0_9"], r["evidence_level_v1"]) == "upgraded"]
    # 分桶
    strong_to_e5 = [r for r in up if r["tier_v1"] == "E5_external" and r["evidence_level_v0_9"] == "E4"]
    prac_to_e5 = [r for r in up if r["tier_v1"] == "E5_external" and r["evidence_level_v0_9"] == "E3"]
    prac_to_strong = [r for r in up if r["tier_v1"] == "E4_strong"]
    prac_to_safety = [r for r in up if r["tier_v1"] == "E4_safety_pass"]
    # practical→E5 里同时过 S2 safety-pass 的(可读串)
    e5_also_safety = "、".join(
        f"{r['species']}×{r['drug']}" for r in prac_to_e5 if (r["species"], r["drug"]) in up_safety
    ) or "无"

    md = f"""# S6 升级组合(v0.9 → v1,共 {len(up)} 个 E 级别上升)

聚合 S2 abstain 复评 + S3 lineage holdout 后,{len(up)} 个组合证据级别上升。升级只来自
**真做过的评估**(holdout 外推 / abstain-aware 复评),不凭空拔高。

## strong(E4) → E5 external-supported({len(strong_to_e5)} 个)

冻结面已 strong-pass 的组合,S3 lineage holdout(留出整组稀有谱系群)上融合仍不劣于规则
(该 anchor 全部 held cluster ΔVME 均值 ≤0),获外推支撑升 E5。

{_md_table(strong_to_e5)}

## practical(E3) → E5 external-supported({len(prac_to_e5)} 个,跨 2 级最大跳)

冻结面仅 practical(不劣于规则但未显著)的组合,在 holdout 外推上依然不劣于规则,直接升
E5。其中 {e5_also_safety} 同时也过 S2 safety-pass。

{_md_table(prac_to_e5)}

## practical(E3) → E4 strong-pass({len(prac_to_strong)} 个,S2 abstain 升 strong)

S2 abstain-aware 复评:在 c=1.0 满覆盖下 per-ST VME 显著优于规则(ΔVME<0 且 p<0.05),
从 practical 实升 strong-pass。

{_md_table(prac_to_strong)}

## practical(E3) → E4 safety-pass({len(prac_to_safety)} 个,S2 abstain 高覆盖安全收益)

S2 abstain-aware 复评:在覆盖率 ≥0.8 下,对 covered 子集把危险漏判 VME 压到 ≤规则且 ME 受控
(fail-closed + abstain 叙事核心),升 safety-pass。这些**未过 holdout**(不在 anchor panel),
故止步 E4 不升 E5。

{_md_table(prac_to_safety)}
"""
    (_OUT / "upgraded_cases.md").write_text(md, encoding="utf-8")


def _write_downgraded_md(surface: list[dict], remained: set) -> None:
    """降级组合 + 诚实边界:敢说哪些不能预测/无对照。"""
    down = [r for r in surface if _direction(r["evidence_level_v0_9"], r["evidence_level_v1"]) == "downgraded"]
    e2 = [r for r in surface if r["tier_v1"] == "E2_model_only"]
    e1 = [r for r in surface if r["tier_v1"] == "E1_artifact"]
    e3 = [r for r in surface if r["tier_v1"] == "E3_evaluated"]
    down_by_sp = Counter(r["species"] for r in down)

    md = f"""# S6 降级组合 + 诚实边界(敢说哪些不能预测)

## 降级({len(down)} 个:全部 no_baseline 的 E3 → E2)

v0.9 冻结面把 **no_baseline**(有模型 + 确定性 E2E 预测,但规则表未收录该药、**无对照基线**)
一律记 E3,与真做过 ST-CV 的 practical 同级——这是 v0.9 的乐观。v1 诚实拆开:no_baseline 降为
**E2 model_only**。

这**不是能力回退**,是**诚实修正**:E2 组合有可跑的模型和确定性预测,但因规则表无该药、
没有对照基线,**无法声称优于规则**,也没做过 CV,故不配 E3。

降级分物种计数:{dict(sorted(down_by_sp.items()))}(共 {len(down)} 个,均 no_baseline)。

## 诚实边界:哪些组合**不能**声称优于规则

### E2 model_only({len(e2)} 个)— 有模型、无对照

有确定性 E2E 预测,但规则表未收录该药、无冻结 AMRFinderPlus 基线可对齐。**只能给预测,
不能声称比规则强**——因为压根没有规则基线可比。这是本证据面最大的一块诚实边界。

### E1 artifact({len(e1)} 个)— 有 artifact、未评估、不能预测优劣

仅有 joblib artifact + 确定性加载,**从未做本地 CV**(PA/AB/SE 部分组合无评估数据)。
对这些组合**我们不声称任何预测能力优劣**,它们只是"模型文件存在"。其中包含 S3 本想评但
数据未收录进面的 **salmonella_enterica × ciprofloxacin**(见下)。

### E3_evaluated({len(e3)} 个 practical 未升级)— 做过 CV 但未显著优于规则

S2 abstain-aware 复评后仍停在 practical:做过 ST-CV,融合不劣于规则,但**未达统计显著**,
且 abstain 也压不动(覆盖不足 / ML 无增益 / 规则已零漏判)。诚实说法:**不劣于规则,但不敢说更强**。
典型卡点(来自 S2 remained_practical):覆盖率 ≥0.70 内 covered ME 始终 ≥0.1(压 ME<0.10 须弃权>30%)、
ΔVME=0.0 p=1.0(ML 无增益)、rule_vme 已 0(规则无漏判无提升空间)。

## S3 lineage holdout 跳过的组合(诚实标注,未给 E5)

以下 anchor 虽在 S3 名单内,但未收录进可评估的冻结面 132(或收录但 unevaluated),无冻结基线
对齐,**本次跳过 holdout,不给 E5**:

- **acinetobacter_baumannii × tigecycline**:不在冻结证据面 132,无此行(待 53 数据收录进面后再评)。
- **salmonella_enterica × ciprofloxacin**:在面内但 tier=unevaluated → v1 记 **E1_artifact**,未做 holdout。

另:PA/AB/SA 的 temporal/source holdout(S3.2/S3.3)未做,当前 E5 仅代表"稀有谱系群 lineage 外推"
一种外推,不等于时间/地域外推也稳。
"""
    (_OUT / "downgraded_cases.md").write_text(md, encoding="utf-8")


def main() -> None:
    surface, transition = build()
    lv = Counter(r["evidence_level_v1"] for r in surface)
    tv = Counter(r["tier_v1"] for r in surface)
    dr = Counter(r["direction"] for r in transition)
    print(f"[S6] 最终证据面 {len(surface)} 组合 → {_OUT}")
    print("  E0-E5 分布:", {k: lv[k] for k in ("E0", "E1", "E2", "E3", "E4", "E5")})
    print("  tier_v1  :", dict(sorted(tv.items())))
    print("  迁移方向 :", {k: dr[k] for k in ("upgraded", "same", "downgraded")})


if __name__ == "__main__":
    main()
