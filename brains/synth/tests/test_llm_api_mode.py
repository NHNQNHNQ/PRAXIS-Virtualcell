"""Mock-API tests for the Anthropic API tier.

Verifies that:
  - llm_api.synthesize() runs the tool-use loop correctly (with an injected api_call)
  - read_memory tool fetches files
  - orchestrator's 3-tier fallback prefers embedded → API → stub in that order
  - When neither embedded nor API is available, falls back to stub cleanly
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agents import llm_api, llm_synthesis
from agents.orchestrator import run_pipeline


# ---------- Block helper: simulate an Anthropic SDK content block ----------

def _tool_use_block(name: str, input_data: dict, block_id: str = "tool-1") -> SimpleNamespace:
    return SimpleNamespace(type="tool_use", name=name, input=input_data, id=block_id)


def _text_block(text: str) -> SimpleNamespace:
    return SimpleNamespace(type="text", text=text)


def _response(content_blocks: list) -> SimpleNamespace:
    return SimpleNamespace(content=content_blocks)


# ---------- Tests ----------

def test_synthesize_returns_tool_input_on_terminal_call():
    """When the model immediately calls final_scoping_plan, synthesize returns the input dict."""
    fake_plan = {
        "task_id": "t1",
        "problem": {"synth_task": "fba", "constraints": []},
        "candidate_strategies": [{
            "name": "X", "rationale": "Y",
            "evidence_case_ids": ["synth-001-fba-ecoli-iml1515"],
        }],
        "retrieved_evidence": {
            "cases": [{"case_id": "synth-001-fba-ecoli-iml1515"}],
            "rules": [],
        },
        "confidence": "high",
    }

    def fake_api(messages, system, tools, model, max_tokens):
        return _response([_tool_use_block("final_scoping_plan", fake_plan)])

    out = llm_api.synthesize(
        "scoping", {"task_id": "t1"}, retrieval_bundle={}, api_call=fake_api,
    )
    assert out == fake_plan


def test_synthesize_handles_read_memory_tool_then_finalizes():
    """Model first calls read_memory, then final_scoping_plan in turn 2."""
    fake_plan = {
        "task_id": "t1",
        "problem": {"synth_task": "fba", "constraints": []},
        "candidate_strategies": [{
            "name": "X", "rationale": "from synth-001",
            "evidence_case_ids": ["synth-001-fba-ecoli-iml1515"],
        }],
        "retrieved_evidence": {"cases": [], "rules": []},
        "confidence": "medium",
    }

    call_count = {"n": 0}

    def fake_api(messages, system, tools, model, max_tokens):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _response([_tool_use_block(
                "read_memory",
                {"path": "memory/cases/synth-001-fba-ecoli-iml1515.md"},
                block_id="rm-1",
            )])
        return _response([_tool_use_block("final_scoping_plan", fake_plan, block_id="fin-1")])

    out = llm_api.synthesize(
        "scoping", {"task_id": "t1"}, retrieval_bundle={}, api_call=fake_api,
    )
    assert out == fake_plan
    assert call_count["n"] == 2  # read_memory turn + final turn


def test_synthesize_returns_none_when_no_terminal_call():
    """If the model gives only text and never calls final_*, synthesize returns None."""
    def fake_api(messages, system, tools, model, max_tokens):
        return _response([_text_block("I am thinking but didn't tool-call.")])

    out = llm_api.synthesize(
        "scoping", {"task_id": "t1"}, retrieval_bundle={}, api_call=fake_api, max_turns=2,
    )
    assert out is None


def test_read_memory_rejects_paths_outside_memory():
    """Path traversal protection — must reject anything not under memory/."""
    s = llm_api._read_memory_tool("../../etc/passwd")
    assert s.startswith("ERROR")
    s = llm_api._read_memory_tool("agents/orchestrator.py")
    assert s.startswith("ERROR")
    # A valid memory path works
    s = llm_api._read_memory_tool("memory/cases/synth-001-fba-ecoli-iml1515.md")
    assert "case_id: synth-001-fba-ecoli-iml1515" in s


def test_is_api_available_without_key():
    """Without ANTHROPIC_API_KEY, is_api_available is False."""
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}, clear=False):
        os.environ.pop("ANTHROPIC_API_KEY", None)
        assert not llm_api.is_api_available()


def test_orchestrator_3tier_falls_back_to_stub_when_no_api_no_embedded():
    """Task without embedded synthesis and no API key → stub takes over."""
    # Make sure no API key
    if "ANTHROPIC_API_KEY" in os.environ:
        del os.environ["ANTHROPIC_API_KEY"]
    task = {
        "task_id": "non-canonical-fba-test",
        "problem": {"synth_task": "fba", "host_organism": "E. coli K-12 MG1655", "constraints": []},
    }
    history = run_pipeline(task, mode="llm")
    src = history["scoping_plan"]["_synthesis_source"]
    assert src.startswith("stub"), f"got {src!r}, expected stub fallback"


def test_orchestrator_3tier_uses_embedded_for_canonical_demo():
    """Canonical demo uses embedded synthesis (highest priority tier)."""
    fixture = json.loads((PROJECT_ROOT / "tests" / "fixtures" / "example_lycopene.json").read_text())
    history = run_pipeline(fixture, mode="llm")
    src = history["scoping_plan"]["_synthesis_source"]
    assert "llm_synthesis" in src and "embedded" in src, src


def test_orchestrator_3tier_uses_api_when_available_and_no_embedded(monkeypatch):
    """Non-canonical task, API available → uses API tier (mocked).

    We monkey-patch llm_api.is_api_available to True and inject a fake api_call
    via patching the module-level _call_api function.
    """
    import agents.llm_api as lmapi

    fake_scoping = {
        "task_id": "non-canonical-pathway-test",
        "problem": {"synth_task": "pathway_design", "constraints": []},
        "candidate_strategies": [
            {"name": "API-derived strategy 1", "rationale": "from synth-002",
             "evidence_case_ids": ["synth-002-pathway-artemisinin"]},
            {"name": "API-derived strategy 2", "rationale": "from synth-001",
             "evidence_case_ids": ["synth-001-fba-ecoli-iml1515"]},
            {"name": "API-derived strategy 3", "rationale": "from synth-009",
             "evidence_case_ids": ["synth-009-strain-engineering-ko"]},
        ],
        "retrieved_evidence": {
            "cases": [{"case_id": "synth-002-pathway-artemisinin"}],
            "rules": [],
        },
        "confidence": "medium",
    }

    fake_design = {
        "task_id": "non-canonical-pathway-test",
        "selected_strategy": {"name": "API-derived strategy 1", "rationale": "ok"},
        "design_library": [{
            "design_id": "D1", "kind": "pathway_enzyme_set",
            "spec": {"target_compound": "test", "host": "E. coli", "p450": False},
            "rationale": "API-derived",
            "evidence_case_ids": ["synth-002-pathway-artemisinin"],
            "evidence_rule_ids": ["02-codon-optimize-mandatory"],
        }],
        "excluded_designs": [{
            "kind": "test", "item": "x",
            "reason": "API-derived; rule 02 enforced",
            "rule_id": "02-codon-optimize-mandatory",
        }],
        "computational_pipeline": [
            {"step": 1, "skill": "codon_optimize",
             "args": {"dna_native_fasta_relpath": "tests/fixtures/gfp_native.fasta",
                      "host": "ecoli",
                      "forbidden_sites": {"BsaI": "GGTCTC", "BsmBI": "CGTCTC"},
                      "preserve_rare_codons": True},
             "rationale": "rule 02"},
            {"step": 2, "skill": "fba_simulate",
             "args": {"model_path": "iML1515"}, "multi_objective": True,
             "rationale": "rule 01"},
        ],
        "validation_plan": {"experiments": [{"assay": "HPLC", "expected_metric": "mg/L"}]},
        "confidence": "medium",
    }

    def fake_api_call(messages, system, tools, model, max_tokens):
        # Decide what to return based on which final_* tool is offered
        tool_names = {t["name"] for t in tools}
        if "final_scoping_plan" in tool_names:
            return _response([_tool_use_block("final_scoping_plan", fake_scoping)])
        if "final_design_plan" in tool_names:
            return _response([_tool_use_block("final_design_plan", fake_design)])
        if "final_report_interpretation" in tool_names:
            return _response([_tool_use_block("final_report_interpretation", {
                "why_succeeded": ["API-derived synthesis"],
                "why_failed": ["No failures recorded"],
                "literature_alignment": ["Test alignment"],
                "rules_invoked": ["02-codon-optimize-mandatory"],
            })])
        return _response([_text_block("no terminal tool")])

    # Patch is_api_available to True and _call_api to our fake
    monkeypatch.setattr(lmapi, "is_api_available", lambda: True)
    monkeypatch.setattr(lmapi, "_call_api", fake_api_call)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    task = {
        "task_id": "non-canonical-pathway-test",
        "problem": {
            "synth_task": "pathway_design",
            "host_organism": "E. coli",
            "constraints": [],
        },
    }
    history = run_pipeline(task, mode="llm", skip_reviewer=True)
    src = history["scoping_plan"]["_synthesis_source"]
    assert "llm_api" in src, f"expected API tier, got {src!r}"
    src2 = history["design_plan"]["_synthesis_source"]
    assert "llm_api" in src2, f"expected API tier, got {src2!r}"
