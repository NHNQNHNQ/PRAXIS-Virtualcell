"""机制特征实验:基线 vs 机制聚合,同一 ST 分组 locked 评估,per-ST VME + 置换。"""
import os, sys, json
from pathlib import Path
os.chdir(Path(__file__).resolve().parents[3]); sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
import numpy as np
from praxis_virtualcell.mdr_gnb.workflows.build_data_foundation import load_inputs_from_disk, _modelable_ids
from praxis_virtualcell.mdr_gnb.workflows.run_g2r_locked import (
    st_dev_locked_split, _y, _rule_pred, _me, _threshold_for_me, _st_of)
from praxis_virtualcell.mdr_gnb.evaluators.significance import st_level_vme, align_st_vme, paired_permutation_test
from praxis_virtualcell.mdr_gnb.predictors.genotype_to_sir import GenotypeToSIR
from praxis_virtualcell.mdr_gnb.predictors.rule_baseline import RuleBaselineSIR
from praxis_virtualcell.mdr_gnb.predictors.features import parse_genotypes
from praxis_virtualcell.mdr_gnb.predictors.mechanism_features import augmented_features

DB="2024-01-frozen"; DATA=Path("data/mdr_gnb"); OUT=Path("reports/antibacterial/mdr_gnb/g2r"); OUT.mkdir(parents=True,exist_ok=True)

def load_rows(sp,dr):
    amr,st_map,_=load_inputs_from_disk(sp,DATA); mids=set(_modelable_ids(amr,dr)); seen,rows=set(),[]
    for r in amr:
        if r.get("antibiotic")==dr:
            g=(r.get("genome_id") or "").strip()
            if g in mids and g not in seen: seen.add(g); rows.append(r)
    return rows,st_map

def fit_vocab(rows,fz):
    v=set()
    for r in rows: v|=fz(r.get("ncbi_amr_genotypes",""))
    return sorted(v)
def build_X(rows,vocab,fz):
    idx={n:i for i,n in enumerate(vocab)}; X=np.zeros((len(rows),len(vocab)),np.float32)
    for i,r in enumerate(rows):
        for t in fz(r.get("ncbi_amr_genotypes","")):
            if t in idx: X[i,idx[t]]=1.0
    return X

def vme_vs_rule(st,y,pred,rule_p,seed):
    vf,vr=st_level_vme(st,y,pred),st_level_vme(st,y,rule_p)
    keys,mm,rr=align_st_vme(vf,vr)
    if len(keys)<1: return float('nan'),float('nan'),float('nan'),0
    perm=paired_permutation_test(mm,rr,keys,n_perm=10000,seed=seed)
    return float(mm.mean()),float(rr.mean()),perm["p_value"],len(keys)

def eval_fz(dev,lock,st_map,rule,dr,fz,seed=0):
    vocab=fit_vocab(dev,fz); Xd=build_X(dev,vocab,fz); yd=_y(dev)
    Xl=build_X(lock,vocab,fz); yl=_y(lock)
    ml=GenotypeToSIR(random_state=seed,model="rf").fit(Xd,yd)
    pd_,pl=ml.predict_proba_r(Xd),ml.predict_proba_r(Xl)
    rd,rl=_rule_pred(rule,dr,dev),_rule_pred(rule,dr,lock)
    t=_threshold_for_me(pd_,yd,_me(yd,rd))
    ml_lk=(pl>=t).astype(int); fu_lk=np.where(rl==1,1,ml_lk)
    st=_st_of(lock,st_map)
    mlv,rv,mlp,nst=vme_vs_rule(st,yl,ml_lk,rl,seed)
    fuv,_,fup,_=vme_vs_rule(st,yl,fu_lk,rl,seed)
    # 机制 token 是否被模型看重(有多少 mech= 进了词表)
    nmech=sum(1 for f in vocab if f.startswith("mech="))
    return {"n_feat":len(vocab),"n_mech":nmech,"n_st_R":nst,"rule_vme":rv,
            "ml_vme":mlv,"ml_p":mlp,"ml_me":_me(yl,ml_lk),
            "fusion_vme":fuv,"fusion_p":fup,"fusion_me":_me(yl,fu_lk)}

out={}
for sp,dr in [("klebsiella_pneumoniae","meropenem"),("escherichia_coli","ceftriaxone")]:
    rows,st_map=load_rows(sp,dr); rule=RuleBaselineSIR(db_version=DB)
    ids=[(r.get("genome_id") or "").strip() for r in rows]
    dev_ids,lock_ids=st_dev_locked_split(ids,st_map,locked_frac=0.25,seed=0)
    id2={(r.get("genome_id") or "").strip():r for r in rows}
    dev=[id2[i] for i in dev_ids]; lock=[id2[i] for i in lock_ids]
    base=eval_fz(dev,lock,st_map,rule,dr,parse_genotypes)
    aug =eval_fz(dev,lock,st_map,rule,dr,augmented_features)
    out[f"{sp}__{dr}"]={"baseline":base,"augmented":aug}
    print(f"\n===== {sp} × {dr}  (n_ST(R)={base['n_st_R']}, 规则 per-ST VME={base['rule_vme']:.3f}) =====")
    print(f"  {'':10} {'nfeat':>6} {'nmech':>6} {'ML VME':>8} {'ML p':>7} {'FUSE VME':>9} {'FUSE p':>8} {'FUSE ME':>8}")
    for name,res in [("baseline",base),("augmented",aug)]:
        print(f"  {name:10} {res['n_feat']:6d} {res['n_mech']:6d} {res['ml_vme']:8.3f} {res['ml_p']:7.4f} "
              f"{res['fusion_vme']:9.3f} {res['fusion_p']:8.4f} {res['fusion_me']:8.3f}")
json.dump(out,open(OUT/"mechanism_feature_experiment.json","w"),indent=1,default=float)
print("\n落盘:", OUT/"mechanism_feature_experiment.json")
