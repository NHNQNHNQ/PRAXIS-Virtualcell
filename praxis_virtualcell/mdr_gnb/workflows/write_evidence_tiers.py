"""证据面 sweep 后处理:重分类 no_baseline + 产 registry 证据分层补丁 + markdown 报告。

tier 语义:
  strong    —— rule-first 融合 per-ST VME 显著低于规则(ΔVME<0,p<0.05,ME 不显著劣于规则)
  practical —— 融合不劣于规则(rule-first 保证 VME≤规则)但未显著优于
  no_baseline —— 冻结 AMRFinderPlus 规则表未收录该药 → 无对照,不可评 G2R
"""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path("reports/antibacterial/mdr_gnb/g2r_locked")


def reclassify(results: list[dict]) -> list[dict]:
    for r in results:
        if r.get("tier") == "error":
            err = str(r.get("error", ""))
            r["tier"] = "no_baseline" if ("未收录" in err or "KeyError" in err) else "error"
    return results


def write_registry_patch(results: list[dict], path: Path) -> None:
    """产 registry 证据分层补丁(每 species×drug:tier + 关键指标)。手写 YAML,无新依赖。"""
    lines = ["# G2R 证据分层(run_g2r_evidence_sweep 产,OOF ST-CV 全功效 + 机制融合)",
             "# tier: strong=显著优于冻结AMRFinderPlus / practical=不劣于规则 / no_baseline=规则表未收录",
             "# 评估: ST 分组, per-ST VME, 版本冻结 AMRFinderPlus 对照, NCBI-only",
             "# 证据等级(模型级 E0-E5): E4=ST-CV 完成且显著优于/匹配 AMRFinderPlus 且有安全收益;",
             "#   E3=ST-CV 完成;E1=artifact 存在+确定性加载(未做本地 CV,如 PA/AB/SE 无评估数据)。",
             "evidence_tiers:"]
    for r in sorted(results, key=lambda x: (x["species"], x.get("drug", ""))):
        lines.append(f"  - species: {r['species']}")
        lines.append(f"    drug: {json.dumps(r.get('drug',''), ensure_ascii=False)}")
        lines.append(f"    tier: {r['tier']}")
        lines.append(f"    evidence_level: {_EVIDENCE_LEVEL.get(r['tier'], 'E3')}")
        if r["tier"] in ("strong", "practical"):
            lines.append(f"    n: {r['n']}")
            lines.append(f"    n_R_ST: {r['n_R_ST']}")
            lines.append(f"    t_star: {r.get('t_star')}   # 机制特征模型的操作点(tuned 用;需匹配重训模型)")
            lines.append(f"    per_st_vme_fusion: {r['per_st_vme_fusion']}")
            lines.append(f"    per_st_vme_rule: {r['per_st_vme_rule']}")
            lines.append(f"    delta_vme: {r['delta_vme']}")
            lines.append(f"    p_value: {r['p_value']}")
            lines.append(f"    me_fusion: {r['me_fusion']}")
            lines.append(f"    me_rule: {r['me_rule']}")
            lines.append(f"    auc_R: {r.get('auc_R')}")
            lines.append(f"    calibration_ece: {r.get('calibration_ece')}")
    # 未评估的有模型物种×药 → E1(artifact+加载,未做 CV)
    evaluated = {(r["species"], r.get("drug", "")) for r in results if r["tier"] != "error"}
    for e in _unevaluated_e1_entries(evaluated):
        lines.append(f"  - species: {e['species']}")
        lines.append(f"    drug: {json.dumps(e['drug'], ensure_ascii=False)}")
        lines.append("    tier: unevaluated")
        lines.append("    evidence_level: E1")
        lines.append("    note: artifact 存在+确定性加载;本地无 phenotype/ST 数据未做 ST-CV(需 53)")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


_EVIDENCE_LEVEL = {"strong": "E4", "practical": "E3", "no_baseline": "E3"}


def _unevaluated_e1_entries(evaluated: set) -> list[dict]:
    """有 joblib 但未被 G2R 评估的物种×药 → E1(artifact+加载,未做 CV)。已评估的跳过。"""
    import re
    out = []
    models_root = Path("data/mdr_gnb/models")
    if not models_root.exists():
        return out
    for mani in sorted(models_root.glob("*/MANIFEST.txt")):
        sp = mani.parent.name
        for line in mani.read_text().splitlines():
            m = re.match(r"OK (.+?): n=", line.strip())
            if m and (sp, m.group(1)) not in evaluated:
                out.append({"species": sp, "drug": m.group(1)})
    return out


def write_report(results: list[dict], path: Path) -> None:
    strong = [r for r in results if r["tier"] == "strong"]
    prac = [r for r in results if r["tier"] == "practical"]
    nob = [r for r in results if r["tier"] == "no_baseline"]
    err = [r for r in results if r["tier"] == "error"]
    L = ["# G2R 证据面 sweep(5 物种 EC/KP/PA/AB/salmonella,2026-07-07)", "",
         "> OOF ST-CV 全功效 + 机制特征 + rule-first 融合 + 预注册运行点(min per-ST VME s.t. ME≤规则ME+0.05)。",
         "> rule-first 保证 per-ST VME≤规则 → 最差 practical(不劣于规则);strong=统计显著优于冻结 AMRFinderPlus。",
         "> 注:sweep 用 OOF(单集选运行点,轻微乐观);锚点已嵌套 CV 确认偏差<0.01。",
         "> EC/KP 本地评估;**PA/AB/salmonella 在 53 评估**(zkyd@10.102.106.53,PRAXIS-article env sklearn 1.9.0,数据+ST 均在 53)。", "",
         f"## 汇总:strong={len(strong)} · practical={len(prac)} · no_baseline={len(nob)} · error={len(err)}", "",
         "## strong 组合(显著优于冻结 AMRFinderPlus 的 VME)", "",
         "| species | drug | n | R-ST | 融合 VME | 规则 VME | ΔVME | p | ME 融合/规则 |",
         "|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(strong, key=lambda x: x["delta_vme"]):
        L.append(f"| {r['species']} | {r['drug']} | {r['n']} | {r['n_R_ST']} | {r['per_st_vme_fusion']} | "
                 f"{r['per_st_vme_rule']} | {r['delta_vme']} | {r['p_value']} | {r['me_fusion']}/{r['me_rule']} |")
    L += ["", "## practical 组合(不劣于规则,未显著优于)", "",
          "| species | drug | R-ST | ΔVME | p |", "|---|---|---|---|---|"]
    for r in sorted(prac, key=lambda x: (x["species"], x.get("drug", ""))):
        L.append(f"| {r['species']} | {r['drug']} | {r['n_R_ST']} | {r['delta_vme']} | {r['p_value']} |")
    if nob:
        L += ["", f"## no_baseline({len(nob)}):冻结规则表未收录,无对照不可评",
              "", ", ".join(f"{r['species'][:2].upper()}×{r['drug']}" for r in nob)]
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    import os
    os.chdir(Path(__file__).resolve().parents[3])
    # 合并 EC+KP(本地) + PA/AB/salmonella(53 评估)两份 sweep
    results = reclassify(json.load(open(OUT / "evidence_sweep.json")))
    new_sp = OUT / "evidence_sweep_new_species.json"
    if new_sp.exists():
        results = results + reclassify(json.load(open(new_sp)))
    write_registry_patch(results, Path("praxis_virtualcell/model_zoo/evidence_tiers.yaml"))
    write_report(results, OUT / "evidence_sweep.md")
    from collections import Counter
    print("tier 分布(5 物种合并):", dict(Counter(r["tier"] for r in results)))
    print("→ evidence_tiers.yaml + evidence_sweep.md")
