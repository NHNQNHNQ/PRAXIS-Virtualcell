import pytest

from praxis_virtualcell.core.exceptions import InputValidationError
from praxis_virtualcell.core.request import VirtualCellRequest

_OK = {
    "request_id": "req-001",
    "species": "human",
    "perturbation_type": "gene",
    "perturbation_targets": ["AHR"],
    "input_modality": "scRNA",
    "output_modality": "delta_expression",
    "task_type": "predict_delta_expression",
}


def test_from_dict_minimal_ok():
    r = VirtualCellRequest.from_dict(_OK)
    assert r.species == "human"
    assert r.perturbation_targets == ["AHR"]
    assert r.cell_type is None and r.metadata == {}


def test_missing_required_raises():
    bad = dict(_OK)
    del bad["species"]
    with pytest.raises(InputValidationError):
        VirtualCellRequest.from_dict(bad)


def test_targets_must_be_list():
    bad = dict(_OK, perturbation_targets="AHR")
    with pytest.raises(InputValidationError):
        VirtualCellRequest.from_dict(bad)
