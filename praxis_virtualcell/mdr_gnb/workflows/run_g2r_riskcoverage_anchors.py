"""G2R v2 驱动:两锚点 locked risk-coverage 曲线。"""
import os, sys, json
from pathlib import Path
os.chdir(Path(__file__).resolve().parents[3]); sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from praxis_virtualcell.mdr_gnb.workflows.build_data_foundation import load_inputs_from_disk, _modelable_ids
from praxis_virtualcell.mdr_gnb.workflows.run_g2r_locked import st_dev_locked_split
from praxis_virtualcell.mdr_gnb.workflows.run_g2r_riskcoverage import anchor_risk_coverage
from praxis_virtualcell.mdr_gnb.predictors.rule_baseline import RuleBaselineSIR

DB="2024-01-frozen"; DATA=Path("data/mdr_gnb"); OUT=Path("reports/antibacterial/mdr_gnb/g2r_locked"); OUT.mkdir(parents=True,exist_ok=True)

def load_rows(sp, dr):
    amr, st_map, _ = load_inputs_from_disk(sp, DATA)
    mids=set(_modelable_ids(amr,dr)); seen,rows=set(),[]
    for r in amr:
        if r.get("antibiotic")==dr:
            g=(r.get("genome_id") or "").strip()
            if g in mids and g not in seen: seen.add(g); rows.append(r)
    return rows, st_map

out={}
for sp,dr in [("klebsiella_pneumoniae","meropenem"),("escherichia_coli","ceftriaxone")]:
    rows,st_map=load_rows(sp,dr); rule=RuleBaselineSIR(db_version=DB)
    ids=[(r.get("genome_id") or "").strip() for r in rows]
    dev_ids,lock_ids=st_dev_locked_split(ids,st_map,locked_frac=0.25,seed=0)
    id2={(r.get("genome_id") or "").strip():r for r in rows}
    dev=[id2[i] for i in dev_ids]; lock=[id2[i] for i in lock_ids]
    res=anchor_risk_coverage(dev,lock,st_map,rule,dr,seed=0,model="rf",n_points=19)
    out[f"{sp}__{dr}"]=res
    print(f"\n===== {sp} × {dr}  (locked n={res['n_locked']}, t*={res['t_star']}) =====")
    print(f"  规则法(满覆盖,locked): VME={res['rule_vme']:.3f}  ME={res['rule_me']:.3f}")
    print(f"  {'cover':>6} {'VME':>7} {'ME':>7}")
    for p in res["curve"]:
        print(f"  {p['coverage']*100:5.0f}% {p['vme']:7.3f} {p['me']:7.3f}")
json.dump(out, open(OUT/"riskcoverage_curves.json","w"), indent=1, default=float)
print("\n落盘:", OUT/"riskcoverage_curves.json")
