"""BacterialCellState 契约测试:8 维、字段名锁定、[0,1] 钳制、向量往返。"""
import pytest

from praxis_virtualcell.mdr_gnb.predictors.mechanistic.cell_state import (
    STATE_DIMENSIONS,
    BacterialCellState,
)


def test_dimensions_are_locked_eight():
    # 契约锁死的 8 个维度,顺序即 to_vector 的顺序
    assert STATE_DIMENSIONS == (
        "cell_wall_stress",
        "outer_membrane_permeability",
        "efflux_activity",
        "beta_lactamase_activity",
        "ribosome_target_sensitivity",
        "dna_gyrase_sensitivity",
        "oxidative_stress_response",
        "biofilm_state",
    )


def test_defaults_are_neutral_midpoint():
    s = BacterialCellState(species="escherichia_coli")
    for name in STATE_DIMENSIONS:
        assert getattr(s, name) == pytest.approx(0.5)


def test_values_are_clamped_to_unit_interval():
    s = BacterialCellState(
        species="klebsiella_pneumoniae",
        outer_membrane_permeability=-3.0,  # 应钳到 0
        efflux_activity=9.0,  # 应钳到 1
    )
    assert s.outer_membrane_permeability == 0.0
    assert s.efflux_activity == 1.0


def test_vector_roundtrip():
    s = BacterialCellState(
        species="pseudomonas_aeruginosa",
        cell_wall_stress=0.1,
        outer_membrane_permeability=0.2,
        efflux_activity=0.9,
        beta_lactamase_activity=0.8,
        ribosome_target_sensitivity=0.3,
        dna_gyrase_sensitivity=0.4,
        oxidative_stress_response=0.6,
        biofilm_state=0.7,
    )
    v = s.to_vector()
    assert len(v) == 8
    s2 = BacterialCellState.from_vector("pseudomonas_aeruginosa", v)
    for name in STATE_DIMENSIONS:
        assert getattr(s2, name) == pytest.approx(getattr(s, name))


def test_every_dimension_has_biology_annotation():
    from praxis_virtualcell.mdr_gnb.predictors.mechanistic.cell_state import (
        DIMENSION_BIOLOGY,
    )

    assert set(DIMENSION_BIOLOGY) == set(STATE_DIMENSIONS)
    for name in STATE_DIMENSIONS:
        assert DIMENSION_BIOLOGY[name].strip()  # 非空生物学说明


def test_delta_reports_only_changed_dims():
    a = BacterialCellState(species="escherichia_coli")
    b = BacterialCellState(species="escherichia_coli", efflux_activity=0.9)
    d = a.delta_to(b)
    assert d["efflux_activity"] == pytest.approx(0.4)
    assert "cell_wall_stress" not in d  # 未变的维度不出现
