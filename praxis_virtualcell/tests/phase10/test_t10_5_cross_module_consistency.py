import hashlib
import json as _json

import pytest

from praxis_virtualcell.core.config import Mode, RuntimeConfig
from praxis_virtualcell.governance.module_consistency import check_module_plan
from praxis_virtualcell.workflows.run_virtualcell_query import run_query

_CFG = RuntimeConfig(mode=Mode.OFFLINE)


_BASELINE_REQS = [

    {"species": "bacteria", "perturbation_type": "gene", "perturbation_targets": ["b0720"],
     "input_modality": "scRNA", "output_modality": "growth", "task_type": "predict_delta_expression"},
    # human gene expression(donor_predictor,Mac mock)
    {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["AHR"],
     "input_modality": "scRNA", "output_modality": "delta_expression",
     "task_type": "predict_delta_expression"},

    {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["SLC2A1"],
     "input_modality": "scRNA", "output_modality": "delta_expression",
     "task_type": "predict_delta_expression"},

    {"species": "bacteria", "perturbation_type": "gene", "perturbation_targets": ["b9999"],
     "input_modality": "scRNA", "output_modality": "growth", "task_type": "predict_delta_expression"},
]


@pytest.mark.parametrize("req", _BASELINE_REQS)
def test_c1_baseline_existing_module_plans_have_no_violations(req):
    """Verify c1 baseline existing module plans have no violations."""
    out = run_query(dict(req), config=_CFG)
    module_plan = out["structured_report"].get("provenance", {}).get("module_plan")
    if module_plan is None:
        pytest.skip("This abstained or unroutable request has no module_plan to check")
    violations = check_module_plan(module_plan)
    assert violations == [], f"The existing module_plan contains violations: {violations}"


def test_c1_consistent_plan_zero_action_byte_equal(monkeypatch):
    """Verify c1 consistent plan zero action byte equal."""
    from praxis_virtualcell.core import runtime as RT

    monkeypatch.setattr(RT, "check_module_plan", lambda plan: [])
    req = {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["AHR"],
           "input_modality": "scRNA", "output_modality": "delta_expression",
           "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    sr = out["structured_report"]
    assert "cross_module_consistency" not in sr.get("provenance", {})
    assert sr["abstain"] is False


def test_c1_consistent_offline_byte_equal_3runs():
    """Verify c1 consistent offline byte equal 3runs."""
    req = {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["AHR"],
           "input_modality": "scRNA", "output_modality": "delta_expression",
           "task_type": "predict_delta_expression"}
    outs = [run_query(dict(req), config=_CFG) for _ in range(3)]
    canon = lambda o: hashlib.sha256(  # noqa: E731
        _json.dumps(o, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()
    assert len({canon(o["structured_report"]) for o in outs}) == 1
    assert len({canon(o["trace"]) for o in outs}) == 1


def test_c1_violation_triggers_gate_abstain(monkeypatch):
    """Verify c1 violation triggers gate abstain."""
    from praxis_virtualcell.core import runtime as RT
    monkeypatch.setattr(RT, "check_module_plan",
                        lambda plan: ["verdict_more_optimistic_than_route[test]: accept < caution"])

    req = {"species": "bacteria", "perturbation_type": "gene", "perturbation_targets": ["b0720"],
           "input_modality": "scRNA", "output_modality": "growth",
           "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    sr = out["structured_report"]
    assert sr["abstain"] is True
    assert sr["prediction"] is None
    assert "cross_module_inconsistency" in sr["abstain_reasons"]
    cmc = sr["provenance"]["cross_module_consistency"]
    assert cmc["gate_abstained"] is True
    assert cmc["reliability_original_abstain"] is False
    assert cmc["violations"]


def test_c1_gate_preserves_reliability_numeric_fields(monkeypatch):
    """Verify c1 gate preserves reliability numeric fields."""
    from praxis_virtualcell.core import runtime as RT
    req = {"species": "bacteria", "perturbation_type": "gene", "perturbation_targets": ["b0720"],
           "input_modality": "scRNA", "output_modality": "growth",
           "task_type": "predict_delta_expression"}

    monkeypatch.setattr(RT, "check_module_plan", lambda plan: [])
    base = run_query(dict(req), config=_CFG)["structured_report"]

    monkeypatch.setattr(RT, "check_module_plan", lambda plan: ["engine_out_of_whitelist[test]"])
    gated = run_query(dict(req), config=_CFG)["structured_report"]

    for f in ("reliability", "model_disagreement", "failed_checks"):
        assert base.get(f) == gated.get(f), f"The gate changed reliability output field {f}"


def test_c1_violation_when_reliability_already_abstain(monkeypatch):
    """Verify c1 violation when reliability already abstain."""
    from praxis_virtualcell.core import runtime as RT
    monkeypatch.setattr(RT, "check_module_plan", lambda plan: ["some_violation"])
    req = {"species": "bacteria", "perturbation_type": "gene", "perturbation_targets": ["b9999"],
           "input_modality": "scRNA", "output_modality": "growth",
           "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    sr = out["structured_report"]
    module_plan = sr.get("provenance", {}).get("module_plan")
    if module_plan is None:
        pytest.skip("This abstained request has no module_plan and is not changed by the gate")
    assert sr["abstain"] is True
    cmc = sr["provenance"]["cross_module_consistency"]
    assert cmc["gate_abstained"] is False
    assert cmc["reliability_original_abstain"] is True



def test_c1_llm_never_used_for_prediction():
    """Verify c1 llm never used for prediction."""
    req = {"species": "bacteria", "perturbation_type": "gene", "perturbation_targets": ["b0720"],
           "input_modality": "scRNA", "output_modality": "growth",
           "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    assert out["llm_used_for_prediction"] is False
