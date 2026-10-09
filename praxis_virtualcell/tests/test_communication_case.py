"""Tests for communication case."""
import pytest

from praxis_virtualcell.agents.case_report import validate_case_report
from praxis_virtualcell.agents.route_table import route
from praxis_virtualcell.agents.species_schema import normalize_request
from praxis_virtualcell.predictors.communication.lr_comm import (
    _DEFAULT_SUBSET,
    LRCommDB,
    run_communication_case,
)

if not _DEFAULT_SUBSET.is_file():
    pytest.skip(f"L-R subset unavailable({_DEFAULT_SUBSET})", allow_module_level=True)


@pytest.fixture(scope="module")
def db():
    return LRCommDB()


def test_route_communication_to_comm_engine():
    d = route(normalize_request({"species": "human", "perturbation_object": "ligand",
                                 "perturbation_targets": ["CXCL10"], "target_output": "communication"}))
    assert d.engine == "communication"


def test_cxcl10_induced_in_monocytes(db):
    ctrl = db.expr("CXCL10", "CD14+ Monocytes", "ctrl")
    stim = db.expr("CXCL10", "CD14+ Monocytes", "stim")
    assert stim > ctrl * 5


def test_cxcl10_cxcr3_communication_accept(db):
    report, dec = run_communication_case({
        "case_id": "S_cxcl10_cxcr3", "species": "human", "perturbation_object": "ligand",
        "perturbation_targets": ["CXCL10"], "target_output": "communication",
        "sender_cell_type": "CD14+ Monocytes", "receiver_cell_type": "CD8 T cells",
    }, db=db)
    validate_case_report(report)
    d = report.to_dict()
    assert dec.engine == "communication"
    assert d["reliability_decision"]["disposition"] == "accept"
    assert d["raw_output"]["stim"]["score"] > d["raw_output"]["ctrl"]["score"]


def test_unknown_ligand_abstains(db):
    report, _ = run_communication_case({
        "species": "human", "perturbation_object": "ligand",
        "perturbation_targets": ["NOTALIGAND"], "target_output": "communication",
        "sender_cell_type": "CD14+ Monocytes", "receiver_cell_type": "CD8 T cells",
    }, db=db)
    assert report.to_dict()["reliability_decision"]["disposition"] == "abstain"


def test_lr_pairs_present(db):
    assert db.receptor_of("CXCL10") == "CXCR3"
