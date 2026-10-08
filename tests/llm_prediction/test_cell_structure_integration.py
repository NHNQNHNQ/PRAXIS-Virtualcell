"""Real structure retrieval through default planning/analysis/review and HTTP."""
from copy import deepcopy
import json

from fastapi.testclient import TestClient

from praxis_virtualcell.cell_structure import cell_structure_overview
from praxis_virtualcell.llm_prediction import analyze_with_agents, workflow
from praxis_virtualcell.web.app import create_app
from tests.llm_prediction.test_orchestrator import Client, Profile, assessment, plan, response, review, tool_response


def grounded_structure(profile):
    data = cell_structure_overview(profile.overview())
    index, row = next((index, row) for index, row in enumerate(data["structures"]) if row["kind"] == "compartment")
    return {"compartment_hypotheses": [{"structure_id": row["structure_id"], "compartment": row["compartment"],
             "evidence_scope": row["evidence_scope"], "evidence_type": row["evidence_type"],
             "hypothesis": "物种来源区室信息可以组织分析，但本株结构和分子通透性尚未实测。",
             "evidence_refs": [{"tool_call_id": "context-cell-structure", "pointer": f"/structures/{index}/compartment",
                                "source_id": row["source_id"], "value": row["compartment"]}]}],
            "accessibility_barriers": [], "limitations": ["蛋白定位、当前膜状态和候选分子通透性未知。"]}


async def test_default_agent_uses_real_structure_in_all_roles_and_preserves_single_modality(monkeypatch):
    monkeypatch.setattr(workflow, "_load_organism", lambda *_: Profile())
    selected = ["genome"]
    target = assessment(selected)
    target["structure_analysis"] = grounded_structure(Profile())
    client = Client([response(plan(selected)), tool_response(selected), response(target), response(review())])
    result = await analyze_with_agents("OCC", "test-strain", client=client, modalities=selected,
                                       max_turns=2, conditions={"temperature_c": 37})
    assert result["status"] == "completed"
    assert result["cell_structure"]["structures"]
    bootstrap = next(call for call in result["execution_trace"]["tool_calls"] if call["name"] == "cell_structure_overview")
    assert any(ref["pointer"].endswith("/compartment") for ref in bootstrap["citation_examples"])
    assert result["assessment"]["structure_analysis"]["compartment_hypotheses"][0]["evidence_scope"] == "species_prior"
    assert result["profile"]["selected_modalities"] == ["genome"]
    planning = json.loads(client.requests[0]["messages"][0]["content"])
    assert planning["cell_structure"]["structures"] == result["cell_structure"]["structures"]
    assert planning["candidate"] == {"smiles": "CCO"}
    assert planning["conditions"]["temperature_c"] == 37
    assert "query_cell_structure" in {tool["function"]["name"] for tool in client.requests[1]["tools"]}
    reviewer = json.loads(client.requests[-1]["messages"][0]["content"])
    assert reviewer["assessment"]["structure_analysis"] == result["assessment"]["structure_analysis"]
    assert any(call["tool_call_id"] == "context-cell-structure" for call in reviewer["observed_tool_results"])


async def test_enabled_structure_cannot_be_silently_omitted(monkeypatch):
    monkeypatch.setattr(workflow, "_load_organism", lambda *_: Profile())
    selected = ["transcriptome"]
    client = Client([response(plan(selected)), tool_response(selected), response(assessment(selected))])
    result = await analyze_with_agents("CCO", "test-strain", client=client, modalities=selected, max_turns=2)
    assert result["status"] == "unsupported"
    assert "cell_structure_analysis_required" in result["evidence_validation"]["issues"]
    assert result["assessment"]["mic_estimate"]["value"] is None


async def test_structure_ablation_has_no_structure_bootstrap_or_tools(monkeypatch):
    monkeypatch.setattr(workflow, "_load_organism", lambda *_: Profile())
    selected = ["transcriptome"]
    client = Client([response(plan(selected)), tool_response(selected), response(assessment(selected)), response(review())])
    result = await analyze_with_agents("CCO", "test-strain", client=client, modalities=selected,
                                       max_turns=2, include_cell_structure=False)
    assert result["status"] == "completed"
    assert "cell_structure" not in result
    assert all(call["name"] != "cell_structure_overview" for call in result["execution_trace"]["tool_calls"])
    assert "cell_structure" not in json.loads(client.requests[0]["messages"][0]["content"])
    assert not {"cell_structure_overview", "query_cell_structure"} & {
        tool["function"]["name"] for tool in client.requests[1]["tools"]}


async def test_revision_cannot_upgrade_species_structure_to_strain_measurement(monkeypatch):
    monkeypatch.setattr(workflow, "_load_organism", lambda *_: Profile())
    selected = ["transcriptome"]
    target = assessment(selected)
    target["structure_analysis"] = grounded_structure(Profile())
    invalid = deepcopy(target)
    invalid["structure_analysis"]["compartment_hypotheses"][0].update(evidence_scope="strain_evidence", evidence_type="measured")
    client = Client([response(plan(selected)), tool_response(selected), response(target), response(review("revise")), response(invalid)])
    result = await analyze_with_agents("CCO", "test-strain", client=client, modalities=selected, max_turns=2)
    assert result["status"] == "unsupported"
    assert result["evidence_validation"]["issues"] == ["revision_evidence_failed"]
    assert "structure_scope_does_not_match_tool" in result["agent_trace"]["stages"][-1]["issues"]
    assert len(client.requests) == 5


def test_structure_http_endpoint_requires_exact_profile_and_returns_sourced_scope(monkeypatch, tmp_path):
    from praxis_virtualcell import omics
    monkeypatch.setattr(omics, "load_profile", lambda profile_id, **_: Profile())
    monkeypatch.setattr(omics, "list_profiles", lambda **_: [])
    app = create_app(env_file=tmp_path / "no-credentials", report_root=tmp_path / "reports")
    with TestClient(app) as client:
        result = client.get("/api/profiles/test-strain/cell-structure")
    assert result.status_code == 200
    assert result.json()["profile_id"] == "test-strain"
    assert {row["scope"]["taxonomy_id"] for row in result.json()["structures"]} == {"NCBITaxon:470"}
    assert all(row["evidence_scope"] == "species_prior" for row in result.json()["structures"])
