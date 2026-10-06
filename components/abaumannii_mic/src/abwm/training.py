"""Direct structure-to-MIC training and validation, independent of cell-state models."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import random
import subprocess
import time
import numpy as np
import pandas as pd
import torch
from .data import dump,mic_split_path
from .models import DirectMICBaseline,censored_nll

def setup(seed,device='auto'):
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    torch.set_num_threads(4)
    torch.backends.cudnn.deterministic=True; torch.backends.cudnn.benchmark=False
    torch.backends.cuda.matmul.allow_tf32=False
    if torch.cuda.is_available(): torch.cuda.manual_seed_all(seed)
    return torch.device('cuda:0' if device=='auto' and torch.cuda.is_available() else ('cpu' if device=='auto' else device))


def tensor(a,device): return torch.as_tensor(a,device=device,dtype=torch.float32)


def provenance(config,seed):
    try: commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True,stderr=subprocess.DEVNULL).strip()
    except subprocess.CalledProcessError: commit='uncommitted'
    return dict(config=config,seed=seed,git_commit=commit,torch_version=str(torch.__version__),
                code_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).resolve().parent.glob('*.py') if not p.name.startswith('._')})


def save_checkpoint(path,model,opt,config,seed,stage,epoch,metric,extra):
    obj=dict(model_state={k:v.detach().cpu() for k,v in model.state_dict().items()},optimizer_state=deepcopy(opt.state_dict()),
             stage=stage,trained=True,epoch=int(epoch),validation_metric=float(metric),**provenance(config,seed),**extra)
    torch.save(obj,path)


def mic_metrics(mu,sigma,lo,hi,kind):
    exact=kind==0; cens=kind>0
    out=dict(n=int(len(mu)),exact=int(exact.sum()),censored=int(cens.sum()))
    for label,ix in [('all',np.ones(len(mu),dtype=bool)),('censored',cens)]:
        if ix.any(): out[label+'_nll']=float(censored_nll(*[torch.as_tensor(a[ix]) for a in [mu,sigma,lo,hi,kind]]))
    if exact.any():
        error=mu[exact]-lo[exact]
        out.update(mae_log2=float(np.abs(error).mean()),rmse_log2=float(np.sqrt(np.mean(error**2))),within_twofold=float(np.mean(np.abs(error)<=1)),
                   normal_90pct_coverage=float(np.mean(np.abs(error)<=1.644854*sigma[exact])))
    if cens.any():
        ok=np.where(kind==1,mu<=hi,np.where(kind==2,mu>=lo,(mu>=lo)&(mu<=hi)))
        out['censored_median_boundary_consistency']=float(ok[cens].mean())
    return out


def mic(config,seed,scheme,data_root,model_root,output_root,resume=True):
    CUR = Path(data_root) / "curated"
    CP = Path(model_root)
    PRED = Path(output_root) / "predictions"
    REPORT = Path(output_root) / "training"
    for folder in (CP,PRED,REPORT): folder.mkdir(parents=True,exist_ok=True)
    name=f'direct_mic_{scheme}_seed{seed}'; path=CP/(name+'.pt')
    if resume and path.exists() and (REPORT/(name+'.json')).exists(): return
    device=setup(seed,config['execution']['device']); start=time.monotonic()
    df=pd.read_csv(CUR/'mic_measurements.csv',dtype={'record_id':str}).fillna('')
    split=pd.read_csv(mic_split_path(scheme,data_root),dtype={'record_id':str}).fillna('')
    assert list(df.record_id)==list(split.record_id)
    tr=np.where(split.split.eq('train'))[0]; va=np.where(split.split.eq('val'))[0]; te=np.where(split.split.eq('test'))[0]
    if min(len(tr),len(va),len(te))<2 or split.loc[tr,'group'].nunique()<3:
        dump(REPORT/(name+'.json'),dict(status='not_evaluable',reason='insufficient independent groups')); return
    x=tensor(np.load(CUR/'mic_fingerprints.npy',allow_pickle=False),device)
    lo=np.array([float(v) if v!='' else -np.inf for v in df.lower_log2]); hi=np.array([float(v) if v!='' else np.inf for v in df.upper_log2])
    kind=df.censor.map({'exact':0,'left':1,'right':2,'interval':3}).to_numpy()
    tl=tensor(lo,device); th=tensor(hi,device); tk=torch.as_tensor(kind,device=device)
    model=DirectMICBaseline(config['model']['hidden_dim']).to(device)
    exact_tr=tr[kind[tr]==0]
    # Start the distribution at a training-only location, never at test thresholds.
    with torch.no_grad():
        model.net[-1].bias[0]=float(np.median(lo[exact_tr])) if len(exact_tr) else 0.
        model.net[-1].bias[1]=2.
    opt=torch.optim.AdamW(model.parameters(),lr=config['training']['learning_rate'],weight_decay=config['training']['weight_decay'])
    tc=config['training']; best=float('inf'); stale=0; logs=[]
    extra=dict(scheme=scheme,model_type='DirectMICBaseline',world_model=False,components_trained=['direct_mic_baseline'],
               split_manifest=str(mic_split_path(scheme,data_root)),split_sha256=hashlib.sha256(mic_split_path(scheme,data_root).read_bytes()).hexdigest(),
               features='Morgan radius2 1024 bits chirality; full recorded structure; no strain/genome features',unit='ug/mL')
    for epoch in range(tc['max_epochs_per_stage']):
        model.train(); losses=[]
        for idx in np.array_split(np.random.permutation(tr),max(1,int(np.ceil(len(tr)/tc['batch_size'])))):
            mu,sigma=model(x[idx]); loss=censored_nll(mu,sigma,tl[idx],th[idx],tk[idx])
            opt.zero_grad(); loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(),10,error_if_nonfinite=True); opt.step(); losses.append(float(loss.detach()))
        model.eval()
        with torch.no_grad(): mu,sigma=model(x[va]); score=float(censored_nll(mu,sigma,tl[va],th[va],tk[va]))
        logs.append(dict(epoch=epoch+1,train_nll=float(np.mean(losses)),val_nll=score))
        if score<best-1e-6:
            best=score; stale=0; save_checkpoint(path,model,opt,config,seed,'direct_mic',epoch+1,best,extra)
        else: stale+=1
        if epoch%10==0: print(name,'epoch',epoch+1,'val',round(score,5),flush=True)
        if stale>=tc['early_stopping_patience']: break
    ck=torch.load(path,map_location=device,weights_only=True); model.load_state_dict(ck['model_state']); model.eval()
    with torch.no_grad(): mu,sigma=model(x); mu=mu.cpu().numpy(); sigma=sigma.cpu().numpy()
    results={}
    for fold,idx in [('val',va),('test',te)]:
        results[fold]=mic_metrics(mu[idx],sigma[idx],lo[idx],hi[idx],kind[idx])
        results[fold]['independent_groups']=int(split.iloc[idx].group.nunique())
        out=df.iloc[idx][['record_id','molecule_id','study','strain','censor','lower_log2','upper_log2','unit']].copy()
        out['group']=split.iloc[idx].group.values; out['pred_log2']=mu[idx]; out['sigma_log2']=sigma[idx]
        out['median_ug_ml']=np.exp2(mu[idx]); out['lower90_ug_ml']=np.exp2(mu[idx]-1.644854*sigma[idx]); out['upper90_ug_ml']=np.exp2(mu[idx]+1.644854*sigma[idx])
        out.to_csv(PRED/(name+'_'+fold+'.csv'),index=False)
        exact=out[out.censor.eq('exact')]
        if exact.group.nunique()>=5:
            rng=np.random.default_rng(seed)
            group_errors=exact.assign(error=(exact.pred_log2-exact.lower_log2.astype(float)).abs()).groupby('group').error.agg(['sum','count'])
            a=group_errors.to_numpy(); values=[]
            for _ in range(500):
                sampled=a[rng.integers(0,len(a),len(a))]; values.append(float(sampled[:,0].sum()/sampled[:,1].sum()))
            results[fold]['mae_group_bootstrap_95ci']=[float(v) for v in np.quantile(values,[.025,.975])]
    dump(REPORT/(name+'.json'),dict(stage='direct_mic',seed=seed,scheme=scheme,metrics=results,epochs=len(logs),best_epoch=ck['epoch'],
         seconds=time.monotonic()-start,parameter_count=sum(p.numel() for p in model.parameters()),log=logs))
