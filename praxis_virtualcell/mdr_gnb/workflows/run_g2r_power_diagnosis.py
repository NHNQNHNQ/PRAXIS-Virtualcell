"""G2R 数据功效诊断:每 species×drug 的耐药 ST 数(=置换检验功效上限)+ 集中度 + 可捞回的 R无ST。

诚实要点:per-ST 置换检验的功效由**不同耐药 ST 数**决定,不是原始菌株数。top-5 ST 高度集中 →
多下同种克隆无益;真正提升功效要**新耐药谱系**。R无ST 是已下载但缺 ST 的耐药株(重跑 MLST 可捞回)。
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

from .build_data_foundation import load_inputs_from_disk, _modelable_ids


def diagnose(species_dir: str, drug: str, data_root: Path) -> dict:
    amr, st_map, _ = load_inputs_from_disk(species_dir, data_root)
    mids = set(_modelable_ids(amr, drug))
    seen, rows = set(), []
    for r in amr:
        if r.get("antibiotic") == drug:
            g = (r.get("genome_id") or "").strip()
            if g in mids and g not in seen:
                seen.add(g); rows.append(r)
    R = [r for r in rows if str(r.get("resistant_phenotype", "")).strip().upper() in ("R", "RESISTANT")]
    Rg = [(r.get("genome_id") or "").strip() for r in R]
    Rst = Counter(st_map.get(g, "unknown") for g in Rg)
    known = {k: v for k, v in Rst.items() if k != "unknown"}
    top5 = sum(sorted(known.values(), reverse=True)[:5])
    return {"species": species_dir, "drug": drug, "n": len(rows), "n_R": len(R),
            "n_R_ST": len(known), "n_R_noST": Rst.get("unknown", 0),
            "top5_ST_frac_of_R": round(top5 / max(1, sum(known.values())), 3)}


if __name__ == "__main__":
    import sys
    data = Path("data/mdr_gnb")
    combos = [("klebsiella_pneumoniae", "meropenem"), ("klebsiella_pneumoniae", "ceftriaxone"),
              ("escherichia_coli", "ceftriaxone"), ("escherichia_coli", "meropenem"),
              ("klebsiella_pneumoniae", "colistin"), ("klebsiella_pneumoniae", "amikacin")]
    for sp, dr in combos:
        try:
            d = diagnose(sp, dr, data)
            print(f"{sp:26} × {dr:14} n={d['n']:5} R={d['n_R']:5} R-ST={d['n_R_ST']:4} "
                  f"R无ST={d['n_R_noST']:4} top5={d['top5_ST_frac_of_R']*100:.0f}%")
        except Exception as e:  # noqa: BLE001
            print(f"{sp} x {dr}: {e}", file=sys.stderr)
