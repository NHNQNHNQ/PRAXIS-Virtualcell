"""嵌套 CV 终判:两锚点,机制特征。运行点选择(内层)与显著性(外层)彻底分离。"""
import os, sys, json
from pathlib import Path
os.chdir(Path(__file__).resolve().parents[3]); sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from praxis_virtualcell.mdr_gnb.workflows.build_data_foundation import load_inputs_from_disk, _modelable_ids
from praxis_virtualcell.mdr_gnb.workflows.run_g2r_nested_cv import nested_cv_verdict
from praxis_virtualcell.mdr_gnb.predictors.rule_baseline import RuleBaselineSIR
from praxis_virtualcell.mdr_gnb.predictors.features import parse_genotypes
from praxis_virtualcell.mdr_gnb.predictors.mechanism_features import augmented_features

DB="2024-01-frozen"; DATA=Path("data/mdr_gnb"); OUT=Path("reports/antibacterial/mdr_gnb/g2r_locked")
def load_rows(sp,dr):
    amr,st_map,_=load_inputs_from_disk(sp,DATA); mids=set(_modelable_ids(amr,dr)); seen,rows=set(),[]
    for r in amr:
        if r.get("antibiotic")==dr:
            g=(r.get("genome_id") or "").strip()
            if g in mids and g not in seen: seen.add(g); rows.append(r)
    return rows,st_map

out={}
for sp,dr in [("klebsiella_pneumoniae","meropenem"),("escherichia_coli","ceftriaxone")]:
    rows,st_map=load_rows(sp,dr); rule=RuleBaselineSIR(db_version=DB)
    print(f"\n===== {sp} × {dr}  嵌套 CV(内层选 t*、外层评,机制特征)=====")
    for fzname,fz in [("基线",parse_genotypes),("机制",augmented_features)]:
        d=nested_cv_verdict(rows,st_map,rule,dr,featurizer=fz,seed=0)
        out[f"{sp}__{dr}__{fzname}"]=d
        print(f"  [{fzname}] {d['verdict']}  ΔVME={d['delta_vme']:+.3f} p={d['p_value']:.4f} "
              f"| 融合VME={d['per_st_vme_fusion']:.3f} 规则VME={d['per_st_vme_rule']:.3f} "
              f"| ME 融合={d['me_fusion']:.3f} 规则={d['me_rule']:.3f} | R-ST={d['n_st_R']} 各折t*={d['tstars_per_fold']}")
json.dump(out,open(OUT/"nested_cv_verdict.json","w"),indent=1,default=float)
print("\n落盘:",OUT/"nested_cv_verdict.json")
