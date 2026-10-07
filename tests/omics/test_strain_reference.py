"""Exact strain identities, independent conditions and native evidence sources."""
from __future__ import annotations

import itertools
import json

import pytest

from praxis_virtualcell.llm_prediction import workflow
from praxis_virtualcell.llm_prediction.evidence import _reference
from praxis_virtualcell.llm_prediction.schemas import EvidenceReference, empty_assessment
from praxis_virtualcell.omics import ProfileError, list_profiles, load_profile
from tests.omics.test_species_reference import NAMES, SPECIES, _references


REFERENCE_ID = "synthetic-strain-reference"


def _strain_references(root):
    _references(root)
    for name in NAMES:
        path = root / f"source-{name}" / "manifest.json"
        source = json.loads(path.read_text())
        source["strain"] = source["modalities"][name]["strain"] = "AB5075"
        path.write_text(json.dumps(source))
    manifest = {
        "schema_version": "praxis.strain-reference.v1", "profile_id": REFERENCE_ID,
        "species": SPECIES, "strain": "AB5075", "label": "AB5075 · synthetic strain reference",
        "strain_namespace": "author_strain_name", "identity_basis": "Synthetic exact native strain declarations; software test only",
        "genotype": None, "reference_profiles": {name: f"source-{name}" for name in NAMES},
        "input_role": "strain_reference", "relation": "same_strain_reference", "prediction_scope": "strain_reference",
        "selection_reasons": {name: "Same explicit synthetic strain, independent culture condition" for name in NAMES},
    }
    directory = root / REFERENCE_ID
    directory.mkdir()
    (directory / "manifest.json").write_text(json.dumps(manifest))
    return manifest


@pytest.mark.parametrize("selected", [list(combo) for size in range(1, 4) for combo in itertools.combinations(NAMES, size)])
def test_seven_views_allow_same_strain_different_conditions_and_keep_native_citations(tmp_path, selected):
    _strain_references(tmp_path)
    profile = load_profile(REFERENCE_ID, tmp_path).select_modalities(selected)
    overview = profile.overview()
    assert overview["strain"] == "AB5075" and overview["pairing"] is None
    assert overview["input_role"] == overview["prediction_scope"] == "strain_reference"
    assert overview["condition"]["role"] == "strain_reference"
    assert "prediction_strain" not in overview["unknown_fields"]
    assert overview["genotype"] is None and "genotype" in overview["unknown_fields"]
    assert list(overview["modalities"]) == selected
    for name in selected:
        assert overview["modalities"][name]["strain"] == "AB5075"
        assert overview["modalities"][name]["condition"]["condition_id"] == f"condition-{name}"
        result = profile.query_features(name, [f"{name}-feature-0", f"{name}-feature-1"])
        assert result["input_role"] == "strain_reference"
        call = {"tool_call_id": "native", "ok": True, "name": "query_features", "data": result}
        for index, row in enumerate(result["features"]):
            assert row["source_id"] == f"omics:source-{name}:{name}:feature:{name}-feature-{index}"
            assert row["source_strain"] == "AB5075"
            assert row["source_condition"]["medium"] == f"medium-{name}"
            field = {"genome": "presence", "transcriptome": "expression_value", "proteome": "abundance_value"}[name]
            reference = EvidenceReference(tool_call_id="native", pointer=f"/features/{index}/{field}",
                                          source_id=row["source_id"], value=row[field])
            _reference(reference, {"native": call})
            if index == 1:
                assert row[field] is None
        forged = reference.model_copy(update={"source_id": f"omics:{REFERENCE_ID}:{name}:feature:forged"})
        with pytest.raises(ValueError, match="source_id_does_not_match_tool"):
            _reference(forged, {"native": call})
    assert {row["modality"] for row in profile.query_genes(["native-gene-0"])["genes"]} == set(selected)
    for absent in set(NAMES) - set(selected):
        assert f"source-{absent}" not in json.dumps(overview)
        with pytest.raises(ProfileError, match="unselected"):
            profile.query_features(absent, [f"{absent}-feature-0"])


@pytest.mark.parametrize("strain", ["AB5075-UW", "AB5075 delta relA", "ATCC 17978", "ab5075"])
def test_other_strains_mutant_names_and_unverified_aliases_are_not_borrowed(tmp_path, strain):
    _strain_references(tmp_path)
    path = tmp_path / "source-proteome/manifest.json"
    source = json.loads(path.read_text())
    source["strain"] = source["modalities"]["proteome"]["strain"] = strain
    path.write_text(json.dumps(source))
    with pytest.raises(ProfileError, match="strain differs"):
        load_profile(REFERENCE_ID, tmp_path)


def test_same_name_does_not_combine_explicit_mutant_with_unknown_parent_genotype(tmp_path):
    _strain_references(tmp_path)
    path = tmp_path / "source-transcriptome/manifest.json"
    source = json.loads(path.read_text())
    source["genotype"] = source["modalities"]["transcriptome"]["genotype"] = "delta-relA"
    path.write_text(json.dumps(source))
    with pytest.raises(ProfileError, match="mutants and derivatives"):
        load_profile(REFERENCE_ID, tmp_path)


@pytest.mark.parametrize("change", [
    {"strain": "unknown"}, {"strain": "WT"}, {"strain_namespace": ""}, {"identity_basis": " "},
    {"reference_profiles": {"genome": "synthetic-species-reference"}},
    {"reference_profiles": {"genome": REFERENCE_ID}},
    {"species": {"scientific_name": "Escherichia coli", "taxonomy_id": "NCBITaxon:562"}},
])
def test_unknown_identity_nested_collections_and_other_species_are_rejected(tmp_path, change):
    manifest = _strain_references(tmp_path)
    manifest.update(change)
    (tmp_path / REFERENCE_ID / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ProfileError):
        load_profile(REFERENCE_ID, tmp_path)


def test_listing_uses_exact_strain_label_and_never_copies_source_assets(tmp_path):
    _strain_references(tmp_path)
    item = next(row for row in list_profiles(tmp_path) if row["profile_id"] == REFERENCE_ID)
    assert item["strain"] == "AB5075" and item["prediction_scope"] == "strain_reference"
    assert item["strain_namespace"] == "author_strain_name"
    assert item["label"].startswith("AB5075")
    assert [path.name for path in (tmp_path / REFERENCE_ID).iterdir()] == ["manifest.json"]


def test_historical_v1_native_identity_can_be_referenced_without_alias_inference(tiny_profile_root):
    native = load_profile(data_root=tiny_profile_root)
    manifest = {"schema_version": "praxis.strain-reference.v1", "profile_id": REFERENCE_ID,
                "species": native.overview()["species"], "strain": "AB5075", "label": "AB5075 RNA",
                "strain_namespace": "author_strain_name", "identity_basis": "Synthetic exact source declaration",
                "input_role": "strain_reference", "relation": "same_strain_reference", "prediction_scope": "strain_reference",
                "reference_profiles": {"transcriptome": native.profile_id}}
    root = tiny_profile_root / REFERENCE_ID
    root.mkdir()
    (root / "manifest.json").write_text(json.dumps(manifest))
    profile = load_profile(REFERENCE_ID, tiny_profile_root)
    assert profile.overview()["modalities"]["transcriptome"]["observation_unit"] == "historical_condition_mean"
    row = profile.query_features("transcriptome", ["ABUW_0001"])["features"][0]
    assert row["source_id"] == "omics:AB5075-AZI000:gene:ABUW_0001"
    assert row["expression_value"] == 0.0 and row["input_role"] == "strain_reference"


@pytest.mark.parametrize("tool,args", [
    ("search_mechanistic_evidence", {"query": "testGene"}),
    ("query_mechanistic_evidence", {"record_ids": ["TEST:reference:GENE_1"]}),
])
def test_runtime_mechanistic_queries_are_exact_strain_without_species_or_model_override(tmp_path, tool, args):
    from tests.llm_prediction.test_mechanistic_tools import catalog

    _strain_references(tmp_path)
    profile = load_profile(REFERENCE_ID, tmp_path).select_modalities(["genome"])
    result = workflow._execute(tool, args, profile, {"canonical_smiles": "CCO"}, "candidate", catalog(tmp_path))
    assert result["requested_scope"]["strain"] == "AB5075"
    assert result["prediction_scope"] == "strain_reference"
    assert all(row["species"]["strain"] == "AB5075" for row in result["records"])
    assert result["strain_namespace"] == "author_strain_name"
    with pytest.raises(ValueError, match="unexpected_tool_arguments"):
        workflow._execute(tool, args | {"strain": None}, profile, {"canonical_smiles": "CCO"}, "candidate")


def test_explicit_mutant_genotype_does_not_retrieve_unverified_parent_catalog(tmp_path):
    manifest = _strain_references(tmp_path)
    manifest["genotype"] = "delta-relA"
    (tmp_path / REFERENCE_ID / "manifest.json").write_text(json.dumps(manifest))
    for name in NAMES:
        path = tmp_path / f"source-{name}" / "manifest.json"
        source = json.loads(path.read_text())
        source["genotype"] = source["modalities"][name]["genotype"] = "delta-relA"
        path.write_text(json.dumps(source))
    profile = load_profile(REFERENCE_ID, tmp_path)
    result = workflow._execute("search_mechanistic_evidence", {"query": "relA"}, profile,
                               {"canonical_smiles": "CCO"}, "candidate")
    assert result["status"] == "unavailable" and result["records"] == []
    assert result["reason"] == "strain_genotype_scope_unverified"


def test_study_local_names_do_not_retrieve_same_named_strains_from_other_contexts(tmp_path):
    from tests.llm_prediction.test_mechanistic_tools import catalog

    manifest = _strain_references(tmp_path)
    manifest["strain_namespace"] = "study:software-fixture-project"
    (tmp_path / REFERENCE_ID / "manifest.json").write_text(json.dumps(manifest))
    profile = load_profile(REFERENCE_ID, tmp_path)
    result = workflow._execute("search_mechanistic_evidence", {"query": "testGene"}, profile,
                               {"canonical_smiles": "CCO"}, "candidate", catalog(tmp_path))
    assert result["status"] == "unavailable" and result["records"] == []
    assert result["reason"] == "strain_namespace_scope_unverified"


def test_public_report_preserves_exact_strain_and_independent_source_conditions(tmp_path):
    from praxis_virtualcell.llm_prediction.report import render_report

    _strain_references(tmp_path)
    profile = load_profile(REFERENCE_ID, tmp_path).select_modalities(["genome", "proteome"])
    report = render_report({"candidate": {"id": "candidate", "smiles": "CCO"}, "profile": profile.overview(),
                            "assessment": empty_assessment("同菌株参考，非配对样本。"), "status": "completed",
                            "evidence_validation": {"status": "passed"}, "execution_trace": {"model": "offline-test"}})
    assert "具体菌株 AB5075" in report and "author_strain_name" in report
    assert "不表示同一样本" in report and "缺失模态不借用其他菌株" in report
    assert "medium-genome" in report and "medium-proteome" in report
    assert "source-transcriptome" not in report and "物种参考背景" not in report
