import argparse
import itertools
import json
import os
import sys
import time

sys.path.insert(0, "/home/zkyd/data1/mzy/Virtual cell")
from collections import defaultdict

import torch
from bench.vcbench.loader import _pert_emb_for

from praxis_virtualcell.predictors.ml.donor_bridge import build_predictor_from_ckpt, load_norman
from praxis_virtualcell.predictors.ml.ml_predictor_agent import MLPredictorAgent

CKPT="/home/zkyd/data1/mzy/Virtual cell/runs/full_bench_20260521_060815/checkpoints/norman_2019"
slots={"linear":"linear_additive","latent":"latent_additive","gnn":"gnn_pert"}

def percell_disagreement(D):
    pairs=[]
    for a,b in itertools.combinations(D,2):
        na=a.norm(dim=1); nb=b.norm(dim=1)
        denom=(na*nb).clamp_min(1e-12)
        cos=((a*b).sum(1)/denom).clamp(-1,1)
        pd=(1-cos)/2
        pd=torch.where((na==0)|(nb==0), torch.full_like(pd,0.5), pd)
        pairs.append(pd)
    return torch.stack(pairs).mean(0)

def delta_batch(m, ctrl_batch, pe, kind, targets):
    """尝试批量 control;失败则逐 cell。返回 (n,G) delta。"""
    try:
        mean=m.predict_tensor(ctrl_batch, pe, kind=kind, targets=targets)
        if mean.shape==ctrl_batch.shape:
            return mean-ctrl_batch
    except Exception:
        pass
    outs=[]
    for i in range(ctrl_batch.shape[0]):
        c=ctrl_batch[i]
        outs.append(m.predict_tensor(c, pe, kind=kind, targets=targets).squeeze(0)-c)
    return torch.stack(outs)

def main(max_perts=None, out=None):
    t0=time.time()
    models={k:MLPredictorAgent(build_predictor_from_ckpt(os.path.join(CKPT,pn))[0]) for k,pn in slots.items()}
    ds=load_norman("test",seed=1)
    groups=defaultdict(list)
    for i in range(len(ds)):
        p=ds[i].perturbation
        if p!="control": groups[p].append(i)
    train_perts=set()
    dstr=load_norman("train",seed=0,max_cells=2)
    for i in range(len(dstr)): train_perts.add(dstr[i].perturbation)
    print(f"[{time.time()-t0:.0f}s] loaded; n_perts={len(groups)}", flush=True)
    perts=sorted(groups)
    if max_perts: perts=perts[:max_perts]
    dev="cpu"
    res={}
    for j,pname in enumerate(perts):
        idxs=groups[pname]; targets=tuple(pname.split("+"))
        kind="gene_combo" if len(targets)>1 else "gene_ko"
        pe=_pert_emb_for(pname, ds.pert_table, ds.pert_dim)
        ctrl=torch.stack([ds[i].control for i in idxs]).to(dev)
        D=[delta_batch(models[k], ctrl, pe, kind, targets).to(dev) for k in slots]
        pcd=percell_disagreement(D)
        res[pname]={"disagreement_percell_mean":float(pcd.mean()),
                    "disagreement_percell_sd":float(pcd.std()),
                    "n_cells":len(idxs),"seen_in_train":pname in train_perts}
        if j<3 or j%40==0: print(f"  [{time.time()-t0:.0f}s] {j+1}/{len(perts)} {pname} dis={res[pname]['disagreement_percell_mean']:.4f} n={len(idxs)}", flush=True)
    if out:
        json.dump(res, open(out,"w"))
        print("WROTE", out, flush=True)
    print(f"DONE {len(res)} perts t={time.time()-t0:.0f}s", flush=True)

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--max-perts",type=int,default=None); ap.add_argument("--out",default=None)
    a=ap.parse_args(); main(a.max_perts, a.out)
