"""Tests for untrusted json whitelist."""
import json

import pytest

from praxis_virtualcell.agents_llm.llm_critic import LLMCriticAgent
from praxis_virtualcell.agents_llm.llm_router import LLMRouterAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.config import Mode, RuntimeConfig
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.llm_orchestration import safety_contract as SC
from praxis_virtualcell.llm_orchestration.cross_module_reasoner import LLMCrossModuleReasoner
from praxis_virtualcell.workflows.run_virtualcell_query import (
    ALLOWED_OUTPUTS,
    coerce_str_list,
    parse_query,
    run_query,
    validate_candidate,
)

_BASE = {"species": "human", "perturbation_type": "gene",
         "task_type": "predict_delta_expression"}


def _norm(s: str) -> str:
    """Test helper: norm."""
    return s.strip().upper()





_TARGETS_CASES = [
    ("Scalar target returned for a single gene", "AHR"),
    ("None must not become an invented NONE target", [None, "AHR"]),
    ("Nested list input", [["AHR"]]),
    ("Dictionary element", [{"g": "AHR"}]),
    ("Integer element", [123]),
    ("Boolean element", [True]),
    ("Valid input", ["AHR"]),
    ("Valid input requiring normalization", ["ahr", " TP53 "]),
]


@pytest.mark.parametrize("desc,raw", _TARGETS_CASES, ids=[c[0] for c in _TARGETS_CASES])
def test_provenance_contract_targets_never_invented(desc, raw):
    """Verify provenance contract targets never invented."""
    v = validate_candidate({**_BASE, "perturbation_targets": raw})
    if not v["schema_valid"]:
        assert v["normalized"] is None, "A failed validation must not return normalized data"
        return
    src = {_norm(s) for s in raw if isinstance(s, str)} if isinstance(raw, list) else set()
    got = set(v["normalized"]["perturbation_targets"])
    assert got <= src, f"Invented targets absent from input: {got - src} (source targets={src})"


@pytest.mark.parametrize("raw", [
    [["delta_expression"]],
    [{"a": 1}],
    [None, "delta_expression"],
    [123, "growth"],
], ids=["Nested list", "Dictionary element", "None element", "Integer element"])
def test_requested_outputs_malformed_element_does_not_crash(raw):
    """Verify requested outputs malformed element does not crash."""
    v = validate_candidate({**_BASE, "perturbation_targets": ["AHR"],
                            "requested_outputs": raw})
    kept = v["normalized"]["metadata"]["requested_outputs"]
    assert all(isinstance(o, str) for o in kept)
    assert set(kept) <= ALLOWED_OUTPUTS

    assert [o for o in raw if isinstance(o, str) and o in ALLOWED_OUTPUTS] == kept


def test_targets_all_elements_malformed_fails_closed():
    """Verify targets all elements malformed fails closed."""
    v = validate_candidate({**_BASE, "perturbation_targets": [["AHR"], {"g": "TP53"}, 123]})
    assert v["schema_valid"] is False
    assert v["normalized"] is None
    assert "perturbation_targets" in v["missing_fields"]


def test_targets_partial_malformed_keeps_legit_drops_garbage():
    """Verify targets partial malformed keeps legit drops garbage."""
    v = validate_candidate({**_BASE, "perturbation_targets": [None, "AHR", ["x"], 7]})
    assert v["schema_valid"] is True
    assert v["normalized"]["perturbation_targets"] == ["AHR"]
    assert "NONE" not in v["normalized"]["perturbation_targets"]


def test_targets_no_silent_partial_loss():
    """Verify targets no silent partial loss."""
    v = validate_candidate({**_BASE, "perturbation_targets":
                            ["AHR", None, "TP53", ["x"], "MYC", {"g": 1}]})
    assert v["schema_valid"] is True
    assert v["normalized"]["perturbation_targets"] == ["AHR", "TP53", "MYC"]


def test_assumptions_non_str_elements_dropped():
    """Verify assumptions non str elements dropped."""
    v = validate_candidate({**_BASE, "perturbation_targets": ["AHR"],
                            "assumptions": ["ok", {"evil": 1}, ["nested"], None, 42]})
    assert v["normalized"]["metadata"]["assumptions"] == ["ok"]


def test_legit_input_zero_regression():
    """Verify legit input zero regression."""
    v = validate_candidate({**_BASE, "perturbation_targets": ["ahr", " TP53 "],
                            "requested_outputs": ["delta_expression", "growth"],
                            "assumptions": ["deterministic keyword parse"]})
    assert v["schema_valid"] is True
    assert v["normalized"]["perturbation_targets"] == ["AHR", "TP53"]
    assert v["normalized"]["metadata"]["requested_outputs"] == ["delta_expression", "growth"]
    assert v["normalized"]["metadata"]["assumptions"] == ["deterministic keyword parse"]


def test_offline_deterministic_parse_products_pass_through_unchanged():
    """Verify offline deterministic parse products pass through unchanged."""
    cand = {"species": "human", "perturbation_type": "gene",
            "perturbation_targets": ["AHR", "TP53"],
            "task_type": "predict_delta_expression",
            "assumptions": ["deterministic keyword parse"]}
    a = validate_candidate(dict(cand))
    b = validate_candidate(dict(cand))
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    assert a["normalized"]["perturbation_targets"] == ["AHR", "TP53"]


def test_boundary_try_non_str_key_returns_invalid_not_raises():
    """Verify boundary try non str key returns invalid not raises."""
    v = validate_candidate({1: "a", "species": "human", "perturbation_type": "gene",
                            "perturbation_targets": ["AHR"],
                            "task_type": "predict_delta_expression"})
    assert v["schema_valid"] is False
    assert v["normalized"] is None
    assert "candidate_malformed" in v["errors"]


def test_boundary_try_deep_nested_dict_returns_invalid_not_raises():
    """Verify boundary try deep nested dict returns invalid not raises."""
    d = cur = {}
    for _ in range(20000):
        cur["n"] = {}
        cur = cur["n"]
    v = validate_candidate({**_BASE, "perturbation_targets": ["AHR"], "deep": d})
    assert v["schema_valid"] is False
    assert "candidate_malformed" in v["errors"]


def test_boundary_try_does_not_swallow_legit_results():
    """Verify boundary try does not swallow legit results."""
    v = validate_candidate({"species": "human", "perturbation_type": "gene",
                            "perturbation_targets": ["AHR"],
                            "task_type": "predict_delta_expression"})
    assert v["schema_valid"] is True
    assert v["normalized"]["perturbation_targets"] == ["AHR"]


# ---------------------------------------------------------------------------



# ---------------------------------------------------------------------------

_GARBAGE = ["ok_flag", {"evil": 1}, ["nested"], None, 42]


class _StubClient:
    """Test fixture: _StubClient."""

    def __init__(self, content) -> None:
        self._c = content

    def complete(self, messages, **kw) -> dict:
        return {"content": self._c}


def _critic_notes(content) -> dict:
    bus = MessageBus()
    bus.set_context(trace_id="trace_c4", task_id="task_c4")
    LLMCriticAgent(_StubClient(content)).handle(
        AgentMessage("m1", "Report", "LLMCritic", "llm_review", {"report": {"abstain": False}},
                     "t1"), bus)
    return bus.latest("llm_critic_notes").payload


def _xmod_notes(content) -> dict:
    bus = MessageBus()
    bus.set_context(trace_id="trace_c4", task_id="task_c4")
    LLMCrossModuleReasoner(_StubClient(content)).handle(
        AgentMessage("m1", "ModuleRouter", "LLMCrossModuleReasoner", "llm_cross_module",
                     {"module_plan": {"primary": "gene_hub", "entries": []}}, "t1"), bus)
    return bus.latest("llm_cross_module_notes").payload


def _route_suggestion(content) -> dict:
    bus = MessageBus()
    bus.set_context(trace_id="trace_c4", task_id="task_c4")
    LLMRouterAgent(_StubClient(content)).handle(
        AgentMessage("m1", "ModelApplicability", "LLMRouter", "llm_route",
                     {"applicable": ["MockPredictor"], "rejected_candidates": [],
                      "request": {"species": "human"}}, "t1"), bus)
    return bus.latest("llm_route_suggestion").payload["suggestion"]


def test_sibling1_parse_query_assumptions_drops_non_str_elements(monkeypatch):
    """Verify sibling1 parse query assumptions drops non str elements."""
    import praxis_virtualcell.agents_llm.llm_client as _llmc
    monkeypatch.setattr(_llmc, "make_llm_client", lambda cfg: _StubClient(json.dumps({
        "species": "human", "perturbation_type": "gene", "perturbation_targets": ["AHR"],
        "task_type": "predict_delta_expression",
        "assumptions": ["Single-gene knockdown", {"note": "The LLM returned an object"}, ["nested"], None, 42],
    })))
    out = parse_query("Knock down AHR in human cells", config=RuntimeConfig(mode=Mode.LLM_ASSISTED, llm_enabled=True))
    assert out["assumptions"] == ["Single-gene knockdown"]
    assert all(isinstance(a, str) for a in out["assumptions"])


def test_sibling1_parse_query_assumptions_e2e_api_not_500(monkeypatch):
    """Verify sibling1 parse query assumptions e2e api not 500."""
    monkeypatch.setenv("PRAXIS_VIRTUALCELL_MODE", "offline")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "stub-key-not-a-real-credential")
    from fastapi.testclient import TestClient

    import praxis_virtualcell.agents_llm.llm_client as _llmc
    monkeypatch.setattr(_llmc, "make_llm_client", lambda cfg: _StubClient(json.dumps({
        "species": "human", "perturbation_type": "gene", "perturbation_targets": ["AHR"],
        "task_type": "predict_delta_expression",
        "assumptions": ["Single-gene knockdown", {"note": "The LLM returned an object"}],
    })))
    from praxis_vc_api.main import app
    c = TestClient(app, raise_server_exceptions=False)
    r = c.post("/api/parse", json={"text": "Knock down AHR in human cells", "mode": "llm_assisted"})
    assert r.status_code == 200, f"Expected HTTP 200; actual status is {r.status_code}"
    assert r.json()["assumptions"] == ["Single-gene knockdown"]


def test_parse_query_deep_nested_json_loads_recursionerror_not_500(monkeypatch):
    """Verify parse query deep nested json loads recursionerror not 500."""
    monkeypatch.setenv("PRAXIS_VIRTUALCELL_MODE", "offline")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "stub-key-not-a-real-credential")
    from fastapi.testclient import TestClient

    deep = "[" * 20000 + "]" * 20000
    import praxis_virtualcell.agents_llm.llm_client as _llmc
    monkeypatch.setattr(_llmc, "make_llm_client", lambda cfg: _StubClient(deep))
    from praxis_vc_api.main import app
    c = TestClient(app, raise_server_exceptions=False)
    r = c.post("/api/parse", json={"text": "Knock down AHR in human cells", "mode": "llm_assisted"})
    assert r.status_code == 200, f"Expected recursion failure to be handled; actual status is {r.status_code}"
    d = r.json()



    assert d["llm_metadata"].get("response_hash"), (
        f"The LLM branch was not executed (llm_metadata={d['llm_metadata']});"
        "json.loads must execute for the following assertions to be meaningful")

    assert d["fallback_used"] is True
    assert d["assumptions"] == ["deterministic keyword parse"]


def test_sibling_critic_notes_flags_drop_non_str_elements():
    """Verify sibling critic notes flags drop non str elements."""
    out = _critic_notes(json.dumps({"notes": _GARBAGE, "flags": _GARBAGE}))
    assert out["notes"] == ["ok_flag"]
    assert out["flags"] == ["ok_flag"]


def test_sibling_xmod_notes_flags_drop_non_str_elements():
    """Verify sibling xmod notes flags drop non str elements."""
    out = _xmod_notes(json.dumps({"notes": _GARBAGE, "flags": _GARBAGE}))
    assert out["notes"] == ["ok_flag"]
    assert out["flags"] == ["ok_flag"]


def test_sibling_router_risk_flags_drop_non_str_elements():
    """Verify sibling router risk flags drop non str elements."""
    sug = _route_suggestion(json.dumps({"recommended_agents": ["MockPredictor"],
                                        "excluded_agents": [], "reasoning_summary": "x",
                                        "risk_flags": _GARBAGE}))
    assert sug["risk_flags"] == ["ok_flag"]
    assert sug["recommended_agents"] == ["MockPredictor"]


def test_sibling_safety_contract_risk_flags_drop_non_str_elements():
    """Verify sibling safety contract risk flags drop non str elements."""
    out = SC.sanitize_llm_plan(
        json.dumps({"selected_modules": ["gene_hub"], "risk_flags": _GARBAGE}),
        ["gene_hub"], primary="gene_hub")
    assert out["risk_flags"] == ["ok_flag"]
    assert out["selected_modules"] == ["gene_hub"]


def test_arch_invariant_router_value_whitelist_natively_safe():
    """Verify arch invariant router value whitelist natively safe."""
    sug = _route_suggestion(json.dumps({"recommended_agents": [["nested"], {"d": 1}, None],
                                        "excluded_agents": [], "reasoning_summary": "",
                                        "risk_flags": []}))
    assert sug["recommended_agents"] == []


def test_arch_invariant_sanitize_llm_plan_fail_closed_on_element_malformed():
    """Verify arch invariant sanitize llm plan fail closed on element malformed."""
    out = SC.sanitize_llm_plan(json.dumps({"selected_modules": [["gene_hub"]]}),
                               ["gene_hub"], primary="gene_hub")
    assert out["risk_flags"] == ["llm_parse_failed"]
    assert out["selected_modules"] == ["gene_hub"]


# ---------------------------------------------------------------------------








# ---------------------------------------------------------------------------

_DEEP_JSON = "[" * 20000 + "]" * 20000


def test_backfill_critic_deep_nested_recursionerror_fail_closed():
    """Verify backfill critic deep nested recursionerror fail closed."""
    out = _critic_notes(_DEEP_JSON)
    assert out["flags"] == ["llm_parse_failed"]
    assert out["notes"] == []


def test_backfill_xmod_deep_nested_recursionerror_fail_closed():
    """Verify backfill xmod deep nested recursionerror fail closed."""
    out = _xmod_notes(_DEEP_JSON)
    assert out["flags"] == ["llm_parse_failed"]
    assert out["notes"] == []


def test_backfill_router_deep_nested_recursionerror_fail_closed():
    """Verify backfill router deep nested recursionerror fail closed."""
    sug = _route_suggestion(_DEEP_JSON)
    assert sug["risk_flags"] == ["llm_parse_failed"]
    assert sug["recommended_agents"] == []


def test_backfill_safety_contract_deep_nested_recursionerror_fail_closed():
    """Verify backfill safety contract deep nested recursionerror fail closed."""
    out = SC.sanitize_llm_plan(_DEEP_JSON, ["gene_hub"], primary="gene_hub")
    assert out["risk_flags"] == ["llm_parse_failed"]
    assert out["selected_modules"] == ["gene_hub"]


def test_backfill_input_interpreter_deep_nested_recursionerror_fail_closed():
    """Verify backfill input interpreter deep nested recursionerror fail closed."""
    from praxis_virtualcell.agents_llm.llm_input_interpreter import LLMInputInterpreterAgent
    bus = MessageBus()
    bus.set_context(trace_id="trace_c4", task_id="task_c4")
    LLMInputInterpreterAgent(_StubClient(_DEEP_JSON)).handle(
        AgentMessage("m1", "client", "LLMInputInterpreter", "parse_text", {"text": "x"}, "t1"), bus)
    m = bus.latest("llm_input_failed")
    assert m is not None, "RecursionError was not caught; the failure path was not taken"
    assert "llm_parse_invalid" in m.payload["reason"]


# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------


def test_e2e_offline_deterministic_byte_equivalence():
    """Verify e2e offline deterministic byte equivalence."""
    req = {"request_id": "c4-det", "species": "human", "perturbation_type": "gene",
           "perturbation_targets": ["AHR"], "input_modality": "scRNA",
           "output_modality": "delta_expression", "task_type": "predict_delta_expression"}
    cfg = RuntimeConfig(mode=Mode.OFFLINE)
    outs = [json.dumps(run_query(dict(req), config=cfg)["structured_report"],
                       sort_keys=True, default=str) for _ in range(3)]
    assert len(set(outs)) == 1, "The same OFFLINE request must be byte-identical across three runs"
    out = run_query(dict(req), config=cfg)
    assert out["llm_used_for_prediction"] is False
    assert out["mode"] == "offline"


def test_e2e_provenance_contract_no_invented_gene_reaches_frontend(monkeypatch):
    """Verify e2e provenance contract no invented gene reaches frontend."""
    monkeypatch.setenv("PRAXIS_VIRTUALCELL_MODE", "offline")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "stub-key-not-a-real-credential")
    from fastapi.testclient import TestClient

    import praxis_virtualcell.agents_llm.llm_client as _llmc
    monkeypatch.setattr(_llmc, "make_llm_client", lambda cfg: _StubClient(json.dumps({
        "species": "human", "perturbation_type": "gene",
        "perturbation_targets": [None, "AHR"],
        "task_type": "predict_delta_expression",
    })))
    from praxis_vc_api.main import app
    c = TestClient(app, raise_server_exceptions=False)
    r = c.post("/api/parse", json={"text": "Knock down AHR in human cells", "mode": "llm_assisted"})
    assert r.status_code == 200, f"Actual status: {r.status_code}"
    d = r.json()

    assert d["llm_metadata"].get("response_hash"), (
        f"The LLM branch was not executed (llm_metadata={d['llm_metadata']}):"
        "_deterministic_parse also produces ['AHR']; the assertions must exercise the LLM path")
    assert d["llm_used"] is True
    targets = d["candidate_request"]["perturbation_targets"]
    assert targets == ["AHR"], f"Invented or lost target: {targets}"
    assert "NONE" not in targets, "The invented NONE gene violates input provenance"


# ---------------------------------------------------------------------------


#





# ---------------------------------------------------------------------------


@pytest.mark.parametrize("raw,expected,desc", [
    ("AHR",            [],       "A scalar single-gene response must not be split into characters"),
    ({"g": "AHR"},     [],       "Dictionary targets must not be converted into invented keys"),
    ([{"g": "AHR"}],   [],       "Dictionary elements must not cause join to raise TypeError"),
    ([1, 2],           [],       "Integer elements must not cause join to raise TypeError"),
    (None,             [],       "None"),
    (["AHR", None, 7], ["AHR"],  "Retain valid elements and discard malformed elements"),
    (["AHR", "TP53"],  ["AHR", "TP53"], "Valid input remains unchanged"),
])
def test_coerce_str_list_two_layer_guard(raw, expected, desc):
    """Verify coerce str list two layer guard."""
    assert coerce_str_list(raw) == expected, desc


def test_coerce_str_list_kills_char_split_that_element_guard_alone_cannot():
    """Verify coerce str list kills char split that element guard alone cannot."""
    naive_element_only = [t for t in "AHR" if isinstance(t, str)]
    assert naive_element_only == ["A", "H", "R"]
    assert coerce_str_list("AHR") == []
    assert ",".join(coerce_str_list("AHR")) == ""


def test_parse_query_false_branch_returns_raw_uncoerced_contract(monkeypatch):
    """Verify parse query false branch returns raw uncoerced contract."""
    monkeypatch.setenv("PRAXIS_VIRTUALCELL_MODE", "offline")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "stub-key-not-a-real-credential")
    import praxis_virtualcell.agents_llm.llm_client as _llmc
    monkeypatch.setattr(_llmc, "make_llm_client", lambda cfg: _StubClient(json.dumps({
        "species": "human", "perturbation_type": "gene",
        "perturbation_targets": "AHR",
        "task_type": "predict_delta_expression",
    })))
    out = parse_query("Knock down AHR in human cells",
                      config=RuntimeConfig(mode=Mode.LLM_ASSISTED, llm_enabled=True))

    assert out["llm_metadata"].get("response_hash"), "The LLM branch must execute for this assertion to be meaningful"
    assert out["schema_valid"] is False

    assert out["candidate_request"]["perturbation_targets"] == "AHR"

    assert ",".join(coerce_str_list(out["candidate_request"]["perturbation_targets"])) == ""
