"""Auditable tool templates preserve observations and remain unapproved."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from praxis_virtualcell.datasets.seeds import SEED_TOOLS, prepare_seed_queue
from praxis_virtualcell.llm_prediction.evidence import _reference
from praxis_virtualcell.llm_prediction.schemas import EvidenceReference
from praxis_virtualcell.llm_prediction.workflow import MULTIOMICS_TOOLS


def _profile(root: Path, profile_id="fixture-profile", modalities=("genome", "transcriptome", "proteome"),
             *, feature_id=None, product=None):
    directory = root / profile_id
    directory.mkdir(parents=True)
    species = {"scientific_name": "Synthetic fixture organism", "taxonomy_id": "NCBITaxon:0"}
    condition = {"condition_id": "fixture-untreated", "role": "pre_treatment_baseline", "medium": None,
                 "time_h": None, "temperature_c": None, "growth_phase": None}
    paired = "fixture-pair" if len(modalities) > 1 else None
    manifest = {"schema_version": "praxis.organism-profile.v2", "profile_id": profile_id,
                "species": species, "strain": "fixture-strain", "genotype": None, "condition": condition,
                "pairing": {"pairing_id": paired, "relation": "same_sample", "evidence": "Synthetic software fixture"}
                if paired else None, "modalities": {}}
    for modality in modalities:
        measurement = {"genome": {"presence": True, "copy_number": None, "variant": None},
                       "transcriptome": {"expression_value": 0.0}, "proteome": {"abundance_value": None}}[modality]
        records = [{"feature_id": feature_id or f"native-{modality}-feature",
                    "gene_id": f"native-{modality}-gene", "protein_id": f"native-{modality}-protein",
                    "gene_symbol": None, "product": product or f"{modality}-private-protein-annotation",
                    "source_locator": {"path": f"{modality}-private-native.csv", "row": 2,
                                       "accession": None, "record_id": None}, **measurement}]
        path = directory / f"{modality}.json"
        path.write_text(json.dumps(records))
        manifest["modalities"][modality] = {
            "species": species, "strain": manifest["strain"], "genotype": None, "condition": condition,
            "sample_id": "fixture-sample", "pairing_id": paired,
            "assay": {"genome": "assembly_annotation", "transcriptome": "RNA_seq", "proteome": "SWATH_MS"}[modality],
            "feature_namespace": f"{modality}-private-native-namespace", "unit": f"{modality}-declared-unit",
            "scale": "native", "value_semantics": f"{modality}-private-observed-value",
            "observation_unit": "measured_baseline_sample",
            "features": {"path": path.name, "format": "json", "size_bytes": path.stat().st_size,
                         "sha256": hashlib.sha256(path.read_bytes()).hexdigest()},
            "provenance": {"study_id": f"{modality}-private-study", "source_samples": ["fixture-sample"],
                           "citation": "Synthetic fixture, no biological measurements", "terms": {
                               "usage": "software_test", "redistribution_approved": False, "license_status": "fixture"},
                           "input_role": "measured_pre_treatment"},
        }
    (directory / "manifest.json").write_text(json.dumps(manifest))
    return directory


def _read(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def _validate_protocol(record):
    seen, pending = set(), set()
    tool_records = []
    names = {tool["function"]["name"] for tool in record["tools"]}
    assert record["messages"][0]["role"] == "system"
    assert record["messages"][1]["role"] == "user"
    for message in record["messages"]:
        if message.get("tool_calls"):
            assert not pending
            assert message["role"] == "assistant"
            for call in message["tool_calls"]:
                assert call["id"] not in seen
                assert call["type"] == "function"
                assert call["function"]["name"] in names
                assert isinstance(json.loads(call["function"]["arguments"]), dict)
                pending.add(call["id"])
                seen.add(call["id"])
        elif message["role"] == "tool":
            assert message["tool_call_id"] in pending
            pending.remove(message["tool_call_id"])
            data = json.loads(message["content"])
            assert data["tool_call_id"] == message["tool_call_id"]
            assert data["ok"] is True
            tool_records.append(data)
        else:
            assert not pending
    assert not pending
    assert record["messages"][-1]["role"] == "assistant"
    assert json.loads(record["messages"][-1]["content"]) == record["public_observations"]
    assert tool_records == record["execution_trace"]["tool_calls"]
    assert {call["name"] for call in tool_records} == {"overview", "search_features", "query_features"}


def test_single_modality_views_keep_exact_source_citations_and_protocol(tmp_path):
    root, output = tmp_path / "profiles", tmp_path / "queue"
    _profile(root)
    readiness = prepare_seed_queue(root, output)
    records = _read(output / "seeds.jsonl")
    assert readiness["record_count"] == 3
    assert readiness["represented_profile_count"] == 1
    assert readiness["independent_biological_sample_count"] is None
    assert readiness["model_calls"] == readiness["endpoint_lookups"] == 0
    assert readiness["source_assets_copied"] is False
    for record in records:
        _validate_protocol(record)
        modality = record["source"]["modality"]
        calls = {call["tool_call_id"]: call for call in record["execution_trace"]["tool_calls"]}
        for observation in record["public_observations"]["observations"]:
            actual, _ = _reference(EvidenceReference.model_validate(observation["evidence_ref"]), calls)
            assert actual == observation["value"]
            assert observation["evidence_ref"]["source_id"] in record["source"]["source_ids"]
        overview = next(call["data"] for call in calls.values() if call["name"] == "overview")
        assert overview["selected_modalities"] == [modality]
        assert set(overview["modalities"]) == {modality}
        for name in {"genome", "transcriptome", "proteome"} - {modality}:
            for marker in (f"{name}-private-native", f"{name}-private-protein", f"{name}-private-study",
                           f"{name}-declared-unit", f"{name}-private-observed"):
                assert marker not in json.dumps(record)
        for call in calls.values():
            if call["name"] != "overview":
                assert call["arguments"]["modality"] == modality
        assert record["source"]["source_sample_ids"] == ["fixture-sample"]
        assert record["source"]["sample_id"] == "fixture-sample"
        assert record["source"]["group_ids"]["source_sample"] == [f"study:{modality}-private-study|sample:fixture-sample"]
        assert record["source"]["representative_feature_id"] == f"native-{modality}-feature"


def test_nulls_true_and_measured_zero_remain_distinct(tmp_path):
    _profile(tmp_path / "profiles")
    prepare_seed_queue(tmp_path / "profiles", tmp_path / "queue")
    records = {record["source"]["modality"]: record for record in _read(tmp_path / "queue/seeds.jsonl")}
    def values(name):
        return {item["field"]: item["value"] for item in records[name]["public_observations"]["observations"]}
    assert values("genome")["presence"] is True
    assert values("genome")["copy_number"] is None
    assert values("genome")["variant"] is None
    assert values("proteome")["abundance_value"] is None
    assert values("transcriptome")["expression_value"] == 0.0
    for name in records:
        for field in ("medium", "time_h", "temperature_c", "growth_phase", "genotype"):
            assert values(name)[field] is None


def test_templates_are_never_labels_or_approved_training(tmp_path):
    directory = _profile(tmp_path / "profiles", modalities=("genome",))
    (directory / "mic.json").write_text('{"mic":12345,"label_source_ids":["FORBIDDEN_ENDPOINT_LABEL"]}')
    (directory / "y_pred.json").write_text('{"prediction":67890,"secret":"FORBIDDEN_OLD_MODEL"}')
    prepare_seed_queue(tmp_path / "profiles", tmp_path / "queue")
    record = _read(tmp_path / "queue/seeds.jsonl")[0]
    assert record["origin"] == "source_grounded_template"
    assert record["review_status"] == "needs_review"
    assert record["trainable"] is record["prediction_is_gold"] is False
    assert record["supervision_scope"] == "tool_use_and_public_observations_only"
    assert record["public_observations"]["mic"] == {
        "status": "unknown", "value": None, "unit": None,
        "reason": "No drug activity endpoint is present in this tool-only observation task."}
    encoded = json.dumps(record)
    for forbidden in ("FORBIDDEN_ENDPOINT_LABEL", "FORBIDDEN_OLD_MODEL", "12345", "67890",
                      "label_source_ids", "approved", "gold_assessment", "supporting_evidence", "mic_estimate"):
        # The word approved occurs in the safety instructions, not an approval field.
        if forbidden != "approved":
            assert forbidden not in encoded
    assert "approved" not in record
    assert "model" not in record
    assert "reasoning_content" not in encoded
    assert "Protein IDs or reference translation annotations are not measured proteome abundance." in record["public_observations"]["limitations"]


def test_tool_definitions_reuse_the_inference_protocol():
    assert SEED_TOOLS == [tool for tool in MULTIOMICS_TOOLS
                          if tool["function"]["name"] in {"overview", "search_features", "query_features"}]


def test_limit_is_a_ceiling_and_not_duplicate_filling(tmp_path):
    _profile(tmp_path / "profiles")
    readiness = prepare_seed_queue(tmp_path / "profiles", tmp_path / "queue", limit=2)
    records = _read(tmp_path / "queue/seeds.jsonl")
    assert len(records) == len({record["record_id"] for record in records}) == 2
    assert readiness["candidate_profile_modality_views"] == 3
    assert readiness["skip_reasons"] == {"queue_limit": 1}
    assert readiness["trainable_record_count"] == readiness["gold_prediction_count"] == 0
    readiness = prepare_seed_queue(tmp_path / "profiles", tmp_path / "queue2", limit=80)
    assert readiness["record_count"] == 3


@pytest.mark.parametrize("limit", [True, 0, 101, 1.5, "80", None])
def test_invalid_limits_are_rejected(tmp_path, limit):
    with pytest.raises(ValueError, match="limit"):
        prepare_seed_queue(tmp_path, tmp_path / "queue", limit)


def test_nonempty_output_refuses_overwrite_before_source_loading(tmp_path, monkeypatch):
    root, output = tmp_path / "profiles", tmp_path / "queue"
    _profile(root)
    output.mkdir()
    sentinel = output / "existing.jsonl"
    sentinel.write_text("KEEP")
    def forbidden(*args, **kwargs):
        raise AssertionError("Must refuse before loading source profiles")
    monkeypatch.setattr("praxis_virtualcell.datasets.seeds.load_profile", forbidden)
    with pytest.raises(FileExistsError, match="nonempty"):
        prepare_seed_queue(root, output)
    assert sentinel.read_text() == "KEEP"


def test_output_must_not_be_inside_source_assets(tmp_path):
    root = tmp_path / "profiles"
    _profile(root)
    with pytest.raises(ValueError, match="separate"):
        prepare_seed_queue(root, root / "new_queue")
    assert not (root / "new_queue").exists()


def test_empty_source_is_not_filled_with_invented_demonstrations(tmp_path):
    root = tmp_path / "profiles"
    root.mkdir()
    readiness = prepare_seed_queue(root, tmp_path / "queue")
    assert readiness["record_count"] == 0
    assert _read(tmp_path / "queue/seeds.jsonl") == []


def test_invalid_profile_is_reported_without_source_error_text(tmp_path):
    root = tmp_path / "profiles"
    directory = root / "broken"
    directory.mkdir(parents=True)
    (directory / "manifest.json").write_text("PRIVATE_NOT_JSON")
    readiness = prepare_seed_queue(root, tmp_path / "queue")
    assert readiness["record_count"] == 0
    skipped = _read(tmp_path / "queue/skipped.jsonl")
    assert skipped[0]["reason"] == "profile_not_loadable"
    assert "PRIVATE_NOT_JSON" not in json.dumps(skipped)


def test_failed_short_search_is_retained_then_real_native_id_is_queried(tmp_path):
    directory = _profile(tmp_path / "profiles", modalities=("genome",), feature_id="locus-a", product="annotation")
    manifest_path = directory / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    path = directory / "genome.json"
    rows = json.loads(path.read_text())
    rows[0]["gene_id"] = rows[0]["protein_id"] = None
    path.write_text(json.dumps(rows))
    manifest["modalities"]["genome"]["features"].update(size_bytes=path.stat().st_size,
        sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    manifest_path.write_text(json.dumps(manifest))
    prepare_seed_queue(tmp_path / "profiles", tmp_path / "queue")
    record = _read(tmp_path / "queue/seeds.jsonl")[0]
    _validate_protocol(record)
    searches = [call for call in record["execution_trace"]["tool_calls"] if call["name"] == "search_features"]
    assert searches[0]["data"]["features"] == []
    assert searches[-1]["data"]["features"][0]["feature_id"] == "locus-a"
    assert record["execution_trace"]["tool_calls"][-1]["arguments"]["feature_ids"] == ["locus-a"]


def test_nonmeasurement_proteome_is_not_admitted_as_a_seed(tmp_path):
    directory = _profile(tmp_path / "profiles", modalities=("proteome",))
    manifest_path = directory / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["modalities"]["proteome"]["assay"] = "assembly_annotation"
    manifest_path.write_text(json.dumps(manifest))
    readiness = prepare_seed_queue(tmp_path / "profiles", tmp_path / "queue")
    assert readiness["record_count"] == 0
    assert readiness["skip_reasons"] == {"profile_not_loadable": 1}


def test_overview_source_identity_is_required_not_fabricated(tmp_path, monkeypatch):
    root = tmp_path / "profiles"
    _profile(root, modalities=("genome",))
    from praxis_virtualcell.omics import load_profile
    real = load_profile("fixture-profile", root)
    class BadSource:
        profile_id = real.profile_id
        def select_modalities(self, modalities):
            return self
        def overview(self):
            data = real.overview()
            data["modalities"]["genome"].pop("source_id")
            return data
        def search_features(self, **kwargs):
            return real.search_features(**kwargs)
        def query_features(self, **kwargs):
            return real.query_features(**kwargs)
    monkeypatch.setattr("praxis_virtualcell.datasets.seeds.load_profile", lambda *args, **kwargs: BadSource())
    readiness = prepare_seed_queue(root, tmp_path / "queue")
    assert readiness["record_count"] == 0
    assert readiness["skip_reasons"] == {"source_tool_or_reference_invalid": 1}


def test_real_frozen_v1_mean_remains_rna_with_all_source_members(tmp_path):
    # This local-data check is useful in the repository and optional in a code-only install.
    root = Path(__file__).resolve().parents[2] / "data/organisms"
    if not (root / "AB5075-AZI000/manifest.json").is_file():
        pytest.skip("Frozen source profile is not included in this code-only installation")
    from praxis_virtualcell.omics import load_profile
    from praxis_virtualcell.datasets.seeds import _build_seed
    record = _build_seed(load_profile("AB5075-AZI000", root), "transcriptome")
    _validate_protocol(record)
    assert record["source"]["source_sample_ids"] == ["Abaum_0017", "Abaum_0023"]
    assert record["source"]["observation_unit"] == "historical_condition_mean"
    assert record["source"]["sample_id"] is None
    assert len(record["source"]["group_ids"]["source_sample"]) == 2
    observations = record["public_observations"]["observations"]
    values = {item["field"]: item["value"] for item in observations}
    assert values["time_h"] is values["temperature_c"] is None
    assert values["unit"] == "author_log2_TPM_QC"
    assert values["expression_value"] == 5.845364570617676
    assert values["sequence_role"].startswith("Reference annotation/translation")
    assert "abundance_value" not in values
    assert record["public_observations"]["mic"]["value"] is None
    assert any("individual measurements cannot be reconstructed" in text
               for text in record["public_observations"]["limitations"])
    calls = {call["tool_call_id"]: call for call in record["execution_trace"]["tool_calls"]}
    for observation in observations:
        _reference(EvidenceReference.model_validate(observation["evidence_ref"]), calls)
