"""Original DirectMICBaseline architecture and censored MIC loss; no world model."""
import math
import torch
from torch import nn
from torch.nn import functional as F

class DirectMICBaseline(nn.Module):
    def __init__(self,hidden=256):
        super().__init__(); self.net=nn.Sequential(nn.Linear(1024,hidden),nn.GELU(),nn.Dropout(.1),nn.Linear(hidden,2))
    def forward(self,x):
        y=self.net(x); return y[:,0], F.softplus(y[:,1])+.15


def censored_nll(mu,sigma,lower,upper,kind):
    """0 exact, 1 left, 2 right, 3 interval, -1 missing. Thresholds are not exact labels."""
    valid=kind>=0
    if not bool(valid.any()): return None
    mu=mu[valid].double(); sigma=sigma[valid].double()
    lower=lower[valid].double(); upper=upper[valid].double(); kind=kind[valid]
    finite_lower=(kind==0)|(kind==2)|(kind==3)
    finite_upper=(kind==1)|(kind==3)
    if not bool(torch.isfinite(lower[finite_lower]).all() and torch.isfinite(upper[finite_upper]).all()):
        raise ValueError('Censor type requires finite observed boundary')
    loss=torch.zeros_like(mu)
    idx=kind==0
    loss[idx]=.5*((lower[idx]-mu[idx])/sigma[idx]).square()+sigma[idx].log()+.5*math.log(2*math.pi)
    idx=kind==1
    loss[idx]=-torch.special.log_ndtr((upper[idx]-mu[idx])/sigma[idx])
    idx=kind==2
    loss[idx]=-torch.special.log_ndtr((mu[idx]-lower[idx])/sigma[idx])
    idx=kind==3
    if bool(idx.any()):
        a=(lower[idx]-mu[idx])/sigma[idx]; b=(upper[idx]-mu[idx])/sigma[idx]
        hi=torch.where(a>0,torch.special.log_ndtr(-a),torch.special.log_ndtr(b))
        lo=torch.where(a>0,torch.special.log_ndtr(-b),torch.special.log_ndtr(a))
        loss[idx]=-(hi+torch.log(-torch.expm1((lo-hi).clamp(max=-1e-14))))
    return loss.mean()


FORBIDDEN_MIC_INPUTS={'observed_post_treatment_omics','future_omics','mic','target_mic','mic_relative_dose',
                      'absolute_dose_derived_from_target_mic','known_target','target_labels'}

def validate_mic_inputs(payload):
    if FORBIDDEN_MIC_INPUTS.intersection(payload): raise ValueError('Label or future-observation leakage in strict MIC inputs')
    if payload.get('mic_informed'): raise ValueError('MIC-informed conditions cannot enter strict MIC inference')
