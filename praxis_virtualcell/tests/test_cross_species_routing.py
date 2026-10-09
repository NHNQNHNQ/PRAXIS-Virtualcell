"""Tests for cross species routing."""  # noqa: E501
from praxis_virtualcell.workflows.predict_delta_expression import run_request


def _req(species, targets=("AHR",), ptype="gene"):
    return {"request_id": "r", "species": species, "perturbation_type": ptype,
            "perturbation_targets": list(targets), "input_modality": "scRNA",
            "output_modality": "delta_expression", "task_type": "predict_delta_expression"}


def test_human_full_applicable_no_caution():
    r = run_request(_req("human", ["AHR"]))
    assert r["abstain"] is False
    assert "MockCPA" in r["models_used"]
    assert r["caution_flags"] == {}


def test_mouse_applicable_with_ortholog_caution():

    r = run_request(_req("mouse", ["TRP53"]))
    assert r["abstain"] is False
    assert r["models_used"]
    assert r["caution_flags"], "mouse requests must include an orthology caution"
    flat = [c for flags in r["caution_flags"].values() for c in flags]
    assert "ortholog_required" in flat
    assert "human_predictor_transfer_to_mouse_requires_ortholog" in r["provenance"]["rules_hit"]


def test_bacteria_abstain_negative_transfer_rule():

    r = run_request(_req("bacteria", ["AHR"]))
    assert r["abstain"] is True
    assert r["models_used"] == []
    rr = r["provenance"]["rejection_reasons"]
    assert rr and all(v["reason"] == "mammalian_scrna_predictor_not_applicable" for v in rr.values())
    assert "mammalian_scrna_predictor_not_applicable" in r["provenance"]["rules_hit"]


def test_yeast_abstain_negative_transfer_rule():
    r = run_request(_req("yeast", ["AHR"]))
    assert r["abstain"] is True
    assert r["models_used"] == []
    assert "mammalian_scrna_predictor_not_applicable" in r["provenance"]["rules_hit"]


def test_martian_no_phantom_rules_referenced():

    r = run_request(_req("martian", ["AHR"]))
    assert r["abstain"] is True
    assert not any("martian" in path for path in r["provenance"]["rules_referenced"])


def test_four_species_route_differently():

    human = run_request(_req("human", ["AHR"]))
    mouse = run_request(_req("mouse", ["TRP53"]))
    bacteria = run_request(_req("bacteria", ["AHR"]))
    yeast = run_request(_req("yeast", ["AHR"]))
    assert human["abstain"] is False and human["caution_flags"] == {}
    assert mouse["abstain"] is False and mouse["caution_flags"]
    assert bacteria["abstain"] is True and yeast["abstain"] is True




def test_mouse_drug_routes_to_real_embedding_abstains():

    r = run_request(_req("mouse", ["aspirin"], ptype="drug"))
    assert r["abstain"] is True
    assert "CaseRunner" in r["models_rejected"]


def test_mockgears_rejects_drug_as_unsupported_not_vocab():


    from praxis_virtualcell.predictors.mock_gears import MockGEARSAgent
    bc = {"model_applicability": {"MockGEARS": {
              "supported_species": ["mouse"], "supported_modalities": ["scRNA"],
              "supported_tasks": ["predict_delta_expression"],
              "supported_perturbations": ["gene", "gene_combination"],
              "reject_if": ["gene_not_in_graph_vocabulary"]}},
          "object_vocabulary": {"genes": []}, "species": "mouse"}
    req = {"species": "mouse", "perturbation_type": "drug", "perturbation_targets": ["aspirin"],
           "input_modality": "scRNA", "task_type": "predict_delta_expression"}
    score, reject = MockGEARSAgent().assess_applicability(req, bc)
    assert (score, reject) == (0.0, "unsupported_perturbation")


def test_mouse_ortholog_projection_distinguishes_unmapped():

    mapped = run_request(_req("mouse", ["TRP53"]))
    unmapped = run_request(_req("mouse", ["ZZZZ9"]))
    mapped_flat = [c for v in mapped["caution_flags"].values() for c in v]
    unmapped_flat = [c for v in unmapped["caution_flags"].values() for c in v]
    assert not any("unmapped_ortholog" in c for c in mapped_flat)
    assert any("unmapped_ortholog" in c for c in unmapped_flat), "Unmapped genes must include unmapped_ortholog caution"


def test_mouse_ortholog_rules_in_rules_referenced():

    r = run_request(_req("mouse", ["TRP53"]))
    assert any("mouse/ortholog_rules.yaml" in p for p in r["provenance"]["rules_referenced"])


def test_empty_targets_abstain():

    r = run_request(_req("human", []))
    assert r["abstain"] is True
    assert "no_perturbation_specified" in r["abstain_reasons"]


def test_martian_species_not_supported_reason():

    r = run_request(_req("martian", ["AHR"]))
    assert "species_not_supported" in r["abstain_reasons"]
