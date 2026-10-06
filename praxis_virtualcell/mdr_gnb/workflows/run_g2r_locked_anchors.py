"""G2R locked 驱动:两锚点 dev 选择 → locked 终判(只跑一次)+ 失败归因。"""
import os, sys, json
from collections import Counter
from pathlib import Path
os.chdir(Path(__file__).resolve().parents[3]); sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
import numpy as np
from praxis_virtualcell.mdr_gnb.workflows.build_data_foundation import load_inputs_from_disk, _modelable_ids
from praxis_virtualcell.mdr_gnb.workflows.run_g2r_locked import (
    st_dev_locked_split, dev_select, locked_verdict, CANDIDATES, ME_BUDGET)
from praxis_virtualcell.mdr_gnb.predictors.rule_baseline import RuleBaselineSIR
from praxis_virtualcell.mdr_gnb.predictors.features import parse_genotypes

DB = "2024-01-frozen"; DATA = Path("data/mdr_gnb"); OUT = Path("reports/antibacterial/mdr_gnb/g2r_locked"); OUT.mkdir(parents=True, exist_ok=True)

def load_rows(species_dir, drug):
    amr, st_map, _ = load_inputs_from_disk(species_dir, DATA)
    mids = set(_modelable_ids(amr, drug)); seen, rows = set(), []
    for r in amr:
        if r.get("antibiotic") == drug:
            g = (r.get("genome_id") or "").strip()
            if g in mids and g not in seen:
                seen.add(g); rows.append(r)
    return rows, st_map

def vme_gene_atlas(rows, drug, rule):
    """规则法在哪些基因缺口上漏判(真 R 但规则判 S)—— 失败归因的轻量版。"""
    miss = Counter()
    for r in rows:
        y = str(r.get("resistant_phenotype","")).strip().upper()
        if y != "RESISTANT": continue
        if rule.predict_one_genotype(drug, r.get("ncbi_amr_genotypes","")) == "R": continue
        genes = [g for g in parse_genotypes(r.get("ncbi_amr_genotypes","")) ]
        for g in (genes or ["<无基因>"]): miss[g]+=1
    return miss.most_common(8)

results = {}
for sp, dr in [("klebsiella_pneumoniae","meropenem"), ("escherichia_coli","ceftriaxone")]:
    rows, st_map = load_rows(sp, dr)
    rule = RuleBaselineSIR(db_version=DB)
    ids = [(r.get("genome_id") or "").strip() for r in rows]
    dev_ids, lock_ids = st_dev_locked_split(ids, st_map, locked_frac=0.25, seed=0)
    id2 = {(r.get("genome_id") or "").strip(): r for r in rows}
    dev_rows = [id2[i] for i in dev_ids]; lock_rows = [id2[i] for i in lock_ids]
    best, table = dev_select(dev_rows, st_map, rule, dr, seed=0, model="rf")
    verd = locked_verdict(dev_rows, lock_rows, st_map, rule, dr, best, seed=0, model="rf")
    atlas = vme_gene_atlas(rows, dr, rule)
    results[f"{sp}__{dr}"] = {"best": best, "dev_table": table, "locked": verd,
                              "n_dev": len(dev_rows), "n_lock": len(lock_rows), "rule_vme_atlas": atlas}
    print(f"\n===== {sp} × {dr} =====")
    print(f"  dev={len(dev_rows)} locked={len(lock_rows)}  选中候选={best}")
    print("  dev 候选表 (per-ST VME / ME):")
    for c in CANDIDATES:
        t=table[c]; print(f"    {c:16} VME={t['per_st_vme']:.3f}  ME={t['me']:.3f}")
    print(f"  >>> LOCKED 终判: {verd['verdict']}")
    print(f"      per-ST VME: best={verd['per_st_vme_best']:.3f} rule={verd['per_st_vme_rule']:.3f} "
          f"Δ={verd['delta_vme']:+.3f} p={verd['p_value']:.4f}  ME best={verd['me_best']:.3f} rule={verd['me_rule']:.3f}")

json.dump(results, open(OUT/"locked_results.json","w"), indent=1, default=float)
print("\n落盘:", OUT/"locked_results.json")
