"""EC×ceftriaxone abstain-aware 运行点 locked 终判(dev 选 τ,locked 跑一次)。"""
import os, sys, json
from pathlib import Path
os.chdir(Path(__file__).resolve().parents[3]); sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from praxis_virtualcell.mdr_gnb.workflows.build_data_foundation import load_inputs_from_disk, _modelable_ids
from praxis_virtualcell.mdr_gnb.workflows.run_g2r_locked import st_dev_locked_split
from praxis_virtualcell.mdr_gnb.workflows.run_g2r_riskcoverage import (
    dev_operating_point, locked_operating_verdict, COV_FLOOR, ME_CAP)
from praxis_virtualcell.mdr_gnb.predictors.rule_baseline import RuleBaselineSIR

DB="2024-01-frozen"; DATA=Path("data/mdr_gnb"); OUT=Path("reports/antibacterial/mdr_gnb/g2r_locked"); OUT.mkdir(parents=True,exist_ok=True)
sp, dr = "escherichia_coli", "ceftriaxone"
amr, st_map, _ = load_inputs_from_disk(sp, DATA)
mids=set(_modelable_ids(amr,dr)); seen,rows=set(),[]
for r in amr:
    if r.get("antibiotic")==dr:
        g=(r.get("genome_id") or "").strip()
        if g in mids and g not in seen: seen.add(g); rows.append(r)
rule=RuleBaselineSIR(db_version=DB)
ids=[(r.get("genome_id") or "").strip() for r in rows]
dev_ids,lock_ids=st_dev_locked_split(ids,st_map,locked_frac=0.25,seed=0)
id2={(r.get("genome_id") or "").strip():r for r in rows}
dev=[id2[i] for i in dev_ids]; lock=[id2[i] for i in lock_ids]

print(f"EC×ceftriaxone  dev={len(dev)} locked={len(lock)}  (COV_FLOOR={COV_FLOOR} ME_CAP={ME_CAP})")
tau, devtab = dev_operating_point(dev, st_map, rule, dr, seed=0, model="rf")
# 展示 dev 上被考虑的运行点(覆盖率≥地板 且 ME<cap)
print("\ndev 合格运行点(覆盖率 / per-ST VME / ME),预注册选 per-ST VME 最小:")
for r in sorted(devtab, key=lambda r:-r["coverage"])[:12]:
    mark = "  <-- 选中" if abs(r["tau"]-tau)<1e-12 else ""
    print(f"  τ={r['tau']:.3f}  cover={r['coverage']*100:5.1f}%  per-ST VME={r['per_st_vme']:.4f}  ME={r['me']:.4f}{mark}")

verd = locked_operating_verdict(dev, lock, st_map, rule, dr, tau, seed=0, model="rf", n_perm=10000)
print("\n>>> LOCKED 终判(只跑一次,per-ST VME + 置换):")
for k in ["verdict","coverage","n_locked","n_covered","n_st_with_R","per_st_vme_fusion",
          "per_st_vme_rule","delta_vme","p_value","me_fusion","me_rule"]:
    print(f"   {k:18} = {verd[k]}")
json.dump({"tau":tau,"dev_table":devtab,"locked":verd}, open(OUT/"ec_ceftriaxone_operating_verdict.json","w"), indent=1, default=float)
print("\n落盘:", OUT/"ec_ceftriaxone_operating_verdict.json")
