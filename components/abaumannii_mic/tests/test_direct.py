import numpy as np
import pandas as pd
import pytest
import torch

from abwm.data import parse_mic, parent_closed_groups
from abwm.models import censored_nll


def test_censored_measurements_keep_bounds_and_units():
    assert parse_mic(">512", "ug/mL")["upper_log2"] is None
    assert parse_mic("≤0.25", "mg/L")["upper_log2"] == -2
    assert parse_mic("0.001", "mg/mL")["lower_log2"] == 0
    assert parse_mic("1", "ug/mL", upper=4)["censor"] == "interval"
    with pytest.raises(ValueError):
        parse_mic(".06", "ug/mL", "<=", 16)


def test_parent_identity_closure_prevents_indirect_leakage():
    frame = pd.DataFrame(dict(parent_id=["P", "P", "Q", "Q"], compound_group=["A", "B", "B", "C"]))
    groups, _ = parent_closed_groups(frame, "compound_group")
    assert groups.nunique() == 1


def test_censored_loss_has_finite_extreme_tail_gradients():
    mu = torch.tensor([100., -100., 20., 0.], requires_grad=True)
    sigma = torch.ones(4)
    lower = torch.tensor([-np.inf, 0., 0., 0.])
    upper = torch.tensor([0., np.inf, .001, 0.])
    loss = censored_nll(mu, sigma, lower, upper, torch.tensor([1, 2, 3, 0]))
    loss.backward()
    assert torch.isfinite(loss) and torch.isfinite(mu.grad).all()


def test_direct_predictor_rejects_world_and_strain_inputs():
    # Input validation happens before any feature or checkpoint inference.
    from abwm.inference import Predictor
    predictor = object.__new__(Predictor)
    for payload in [{"task": "response"}, {"model": "world"}, {"smiles": "CCO", "strain": "ATCC 17978"}, {"smiles": "CCO", "target_mic": 8}]:
        with pytest.raises(ValueError):
            predictor.predict(payload)
