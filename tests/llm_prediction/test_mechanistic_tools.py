"""Trusted organism/candidate scope and curated mechanism tool integration."""
from __future__ import annotations

from copy import deepcopy
import json

import pytest

import praxis_virtualcell.knowledge as knowledge
from praxis_virtualcell.knowledge.store import DEFAULT_CATALOG_PATH
from praxis_virtualcell.llm_prediction import workflow
from praxis_virtualcell.llm_prediction.evidence import _reference, validate_evidence, validate_modality_coverage
from praxis_virtualcell.llm_prediction.orchestrator import analyze_with_agents
from praxis_virtualcell.llm_prediction.schemas import Assessment, EvidenceReference, empty_assessment


class Profile:
    def __init__(self, selected=None, *, taxonomy_id="NCBITaxon:470", strain="AB5075"):
        self.selected = list(selected or ["transcriptome"])
        self.taxonomy_id = taxonomy_id
        self.strain = strain

    def select_modalities(self, selected=None):
        return Profile(selected or self.selected, taxonomy_id=self.taxonomy_id, strain=self.strain)

    def overview(self):
        return {"profile_id": "fixture-profile", "source_id": "omics:fixture:profile",
                "species": {"scientific_name": "Acinetobacter baumannii", "taxonomy_id": self.taxonomy_id},
                "strain": self.strain, "available_modalities": ["genome", "transcriptome"],
                "selected_modalities": self.selected}

    def query_features(self, modality, feature_ids, limit=30):
        row = {"feature_id": "GENE_1", "gene_id": "GENE_1", "protein_id": "TEST_PROTEIN_1",
               "source_id": f"omics:fixture:{modality}:feature:GENE_1", "modality": modality,
               "unit": "test_native_unit", "source_locator": {"path": "fixture-only.csv", "row": 2}}
        row.update({"expression_value": 3.0} if modality == "transcriptome" else {"presence": True})
        return {"profile_id": "fixture-profile", "modality": modality,
                "features": [row] if "GENE_1" in feature_ids else []}


def reference_record():
    return {
        "record_id": "TEST:reference:GENE_1", "source_id": "knowledge:TEST:reference:GENE_1",
        "evidence_type": "gene_function", "support_level": "reference_annotation",
        "species": {"scientific_name": "Acinetobacter baumannii", "taxonomy_id": "NCBITaxon:470",
                    "strain": "AB5075", "identity_basis": "Synthetic unit-test fixture, not actual biology"},
        "native_ids": [{"namespace": "Fixture gene locus", "id": "GENE_1"},
                       {"namespace": "Fixture protein accession", "id": "TEST_PROTEIN_1"}],
        "gene_id": "GENE_1", "protein_id": "TEST_PROTEIN_1", "gene_symbol": "testGene",
        "claim": "Synthetic reference annotation used only to test exact retrieval.",
        "assay_type": "reference_genome_annotation", "assay": None, "compound_context": None,
        "source": {"citation": "Synthetic contract fixture only.", "doi": None,
                   "url": "https://example.invalid/test-only",
                   "source_locator": {"path": "fixture-only.csv", "table": "reference", "row": 2,
                                      "key_field": "gene_id", "key_value": "GENE_1", "sha256": None},
                   "supporting_locators": [],
                   "terms": {"usage": "local_research_copy", "license_name": None,
                             "license_status": "Synthetic unit-test fixture", "redistribution_approved": False}},
        "limitations": ["Synthetic test fixture is not a measured mechanism."],
        "candidate_causality_supported": False,
    }


def catalog(tmp_path, records=None):
    path = tmp_path / "knowledge.json"
    raw = {"schema_version": "praxis.mechanistic-knowledge.v1", "catalog_id": "integration-test-only",
           "created_at": "2026-10-07", "records": [reference_record()] if records is None else records,
           "limitations": ["Synthetic test-only catalog"], "excluded_assets": []}
    knowledge.KnowledgeCatalog.model_validate(raw)
    path.write_text(json.dumps(raw), encoding="utf-8")
    return path


def execute(name, arguments, path, profile=None):
    molecule = workflow.normalize_molecule("OCC", candidate_id="candidate")
    return workflow._execute(name, arguments, profile or Profile(), molecule, "candidate", path)


def response(value, *, tool_calls=None):
    return {"choices": [{"message": {"content": None if tool_calls is not None else json.dumps(value),
                                      **({"tool_calls": tool_calls} if tool_calls is not None else {})},
                         "finish_reason": "stop"}], "usage": {"total_tokens": 1}}


def tool_call(name, arguments, call_id):
    return {"id": call_id, "type": "function", "function": {"name": name, "arguments": json.dumps(arguments)}}


class Client:
    def __init__(self, responses):
        self.responses = deepcopy(responses)
        self.requests = []

    async def messages(self, **request):
        self.requests.append(deepcopy(request))
        return self.responses.pop(0)


def analysis_plan(selected=None):
    return {"selected_modalities": selected or ["transcriptome"], "questions": ["观察有哪些支持和缺口？"],
            "search_terms": ["testGene"], "limitations": ["没有该候选的靶点结合实验。"]}


def feature_assessment(include_reference=False):
    value = empty_assessment("这些观察只能提供未校准假说。")
    feature_ref = {"tool_call_id": "read-rna", "pointer": "/features/0/expression_value",
                   "source_id": "omics:fixture:transcriptome:feature:GENE_1", "value": 3.0}
    observations = [{"gene_id": "GENE_1", "field": "expression_value", "value": 3.0, "evidence_ref": feature_ref}]
    if include_reference:
        claim = reference_record()["claim"]
        observations.append({"gene_id": "GENE_1", "field": "claim", "value": claim,
                             "evidence_ref": {"tool_call_id": "read-mechanism", "pointer": "/records/0/claim",
                                              "source_id": reference_record()["source_id"], "value": claim}})
    value["supporting_evidence"] = [{"claim": "RNA与参考注释均不能证明该候选的直接结合。", "observations": observations}]
    return value


@pytest.mark.parametrize("name,arguments", [
    ("search_mechanistic_evidence", {"query": "testGene"}),
    ("query_mechanistic_evidence", {"record_ids": ["TEST:reference:GENE_1"]}),
])
@pytest.mark.parametrize("override", ["taxonomy_id", "strain", "compound_smiles", "catalog_path", "knowledge_catalog_path"])
def test_model_cannot_override_trusted_scope_structure_or_catalog(tmp_path, name, arguments, override):
    path = catalog(tmp_path)
    with pytest.raises(ValueError, match="unexpected_tool_arguments"):
        execute(name, {**arguments, override: "untrusted"}, path)
    definition = next(item["function"] for item in workflow.AGENT_TOOLS if item["function"]["name"] == name)
    assert override not in definition["parameters"]["properties"]
    assert definition["parameters"]["additionalProperties"] is False


def test_exact_candidate_tool_uses_only_profile_identity_and_normalized_candidate(tmp_path, monkeypatch):
    path = catalog(tmp_path)
    calls = []
    def search(taxonomy_id, query, **arguments):
        calls.append((taxonomy_id, query, arguments))
        return {"status": "empty", "records": [], "candidate_causality_supported": False}
    monkeypatch.setattr(knowledge, "search_mechanistic_evidence", search)
    result = execute("search_mechanistic_evidence", {"query": "", "candidate_interactions_only": True, "limit": 5}, path)
    assert result["profile_id"] == "fixture-profile"
    assert calls == [("NCBITaxon:470", "", {"native_ids": None, "compound_smiles": "CCO", "strain": "AB5075",
                                           "limit": 5, "catalog_path": path})]


def test_query_tool_uses_profile_scope_and_only_trusted_catalog(tmp_path, monkeypatch):
    path = catalog(tmp_path)
    calls = []
    def query(taxonomy_id, record_ids, **arguments):
        calls.append((taxonomy_id, record_ids, arguments))
        return {"status": "empty", "records": []}
    monkeypatch.setattr(knowledge, "query_mechanistic_evidence", query)
    execute("query_mechanistic_evidence", {"record_ids": ["TEST:reference:GENE_1"]}, path)
    assert calls == [("NCBITaxon:470", ["TEST:reference:GENE_1"], {"strain": "AB5075", "limit": 30, "catalog_path": path})]


@pytest.mark.parametrize("scope", [{"taxonomy_id": None}, {"taxonomy_id": "470"}, {"strain": None}, {"strain": ""}])
def test_unverified_profile_identity_cannot_broaden_mechanistic_search(tmp_path, scope):
    result = execute("search_mechanistic_evidence", {"query": "testGene"}, catalog(tmp_path), Profile(**scope))
    assert result["status"] == "unavailable" and result["records"] == []
    assert result["reason"] == "organism_scope_unverified"


@pytest.mark.parametrize("name,arguments", [
    ("search_mechanistic_evidence", {"query": "testGene"}),
    ("query_mechanistic_evidence", {"record_ids": ["TEST:reference:GENE_1"]}),
])
def test_native_mutant_profile_cannot_borrow_an_unverified_parent_catalog(tmp_path, name, arguments):
    class MutantProfile(Profile):
        def overview(self):
            return {**super().overview(), "genotype": "delta-relA"}

    path = catalog(tmp_path)
    assert execute(name, arguments, path)["records"]
    result = execute(name, arguments, path, MutantProfile())
    assert result["status"] == "unavailable" and result["records"] == []
    assert result["reason"] == "strain_genotype_scope_unverified"
    assert "prediction_scope" not in result


def test_retrieval_is_exact_and_reference_annotation_does_not_become_candidate_binding(tmp_path):
    path = catalog(tmp_path)
    result = execute("search_mechanistic_evidence", {"query": "testGene", "native_ids": ["GENE_1"]}, path)
    assert result["status"] == "available"
    assert result["records"][0]["evidence_type"] == "gene_function"
    assert result["records"][0]["compound_context"] is None
    assert execute("search_mechanistic_evidence", {"query": "", "candidate_interactions_only": True}, path)["status"] == "empty"
    assert execute("search_mechanistic_evidence", {"query": "testGene"}, path, Profile(strain="another-strain"))["status"] == "empty"
    assert execute("search_mechanistic_evidence", {"query": "testGene"}, path, Profile(taxonomy_id="NCBITaxon:562"))["status"] == "empty"


def test_source_references_bind_actual_values_and_do_not_replace_modality_evidence(tmp_path):
    path = catalog(tmp_path)
    data = execute("query_mechanistic_evidence", {"record_ids": ["TEST:reference:GENE_1"]}, path)
    calls = [
        {"tool_call_id": "read-rna", "name": "query_features", "ok": True,
         "data": Profile().query_features("transcriptome", ["GENE_1"])},
        {"tool_call_id": "read-mechanism", "name": "query_mechanistic_evidence", "ok": True, "data": data},
    ]
    assessment = Assessment.model_validate(feature_assessment(include_reference=True))
    assert validate_evidence(assessment, calls) == []
    issues = validate_modality_coverage(assessment, calls, ["genome", "transcriptome"])
    assert issues == ["selected_modality_not_observed:genome", "selected_modality_not_cited:genome"]
    reference = assessment.supporting_evidence[0].observations[1].evidence_ref
    _reference(reference, {call["tool_call_id"]: call for call in calls})
    wrong = EvidenceReference(**{**reference.model_dump(), "source_id": "knowledge:forged"})
    with pytest.raises(ValueError, match="source_id_does_not_match_tool"):
        _reference(wrong, {call["tool_call_id"]: call for call in calls})


def test_numeric_mic_requires_omics_gene_reference_even_with_verified_annotation_gene(tmp_path):
    mechanism = execute("query_mechanistic_evidence", {"record_ids": ["TEST:reference:GENE_1"]}, catalog(tmp_path))
    calls = [
        {"tool_call_id": "read-rna", "name": "query_features", "ok": True,
         "data": Profile().query_features("transcriptome", ["GENE_1"])},
        {"tool_call_id": "read-mechanism", "name": "query_mechanistic_evidence", "ok": True, "data": mechanism},
    ]
    draft = feature_assessment(include_reference=True)
    observations = draft["supporting_evidence"][0]["observations"]
    draft["mic_estimate"].update(value=8.0, evidence_refs=[deepcopy(observations[1]["evidence_ref"])])
    assessment = Assessment.model_validate(draft)
    # Reading/citing every selected modality does not make a knowledge annotation
    # an omics measurement eligible to ground a numeric MIC citation.
    assert validate_modality_coverage(assessment, calls, ["transcriptome"]) == []
    assert validate_evidence(assessment, calls) == ["numeric_mic_requires_verified_gene_evidence"]
    draft["mic_estimate"]["evidence_refs"] = [deepcopy(observations[0]["evidence_ref"])]
    assert validate_evidence(Assessment.model_validate(draft), calls) == []


def test_invalid_catalog_and_empty_catalog_never_return_whole_cell_labels(tmp_path):
    path = catalog(tmp_path, [])
    empty = execute("search_mechanistic_evidence", {"query": "", "candidate_interactions_only": True}, path)
    assert empty["status"] == "empty" and empty["records"] == []
    raw = json.loads(path.read_text())
    raw["MIC"] = "LABEL_SECRET_SENTINEL"
    path.write_text(json.dumps(raw))
    invalid = execute("search_mechanistic_evidence", {"query": "testGene"}, path)
    assert invalid["status"] == "unavailable" and invalid["records"] == []
    assert "LABEL_SECRET_SENTINEL" not in json.dumps(invalid)


async def test_agent_analysis_requires_each_modality_even_with_citable_mechanism(tmp_path):
    path = catalog(tmp_path)
    profile = Profile(["genome", "transcriptome"])
    client = Client([response(None, tool_calls=[
        tool_call("query_features", {"modality": "transcriptome", "feature_ids": ["GENE_1"]}, "read-rna"),
        tool_call("query_mechanistic_evidence", {"record_ids": ["TEST:reference:GENE_1"]}, "read-mechanism"),
    ]), response(feature_assessment(include_reference=True))])
    result = await workflow.analyze_candidate("OCC", "fixture-profile", client=client, max_turns=2,
                                              analysis_plan=analysis_plan(profile.selected), _profile=profile,
                                              knowledge_catalog_path=path)
    assert result["status"] == "unsupported"
    assert "selected_modality_not_observed:genome" in result["evidence_validation"]["issues"]
    assert "selected_modality_not_cited:genome" in result["evidence_validation"]["issues"]


async def test_model_cannot_reuse_the_mechanistic_bootstrap_call_id(tmp_path):
    client = Client([response(None, tool_calls=[
        tool_call("query_features", {"modality": "transcriptome", "feature_ids": ["GENE_1"]}, "context-candidate-interactions"),
    ])])
    result = await workflow.analyze_candidate("CCO", "fixture-profile", client=client, max_turns=2,
                                              analysis_plan=analysis_plan(), _profile=Profile(),
                                              knowledge_catalog_path=catalog(tmp_path, []))
    assert result["status"] == "unsupported"
    assert result["evidence_validation"]["issues"] == ["invalid_or_duplicate_tool_call_id"]
    assert len(client.requests) == 1


async def test_default_orchestration_passes_catalog_to_planning_and_analysis(tmp_path, monkeypatch):
    path = catalog(tmp_path, [])
    monkeypatch.setattr(workflow, "_load_organism", lambda profile_id, data_root: Profile())
    calls = []
    actual = knowledge.search_mechanistic_evidence
    def search(taxonomy_id, query, **arguments):
        calls.append(arguments)
        return actual(taxonomy_id, query, **arguments)
    monkeypatch.setattr(knowledge, "search_mechanistic_evidence", search)
    review = {"decision": "accept", "summary": "保持假说和缺口。", "issues": [], "recommended_changes": []}
    client = Client([response(analysis_plan()), response(None, tool_calls=[
        tool_call("query_features", {"modality": "transcriptome", "feature_ids": ["GENE_1"]}, "read-rna")]),
        response(feature_assessment()), response(review)])
    result = await analyze_with_agents("OCC", "fixture-profile", client=client, max_turns=2, knowledge_catalog_path=path, include_cell_structure=False)
    assert result["status"] == "completed"
    planner = json.loads(client.requests[0]["messages"][0]["content"])
    assert planner["mechanistic_catalog"]["catalog_id"] == "integration-test-only"
    assert planner["mechanistic_catalog"]["status"] == "empty"
    assert calls and all(arguments["catalog_path"] == path for arguments in calls)
    bootstrap = next(call for call in result["execution_trace"]["tool_calls"] if call["tool_call_id"] == "context-candidate-interactions")
    assert bootstrap["data"]["status"] == "empty" and bootstrap["data"]["catalog_id"] == "integration-test-only"
    initial_analysis = json.loads(client.requests[1]["messages"][0]["content"])
    assert any(item["tool_call_id"] == "context-candidate-interactions" and item["data"]["status"] == "empty"
               for item in initial_analysis["observed_context"])
    tool_names = {item["function"]["name"] for item in client.requests[1]["tools"]}
    assert {"search_mechanistic_evidence", "query_mechanistic_evidence"} <= tool_names


def test_actual_local_reference_record_keeps_curated_source_and_type():
    if not DEFAULT_CATALOG_PATH.exists():
        pytest.skip("real locally retained third-party reference catalog is not bundled with Git")
    data = execute("query_mechanistic_evidence", {"record_ids": ["AB5075:reference:ABUW_0960"]}, DEFAULT_CATALOG_PATH)
    record = data["records"][0]
    assert record["gene_id"] == "ABUW_0960" and record["protein_id"] == "AKA30714.1"
    assert record["source"]["source_locator"]["row"] == 915
    assert record["source"]["supporting_locators"][0]["row"] == 931
    assert record["evidence_type"] == "gene_function" and record["support_level"] == "reference_annotation"
    assert record["candidate_causality_supported"] is False and record["compound_context"] is None
    assert record["source"]["terms"]["redistribution_approved"] is False


def test_citation_hints_all_resolve_to_actual_values_with_the_closest_source(tmp_path):
    actual_calls = [
        {"tool_call_id": "feature-values", "name": "query_features", "ok": True,
         "data": {"features": [
             {"gene_id": "GENE_1", "source_id": "omics:zero", "expression_value": 0.0},
             {"protein_id": "TEST_PROTEIN_1", "source_id": "omics:null", "abundance_value": None},
             {"gene_id": "GENE_2", "source_id": "omics:false", "presence": False},
         ]}},
        {"tool_call_id": "mechanism-values", "name": "query_mechanistic_evidence", "ok": True,
         "data": execute("query_mechanistic_evidence", {"record_ids": ["TEST:reference:GENE_1"]}, catalog(tmp_path))},
    ]
    hinted_values = []
    for call in actual_calls:
        hints = workflow._citation_examples(call)
        assert hints
        for hint in hints:
            reference = EvidenceReference.model_validate(hint)
            actual, _ = _reference(reference, {call["tool_call_id"]: call})
            assert type(actual) is type(hint["value"])
            assert actual == hint["value"]
            hinted_values.append(actual)
    assert 0.0 in hinted_values and None in hinted_values
    assert any(value is False for value in hinted_values)
    assert reference_record()["claim"] in hinted_values
    assert workflow._citation_examples({"tool_call_id": "failed", "ok": False}) == []


def test_empty_mechanistic_query_has_its_own_citable_status_source(tmp_path):
    data = execute("search_mechanistic_evidence", {"query": "", "candidate_interactions_only": True}, catalog(tmp_path, []))
    assert data["status"] == "empty" and data["records"] == []
    assert data["source_id"] == "mechanistic-query:fixture-profile:integration-test-only"
    call = {"tool_call_id": "empty-query", "name": "search_mechanistic_evidence", "ok": True, "data": data}
    hints = workflow._citation_examples(call)
    status_hint = next(hint for hint in hints if hint["pointer"] == "/status")
    assert status_hint["source_id"] == data["source_id"]
    assert _reference(EvidenceReference.model_validate(status_hint), {"empty-query": call})[0] == "empty"
    wrong_source = EvidenceReference(**{**status_hint, "source_id": data["catalog_id"]})
    with pytest.raises(ValueError, match="source_id_does_not_match_tool"):
        _reference(wrong_source, {"empty-query": call})


def test_v1_and_v2_provenance_hints_preserve_the_actual_nested_path():
    v1 = {"source_id": "omics:v1:profile", "unit": "native RNA scale",
          "provenance": {"input_role": "Historical untreated reference, test fixture"}}
    v2 = {"source_id": "omics:v2:profile", "modalities": {
        "transcriptome": {"source_id": "omics:v2:transcriptome", "provenance": {
            "input_role": "Observed RNA source, test fixture"}},
    }}
    expected = ["/provenance/input_role", "/modalities/transcriptome/provenance/input_role"]
    for index, data in enumerate([v1, v2]):
        call = {"tool_call_id": f"overview-{index}", "name": "overview", "ok": True, "data": data}
        roles = [hint for hint in workflow._citation_examples(call) if hint["pointer"].endswith("/input_role")]
        assert len(roles) == 1 and roles[0]["pointer"] == expected[index]
        _reference(EvidenceReference.model_validate(roles[0]), {call["tool_call_id"]: call})
        assert roles[0]["source_id"] == (v1["source_id"] if index == 0 else v2["modalities"]["transcriptome"]["source_id"])


async def test_flattened_input_role_reference_remains_rejected_despite_correct_hints(tmp_path):
    class NestedProfile(Profile):
        def overview(self):
            return {**super().overview(), "provenance": {"input_role": "Historical untreated reference, test fixture"}}
    profile = NestedProfile()
    draft = feature_assessment()
    role = profile.overview()["provenance"]["input_role"]
    draft["counterevidence"] = [{"claim": "背景状态不能证明候选药物处理后的反应。", "observations": [
        {"gene_id": None, "field": "input_role", "value": role,
         "evidence_ref": {"tool_call_id": "context-overview", "pointer": "/input_role",
                          "source_id": profile.overview()["source_id"], "value": role}},
    ]}]
    client = Client([response(None, tool_calls=[tool_call("query_features", {
        "modality": "transcriptome", "feature_ids": ["GENE_1"]}, "read-rna")]), response(draft)])
    result = await workflow.analyze_candidate("CCO", "fixture-profile", client=client, max_turns=2,
                                              analysis_plan=analysis_plan(), _profile=profile,
                                              knowledge_catalog_path=catalog(tmp_path, []))
    assert result["status"] == "unsupported"
    assert "invalid_observation_reference" in result["evidence_validation"]["issues"]
    assert len(client.requests) == 2
    overview_call = next(call for call in result["execution_trace"]["tool_calls"] if call["tool_call_id"] == "context-overview")
    assert any(hint["pointer"] == "/provenance/input_role" for hint in overview_call["citation_examples"])
    assert "/input_role" in json.dumps(result["rejected_output"])
    # Both bootstrap and actual tool messages expose hints; no draft is rewritten.
    context = json.loads(client.requests[0]["messages"][0]["content"])["observed_context"]
    assert all("citation_examples" in call for call in context)
    tool_envelopes = [json.loads(message["content"]) for message in client.requests[1]["messages"] if message["role"] == "tool"]
    assert tool_envelopes and all("citation_examples" in envelope for envelope in tool_envelopes)
