"""Synthetic fixtures test contracts; no fixture asserts a real interaction."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from praxis_virtualcell.knowledge import (
    KnowledgeCatalog, MechanisticRecord, catalog_overview,
    query_mechanistic_evidence, search_mechanistic_evidence,
)
from praxis_virtualcell.llm_prediction.evidence import matching_value_pointers
from praxis_virtualcell.llm_prediction.schemas import EvidenceReference


def annotation(record_id="TEST:reference:GENE_1", gene_id="GENE_1"):
    return {
        "record_id": record_id, "source_id": f"knowledge:{record_id}",
        "evidence_type": "gene_function", "support_level": "reference_annotation",
        "species": {"scientific_name": "Synthetic test organism", "taxonomy_id": "NCBITaxon:470",
                    "strain": "TEST_ONLY", "identity_basis": "Synthetic fixture, not real biology"},
        "native_ids": [{"namespace": "Synthetic native locus", "id": gene_id},
                       {"namespace": "Synthetic protein", "id": "TEST_PROTEIN_1"}],
        "gene_id": gene_id, "protein_id": "TEST_PROTEIN_1", "gene_symbol": "testGene",
        "claim": "Synthetic reference annotation fixture.",
        "assay_type": "reference_genome_annotation", "assay": None, "compound_context": None,
        "source": {
            "citation": "Synthetic test fixture, not a published biology fact.", "doi": None,
            "url": "https://example.invalid/test-only",
            "source_locator": {"path": "test-only.csv", "table": "fixture", "row": 2,
                               "key_field": "gene_id", "key_value": gene_id, "sha256": None},
            "supporting_locators": [],
            "terms": {"usage": "local_research_copy", "license_name": None,
                      "license_status": "Synthetic unit-test fixture", "redistribution_approved": False},
        },
        "limitations": ["Synthetic test data; never an actual measured mechanism."],
        "candidate_causality_supported": False,
    }


def interaction():
    result = annotation("TEST:interaction:1")
    result.update({
        "evidence_type": "compound_protein_interaction", "support_level": "experimental_protein_measurement",
        "claim": "Synthetic protein measurement fixture; not a real experimental claim.",
        "assay_type": "protein_binding",
        "assay": {"assay_id": "TEST_ASSAY", "assay_type": "protein_binding",
                  "target_entity": "purified_protein", "target_identity_confirmed": True,
                  "assay_species_confirmed": True, "interaction_mode": "direct_binding",
                  "measurement": {"endpoint": "Kd", "value": 2.0, "unit": "nM", "relation": "="}},
        "compound_context": {"source_compound_id": "TEST_COMPOUND", "tested_smiles": "C[C@H](O)N",
                             "structure_context": "Synthetic stereochemical graph only, test-only neutral chemical form",
                             "inchikey": None, "match_policy": "exact_stereochemical_graph"},
    })
    return result


def write_catalog(tmp_path, records=None):
    path = tmp_path / "catalog.json"
    catalog = {"schema_version": "praxis.mechanistic-knowledge.v1", "catalog_id": "synthetic-test-only",
               "created_at": "2026-10-07", "records": records if records is not None else [annotation(), interaction()],
               "limitations": ["Synthetic test-only catalog"], "excluded_assets": []}
    path.write_text(json.dumps(catalog), encoding="utf-8")
    return path


@pytest.mark.parametrize("field,value", [("MIC", 1), ("mic", 1), ("mic_value", 1),
                                       ("activity", "likely_active"), ("survival", 0.5)])
def test_whole_cell_fields_are_forbidden(field, value):
    record = annotation()
    record[field] = value
    with pytest.raises(ValidationError):
        MechanisticRecord.model_validate(record)


def test_labels_cannot_be_inserted_into_a_claim():
    record = annotation()
    record["claim"] = "MIC 0.25 ug/mL"
    with pytest.raises(ValidationError, match="whole-cell efficacy"):
        MechanisticRecord.model_validate(record)


@pytest.mark.parametrize("location,field", [("source", "abstract"), ("compound_context", "activity"),
                                         ("assay", "MIC")])
def test_nested_unselected_raw_labels_are_forbidden(location, field):
    record = interaction()
    record[location][field] = "unselected label"
    with pytest.raises(ValidationError):
        MechanisticRecord.model_validate(record)


@pytest.mark.parametrize("change", ["annotation_compound", "annotation_experiment", "missing_protein",
                                   "missing_assay", "missing_structure", "organism_target", "wrong_mode", "MIC_endpoint"])
def test_reference_and_experimental_support_cannot_be_conflated(change):
    record = interaction()
    if change == "annotation_compound":
        record.update(evidence_type="gene_function", support_level="reference_annotation", assay_type="reference_genome_annotation")
    elif change == "annotation_experiment":
        record = annotation()
        record["support_level"] = "experimental_protein_measurement"
    elif change == "missing_protein":
        record["protein_id"] = None
    elif change == "missing_assay":
        record["assay"] = None
    elif change == "missing_structure":
        record["compound_context"] = None
    elif change == "organism_target":
        record["assay"]["target_entity"] = "whole_organism"
    elif change == "wrong_mode":
        record["assay"]["interaction_mode"] = "biochemical_modulation"
    else:
        record["assay"]["measurement"]["endpoint"] = "MIC"
    with pytest.raises(ValidationError):
        MechanisticRecord.model_validate(record)


def test_annotation_cannot_assert_candidate_causality_or_unmapped_target():
    record = annotation()
    record["candidate_causality_supported"] = True
    with pytest.raises(ValidationError):
        MechanisticRecord.model_validate(record)
    record = annotation()
    record["protein_id"] = "unknown-protein"
    with pytest.raises(ValidationError, match="native_ids"):
        MechanisticRecord.model_validate(record)


def test_protein_record_requires_a_valid_tested_molecular_structure():
    record = interaction()
    record["compound_context"]["tested_smiles"] = "not_a_structure"
    with pytest.raises(ValidationError, match="valid molecular structure"):
        MechanisticRecord.model_validate(record)


def test_search_requires_exact_taxon_strain_and_native_ids(tmp_path):
    path = write_catalog(tmp_path)
    result = search_mechanistic_evidence("NCBITaxon:470", "testGene", native_ids=["GENE_1"], strain="TEST_ONLY", catalog_path=path)
    assert result["status"] == "available"
    assert len(result["records"]) == 2
    for arguments in ({"taxonomy_id": "NCBITaxon:562"}, {"strain": "another strain"},
                      {"native_ids": ["testGene"]}, {"native_ids": ["gene_1"]}):
        parameters = dict(taxonomy_id="NCBITaxon:470", query="testGene", strain="TEST_ONLY", catalog_path=path)
        parameters.update(arguments)
        assert search_mechanistic_evidence(**parameters)["status"] == "empty"


def test_query_returns_missing_ids_without_cross_taxon_transfer(tmp_path):
    path = write_catalog(tmp_path)
    result = query_mechanistic_evidence("NCBITaxon:470", ["TEST:reference:GENE_1", "unknown"], strain="TEST_ONLY", catalog_path=path)
    assert result["missing_record_ids"] == ["unknown"]
    assert result["records"][0]["gene_id"] == "GENE_1"
    other = query_mechanistic_evidence("NCBITaxon:562", ["TEST:reference:GENE_1"], catalog_path=path)
    assert other["status"] == "empty"
    assert other["missing_record_ids"] == ["TEST:reference:GENE_1"]


def test_compound_matching_excludes_annotations_and_similar_molecules(tmp_path):
    path = write_catalog(tmp_path)
    result = search_mechanistic_evidence("NCBITaxon:470", "", compound_smiles="C[C@H](O)N", strain="TEST_ONLY", catalog_path=path)
    assert len(result["records"]) == 1
    assert result["records"][0]["evidence_type"] == "compound_protein_interaction"
    assert result["candidate_causality_supported"] is False
    for smiles in ["C[C@@H](O)N", "CC(O)N", "CC(O)NC", "C[C@H](O)N.[Cl-]"]:
        assert search_mechanistic_evidence("NCBITaxon:470", "", compound_smiles=smiles, catalog_path=path)["status"] == "empty"


def test_same_stereochemical_graph_can_have_different_smiles_order(tmp_path):
    path = write_catalog(tmp_path)
    result = search_mechanistic_evidence("NCBITaxon:470", "", compound_smiles="O[C@@H](C)N", catalog_path=path)
    assert result["status"] == "available"


def test_empty_unavailable_and_invalid_are_explicit(tmp_path):
    missing = search_mechanistic_evidence("NCBITaxon:470", "gene", catalog_path=tmp_path / "missing.json")
    assert (missing["status"], missing["reason"], missing["records"]) == ("unavailable", "catalog_not_found", [])
    empty = search_mechanistic_evidence("NCBITaxon:470", "gene", catalog_path=write_catalog(tmp_path, []))
    assert empty["status"] == "empty"
    path = write_catalog(tmp_path)
    raw = json.loads(path.read_text())
    raw["records"][0]["MIC"] = "DO_NOT_LEAK_123"
    path.write_text(json.dumps(raw))
    invalid = query_mechanistic_evidence("NCBITaxon:470", ["TEST:reference:GENE_1"], catalog_path=path)
    assert invalid["status"] == "unavailable"
    assert invalid["reason"] == "catalog_invalid"
    assert "DO_NOT_LEAK_123" not in json.dumps(invalid)


def test_source_id_and_values_are_compatible_with_existing_reference_binding(tmp_path):
    result = query_mechanistic_evidence("NCBITaxon:470", ["TEST:reference:GENE_1"], catalog_path=write_catalog(tmp_path))
    reference = EvidenceReference(tool_call_id="knowledge_1", pointer="/records/0/claim",
                                  source_id=result["records"][0]["source_id"], value=result["records"][0]["claim"])
    calls = {"knowledge_1": {"tool_call_id": "knowledge_1", "ok": True, "data": result}}
    assert reference.pointer in matching_value_pointers(reference, calls)
    reference.source_id = "knowledge:another-record"
    assert matching_value_pointers(reference, calls) == []


def test_overview_and_truncation(tmp_path):
    path = write_catalog(tmp_path)
    assert catalog_overview(path)["evidence_type_counts"] == {"gene_function": 1, "pathway": 0, "compound_protein_interaction": 1}
    result = query_mechanistic_evidence("NCBITaxon:470", ["TEST:reference:GENE_1", "TEST:interaction:1"], limit=1, catalog_path=path)
    assert len(result["records"]) == 1 and result["truncated"] is True


@pytest.mark.parametrize("scope", [{"taxonomy_id": "Acinetobacter baumannii"}, {"taxonomy_id": "470"},
                                 {"taxonomy_id": "NCBITaxon:470", "limit": True},
                                 {"taxonomy_id": "NCBITaxon:470", "limit": 101}])
def test_scope_is_not_a_fuzzy_species_or_unbounded_request(tmp_path, scope):
    with pytest.raises(ValueError):
        search_mechanistic_evidence(query="gene", catalog_path=write_catalog(tmp_path), **scope)


def test_catalog_cannot_duplicate_source_id_or_record_identity():
    record = annotation()
    record["source_id"] = "knowledge:wrong"
    with pytest.raises(ValidationError):
        MechanisticRecord.model_validate(record)
    raw = {"schema_version": "praxis.mechanistic-knowledge.v1", "catalog_id": "test",
           "created_at": "2026-10-07", "records": [annotation(), copy.deepcopy(annotation())],
           "limitations": ["test"]}
    with pytest.raises(ValidationError, match="unique"):
        KnowledgeCatalog.model_validate(raw)


def test_portable_empty_example():
    example = Path(__file__).resolve().parents[2] / "examples/knowledge/empty_catalog.json"
    assert catalog_overview(example)["status"] == "empty"


def test_local_real_seed_retains_native_identity_and_reference_evidence():
    root = Path(__file__).resolve().parents[2]
    manifest = root / "data/organisms/AB5075-AZI000/manifest.json"
    if not manifest.exists():
        pytest.skip("local third-party reference delivery is intentionally not bundled in GitHub")
    from examples.knowledge.build_catalog import build_catalog
    catalog = build_catalog(root / "data/organisms")
    assert len(catalog["records"]) == 7
    assert {record["evidence_type"] for record in catalog["records"]} == {"gene_function"}
    gyr_a = next(record for record in catalog["records"] if record["gene_id"] == "ABUW_0960")
    assert gyr_a["protein_id"] == "AKA30714.1"
    assert gyr_a["source"]["source_locator"]["row"] == 915
    assert gyr_a["source"]["supporting_locators"][0]["row"] == 931
    assert gyr_a["compound_context"] is None
    assert gyr_a["source"]["terms"]["redistribution_approved"] is False
