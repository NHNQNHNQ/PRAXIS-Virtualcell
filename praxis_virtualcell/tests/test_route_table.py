"""Tests for route table."""
from praxis_virtualcell.agents.route_table import ENGINES, route
from praxis_virtualcell.agents.species_schema import normalize_request


def _route(species, obj, out, targets=("AHR",), **extra):
    req = normalize_request({"species": species, "perturbation_object": obj,
                             "perturbation_targets": list(targets), "target_output": out, **extra})
    return route(req)


def test_engines_defined():
    assert {"donor_predictor", "gem_fba", "embedding", "reject"} <= set(ENGINES)


def test_human_gene_expression_accept():
    d = _route("human", "gene", "expression")
    assert d.engine == "donor_predictor"
    assert d.disposition == "accept"
    assert d.caution_flags == []


def test_mouse_gene_expression_ortholog_caution():
    d = _route("mouse", "gene", "expression", targets=("TRP53",))
    assert d.engine == "donor_predictor"
    assert d.disposition in ("caution", "downgrade")
    assert any("ortholog" in c for c in d.caution_flags), "mouse requests must include an orthology caution"


def test_bacteria_growth_routes_to_gem_not_mammalian():

    d = _route("bacteria", "gene", "growth", targets=("b0720",))
    assert d.engine == "gem_fba"
    assert d.engine != "donor_predictor"
    assert d.disposition in ("accept", "caution")


def test_yeast_growth_routes_to_gem():
    d = _route("yeast", "gene", "growth", targets=("YAL001C",))
    assert d.engine == "gem_fba"


def test_bacteria_expression_abstains_no_mammalian_transfer():

    d = _route("bacteria", "gene", "expression", targets=("b0720",))
    assert d.disposition == "abstain"
    assert d.engine != "donor_predictor"
    assert "mammalian" in d.reason or "not_applicable" in d.reason


def test_drug_routes_to_embedding_wired():

    d = _route("human", "drug", "expression", targets=("aspirin",))
    assert d.engine == "embedding"
    assert d.data_gated is False


def test_ligand_expression_still_data_gated():

    d = _route("human", "ligand", "expression", targets=("TNF",))
    assert d.engine == "embedding"
    assert d.data_gated is True


def test_human_communication_routes_to_comm_engine():
    d = _route("human", "ligand", "communication", targets=("CXCL10",))
    assert d.engine == "communication" and d.disposition == "accept"


def test_human_gene_growth_no_mammalian_gem_downgrade():

    d = _route("human", "gene", "growth")
    assert d.disposition in ("downgrade", "abstain")
    assert d.engine in ("gem_fba", "reject")


def test_route_decision_is_serializable():

    d = _route("bacteria", "gene", "growth", targets=("b0720",))
    dd = d.to_dict()
    assert dd["engine"] == "gem_fba"
    assert set(dd) >= {"engine", "disposition", "reason", "caution_flags", "data_gated"}
