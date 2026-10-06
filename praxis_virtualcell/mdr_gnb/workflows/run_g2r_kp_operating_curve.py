"""KP meropenem VME-ME 操作曲线:OOF ST-CV(机制特征),扫 ML 阈值 t* 出 Pareto 前沿。
两前沿:rule-first 融合(rule=R OR ml>=t*,VME 有规则兜底)与纯 ML(ml>=t*,可低于规则 ME)。"""
import os, sys, json
from pathlib import Path
os.chdir(Path(__file__).resolve().parents[3]); sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
import numpy as np
from praxis_virtualcell.mdr_gnb.workflows.build_data_foundation import load_inputs_from_disk, _modelable_ids
from praxis_virtualcell.mdr_gnb.workflows.run_g2r_locked import _y, _rule_pred, _st_of
from praxis_virtualcell.mdr_gnb.workflows.run_g2r_lever_a import fit_vocab, build_X
from praxis_virtualcell.mdr_gnb.evaluators.lineage_split import make_lineage_splits
from praxis_virtualcell.mdr_gnb.evaluators.significance import st_level_vme
from praxis_virtualcell.mdr_gnb.predictors.genotype_to_sir import GenotypeToSIR
from praxis_virtualcell.mdr_gnb.predictors.rule_baseline import RuleBaselineSIR
from praxis_virtualcell.mdr_gnb.predictors.mechanism_features import augmented_features

DB="2024-01-frozen"; DATA=Path("data/mdr_gnb"); OUT=Path("reports/antibacterial/mdr_gnb/g2r_locked")
sp,dr="klebsiella_pneumoniae","meropenem"
amr,st_map,_=load_inputs_from_disk(sp,DATA); mids=set(_modelable_ids(amr,dr)); seen,rows=set(),[]
for r in amr:
    if r.get("antibiotic")==dr:
        g=(r.get("genome_id") or "").strip()
        if g in mids and g not in seen: seen.add(g); rows.append(r)
rule=RuleBaselineSIR(db_version=DB)
id2={(r.get("genome_id") or "").strip():r for r in rows}; ids=list(id2)
specs=make_lineage_splits(ids,st_map,n_splits=5)

# OOF:每折训一次机制特征模型,存 p_r / rule / y / st
P,RU,Y,ST=[],[],[],[]
for s in specs:
    tr=[id2[g] for g in s.train_ids]; te=[id2[g] for g in s.test_ids]
    vocab=fit_vocab(tr,augmented_features); Xtr=build_X(tr,vocab,augmented_features); ytr=_y(tr)
    Xte=build_X(te,vocab,augmented_features)
    ml=GenotypeToSIR(random_state=0,model="rf").fit(Xtr,ytr)
    P.append(ml.predict_proba_r(Xte)); RU.append(_rule_pred(rule,dr,te)); Y.append(_y(te)); ST.append(_st_of(te,st_map))
p=np.concatenate(P); ru=np.concatenate(RU); y=np.concatenate(Y); st=np.concatenate(ST)

def metrics(pred):
    per=st_level_vme(st,y,pred); per_vme=float(np.mean(list(per.values()))) if per else float('nan')
    R=(y==1); S=(y==0)
    gv=float((pred[R]==0).mean()) if R.any() else float('nan')   # 全局 VME
    me=float((pred[S]==1).mean()) if S.any() else float('nan')   # 全局 ME
    return per_vme,gv,me

# 规则参照点
rv_per,rv_g,rv_me=metrics(ru)
rows_out={"rule":{"per_st_vme":rv_per,"global_vme":rv_g,"me":rv_me}}
fusion=[]; pureml=[]
for t in np.linspace(0.02,0.98,49):
    ml_pred=(p>=t).astype(int)
    fu_pred=np.where(ru==1,1,ml_pred)
    pv,gv,me=metrics(fu_pred); fusion.append({"t":round(float(t),3),"per_st_vme":round(pv,4),"global_vme":round(gv,4),"me":round(me,4)})
    pv2,gv2,me2=metrics(ml_pred); pureml.append({"t":round(float(t),3),"per_st_vme":round(pv2,4),"global_vme":round(gv2,4),"me":round(me2,4)})
rows_out["fusion_curve"]=fusion; rows_out["pure_ml_curve"]=pureml

print(f"KP × meropenem 操作曲线(规则参照: per-ST VME={rv_per:.3f} global VME={rv_g:.3f} ME={rv_me:.3f})\n")
print("rule-first 融合前沿(选几个 ME 档看对应 VME):")
print(f"  {'t*':>5} {'ME':>6} {'per-ST VME':>11} {'global VME':>11}")
for tgt in [0.10,0.15,0.20,0.25,0.30]:
    best=min(fusion,key=lambda r:abs(r["me"]-tgt))
    print(f"  {best['t']:5.2f} {best['me']:6.3f} {best['per_st_vme']:11.3f} {best['global_vme']:11.3f}  (≈ME {tgt})")
print("\n纯 ML 前沿(可低于规则 ME):")
for tgt in [0.05,0.08,0.10,0.15]:
    best=min(pureml,key=lambda r:abs(r["me"]-tgt))
    print(f"  {best['t']:5.2f} {best['me']:6.3f} {best['per_st_vme']:11.3f} {best['global_vme']:11.3f}  (≈ME {tgt})")
json.dump(rows_out,open(OUT/"kp_meropenem_operating_curve.json","w"),indent=1,default=float)
print("\n落盘:",OUT/"kp_meropenem_operating_curve.json")
