"""Structure hypotheses cite source rows without replacing omics evidence."""
from copy import deepcopy

import pytest
from pydantic import ValidationError

from praxis_virtualcell.llm_prediction.evidence import (
    validate_evidence, validate_modality_coverage, validate_structure_evidence,
)
from praxis_virtualcell.llm_prediction.report import render_report
from praxis_virtualcell.llm_prediction.schemas import Assessment, empty_assessment


def row(**updates):
    return {"structure_id": "fixture:outer_membrane", "kind": "compartment", "compartment": "outer_membrane",
            "adjacent_to": None, "protein_id": None, "protein_namespace": None,
            "statement": "Synthetic source compartment, not a biological assertion.",
            "evidence_scope": "species_prior", "evidence_type": "reference_knowledge",
            "scope": {"taxonomy_id": "NCBITaxon:470", "strain": None, "strain_namespace": None,
                      "genotype": None, "genotype_scope": "not_reported"},
            "source_id": "structure:fixture:outer_membrane", "source_url": "https://example.invalid/fixture",
            "source_locator": {"section": "synthetic fixture"}, "condition": None, **updates}


def calls(structures=None, **updates):
    return [{"tool_call_id": "read-structure", "name": "cell_structure_overview", "ok": True,
             "data": {"structures": [row()] if structures is None else structures}, **updates}]


def reference(pointer="/structures/0/compartment", value="outer_membrane", **updates):
    return {"tool_call_id": "read-structure", "pointer": pointer,
            "source_id": "structure:fixture:outer_membrane", "value": value, **updates}


def claim(**updates):
    return {"structure_id": "fixture:outer_membrane", "compartment": "outer_membrane",
            "evidence_scope": "species_prior", "evidence_type": "reference_knowledge",
            "hypothesis": "Use this source only as a prior; candidate transport is unknown.",
            "evidence_refs": [reference()], **updates}


def assessment(structure=None):
    value = empty_assessment("Synthetic test; MIC unknown.")
    value["structure_analysis"] = structure if structure is not None else {
        "compartment_hypotheses": [claim()], "accessibility_barriers": [],
        "limitations": ["No actual strain protein localization or current-state measurement."]}
    return Assessment.model_validate(value)


def test_v3_missing_structure_field_is_compatible():
    raw = empty_assessment("Legacy prediction.")
    raw.pop("structure_analysis")
    old = Assessment.model_validate(raw)
    assert old.structure_analysis is None
    assert validate_structure_evidence(old, []) == []


def test_exact_species_prior_and_query_tool_citations_are_valid():
    for name in ("cell_structure_overview", "query_cell_structure"):
        diagnostics = []
        assert validate_structure_evidence(assessment(), calls(name=name), diagnostics=diagnostics) == []
        assert diagnostics == []


def test_packaged_catalog_has_compatible_exact_citations_without_native_localization():
    from praxis_virtualcell.cell_structure import cell_structure_overview

    data = cell_structure_overview({"profile_id": "contract-catalog-check", "input_role": "species_reference",
                                    "species": {"taxonomy_id": "NCBITaxon:470"}, "strain": None,
                                    "strain_namespace": None, "genotype": None})
    source = data["structures"][0]
    ref = reference(value=source["compartment"], source_id=source["source_id"])
    grounded = claim(structure_id=source["structure_id"], compartment=source["compartment"],
                     evidence_scope=source["evidence_scope"], evidence_type=source["evidence_type"],
                     evidence_refs=[ref])
    model = assessment({"compartment_hypotheses": [grounded], "limitations": data["gaps"]})
    tool = {"tool_call_id": "read-structure", "name": "cell_structure_overview", "ok": True, "data": data}
    assert validate_structure_evidence(model, [tool]) == []
    assert data["coverage"]["species_prior_count"] > 0
    assert data["coverage"]["strain_evidence_count"] == data["coverage"]["protein_localization_count"] == 0
    assert data["coverage"]["current_state_supported"] is False
    assert source["source_url"].startswith("https://") and source["source_locator"]


@pytest.mark.parametrize("field,value,issue", [
    ("evidence_scope", "strain_evidence", "structure_scope_does_not_match_tool"),
    ("evidence_type", "measured", "structure_evidence_type_does_not_match_tool"),
    ("structure_id", "fixture:invented", "structure_identity_not_bound_to_reference"),
    ("compartment", "cytoplasm", "structure_compartment_does_not_match_tool"),
])
def test_structure_identity_and_scope_cannot_be_upgraded(field, value, issue):
    draft = assessment().model_dump()
    draft["structure_analysis"]["compartment_hypotheses"][0][field] = value
    assert issue in validate_structure_evidence(Assessment.model_validate(draft), calls())


@pytest.mark.parametrize("ref,issue", [
    (reference(source_id="structure:forged"), "source_id_does_not_match_tool"),
    (reference(value="cytoplasm"), "quoted_value_does_not_match_tool"),
    (reference(tool_call_id="unobserved"), "unknown_or_failed_tool_call"),
])
def test_exact_value_and_source_are_required_with_diagnostics(ref, issue):
    diagnostics = []
    model = assessment({"compartment_hypotheses": [claim(evidence_refs=[ref])]})
    assert issue in validate_structure_evidence(model, calls(), diagnostics=diagnostics)
    assert any(item["location"] == ["structure_analysis", "compartment_hypotheses", 0, "evidence_refs", 0]
               for item in diagnostics)


def test_compartment_must_be_explicitly_cited_at_the_structure_row():
    source = row(source_locator={"compartment": "outer_membrane"})
    for ref in (reference("/structures/0/statement", source["statement"]),
                reference("/structures/0/source_locator/compartment")):
        model = assessment({"compartment_hypotheses": [claim(evidence_refs=[ref])]})
        assert "structure_compartment_requires_exact_reference" in validate_structure_evidence(model, calls([source]))


def test_genome_presence_and_compartment_prior_are_not_protein_localization():
    protein = claim(protein_id="NATIVE_P1", protein_namespace="fixture_accession")
    model = assessment({"compartment_hypotheses": [protein]})
    assert "protein_localization_not_observed" in validate_structure_evidence(model, calls())
    genome_row = row(kind="protein_localization", protein_id="NATIVE_P1", protein_namespace="fixture_accession")
    assert "structure_reference_requires_structure_tool" in validate_structure_evidence(
        model, calls([genome_row], name="query_features"))


def test_actual_native_protein_localization_binds_identity_namespace_and_source_grade():
    source = row(kind="protein_localization", protein_id="NATIVE_P1", protein_namespace="fixture_accession",
                 evidence_scope="strain_evidence", evidence_type="source_annotation")
    protein = claim(protein_id="NATIVE_P1", protein_namespace="fixture_accession",
                    evidence_scope="strain_evidence", evidence_type="source_annotation")
    model = assessment({"compartment_hypotheses": [protein]})
    assert validate_structure_evidence(model, calls([source])) == []
    protein["protein_namespace"] = "invented_namespace"
    assert "protein_identity_does_not_match_structure" in validate_structure_evidence(
        assessment({"compartment_hypotheses": [protein]}), calls([source]))
    protein.pop("protein_namespace")
    with pytest.raises(ValidationError, match="protein localization requires both"):
        assessment({"compartment_hypotheses": [protein]})


def test_known_structure_cannot_be_silently_ignored_and_unknown_requires_limitation():
    unknown = assessment({"limitations": ["Tool returned no structural records."]})
    assert validate_structure_evidence(unknown, calls([])) == []
    assert "available_structure_requires_grounded_hypothesis" in validate_structure_evidence(unknown, calls())
    assert "structure_analysis_requires_structure_tool" in validate_structure_evidence(unknown, [])
    assert "structure_missing_data_requires_limitation" in validate_structure_evidence(assessment({}), calls([]))


def test_structure_never_replaces_numeric_mic_or_selected_omics_requirements():
    value = assessment().model_dump()
    value["mic_estimate"].update(value=8, evidence_refs=[reference()])
    model = Assessment.model_validate(value)
    issues = validate_evidence(model, calls())
    assert "no_gene_observations_loaded" in issues
    assert "numeric_mic_requires_verified_gene_evidence" in issues
    assert validate_modality_coverage(model, calls(), ["genome"]) == [
        "selected_modality_not_observed:genome", "selected_modality_not_cited:genome"]


def test_structure_prose_still_obeys_existing_native_gene_reference_rule():
    model = assessment({"compartment_hypotheses": [claim(hypothesis="ABUW_INVENTED has not been observed.")]})
    assert "gene_in_text_not_observed" in validate_evidence(model, calls())


def test_structure_claims_require_grounding_and_remain_hypotheses():
    for change in ({"evidence_refs": []}, {"status": "confirmed"}):
        with pytest.raises(ValidationError):
            assessment({"compartment_hypotheses": [claim(**change)]})


def test_report_exposes_source_scope_exact_citation_and_unknown_state():
    result = {"candidate": {"id": "test", "smiles": "CCO"}, "profile": {"species": "Test bacterium"},
              "assessment": assessment().model_dump(), "status": "completed",
              "evidence_validation": {"status": "passed"}, "execution_trace": {"model": "fixture"}}
    original = deepcopy(result)
    text = render_report(result)
    assert "物种背景（species_prior）" in text
    assert "当前菌株结构与状态未知" in text
    assert "蛋白定位：未知" in text
    assert "read-structure/structures/0/compartment" in text
    assert "参考知识" in text and "候选分子的穿透或结合" in text
    assert result == original
    result["assessment"]["structure_analysis"] = None
    assert "本报告未提供经引用核验的结构分析" in render_report(result)
