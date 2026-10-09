import copy
import json
from pathlib import Path

import pytest

from praxis_virtualcell.cell_structure import (
    CellStructureError,
    cell_structure_overview,
    load_catalog,
    query_cell_structure,
)


def _overview(taxon="470", **updates):
    return {"profile_id": "cpu-fixture", "species": {"taxonomy_id": f"NCBITaxon:{taxon}"},
            "strain": "AB5075", "genotype": None, **updates}


def _write(tmp_path, payload):
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(payload))
    return path


@pytest.mark.parametrize("taxon", ["470", "562", "287", "573"])
def test_shipped_species_priors_are_traceable_and_not_current_cell(taxon):
    result = cell_structure_overview(_overview(taxon))
    assert len(result["structures"]) == 9
    assert result["coverage"] == {"species_prior_count": 9, "strain_evidence_count": 0,
                                  "protein_localization_count": 0, "current_state_supported": False}
    assert {item["kind"] for item in result["structures"]} == {"compartment", "adjacency"}
    for item in result["structures"]:
        assert item["evidence_scope"] == "species_prior"
        assert item["evidence_type"] == "reference_knowledge"
        assert item["scope"]["taxonomy_id"] == f"NCBITaxon:{taxon}"
        assert item["scope"]["strain"] is item["scope"]["genotype"] is None
        assert item["source_id"].startswith("doi:")
        assert item["source_url"].startswith("https://") and item["source_locator"]
        assert item["protein_id"] is None


@pytest.mark.parametrize("species", [{"taxonomy_id": "NCBITaxon:1280"}, {"taxonomy_id": "NCBITaxon:2104"},
                                    {"taxonomy_id": "470"}, {}, None])
def test_unsupported_or_unverified_species_has_no_gram_negative_fallback(species):
    result = cell_structure_overview(_overview(species=species))
    assert result["status"] == "unknown"
    assert result["structures"] == []
    assert result["coverage"]["species_prior_count"] == 0


def test_query_preserves_fact_identity_source_and_independent_condition():
    overview = _overview("562", condition={"medium": "different", "temperature_c": 25})
    result = query_cell_structure(overview, structure_ids=["cell:562:periplasm", "missing"])
    assert result["missing_structure_ids"] == ["missing"]
    row = result["structures"][0]
    assert row["structure_id"] == "cell:562:periplasm"
    assert row["compartment"] == "periplasm"
    assert row["condition"]["temperature_c"] == 37
    assert row["condition"]["medium"] != overview["condition"]["medium"]
    assert row["source_context"]["source_strains"] == ["Escherichia coli K-12", "Pseudomonas aeruginosa PAO1"]
    assert result["request_scope"]["genotype"] is None


def test_native_protein_query_is_unknown_without_localization_source():
    result = query_cell_structure(_overview(), protein_ids=["ABUW_0001"], protein_namespace="AB5075_original")
    assert result["structures"] == []
    assert result["missing_protein_ids"] == ["ABUW_0001"]
    assert result["coverage"]["protein_localization_count"] == 0


@pytest.fixture
def strain_catalog(tmp_path):
    payload = load_catalog().model_dump()
    fact = copy.deepcopy(payload["structures"][0])
    fact.update({"structure_id": "cpu:protein-localization", "kind": "protein_localization",
                 "compartment": "outer_membrane", "protein_id": "native-protein-1", "protein_namespace": "native:test",
                 "statement": "Synthetic localization fixture, not a biological source claim.",
                 "evidence_scope": "strain_evidence", "evidence_type": "source_annotation"})
    fact["scope"].update({"strain": "isolate-1", "strain_namespace": "study:A"})
    fact["source_context"]["interpretation"] = "Synthetic CPU fixture only."
    payload["structures"].append(fact)
    return _write(tmp_path, payload)


def test_exact_strain_source_scope_keeps_unknown_genotype_unknown(strain_catalog):
    result = query_cell_structure(_overview(strain="isolate-1", strain_namespace="study:A"),
                                  protein_ids=["native-protein-1"], protein_namespace="native:test",
                                  catalog_path=strain_catalog)
    assert result["coverage"]["strain_evidence_count"] == 1
    assert result["coverage"]["protein_localization_count"] == 1
    assert result["structures"][0]["scope"]["genotype_scope"] == "not_reported"
    assert any("wild-type status is unknown" in gap for gap in result["gaps"])
    assert result["coverage"]["current_state_supported"] is False


@pytest.mark.parametrize("updates", [{"strain": "other-isolate"}, {"strain_namespace": "study:B"},
                                      {"strain_namespace": None}, {"strain": "wild type"},
                                      {"strain": "unknown strain"}, {"strain": "unidentified isolate"},
                                      {"genotype": "wild type"}, {"genotype": "delta-ompA"},
                                      {"species": {"taxonomy_id": "NCBITaxon:562"}},
                                      {"input_role": "species_reference"}])
def test_no_alias_cross_study_genotype_or_species_fallback(strain_catalog, updates):
    overview = _overview(strain="isolate-1", strain_namespace="study:A") | updates
    result = query_cell_structure(overview, protein_ids=["native-protein-1"], protein_namespace="native:test",
                                  catalog_path=strain_catalog)
    assert result["structures"] == []
    assert result["missing_protein_ids"] == ["native-protein-1"]


def test_declared_mutant_does_not_match_unreported_genotype(tmp_path, strain_catalog):
    payload = json.loads(strain_catalog.read_text())
    payload["structures"][-1]["scope"].update(genotype="delta-ompA", genotype_scope="declared")
    path = _write(tmp_path, payload)
    assert query_cell_structure(_overview(strain="isolate-1", strain_namespace="study:A"),
                                protein_ids=["native-protein-1"], protein_namespace="native:test",
                                catalog_path=path)["structures"] == []
    match = query_cell_structure(_overview(strain="isolate-1", strain_namespace="study:A", genotype="delta-ompA"),
                                 protein_ids=["native-protein-1"], protein_namespace="native:test", catalog_path=path)
    assert len(match["structures"]) == 1


def test_species_reference_only_returns_species_priors(strain_catalog):
    result = cell_structure_overview(_overview(strain="isolate-1", strain_namespace="study:A",
                                               input_role="species_reference"), catalog_path=strain_catalog)
    assert len(result["structures"]) == 9
    assert result["coverage"]["strain_evidence_count"] == 0


def test_catalog_root_and_explicit_override(tmp_path):
    payload = load_catalog().model_dump()
    payload["catalog_id"] = "cpu-root"
    path = _write(tmp_path, payload)
    assert cell_structure_overview(_overview(), data_root=tmp_path)["catalog_id"] == "cpu-root"
    assert cell_structure_overview(_overview(), data_root=Path("missing"), catalog_path=path)["catalog_id"] == "cpu-root"


@pytest.mark.parametrize("change", ["duplicate", "measured_prior", "dangling_adjacency", "gene_only", "missing_source"])
def test_catalog_rejects_untraceable_or_misrepresented_facts(tmp_path, change):
    payload = load_catalog().model_dump()
    if change == "duplicate":
        payload["structures"].append(copy.deepcopy(payload["structures"][0]))
    elif change == "measured_prior":
        payload["structures"][0]["evidence_type"] = "measured"
    elif change == "dangling_adjacency":
        payload["structures"][-1]["adjacent_to"] = "nonexistent"
    elif change == "gene_only":
        payload["structures"][0]["protein_id"] = "gene-is-not-a-location"
    else:
        payload["structures"][0]["source_locator"] = {}
    with pytest.raises(CellStructureError):
        cell_structure_overview(_overview(), catalog_path=_write(tmp_path, payload))


@pytest.mark.parametrize("args", [{"limit": True}, {"limit": 31}, {"structure_ids": []},
                                  {"protein_ids": ["p1"]}, {"protein_namespace": "namespace"},
                                  {"compartment": " "}])
def test_query_rejects_ambiguous_arguments(args):
    with pytest.raises(ValueError):
        query_cell_structure(_overview(), **args)


def test_truncation_does_not_invent_missing_ids():
    result = query_cell_structure(_overview(), structure_ids=["cell:470:cytoplasm", "cell:470:periplasm"], limit=1)
    assert result["match_count"] == 2 and result["truncated"] is True
    assert result["missing_structure_ids"] == []
