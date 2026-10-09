"""Reference collections retain separate source identities and exact citations."""
from __future__ import annotations

import itertools
import json

import pytest

from praxis_virtualcell.llm_prediction import workflow
from praxis_virtualcell.llm_prediction.evidence import _reference
from praxis_virtualcell.llm_prediction.schemas import EvidenceReference
from praxis_virtualcell.omics import ProfileError, list_profiles, load_profile
from tests.omics.test_multiomics_profiles import PROFILE_ID, _build


NAMES = ("genome", "transcriptome", "proteome")
SPECIES = {"scientific_name": "Acinetobacter baumannii", "taxonomy_id": "NCBITaxon:470"}
REFERENCE_ID = "synthetic-species-reference"


def _references(root):
    for index, name in enumerate(NAMES):
        manifest = _build(root, [name])
        profile_id = f"source-{name}"
        manifest.update(profile_id=profile_id, species=SPECIES, strain=f"strain-{name}")
        manifest["condition"].update(condition_id=f"condition-{name}", medium=f"medium-{name}", time_h=float(index))
        item = manifest["modalities"][name]
        item.update(species=SPECIES, strain=f"strain-{name}", condition=manifest["condition"], sample_id=f"sample-{name}")
        item["provenance"]["source_samples"] = [f"sample-{name}"]
        source = root / PROFILE_ID
        (source / "manifest.json").write_text(json.dumps(manifest))
        source.rename(root / profile_id)
    manifest = {
        "schema_version": "praxis.species-reference.v1", "profile_id": REFERENCE_ID,
        "species": SPECIES, "reference_profiles": {name: f"source-{name}" for name in NAMES},
        "input_role": "species_reference", "relation": "species_level_reference",
        "prediction_scope": "species_reference", "selection_reasons": {name: f"Synthetic {name} selection" for name in NAMES},
    }
    directory = root / REFERENCE_ID
    directory.mkdir()
    (directory / "manifest.json").write_text(json.dumps(manifest))
    return manifest


def _update(root, manifest):
    (root / REFERENCE_ID / "manifest.json").write_text(json.dumps(manifest))


@pytest.mark.parametrize("selected", [list(combo) for size in range(1, 4) for combo in itertools.combinations(NAMES, size)])
def test_reference_selection_retains_cross_strain_condition_identity_and_isolation(tmp_path, selected):
    _references(tmp_path)
    profile = load_profile(REFERENCE_ID, tmp_path).select_modalities(selected)
    overview = profile.overview()
    assert overview["strain"] is None and overview["pairing"] is None
    assert overview["input_role"] == overview["prediction_scope"] == "species_reference"
    assert overview["relation"] == "species_level_reference"
    assert list(overview["modalities"]) == selected
    assert overview["feature_count"] == len(selected) * 2
    for name in selected:
        native = load_profile(f"source-{name}", tmp_path).select_modalities([name]).overview()
        assert overview["modalities"][name] == native
        row = profile.query_features(name, [f"{name}-feature-0"])["features"][0]
        assert row["source_id"] == f"omics:source-{name}:{name}:feature:{name}-feature-0"
        assert row["source_strain"] == f"strain-{name}"
        assert row["source_condition"]["medium"] == f"medium-{name}"
        assert row["input_role"] == "species_reference"
    assert [row["modality"] for row in profile.query_genes(["native-gene-0"])["genes"]] == selected
    assert profile.search_annotations("private-product")["match_count"] == len(selected) * 2
    payload = json.dumps({"overview": overview, "rows": profile.search_annotations("private")})
    for name in set(NAMES) - set(selected):
        assert f"source-{name}" not in payload
        assert f"{name}-private" not in payload
        assert f"medium-{name}" not in payload
        with pytest.raises(ProfileError, match="unselected"):
            profile.query_features(name, [f"{name}-feature-0"])


def test_reference_listing_and_source_pointers_require_no_copied_data(tmp_path):
    _references(tmp_path)
    entry = next(item for item in list_profiles(tmp_path) if item["profile_id"] == REFERENCE_ID)
    assert entry["strain"] is None and entry["prediction_scope"] == "species_reference"
    assert "物种参考" in entry["label"]
    assert [path.name for path in (tmp_path / REFERENCE_ID).iterdir()] == ["manifest.json"]


def test_author_condition_summary_is_preserved_without_claiming_single_sample(tmp_path):
    _references(tmp_path)
    path = tmp_path / "source-proteome" / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["modalities"]["proteome"]["observation_unit"] = "author_condition_summary"
    path.write_text(json.dumps(manifest))
    overview = load_profile(REFERENCE_ID, tmp_path).select_modalities(["proteome"]).overview()
    assert overview["modalities"]["proteome"]["modalities"]["proteome"]["observation_unit"] == "author_condition_summary"
    assert overview["pairing"] is None and overview["strain"] is None


def test_historical_v1_reference_retains_aggregation_and_native_source_ids(tiny_profile_root):
    native = load_profile(data_root=tiny_profile_root)
    manifest = {
        "schema_version": "praxis.species-reference.v1", "profile_id": REFERENCE_ID,
        "species": native.overview()["species"], "reference_profiles": {"transcriptome": native.profile_id},
        "input_role": "species_reference", "relation": "species_level_reference", "prediction_scope": "species_reference",
    }
    root = tiny_profile_root / REFERENCE_ID
    root.mkdir()
    (root / "manifest.json").write_text(json.dumps(manifest))
    profile = load_profile(REFERENCE_ID, tiny_profile_root)
    overview = profile.overview()["modalities"]["transcriptome"]
    assert overview == native.overview()
    assert overview["observation_unit"] == "historical_condition_mean"
    result = profile.query_features("transcriptome", ["ABUW_0001"])
    row = result["features"][0]
    assert row["source_id"] == "omics:AB5075-AZI000:gene:ABUW_0001"
    assert row["source_strain"] == "AB5075" and row["expression_value"] == 0.0
    assert "mic" not in row and "treated" not in row and "delta" not in row
    call = {"tool_call_id": "native-v1", "name": "query_features", "ok": True, "data": result}
    assert workflow._citation_examples(call)


@pytest.mark.parametrize("mutation", [
    lambda m: m.update(mic=1.0),
    lambda m: m.update(strain="pretend-matched-strain"),
    lambda m: m.update(relation="matched_samples"),
    lambda m: m.update(reference_profiles={"RNA": "source-transcriptome"}),
    lambda m: m["reference_profiles"].update(genome=["source-genome", "source-proteome"]),
    lambda m: m["reference_profiles"].update(genome="../source-genome"),
    lambda m: m["reference_profiles"].update(genome=REFERENCE_ID),
    lambda m: m["reference_profiles"].update(genome="source-proteome"),
    lambda m: m["selection_reasons"].update(unknown="No source"),
])
def test_invalid_reference_and_mic_fields_rejected(tmp_path, mutation):
    manifest = _references(tmp_path)
    mutation(manifest)
    _update(tmp_path, manifest)
    with pytest.raises(ProfileError):
        load_profile(REFERENCE_ID, tmp_path)


def test_cross_species_reference_rejected(tmp_path):
    manifest = _references(tmp_path)
    manifest["species"] = {"scientific_name": "Escherichia coli", "taxonomy_id": "NCBITaxon:562"}
    _update(tmp_path, manifest)
    with pytest.raises(ProfileError, match="species differs"):
        load_profile(REFERENCE_ID, tmp_path)


def test_native_source_mic_and_nested_references_rejected(tmp_path):
    manifest = _references(tmp_path)
    native_path = tmp_path / "source-genome" / "manifest.json"
    native = json.loads(native_path.read_text())
    native["modalities"]["genome"]["provenance"]["mic"] = 2.0
    native_path.write_text(json.dumps(native))
    with pytest.raises(ProfileError, match="Invalid organism"):
        load_profile(REFERENCE_ID, tmp_path)
    nested = tmp_path / "nested-reference"
    nested.mkdir()
    (nested / "manifest.json").write_text(json.dumps(manifest | {"profile_id": "nested-reference"}))
    manifest["reference_profiles"]["genome"] = "nested-reference"
    _update(tmp_path, manifest)
    with pytest.raises(ProfileError, match="native organism profiles"):
        load_profile(REFERENCE_ID, tmp_path)


def test_exact_citations_keep_original_sources_and_reject_invented_collection_feature_source(tmp_path):
    _references(tmp_path)
    profile = load_profile(REFERENCE_ID, tmp_path)
    data = profile.query_features("transcriptome", ["transcriptome-feature-0"])
    call = {"tool_call_id": "reference-rna", "ok": True, "name": "query_features", "data": data}
    hints = workflow._citation_examples(call)
    ref = EvidenceReference(**next(item for item in hints if item["pointer"] == "/features/0/expression_value"))
    actual, row = _reference(ref, {call["tool_call_id"]: call})
    assert actual == 0.0 and row["source_profile_id"] == "source-transcriptome"
    forged = ref.model_copy(update={"source_id": f"omics:{REFERENCE_ID}:transcriptome:feature:transcriptome-feature-0"})
    with pytest.raises(ValueError, match="source_id_does_not_match_tool"):
        _reference(forged, {call["tool_call_id"]: call})
    overview_call = {"tool_call_id": "overview", "ok": True, "name": "overview", "data": profile.overview()}
    assert any(item["pointer"] == "/prediction_scope" for item in workflow._citation_examples(overview_call))


@pytest.mark.parametrize("tool,args", [
    ("search_mechanistic_evidence", {"query": "testGene"}),
    ("query_mechanistic_evidence", {"record_ids": ["TEST:reference:GENE_1"]}),
])
def test_species_mechanistic_query_preserves_record_strain_and_scope(tmp_path, tool, args):
    from tests.llm_prediction.test_mechanistic_tools import catalog

    _references(tmp_path)
    profile = load_profile(REFERENCE_ID, tmp_path).select_modalities(["genome"])
    path = catalog(tmp_path)
    result = workflow._execute(tool, args, profile, {"canonical_smiles": "CCO"}, "candidate", path)
    assert result["status"] == "available"
    assert result["requested_scope"]["strain"] is None
    assert result["records"][0]["species"]["strain"] == "AB5075"
    assert result["prediction_scope"] == "species_reference"
    assert result["reference_source_strains"] == ["strain-genome"]
    assert any("every strain" in text for text in result["limitations"])
    assert "source-transcriptome" not in json.dumps(result)
    with pytest.raises(ValueError, match="unexpected_tool_arguments"):
        workflow._execute(tool, args | {"strain": "model-override"}, profile, {"canonical_smiles": "CCO"}, "candidate", path)


def test_report_names_species_reference_and_only_selected_source_strains(tmp_path):
    from praxis_virtualcell.llm_prediction.report import render_report
    from praxis_virtualcell.llm_prediction.schemas import empty_assessment

    _references(tmp_path)
    profile = load_profile(REFERENCE_ID, tmp_path).select_modalities(["genome", "proteome"])
    result = {"candidate": {"id": "candidate", "smiles": "CCO"}, "profile": profile.overview(),
              "assessment": empty_assessment("参考组学仅用于物种背景。"), "status": "completed",
              "evidence_validation": {"status": "passed"}, "execution_trace": {"model": "offline-test"}}
    report = render_report(result)
    assert "物种参考档案" in report and "不表示同一样本" in report
    assert "strain-genome" in report and "strain-proteome" in report
    assert "medium-genome" in report and "medium-proteome" in report
    assert "strain-transcriptome" not in report and "菌株档案" not in report and "/ None" not in report


def test_report_preserves_native_source_caveats_when_assessment_omits_gaps(tmp_path):
    from praxis_virtualcell.llm_prediction.report import render_report
    from praxis_virtualcell.llm_prediction.schemas import empty_assessment

    _references(tmp_path)
    for name in NAMES:
        path = tmp_path / f"source-{name}" / "manifest.json"
        manifest = json.loads(path.read_text())
        native = manifest["modalities"][name]
        native["provenance"]["citation"] = f"https://example.org/author/{name}; synthetic author source"
        if name == "proteome":
            native["value_semantics"] = "Control identity inferred; untreated identity and LFQ scale are unconfirmed."
            native["observation_unit"] = "author_condition_summary"
            native["scale"] = "source_native_unconfirmed"
            manifest["condition"]["medium"] = native["condition"]["medium"] = None
            manifest["condition"]["time_h"] = native["condition"]["time_h"] = None
        path.write_text(json.dumps(manifest))
    profile = load_profile(REFERENCE_ID, tmp_path).select_modalities(["genome", "proteome"])
    assessment = empty_assessment("模型未主动讨论来源限制。")
    assessment["gaps"] = []
    result = {"candidate": {"id": "candidate", "smiles": "CCO"}, "profile": profile.overview(),
              "assessment": assessment, "status": "completed",
              "evidence_validation": {"status": "passed"}, "execution_trace": {"model": "offline-test"}}
    report = render_report(result)
    assert assessment["gaps"] == []
    assert "Control identity inferred; untreated identity and LFQ scale are unconfirmed." in report
    assert "观察单位：author_condition_summary" in report
    assert "数值单位：proteome-declared-unit；尺度：source_native_unconfirmed" in report
    assert "培养基 未知" in report and "未知来源条件 / 字段：medium、time_h" in report
    assert "[作者来源](<https://example.org/author/proteome>)" in report
    assert "[作者来源](<https://example.org/author/genome>)" in report
    assert "https://example.org/author/transcriptome" not in report
    assert "synthetic transcriptome test values" not in report
