"""simulate_intervention:已知干预须把对应维度朝生物学正确方向推,且为纯函数。"""
import pytest

from praxis_virtualcell.mdr_gnb.predictors.mechanistic.cell_state import (
    BacterialCellState,
)
from praxis_virtualcell.mdr_gnb.predictors.mechanistic.intervention import (
    KNOWN_INTERVENTIONS,
    simulate_intervention,
)


def _base(species="klebsiella_pneumoniae"):
    return BacterialCellState(species=species)


def test_ompk36_knockout_lowers_om_permeability():
    base = _base()
    out = simulate_intervention(base, "ompK36_knockout")
    assert out.outer_membrane_permeability < base.outer_membrane_permeability


def test_ampc_derepression_raises_beta_lactamase():
    base = _base("enterobacter_cloacae")
    out = simulate_intervention(base, "ampC_derepression")
    assert out.beta_lactamase_activity > base.beta_lactamase_activity


def test_mexab_overexpression_raises_efflux():
    base = _base("pseudomonas_aeruginosa")
    out = simulate_intervention(base, "mexAB_overexpression")
    assert out.efflux_activity > base.efflux_activity


def test_oprd_knockout_lowers_om_permeability():
    base = _base("pseudomonas_aeruginosa")
    out = simulate_intervention(base, "oprD_knockout")
    assert out.outer_membrane_permeability < base.outer_membrane_permeability


def test_intervention_is_pure_and_records_delta():
    base = _base()
    snapshot = base.to_vector()
    out = simulate_intervention(base, "ompK36_knockout")
    assert base.to_vector() == snapshot  # 原状态不变(纯函数)
    assert any("ompK36_knockout" in p for p in out.provenance)


def test_unknown_intervention_raises():
    with pytest.raises(KeyError):
        simulate_intervention(_base(), "warp_drive_engage")


def test_registry_covers_required_four():
    for name in (
        "ompK36_knockout",
        "ampC_derepression",
        "mexAB_overexpression",
        "oprD_knockout",
    ):
        assert name in KNOWN_INTERVENTIONS
