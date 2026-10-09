"""Tests for metabolic tendency case."""
import pytest

from praxis_virtualcell.agents.case_report import validate_case_report
from praxis_virtualcell.agents.route_table import route
from praxis_virtualcell.agents.species_schema import normalize_request
from praxis_virtualcell.predictors.state.metabolic_tendency import (
    _DEFAULT_SUBSET,
    MetabolicDB,
    run_metabolic_tendency_case,
)

if not _DEFAULT_SUBSET.is_file():
    pytest.skip(f"Metabolic subset unavailable({_DEFAULT_SUBSET})", allow_module_level=True)


@pytest.fixture(scope="module")
def db():
    return MetabolicDB()


def test_route_human_flux_to_pathway_scoring():
    d = route(normalize_request({"species": "human", "perturbation_object": "ligand",
                                 "perturbation_targets": ["IFNB1"], "target_output": "flux"}))
    assert d.engine == "pathway_scoring"


def test_metabolic_signal_is_weak(db):

    shifts = {s["panel"]: s for s in [db.pathway_shift(p) for p in db.panels()]}
    assert abs(shifts["glycolysis"]["cohens_d"]) < 0.8


def test_full_case_downgrades_weak_metabolic(db):
    report, dec = run_metabolic_tendency_case({
        "case_id": "S_ifn_metab", "species": "human", "cell_type": "PBMC",
        "perturbation_object": "ligand", "perturbation_targets": ["IFNB1"],
        "target_output": "flux",
    }, db=db)
    validate_case_report(report)
    d = report.to_dict()
    assert dec.engine == "pathway_scoring"

    assert d["reliability_decision"]["disposition"] in ("downgrade", "caution")
    assert d["raw_output"]["max_abs_cohens_d"] < 0.8


def test_pathways_covered(db):
    assert {"glycolysis", "oxphos"} <= set(db.panels())
