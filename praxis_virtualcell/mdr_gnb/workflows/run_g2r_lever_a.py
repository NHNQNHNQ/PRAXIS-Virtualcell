"""杠杆 A:OOF ST 分组 CV(全 R-ST 进显著性)+ 机制特征 ± 弃权。
每折 held out,operating point(t* 对齐规则 ME、弃权 τ)只从 train 定 → 无 test 泄漏。诚实全功效终判。"""
import json
from pathlib import Path
import numpy as np
from praxis_virtualcell.mdr_gnb.workflows.build_data_foundation import load_inputs_from_disk, _modelable_ids
from praxis_virtualcell.mdr_gnb.workflows.run_g2r_locked import _y, _rule_pred, _me, _threshold_for_me, _st_of
from praxis_virtualcell.mdr_gnb.evaluators.lineage_split import make_lineage_splits
from praxis_virtualcell.mdr_gnb.evaluators.significance import st_level_vme, align_st_vme, paired_permutation_test
from praxis_virtualcell.mdr_gnb.predictors.genotype_to_sir import GenotypeToSIR
from praxis_virtualcell.mdr_gnb.predictors.rule_baseline import RuleBaselineSIR
from praxis_virtualcell.mdr_gnb.predictors.features import parse_genotypes
from praxis_virtualcell.mdr_gnb.predictors.mechanism_features import augmented_features

DB="2024-01-frozen"; DATA=Path("data/mdr_gnb"); OUT=Path("reports/antibacterial/mdr_gnb/g2r_locked"); OUT.mkdir(parents=True,exist_ok=True)

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

def lever_a(rows, st_map, rule, dr, fz, seed=0, abstain_cov=None):
    id2={(r.get("genome_id") or "").strip():r for r in rows}; ids=list(id2)
    specs=make_lineage_splits(ids, st_map, n_splits=5)
    OY,OST,OFU,ORU,OCOV=[],[],[],[],[]
    for s in specs:
        tr=[id2[g] for g in s.train_ids]; te=[id2[g] for g in s.test_ids]
        vocab=fit_vocab(tr,fz); Xtr=build_X(tr,vocab,fz); ytr=_y(tr)
        Xte=build_X(te,vocab,fz); yte=_y(te)
        ml=GenotypeToSIR(random_state=seed,model="rf").fit(Xtr,ytr)
        p_tr,p_te=ml.predict_proba_r(Xtr),ml.predict_proba_r(Xte)
        rtr,rte=_rule_pred(rule,dr,tr),_rule_pred(rule,dr,te)
        t=_threshold_for_me(p_tr,ytr,_me(ytr,rtr))
        base=np.where(rte==1,1,(p_te>=t).astype(int))
        conf=np.where(rte==1,np.inf,np.abs(p_te-t))
        if abstain_cov is not None:
            conf_tr=np.where(rtr==1,np.inf,np.abs(p_tr-t))
            tau=float(np.quantile(conf_tr,1-abstain_cov))     # τ 从 train 定
            covered=conf>=tau
        else:
            covered=np.ones(len(te),bool)
        OY.append(yte); OST.append(_st_of(te,st_map)); OFU.append(base); ORU.append(rte); OCOV.append(covered)
    y=np.concatenate(OY); st=np.concatenate(OST); fu=np.concatenate(OFU); ru=np.concatenate(ORU); cov=np.concatenate(OCOV)
    stc,yc,fc,rc=st[cov],y[cov],fu[cov],ru[cov]
    vf,vr=st_level_vme(stc,yc,fc),st_level_vme(stc,yc,rc)
    keys,mm,rr=align_st_vme(vf,vr)
    perm=paired_permutation_test(mm,rr,keys,n_perm=10000,seed=seed) if len(keys) else {"p_value":float('nan')}
    return {"n_st_R":len(keys),"coverage":float(cov.mean()),
            "per_st_vme_fusion":float(mm.mean()) if len(keys) else float('nan'),
            "per_st_vme_rule":float(rr.mean()) if len(keys) else float('nan'),
            "delta_vme":float(mm.mean()-rr.mean()) if len(keys) else float('nan'),
            "p_value":perm["p_value"],"me_fusion":_me(yc,fc),"me_rule":_me(yc,rc)}

def verdict(d):
    if d["n_st_R"] and d["delta_vme"]<0 and d["p_value"]<0.05 and d["me_fusion"]<0.10: return "STRONG-pass"
    if d["n_st_R"] and d["delta_vme"]<=0.001 and d["me_fusion"]<0.10: return "practical-pass"
    return "FAIL"

if __name__ == "__main__":       # 驱动仅命令行运行,import 时不执行(供 nested_cv 复用 fit_vocab/build_X)
    out={}
    for sp,dr in [("klebsiella_pneumoniae","meropenem"),("escherichia_coli","ceftriaxone")]:
        rows,st_map=load_rows(sp,dr); rule=RuleBaselineSIR(db_version=DB)
        configs={"基线特征/无弃权":(parse_genotypes,None),
                 "机制特征/无弃权":(augmented_features,None),
                 "机制特征/弃权→90%":(augmented_features,0.90)}
        print(f"\n===== {sp} × {dr}  (OOF ST-CV,全 R-ST 进检验)=====")
        print(f"  {'配置':22} {'R-ST':>5} {'cover':>6} {'融合VME':>8} {'规则VME':>8} {'ΔVME':>8} {'p':>8} {'ME':>6} 判定")
        res={}
        for name,(fz,ac) in configs.items():
            d=lever_a(rows,st_map,rule,dr,fz,abstain_cov=ac); res[name]=d
            print(f"  {name:22} {d['n_st_R']:5d} {d['coverage']*100:5.0f}% {d['per_st_vme_fusion']:8.3f} "
                  f"{d['per_st_vme_rule']:8.3f} {d['delta_vme']:+8.3f} {d['p_value']:8.4f} {d['me_fusion']:6.3f} {verdict(d)}")
        out[f"{sp}__{dr}"]=res
    json.dump(out,open(OUT/"lever_a_nested_cv.json","w"),indent=1,default=float)
    print("\n落盘:",OUT/"lever_a_nested_cv.json")
