"""Tests for provenance gates."""
import hashlib
import json
import re

import pytest

from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.config import Mode, RuntimeConfig
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.governance.cell_type_domain import check_cell_type_domain
from praxis_virtualcell.governance.gate_util import apply_governance_gate
from praxis_virtualcell.governance.provenance_completeness import check_report_provenance
from praxis_virtualcell.governance.provenance_hash import check_call_provenance, compute_call_provenance
from praxis_virtualcell.predictors.base import PredictorAgent
from praxis_virtualcell.predictors.ml.agent_adapter import MLBackedPredictorAgent
from praxis_virtualcell.predictors.ml.checkpoint_identity import (
    ML_SLOT_CHECKPOINTS,
    checkpoint_model_version,
)
from praxis_virtualcell.workflows.run_virtualcell_query import run_query

_CFG = RuntimeConfig(mode=Mode.OFFLINE)
_ACCEPT = {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["AHR"],
           "input_modality": "scRNA", "output_modality": "delta_expression",
           "task_type": "predict_delta_expression"}


def test_baseline_accept_report_healthy():
    """Verify baseline accept report healthy."""
    out = run_query(dict(_ACCEPT), config=_CFG)
    sr = out["structured_report"]
    assert sr["abstain"] is False
    prov = sr["provenance"]
    for f in ("rules_referenced", "models_used", "n_messages"):
        assert f in prov, f"provenance is missing required field {f}"


def test_compute_call_provenance_deterministic():
    a = compute_call_provenance("MockLinear", "mock:MockLinear", {"targets": ["AHR"]},
                                {"delta": [0.0]}, ["mock"])
    b = compute_call_provenance("MockLinear", "mock:MockLinear", {"targets": ["AHR"]},
                                {"delta": [0.0]}, ["mock"])
    assert a == b
    assert set(a) == {"model_name", "model_version", "input_hash", "output_hash", "evidence_source"}
    assert a["model_name"] == "MockLinear"
    assert a["model_version"] == "mock:MockLinear"
    assert len(a["input_hash"]) == 64 and len(a["output_hash"]) == 64


def test_compute_call_provenance_input_sensitive():
    a = compute_call_provenance("X", "v1", {"targets": ["AHR"]}, {"delta": [0.1]}, [])
    b = compute_call_provenance("X", "v1", {"targets": ["TP53"]}, {"delta": [0.1]}, [])
    assert a["input_hash"] != b["input_hash"]


def test_check_call_provenance_complete_and_missing():
    ok = compute_call_provenance("X", "v1", {"a": 1}, {"b": 2}, [])
    assert check_call_provenance(ok) == []
    assert "model_version" in check_call_provenance({**ok, "model_version": None})
    assert "model_name" in check_call_provenance({})
    assert check_call_provenance("not_a_dict") == ["model_name", "model_version",
                                                   "input_hash", "output_hash"]


@pytest.mark.parametrize("bad_hash", ["x", "a" * 63, "A" * 64])
def test_check_call_provenance_rejects_malformed_sha256(bad_hash):
    ok = compute_call_provenance("X", "v1", {"a": 1}, {"b": 2}, [])
    assert "input_hash" in check_call_provenance({**ok, "input_hash": bad_hash})


def test_per_call_hashes_in_report_for_used_models():
    out = run_query(dict(_ACCEPT), config=_CFG)
    sr = out["structured_report"]
    pch = sr["provenance"]["per_call_hashes"]
    assert sr["models_used"], "Accepted requests must have models_used"
    for name in sr["models_used"]:
        assert name in pch, f"{name} missing per_call_hashes"
        pc = pch[name]
        assert pc["model_name"] == name
        assert pc["model_version"]
        assert len(pc["input_hash"]) == 64 and len(pc["output_hash"]) == 64


def test_per_call_hash_offline_byte_equal_rerun():
    def _h(o): return hashlib.sha256(
        json.dumps(o, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()
    outs = [run_query(dict(_ACCEPT), config=_CFG)["structured_report"] for _ in range(3)]
    assert len({_h(o) for o in outs}) == 1, (
        "structured_report must remain byte-identical across three runs with per-call hashes"
    )


class _BoomPredictor(PredictorAgent):
    """Test fixture: _BoomPredictor."""
    name = "BoomPredictor"
    model_version = "mock:BoomPredictor"

    def run_prediction(self, model_input: dict) -> dict:
        raise RuntimeError("boom")


def test_failed_branch_per_call_model_version_not_none():
    """Verify failed branch per call model version not none."""
    bus = MessageBus()
    bus.send(AgentMessage("b1", "SpeciesBrain", "X", "brain_retrieved", {}, "t0"))
    bc = {"species": "human", "species_supported": True,
          "model_applicability": {"BoomPredictor": {"supported_species": ["human"],
              "supported_modalities": ["scRNA"], "supported_tasks": ["predict_delta_expression"],
              "supported_perturbations": ["gene"]}}}
    req = {"species": "human", "input_modality": "scRNA",
           "task_type": "predict_delta_expression", "perturbation_type": "gene",
           "perturbation_targets": ["AHR"]}
    _BoomPredictor().handle(
        AgentMessage("m1", "X", "BoomPredictor", "predict",
                     {"request": req, "brain_context": bc}, "t1"), bus)
    out = bus.latest("predictor_result").payload
    assert out["status"] == "failed"
    pc = out["provenance"]["per_call"]
    assert pc["model_version"] == "mock:BoomPredictor", (
        "The failed path must provide a fallback model_version rather than None"
    )
    assert len(pc["input_hash"]) == 64 and len(pc["output_hash"]) == 64


def test_apply_gate_overrides_when_not_already_abstain():
    rep = {"abstain": False, "prediction": {"delta": [0.1]}, "provenance": {}}
    gated = apply_governance_gate(rep, "some_reason", "some_gate", {"detail": 1})
    assert gated is True
    assert rep["abstain"] is True and rep["prediction"] is None
    assert "some_reason" in rep["abstain_reasons"]
    g = rep["provenance"]["some_gate"]
    assert g["gate_abstained"] is True and g["reliability_original_abstain"] is False
    assert g["detail"] == 1


def test_apply_gate_records_but_no_override_when_already_abstain():
    rep = {"abstain": True, "prediction": None, "provenance": {}}
    gated = apply_governance_gate(rep, "r", "g", {})
    assert gated is False
    assert rep["provenance"]["g"]["gate_abstained"] is False
    assert rep["provenance"]["g"]["reliability_original_abstain"] is True


def test_gate_a_healthy_report_no_override():
    """Verify gate a healthy report no override."""
    out = run_query(dict(_ACCEPT), config=_CFG)
    sr = out["structured_report"]
    assert sr["abstain"] is False
    assert "provenance_hash_gate" not in sr["provenance"] or \
        sr["provenance"]["provenance_hash_gate"]["gate_abstained"] is False


def test_gate_a_triggers_on_incomplete_call_provenance(monkeypatch):
    """Verify gate a triggers on incomplete call provenance."""
    from praxis_virtualcell.governance import provenance_hash as PH
    orig = PH.compute_call_provenance
    def broken(name, version, mi, out, ev):
        pc = orig(name, version, mi, out, ev)
        pc["model_version"] = None
        return pc
    monkeypatch.setattr("praxis_virtualcell.predictors.base.compute_call_provenance", broken)
    out = run_query(dict(_ACCEPT), config=_CFG)
    sr = out["structured_report"]
    assert sr["abstain"] is True
    assert "incomplete_call_provenance" in sr["abstain_reasons"]
    g = sr["provenance"]["provenance_hash_gate"]
    assert g["gate_abstained"] is True and g["missing"]


def test_check_report_provenance_complete():
    rep = {"models_used": [], "models_rejected": [], "reliability": "low",
           "provenance": {"n_messages": 3, "rules_referenced": [], "models_used": []}}
    assert check_report_provenance(rep) == []


def test_check_report_provenance_missing_top_and_prov_keys():
    rep = {"models_used": [], "provenance": {"n_messages": 3}}
    miss = check_report_provenance(rep)
    assert "models_rejected" in miss and "reliability" in miss
    assert "provenance.rules_referenced" in miss and "provenance.models_used" in miss


def test_check_report_provenance_provenance_not_dict():
    assert "provenance" in check_report_provenance({"models_used": [], "models_rejected": [],
                                                    "reliability": "low", "provenance": None})


def test_check_report_provenance_provenance_key_absent():
    rep = {"models_used": [], "models_rejected": [], "reliability": "low"}
    assert "provenance" in check_report_provenance(rep)


def test_gate_b_healthy_report_no_trigger():
    """Verify gate b healthy report no trigger."""
    out = run_query(dict(_ACCEPT), config=_CFG)
    sr = out["structured_report"]
    assert "provenance_completeness_gate" not in sr["provenance"] or \
        sr["provenance"]["provenance_completeness_gate"]["gate_abstained"] is False
    assert sr["abstain"] is False


def test_gate_b_triggers_on_missing_provenance_key(monkeypatch):
    """Verify gate b triggers on missing provenance key."""
    monkeypatch.setattr("praxis_virtualcell.core.runtime.check_report_provenance",
                        lambda report: ["provenance.n_messages"])
    out = run_query(dict(_ACCEPT), config=_CFG)
    sr = out["structured_report"]
    assert sr["abstain"] is True
    assert "incomplete_provenance" in sr["abstain_reasons"]
    g = sr["provenance"]["provenance_completeness_gate"]
    assert g["gate_abstained"] is True and g["missing"] == ["provenance.n_messages"]


_APPMAP = {"MockGEARS": {"supported_cell_types": ["K562", "A549"]},
           "MockCPA": {"supported_cell_types": ["K562"]},
           "NoDeclare": {}}


def test_cell_type_domain_all_out_of_domain():
    bc = {"model_applicability": _APPMAP}
    assert check_cell_type_domain({"cell_type": "HeLa"}, bc, ["MockGEARS", "MockCPA"]) == ["MockGEARS", "MockCPA"]


def test_cell_type_domain_in_domain_no_violation():
    bc = {"model_applicability": _APPMAP}
    assert check_cell_type_domain({"cell_type": "K562"}, bc, ["MockGEARS", "MockCPA"]) == []


def test_cell_type_domain_partial_declare_only_declaring_checked():
    """Verify cell type domain partial declare only declaring checked."""
    bc = {"model_applicability": _APPMAP}
    assert check_cell_type_domain({"cell_type": "HeLa"}, bc, ["MockGEARS", "NoDeclare"]) == ["MockGEARS"]


def test_cell_type_domain_partial_out_of_domain_no_trigger():
    """Verify cell type domain partial out of domain no trigger."""
    bc = {"model_applicability": _APPMAP}

    assert check_cell_type_domain({"cell_type": "A549"}, bc, ["MockGEARS", "MockCPA"]) == []


def test_cell_type_domain_skips_when_reliability_abstained():
    """Verify cell type domain skips when reliability abstained."""
    bc = {"model_applicability": _APPMAP}
    assert check_cell_type_domain({"cell_type": "HeLa"}, bc, ["MockGEARS"],
                                  reliability_abstained=True) == []


def test_cell_type_domain_no_cell_type_or_no_used():
    bc = {"model_applicability": _APPMAP}
    assert check_cell_type_domain({}, bc, ["MockGEARS"]) == []
    assert check_cell_type_domain({"cell_type": "HeLa"}, bc, []) == []
    assert check_cell_type_domain({"cell_type": "HeLa"}, {}, ["MockGEARS"]) == []


def test_gate_c_out_of_domain_cell_type_abstains():
    """Verify gate c out of domain cell type abstains."""
    req = dict(_ACCEPT)
    req["cell_type"] = "Jurkat"
    sr = run_query(req, config=_CFG)["structured_report"]
    assert sr["abstain"] is True
    assert "cell_type_out_of_domain" in sr["abstain_reasons"]
    g = sr["provenance"]["cell_type_gate"]
    assert g["gate_abstained"] is True and g["out_of_domain_predictors"]


def test_gate_c_in_domain_cell_type_no_trigger():
    """Verify gate c in domain cell type no trigger."""
    req = dict(_ACCEPT)
    req["cell_type"] = "K562"
    sr = run_query(req, config=_CFG)["structured_report"]
    assert sr["provenance"].get("cell_type_gate", {}).get("gate_abstained", False) is False




def test_c2_gate_preserves_reliability_numeric_fields(monkeypatch):
    """Verify c2 gate preserves reliability numeric fields."""
    base = run_query(dict(_ACCEPT), config=_CFG)["structured_report"]
    base_fields = {k: base.get(k) for k in ("reliability", "failed_checks", "model_disagreement")}
    from praxis_virtualcell.governance import provenance_hash as PH
    orig = PH.compute_call_provenance
    def broken(name, version, mi, out, ev):
        pc = orig(name, version, mi, out, ev)
        pc["input_hash"] = None
        return pc
    monkeypatch.setattr("praxis_virtualcell.predictors.base.compute_call_provenance", broken)
    gated = run_query(dict(_ACCEPT), config=_CFG)["structured_report"]
    assert gated["abstain"] is True
    for k, v in base_fields.items():
        assert gated.get(k) == v, f"{k} was changed by the gate:{v} -> {gated.get(k)}"


def test_multi_gate_reasons_accumulate_and_keys_independent(monkeypatch):
    """Verify multi gate reasons accumulate and keys independent."""
    from praxis_virtualcell.governance import provenance_hash as PH
    orig = PH.compute_call_provenance
    def broken(name, version, mi, out, ev):
        pc = orig(name, version, mi, out, ev)
        pc["output_hash"] = None
        return pc
    monkeypatch.setattr("praxis_virtualcell.predictors.base.compute_call_provenance", broken)
    req = dict(_ACCEPT)
    req["cell_type"] = "Jurkat"
    sr = run_query(req, config=_CFG)["structured_report"]
    assert sr["abstain"] is True
    assert sr["abstain_reasons"] == ["incomplete_call_provenance"]
    assert "provenance_hash_gate" in sr["provenance"]
    g_a = sr["provenance"]["provenance_hash_gate"]
    assert g_a["gate_abstained"] is True and g_a["reliability_original_abstain"] is False

    assert "cell_type_gate" in sr["provenance"]
    g_c = sr["provenance"]["cell_type_gate"]
    assert g_c["gate_abstained"] is False

    assert g_c["reliability_original_abstain"] is True
    assert g_c["out_of_domain_predictors"]

    if "provenance_completeness_gate" in sr["provenance"]:
        assert sr["provenance"]["provenance_completeness_gate"]["gate_abstained"] is False


def test_c2_deterministic_no_llm():
    """Verify c2 deterministic no llm."""
    out = run_query(dict(_ACCEPT), config=_CFG)
    assert out["llm_used_for_prediction"] is False


def test_c2_gate_path_deterministic_rerun(monkeypatch):
    """Verify c2 gate path deterministic rerun."""
    from praxis_virtualcell.governance import provenance_hash as PH
    orig = PH.compute_call_provenance
    def broken(name, version, mi, out, ev):
        pc = orig(name, version, mi, out, ev)
        pc["input_hash"] = None
        return pc
    monkeypatch.setattr("praxis_virtualcell.predictors.base.compute_call_provenance", broken)
    def _h(o):
        return hashlib.sha256(
            json.dumps(o, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()
    outs = [run_query(dict(_ACCEPT), config=_CFG)["structured_report"] for _ in range(3)]
    assert len({_h(o) for o in outs}) == 1


class _FakeDonorModel:
    """Test fixture: _FakeDonorModel."""

    def eval(self):
        return self


class _AdapterSeamMLAgent(MLBackedPredictorAgent):
    """No-torch adapter seam double; this is not evidence of a real donor inference."""

    def prepare_input(self, request: dict, brain_context: dict) -> dict:
        return {"targets": tuple(request.get("perturbation_targets", []))}

    def run_prediction(self, model_input: dict) -> dict:
        return {
            "prediction": {"delta": [0.25], "n_genes": 1},
            "uncertainty": {"std": 0.0},
        }


def _run_ml_adapter_seam(monkeypatch, *, broken_slot: str | None = None) -> tuple[dict, list]:
    from praxis_virtualcell.core.request import VirtualCellRequest
    from praxis_virtualcell.workflows.predict_delta_expression import build_runtime

    monkeypatch.setattr(
        "praxis_virtualcell.agents.model_applicability.gears_available", lambda: False
    )
    runtime = build_runtime(_CFG)
    for index, (slot, (_stem, class_name)) in enumerate(ML_SLOT_CHECKPOINTS.items(), start=1):
        agent = _AdapterSeamMLAgent(
            _FakeDonorModel(),
            control=None,
            pert_table=None,
            pert_dim=0,
            name=slot,
            model_version=f"donor_ml:{class_name}@sha256:{index:064x}",
        )
        if slot == broken_slot:
            agent.model_version = ""
        runtime.register_agent(agent)
    request = VirtualCellRequest.from_dict({**_ACCEPT, "request_id": "adapter-seam"})
    report = runtime.run_workflow(request)
    results = [
        message.payload
        for message in runtime.bus.trace
        if message.message_type == "predictor_result"
    ]
    return report, results


def test_ml_adapter_seam_three_successes_do_not_trigger_gate_a(monkeypatch):
    """Local adapter/runtime seam proof only; real checkpoint inference remains remote pending."""
    report, results = _run_ml_adapter_seam(monkeypatch)

    assert report["abstain"] is False, report
    assert report["models_used"] == list(ML_SLOT_CHECKPOINTS)
    assert report["models_rejected"] == report["models_failed"] == []
    assert [result["agent_name"] for result in results] == list(ML_SLOT_CHECKPOINTS)
    assert all(result["status"] == "success" for result in results)
    assert "provenance_hash_gate" not in report["provenance"]


def test_ml_adapter_seam_missing_version_triggers_gate_a(monkeypatch):
    """The seam still fails closed when one accepted ML adapter loses its version."""
    report, _results = _run_ml_adapter_seam(monkeypatch, broken_slot="MockLinear")

    assert report["abstain"] is True
    assert "incomplete_call_provenance" in report["abstain_reasons"]
    assert report["provenance"]["provenance_hash_gate"]["missing"] == {
        "MockLinear": ["model_version"]
    }


def test_ml_backed_predictor_declares_model_version():
    """Verify ml backed predictor declares model version."""
    agent = MLBackedPredictorAgent(_FakeDonorModel(), control=None, pert_table=None, pert_dim=0)
    assert agent.model_version
    assert agent.model_version.startswith("donor_ml")
    assert MLBackedPredictorAgent.model_version == "donor_ml"


def test_ml_backed_predictor_can_bind_version_to_checkpoint_content(tmp_path):
    """Verify ml backed predictor can bind version to checkpoint content."""
    stem = tmp_path / "linear_additive"
    stem.with_suffix(".json").write_text(
        '{"class_name":"LinearAdditivePredictor","kwargs":{}}', encoding="utf-8"
    )
    stem.with_suffix(".pt").write_bytes(b"first checkpoint")
    first = checkpoint_model_version(stem)

    assert re.fullmatch(r"donor_ml:LinearAdditivePredictor@sha256:[0-9a-f]{64}", first)
    agent = MLBackedPredictorAgent(
        _FakeDonorModel(), control=None, pert_table=None, pert_dim=0, model_version=first
    )
    assert agent.model_version == first

    stem.with_suffix(".json").write_text(
        '{"class_name":"LinearAdditivePredictor","kwargs":{"changed":true}}',
        encoding="utf-8",
    )
    assert checkpoint_model_version(stem) != first

    stem.with_suffix(".json").write_text(
        '{"class_name":"LinearAdditivePredictor","kwargs":{}}', encoding="utf-8"
    )
    stem.with_suffix(".pt").write_bytes(b"second checkpoint")
    assert checkpoint_model_version(stem) != first

    moved = tmp_path / "elsewhere" / stem.name
    moved.parent.mkdir()
    moved.with_suffix(".json").write_bytes(stem.with_suffix(".json").read_bytes())
    moved.with_suffix(".pt").write_bytes(stem.with_suffix(".pt").read_bytes())
    assert checkpoint_model_version(moved) == checkpoint_model_version(stem)


def test_ml_backed_predictor_rejects_empty_explicit_model_version():
    with pytest.raises(ValueError, match="model_version"):
        MLBackedPredictorAgent(
            _FakeDonorModel(), control=None, pert_table=None, pert_dim=0, model_version=""
        )


def test_checkpoint_identity_rejects_wrong_slot_class(tmp_path):
    stem = tmp_path / "linear_additive"
    stem.with_suffix(".json").write_text(
        '{"class_name":"LatentAdditivePredictor","kwargs":{}}', encoding="utf-8"
    )
    stem.with_suffix(".pt").write_bytes(b"checkpoint")
    with pytest.raises(ValueError, match="class mismatch"):
        checkpoint_model_version(stem, expected_class="LinearAdditivePredictor")
