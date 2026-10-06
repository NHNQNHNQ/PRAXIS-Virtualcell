"""abstain 七类硬规则:任一触发即 abstain,多原因全报,干净输入不 abstain。"""
from praxis_virtualcell.mdr_gnb.abstain import evaluate_abstain, AbstainContext


def _ctx(**kw):
    base = dict(species="escherichia_coli", species_confident=True,
                genome_quality_ok=True, drug="meropenem",
                drug_in_training_dist=True, mechanism_conflict=False,
                n_mic_samples=200, model_disagreement=0.1,
                combo_gate_status="pass")
    base.update(kw)
    return AbstainContext(**base)


def test_clean_input_no_abstain():
    r = evaluate_abstain(_ctx())
    assert r.abstain is False and r.reasons == []


def test_species_uncertain():
    assert "species_uncertain" in evaluate_abstain(_ctx(species_confident=False)).reasons


def test_bad_genome_quality():
    assert "genome_quality_poor" in evaluate_abstain(_ctx(genome_quality_ok=False)).reasons


def test_drug_out_of_distribution():
    assert "drug_out_of_training_distribution" in \
        evaluate_abstain(_ctx(drug_in_training_dist=False)).reasons


def test_mechanism_conflict():
    assert "mechanism_conflict" in evaluate_abstain(_ctx(mechanism_conflict=True)).reasons


def test_insufficient_mic_samples():
    assert "insufficient_mic_samples" in evaluate_abstain(_ctx(n_mic_samples=5)).reasons


def test_high_disagreement():
    assert "model_disagreement_too_high" in \
        evaluate_abstain(_ctx(model_disagreement=0.8)).reasons


def test_combo_gate_excluded():
    assert "combo_gate_excluded" in evaluate_abstain(_ctx(combo_gate_status="excluded")).reasons


def test_multiple_reasons_all_reported():
    r = evaluate_abstain(_ctx(species_confident=False, n_mic_samples=3))
    assert {"species_uncertain", "insufficient_mic_samples"} <= set(r.reasons)
    assert r.abstain is True
