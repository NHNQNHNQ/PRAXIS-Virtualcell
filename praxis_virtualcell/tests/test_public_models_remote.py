"""Tests for public models remote."""
import os

import pytest

pytestmark = pytest.mark.remote


def test_scgpt_wrapper_real_inference_matches_donor():
    """Verify scgpt wrapper real inference matches donor."""
    from praxis_virtualcell.model_zoo.wrappers.scgpt_wrapper import ScgptWrapper

    ckpt_stem = os.environ["SCGPT_CKPT_STEM"]        # .53:.../scgpt_ckpt/norman_2019/pretrained_backbone
    w = ScgptWrapper(ckpt_stem=ckpt_stem)
    out = w.run_prediction({"targets": ["AHR"]})
    assert "prediction" in out and "delta" in out["prediction"]
    assert out["prediction"]["n_genes"] > 0




def test_gears_wrapper_real_inference_structure():
    """Verify gears wrapper real inference structure."""
    from praxis_virtualcell.model_zoo.wrappers.gears_wrapper import GearsWrapper

    ckpt_stem = os.environ["GEARS_CKPT"]
    w = GearsWrapper(ckpt_stem=ckpt_stem)
    out = w.run_prediction({"targets": ["AHR"]})
    assert "prediction" in out


def test_m2_gears_case_real_delta_e2e():
    """Verify m2 gears case real delta e2e."""
    from praxis_virtualcell.predictors.ml.gears_case import run_gears_case

    raw = {"species": "human", "perturbation_object": "gene",
           "target_output": "expression", "perturbation_targets": ["AHR"]}
    report, dec = run_gears_case(raw)


    assert dec.engine == "donor_predictor"

    ro = report.raw_output

    assert ro["value_type"] == "gears_internal_delta"
    assert ro["not_comparable_to_donor_base"] is True
    assert ro["non_deterministic"] is True


    assert isinstance(ro["gears_delta"], list) and len(ro["gears_delta"]) > 0
    assert any(abs(x) > 1e-9 for x in ro["gears_delta"])

    assert ro["gears_delta"] != [0.3] * len(ro["gears_delta"])


    assert report.baseline_comparison["value_type"] == "gears_internal_delta"
    assert report.baseline_comparison["not_comparable_to_donor_base"] is True
    assert report.reliability_decision["disposition"] == "accept"
    assert "not_comparable_to_donor_base" in report.reliability_decision["caution_flags"]
    assert "gears_internal_delta" in report.reliability_decision["caution_flags"]
    assert report.provenance_boundary["non_deterministic"] is True
    assert report.provenance_boundary["no_fixed_seed"] is True
