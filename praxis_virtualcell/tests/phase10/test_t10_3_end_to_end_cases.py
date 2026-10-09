"""Tests for end to end cases."""

import json

from praxis_virtualcell.core.config import Mode, RuntimeConfig
from praxis_virtualcell.workflows.run_virtualcell_query import run_query

_CFG = RuntimeConfig(mode=Mode.OFFLINE)
_BASE = {"input_modality": "scRNA", "task_type": "predict_delta_expression"}


def _req(species, ptype, targets, out="delta_expression"):
    return {**_BASE, "species": species, "perturbation_type": ptype,
            "perturbation_targets": targets, "output_modality": out}


def _run(req):
    """Test helper: run."""
    out = run_query(dict(req), config=_CFG)
    sr = out["structured_report"]
    mp = out["provenance"].get("module_plan")
    return sr, out["provenance"], mp, out


def _entry(mp, module):
    """Test helper: entry."""
    for e in (mp or {}).get("entries", []):
        if e.get("module") == module:
            return e
    return None




def test_S1_M1_membrane_advisory():
    """Verify S1 M1 membrane advisory."""
    sr, prov, mp, out = _run(_req("human", "gene", ["FASN"]))
    assert sr["abstain"] is True
    assert "learned_abstain_low_reliability" in sr["abstain_reasons"]
    assert sr["prediction"] is None
    assert mp["primary"] == "genetic_hub"
    assert "membrane_system" in mp["secondary"]
    e = _entry(mp, "membrane_system")
    assert e["role"] == "secondary" and e["verdict"] == "downgrade"
    assert "rule_based:membrane_system_gene_set" in e["caution_flags"]
    assert "evidence_limited" in e["caution_flags"]
    assert mp["overall_verdict"] == "downgrade"
    assert out["llm_used_for_prediction"] is False


def test_S2_M2_genetic_hub_mock_accept():
    """Verify S2 M2 genetic hub mock accept."""
    sr, prov, mp, out = _run(_req("human", "gene", ["AHR"]))
    assert sr["abstain"] is False
    assert sr["reliability"] == "high"
    assert sr["models_used"] == ["MockLinear", "MockCPA", "MockGEARS"]
    assert sr["prediction"] == {"delta": [0.3]}
    assert mp["primary"] == "genetic_hub" and mp["secondary"] == []
    e = _entry(mp, "genetic_hub")
    assert e["engine"] == "donor_predictor" and e["verdict"] == "accept"
    assert mp["overall_verdict"] == "accept"
    assert out["llm_used_for_prediction"] is False


def test_S3_M3_mito_secondary_downgrade():
    """Verify S3 M3 mito secondary downgrade."""
    sr, prov, mp, out = _run(_req("human", "gene", ["MYC"], "growth"))
    assert sr["abstain"] is True
    assert "CaseRunner" in sr["models_rejected"]
    assert sr["prediction"] is None
    assert mp["primary"] == "cytoplasmic_metabolism"
    assert "mitochondrial_energy_metabolism" in mp["secondary"]
    e = _entry(mp, "mitochondrial_energy_metabolism")
    assert e["role"] == "secondary" and e["engine"] == "gem_fba" and e["verdict"] == "downgrade"
    assert mp["overall_verdict"] == "downgrade"


def test_S4_M4_cobra_fba_accept():
    """Verify S4 M4 cobra fba accept."""
    sr, prov, mp, out = _run(_req("bacteria", "gene", ["b0720", "b1136"], "growth"))
    assert sr["abstain"] is False
    assert sr["reliability"] == "medium"
    assert sr["models_used"] == ["CaseRunner"]
    assert sr["prediction"] == {"delta": [-1.0, -1.0]}
    assert mp["primary"] == "cytoplasmic_metabolism"
    e = _entry(mp, "cytoplasmic_metabolism")
    assert e["engine"] == "gem_fba" and e["verdict"] == "accept"
    assert mp["overall_verdict"] == "accept"
    assert out["llm_used_for_prediction"] is False


def test_S5_M5_biosynthetic_advisory():
    """Verify S5 M5 biosynthetic advisory."""
    sr, prov, mp, out = _run(_req("human", "gene", ["RPL5"]))
    assert sr["abstain"] is True
    assert sr["prediction"] is None
    assert mp["primary"] == "genetic_hub"
    assert "biosynthetic_network" in mp["secondary"]
    e = _entry(mp, "biosynthetic_network")
    assert e["verdict"] == "downgrade"
    assert "rule_based:biosynthetic_network_gene_set" in e["caution_flags"]
    assert "evidence_limited" in e["caution_flags"]
    assert mp["overall_verdict"] == "downgrade"


def test_S6_M6_spatial_niche_pipeline_limitation():
    """Verify S6 M6 spatial niche pipeline limitation."""
    sr, prov, mp, out = _run(_req("human", "medium", ["stromal_niche"], "state"))
    assert sr["abstain"] is True
    assert mp is None
    assert sr["prediction"] is None
    assert sr["models_used"] == []


def test_S7_M7_state_scoring_accept():
    """Verify S7 M7 state scoring accept."""
    sr, prov, mp, out = _run(_req("human", "ligand", ["IFNB1"], "state"))
    assert sr["abstain"] is False
    assert sr["reliability"] == "medium"
    assert sr["models_used"] == ["CaseRunner"]
    assert sr["prediction"] == {"delta": [2.485]}
    assert mp["primary"] == "stress_processor"
    e = _entry(mp, "stress_processor")
    assert e["engine"] == "state_scoring" and e["verdict"] == "accept"
    assert mp["overall_verdict"] == "accept"


def test_S8_M8_degradation_advisory_mismatch():
    """Verify S8 M8 degradation advisory mismatch."""
    sr, prov, mp, out = _run(_req("bacteria", "gene", ["UBB"], "growth"))
    assert sr["abstain"] is True
    assert mp["primary"] == "cytoplasmic_metabolism"
    assert "degradation_machinery" in mp["secondary"]
    e = _entry(mp, "degradation_machinery")
    assert e["verdict"] == "downgrade"
    assert e["mismatch"] == "caution"
    assert "rule_based:degradation_machinery_gene_set" in e["caution_flags"]
    assert mp["overall_verdict"] == "downgrade"




def test_X1_M4_M3_flux_positive():
    """Verify X1 M4 M3 flux positive."""
    sr, prov, mp, out = _run(_req("human", "ligand", ["IFNB1"], "flux"))
    assert sr["abstain"] is False
    assert sr["models_used"] == ["CaseRunner"]
    assert sr["prediction"] == {"delta": [0.101, 0.281]}
    assert mp["primary"] == "cytoplasmic_metabolism"
    assert mp["secondary"] == ["mitochondrial_energy_metabolism"]
    for m in ("cytoplasmic_metabolism", "mitochondrial_energy_metabolism"):
        e = _entry(mp, m)
        assert e["engine"] == "pathway_scoring" and e["verdict"] == "caution"
    assert mp["overall_verdict"] == "caution"


def test_X2_M4_M3_growth_negative_abstain():
    """Verify X2 M4 M3 growth negative abstain."""
    sr, prov, mp, out = _run(_req("human", "gene_combination", ["MYC", "KRAS"], "growth"))
    assert sr["abstain"] is True
    assert "CaseRunner" in sr["models_rejected"]
    assert sr["prediction"] is None
    assert mp["primary"] == "cytoplasmic_metabolism"
    assert mp["secondary"] == ["mitochondrial_energy_metabolism"]
    for m in ("cytoplasmic_metabolism", "mitochondrial_energy_metabolism"):
        assert _entry(mp, m)["verdict"] == "downgrade"
    assert mp["overall_verdict"] == "downgrade"


def test_X3_quad_four_module_advisory():
    """Verify X3 quad four module advisory."""
    sr, prov, mp, out = _run(_req("human", "gene", ["SLC2A1", "RPL5", "PSMB5"]))
    assert sr["abstain"] is True
    assert sr["prediction"] is None
    assert mp["primary"] == "genetic_hub"
    assert mp["secondary"] == ["membrane_system", "biosynthetic_network", "degradation_machinery"]
    assert len(mp["entries"]) == 4
    for m in ("membrane_system", "biosynthetic_network", "degradation_machinery"):
        e = _entry(mp, m)
        assert e["verdict"] == "downgrade"
        assert f"rule_based:{m}_gene_set" in e["caution_flags"]
        assert "evidence_limited" in e["caution_flags"]
    assert mp["overall_verdict"] == "downgrade"


def test_X4_M4_M8_bacteria_mismatch():
    """Verify X4 M4 M8 bacteria mismatch."""
    sr, prov, mp, out = _run(_req("bacteria", "gene", ["UBB"], "growth"))
    assert sr["abstain"] is True
    assert mp["primary"] == "cytoplasmic_metabolism"
    assert _entry(mp, "cytoplasmic_metabolism")["engine"] == "gem_fba"
    assert "degradation_machinery" in mp["secondary"]
    e = _entry(mp, "degradation_machinery")
    assert e["mismatch"] == "caution"
    assert "rule_based:degradation_machinery_gene_set" in e["caution_flags"]
    assert mp["overall_verdict"] == "downgrade"


def test_X5_negative_transfer_unroutable():
    """Verify X5 negative transfer unroutable."""
    sr, prov, mp, out = _run(_req("bacteria", "gene", ["b0720"]))
    assert sr["abstain"] is True
    assert "all_predictors_rejected" in sr["abstain_reasons"]
    assert sr["models_used"] == []
    assert set(sr["models_rejected"]) == {"MockLinear", "MockCPA", "MockGEARS"}
    assert mp is None
    assert sr["prediction"] is None


def test_X6_C1_gate_noop_and_deterministic():
    """Verify X6 C1 gate noop and deterministic."""
    req = _req("human", "gene", ["MYC"], "growth")
    sr, prov, mp, out = _run(req)
    assert "cross_module_consistency" not in prov
    assert mp["primary"] == "cytoplasmic_metabolism"
    assert mp["secondary"] == ["mitochondrial_energy_metabolism"]
    assert out["llm_used_for_prediction"] is False

    hashes = {json.dumps(_run(req)[0], sort_keys=True, default=str) for _ in range(3)}
    assert len(hashes) == 1


def test_X7_M2_cross_species_ortholog_caution():
    """Verify X7 M2 cross species ortholog caution."""
    sr, prov, mp, out = _run(_req("mouse", "gene", ["GATA1"]))
    assert sr["abstain"] is False
    assert sr["reliability"] == "high"
    assert sr["prediction"] == {"delta": [0.3]}
    assert mp["primary"] == "genetic_hub"
    e = _entry(mp, "genetic_hub")
    assert e["verdict"] == "caution" and "ortholog_required" in e["caution_flags"]
    assert mp["overall_verdict"] == "caution"


def test_X8_route_declaration_diverges_from_engine():
    """Verify X8 route declaration diverges from engine."""
    sr, prov, mp, out = _run(_req("human", "gene", ["SNAI1"], "state"))

    assert mp["primary"] == "stress_processor"
    e = _entry(mp, "stress_processor")
    assert e["engine"] == "state_scoring" and e["verdict"] == "accept"
    assert mp["overall_verdict"] == "accept"

    assert sr["abstain"] is True
    assert "CaseRunner" in sr["models_rejected"]
    assert sr["models_used"] == []
    assert sr["prediction"] is None
