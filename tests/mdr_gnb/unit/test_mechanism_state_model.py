"""MechanismStateModel:基因型(amr_profile)→ 8 维状态,方向性须生物学正确。"""

from praxis_virtualcell.mdr_gnb.predictors.mechanistic.cell_state import (
    BacterialCellState,
)
from praxis_virtualcell.mdr_gnb.predictors.mechanistic.mechanism_state_model import (
    MechanismStateModel,
)


def _neutral(species="klebsiella_pneumoniae"):
    return BacterialCellState(species=species)


def test_carbapenemase_raises_beta_lactamase_activity():
    m = MechanismStateModel()
    s = m.apply(_neutral(), amr_profile={"genes": ["blaKPC-2"]})
    assert s.beta_lactamase_activity > 0.5


def test_porin_loss_lowers_om_permeability():
    m = MechanismStateModel()
    s = m.apply(_neutral(), amr_profile={"genes": [], "porin_loss": ["ompK36"]})
    assert s.outer_membrane_permeability < 0.5


def test_efflux_overexpression_raises_efflux_activity():
    m = MechanismStateModel()
    s = m.apply(
        _neutral("acinetobacter_baumannii"),
        amr_profile={"efflux_overexpression": ["adeABC"]},
    )
    assert s.efflux_activity > 0.5


def test_gyra_qrdr_lowers_gyrase_sensitivity():
    m = MechanismStateModel()
    s = m.apply(_neutral("escherichia_coli"), amr_profile={"mutations": ["gyrA_S83L"]})
    assert s.dna_gyrase_sensitivity < 0.5


def test_multiple_mechanisms_compose_monotonically():
    m = MechanismStateModel()
    s = m.apply(
        _neutral(),
        amr_profile={"genes": ["blaNDM-1"], "porin_loss": ["ompK36"]},
    )
    # 两个机制叠加:β-内酰胺酶更高、外膜通透更低
    assert s.beta_lactamase_activity > 0.7
    assert s.outer_membrane_permeability < 0.4


def test_unknown_genotype_leaves_state_unchanged():
    m = MechanismStateModel()
    base = _neutral()
    s = m.apply(base, amr_profile={"genes": ["blaZZZ-unknown"]})
    # 未知基因不得胡乱扰动状态(避免假机理)
    assert s.to_vector() == base.to_vector()


def test_provenance_records_which_rule_fired():
    m = MechanismStateModel()
    s = m.apply(_neutral(), amr_profile={"genes": ["blaKPC-2"]})
    assert any("blaKPC" in p or "carbapenemase" in p for p in s.provenance)
