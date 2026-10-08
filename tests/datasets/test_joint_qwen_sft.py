from copy import deepcopy
import json
from pathlib import Path

import pytest

from praxis_virtualcell.datasets import strain_supervision
from praxis_virtualcell.datasets.joint_qwen_sft import (
    TARGET_CONTRACT, prepare_joint_qwen_sft, validate_joint_qwen_sft,
)
from praxis_virtualcell.datasets.joint_supervision import prepare_joint_supervision
from praxis_virtualcell.datasets.literature import parse_jats
from praxis_virtualcell.datasets.qwen_sft import prepare_qwen_sft
from praxis_virtualcell.datasets.species_registry import _digest
from praxis_virtualcell.datasets.strain_supervision import prepare_strain_supervision
from tests.datasets.test_qwen_sft import fixture_components


def _write(path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


@pytest.fixture
def joint_source(tmp_path, monkeypatch):
    initial, cases = fixture_components(tmp_path, monkeypatch)
    dataset_summary = Path(json.loads((initial / "summary.json").read_text())["dataset_summary"])
    for case in cases:
        if case["split"] == "train":
            case["strain"]["identity_basis"] = "exact_source_reference_label"
            case.update(profile_id="A-STRAIN", reference_profiles={
                "genome": {"manifest_path": str(tmp_path / "profiles/A-STRAIN/manifest.json")}})
    _write(dataset_summary.parent / "cases.jsonl", cases)
    tools = [{"role": "assistant", "content": None, "tool_calls": [{"id": "observed_1", "type": "function",
              "function": {"name": "overview", "arguments": "{}"}}]},
             {"role": "tool", "tool_call_id": "observed_1", "content": json.dumps({"tool_call_id": "observed_1",
              "name": "overview", "arguments": {}, "ok": True, "data": {"profile_id": "A-STRAIN",
              "species": {"scientific_name": "Acinetobacter baumannii", "taxonomy_id": "NCBITaxon:470"},
              "strain": "A", "modality": "genome",
              "gene_symbol": "gyrB", "feature_count": 1, "native_source": {
                  "path": "/Volumes/T7/reference_genome.csv", "row": 3}}})}]
    view = {"profile_id": "A-STRAIN", "messages": tools, "tool_calls": ["observed_1"], "evidence_refs": []}
    monkeypatch.setattr(strain_supervision, "_view", lambda *_: deepcopy(view))
    source = tmp_path / "joint_components"
    prepare_strain_supervision(dataset_summary, source)
    components = [json.loads(line) for line in (source / "mic_sft.jsonl").read_text().splitlines()]
    component = next(row for row in components if row["source_case_count"] == 2)
    other = next(row for row in components if row["record_id"] != component["record_id"])

    literature = tmp_path / "literature"
    literature.mkdir()
    article = literature / "article.xml"
    article.write_text('<article><front><article-meta><article-id pub-id-type="doi">10.1234/paper-a</article-id>'
                       '</article-meta></front><body><p>Drug A was tested against strain A.</p>'
                       '<p>Drug A may affect fatty acid metabolism; no protein target was identified.</p></body></article>')
    asset = {"file": str(article), "sha256": _digest(article),
             "url": "https://www.ebi.ac.uk/europepmc/webservices/rest/PMC1/fullTextXML"}
    passages = parse_jats(article.read_bytes(), paper_id="paper:fixture", source=asset)["passages"]
    _write(literature / "papers.jsonl", [{"doi": "10.1234/paper-a", "paper_id": "paper:fixture",
                                         "case_ids": component["case_ids"], "status": "open_fulltext_parsed",
                                         "article": asset}])
    _write(literature / "passages.jsonl", passages)
    mapping = tmp_path / "mapping.json"
    mapping.write_text(json.dumps({"compound_records": [{"compound_key": "Drug A", "molecule_chembl_id": "CHEMBL1",
                                                         "document_chembl_id": "paper-a"}]}))
    def quote(passage):
        return {"passage_id": passage["passage_id"], "start": 0, "end": len(passage["text"]), "text": passage["text"]}
    annotation = {"component_record_id": component["record_id"], "case_ids": component["case_ids"],
                  "doi": "10.1234/paper-a", "compound_paper_name": "Drug A",
                  "compound_mapping": {"file": str(mapping), "sha256": _digest(mapping), "pointer": "/compound_records/0"},
                  "compound_binding_basis": "Exact canonical source molecule and document.",
                  "strain_binding_basis": "Paper explicitly identifies strain A.", "binding_quotes": [quote(passages[0])],
                  "claims": [{"statement": "Possible fatty acid metabolism effect; molecular target unknown.",
                              "evidence_grade": "author_proposed", "experiment_type": "author_hypothesis",
                              "target_names": [], "quotes": [quote(passages[1])]}],
                  "reviewer": "agent-source-review-fixture", "review_status": "source_reviewed",
                  "claim_scope": "exact_compound_general_mechanism"}
    reviews = literature / "source_reviews.json"
    reviews.write_text(json.dumps({"schema_version": "praxis.literature-reviews.v1", "annotations": [annotation]}))
    joint = tmp_path / "joint"
    prepare_joint_supervision(source, literature, reviews, joint)
    return source, joint, component, other, passages, reviews, mapping


def test_joint_replaces_component_preserves_MIC_and_isolates_quotes_paths_and_answers(joint_source, tmp_path):
    source, joint, component, _, passages, _, _ = joint_source
    base = tmp_path / "base"
    prepare_qwen_sft(source, base)
    output = tmp_path / "joint_qwen"
    report = prepare_joint_qwen_sft(source, joint, output, base_qwen_dir=base)
    assert report["training_record_count"] == 2
    assert report["training_MIC_measurement_count"] == 3
    assert report["mechanism_training_records"] == 1
    assert report["duplicate_MIC_components"] == 0
    assert report["human_gold_mechanism_records"] == 0
    rows = [json.loads(line) for line in (output / "train.jsonl").read_text().splitlines()]
    record = next(row for row in rows if row["target_contract"] == TARGET_CONTRACT)
    assert record["source_record_id"] == component["record_id"]
    assert len({row["source_record_id"] for row in rows}) == len(rows)
    target = json.loads(record["messages"][-1]["content"])
    assert target["observations"] == json.loads(component["messages"][-1]["content"])["observations"]
    claim = target["mechanism_claims"][0]
    assert claim["evidence_grade"] == "author_proposed"
    assert claim["target_names"] == []
    assert claim["scope"] == "exact_compound_general_mechanism"
    assert claim["sources"] == [{"doi": "10.1234/paper-a", "locator_id": passages[1]["passage_id"]}]
    public = json.dumps([row["messages"] for row in rows])
    assert passages[1]["text"] not in public
    assert "/Volumes/T7/" not in public
    assert 'asset:' in public and "gyrB" in public
    assert "Possible fatty acid" not in json.dumps(record["messages"][:-1])
    assert json.loads((output / "joint.train.jsonl").read_text()) == record
    private = [json.loads(line) for line in (output / "source_refs.jsonl").read_text().splitlines()]
    reference = next(row for row in private if row["record_id"] == record["record_id"])
    assert reference["human_gold"] is False
    assert passages[1]["text"] in json.dumps(reference)
    assert "/Volumes/T7/reference_genome.csv" in reference["public_asset_paths"].values()
    for split in ("validation", "test"):
        old = json.loads((base / f"{split}.inputs.jsonl").read_text())
        new = json.loads((output / f"{split}.inputs.jsonl").read_text())
        assert old == new
        assert "777.0" not in json.dumps(new) and "999.0" not in json.dumps(new)
        assert (output / f"{split}.answers.index.jsonl").read_text() == (base / f"{split}.answers.index.jsonl").read_text()
    assert validate_joint_qwen_sft(output)["schema_version"] == report["schema_version"]


def test_explicit_quarantine_removes_component_and_measurements_without_new_split(joint_source, tmp_path):
    source, joint, _, other, _, _, _ = joint_source
    output = tmp_path / "quarantined"
    report = prepare_joint_qwen_sft(source, joint, output,
                                    exclude_component_ids={other["record_id"]: "Post-treatment selected population; baseline omics incompatible."})
    assert report["training_record_count"] == 1
    assert report["training_MIC_measurement_count"] == 2
    assert report["quarantined_component_count"] == 1
    assert report["quarantined_MIC_measurement_count"] == 1
    assert report["evaluation"]["validation"]["record_count"] == 1
    quarantine = json.loads((output / "quarantined_components.index.jsonl").read_text())
    assert quarantine["component_id"] == other["record_id"] and quarantine["training_eligible"] is False
    assert other["record_id"] not in (output / "train.jsonl").read_text()


@pytest.mark.parametrize("mutation", ["quote", "compound", "target", "input", "heldout", "source", "provenance"])
def test_source_review_flag_cannot_admit_forged_rows_or_unbound_inputs(joint_source, tmp_path, mutation):
    source, joint, _, _, _, reviews, mapping = joint_source
    if mutation in {"quote", "compound"}:
        data = json.loads(reviews.read_text())
        if mutation == "quote":
            data["annotations"][0]["claims"][0]["quotes"][0]["text"] = "Invented direct protein binding."
        else:
            data["annotations"][0]["compound_paper_name"] = "Drug B"
        reviews.write_text(json.dumps(data))
        summary = json.loads((joint / "summary.json").read_text())
        summary["input_files"][str(reviews)] = _digest(reviews)
        (joint / "summary.json").write_text(json.dumps(summary))
    elif mutation == "source":
        mapping.write_text('{"compound_records": []}')
    elif mutation == "provenance":
        data = json.loads((joint / "private_literature_reviews.jsonl").read_text())
        data["inference_eligible"] = True
        _write(joint / "private_literature_reviews.jsonl", [data])
    else:
        row = json.loads((joint / "joint_sft.jsonl").read_text())
        if mutation == "target":
            target = json.loads(row["messages"][-1]["content"])
            target["observations"][0]["value"] = 123.0
            row["messages"][-1]["content"] = json.dumps(target)
        elif mutation == "input":
            request = json.loads(row["messages"][1]["content"])
            request["candidate"]["smiles"] = "CCO"
            row["messages"][1]["content"] = json.dumps(request)
        else:
            row["split"] = "test"
        _write(joint / "joint_sft.jsonl", [row])
    with pytest.raises(ValueError):
        prepare_joint_qwen_sft(source, joint, tmp_path / "rejected")
    assert not (tmp_path / "rejected").exists()


def test_duplicate_reviews_unknown_quarantine_and_joint_quarantine_are_rejected(joint_source, tmp_path):
    source, joint, component, _, _, _, _ = joint_source
    with pytest.raises(ValueError, match="duplicate_joint_component"):
        prepare_joint_qwen_sft(source, [joint, joint], tmp_path / "duplicate")
    with pytest.raises(ValueError, match="not_in_frozen_training_set"):
        prepare_joint_qwen_sft(source, joint, tmp_path / "unknown", exclude_component_ids={"mic:unknown"})
    with pytest.raises(ValueError, match="is_quarantined"):
        prepare_joint_qwen_sft(source, joint, tmp_path / "reviewed", exclude_component_ids={component["record_id"]})


def test_base_hash_receipts_do_not_replace_source_verification_and_destination_is_preserved(joint_source, tmp_path):
    source, joint, _, _, _, _, _ = joint_source
    base = tmp_path / "base"
    prepare_qwen_sft(source, base)
    rows = [json.loads(line) for line in (base / "train.jsonl").read_text().splitlines()]
    rows[0]["messages"][1]["content"] = rows[0]["messages"][1]["content"].replace('"A"', '"Other strain"')
    _write(base / "train.jsonl", rows)
    manifest = json.loads((base / "manifest.json").read_text())
    manifest["files"]["train.jsonl"]["sha256"] = _digest(base / "train.jsonl")
    (base / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="differs_from_frozen_components"):
        prepare_joint_qwen_sft(source, joint, tmp_path / "forged", base_qwen_dir=base)
    existing = tmp_path / "existing"
    existing.mkdir()
    (existing / "keep").write_text("original")
    with pytest.raises(FileExistsError):
        prepare_joint_qwen_sft(source, joint, existing)
    assert (existing / "keep").read_text() == "original"
