import json
from pathlib import Path
import shutil

import pytest

from praxis_virtualcell.datasets.joint_qwen_sft import prepare_joint_qwen_sft
from praxis_virtualcell.datasets.species_registry import _digest
from praxis_virtualcell.datasets.verify_joint_sources import verify_joint_sources
from tests.datasets.test_joint_qwen_sft import joint_source  # noqa: F401


@pytest.fixture
def relocated_sources(joint_source, tmp_path):
    source, joint, _, _, _, _, _ = joint_source
    dataset = tmp_path / "joint_qwen"
    prepare_joint_qwen_sft(source, joint, dataset)
    private = [json.loads(line) for line in (dataset / "source_refs.jsonl").read_text().splitlines()]
    files = set()
    for row in private:
        files.update(item["locator"]["path"] for item in row["source_refs"])
        if "literature_review" in row:
            review = row["literature_review"]
            files.update((review["annotation"]["compound_mapping"]["file"], review["paper_source"]["file"]))
    relocated = tmp_path / "native_sources"
    relocated.mkdir()
    path_map = {}
    for number, old in enumerate(sorted(files)):
        new = relocated / f"source_{number}{Path(old).suffix}"
        shutil.copyfile(old, new)
        path_map[old] = str(new)
        Path(old).unlink()
    return dataset, path_map


def _rewrite_receipt(dataset, name, rows):
    path = dataset / name
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    manifest = json.loads((dataset / "manifest.json").read_text())
    manifest["files"][name]["sha256"] = _digest(path)
    (dataset / "manifest.json").write_text(json.dumps(manifest))


def test_verifier_uses_relocated_bytes_and_retains_original_article_locators(relocated_sources, tmp_path, monkeypatch):
    dataset, path_map = relocated_sources
    original_open = Path.open
    def guarded_open(path, *args, **kwargs):
        if path.name.startswith(("validation.", "test.")):
            raise AssertionError("Native source verifier attempted to open held-out answers.")
        return original_open(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", guarded_open)
    report_path = tmp_path / "verification.json"
    report = verify_joint_sources(dataset, path_map, report_path=report_path)
    assert report["status"] == "passed"
    assert report["training_records_checked"] == 2
    assert report["training_MIC_measurements_checked"] == 3
    assert report["joint_records_checked"] == 1 and report["mechanism_claims_checked"] == 1
    assert report["mechanism_source_subset_cases_checked"] == 2
    assert report["native_quotes_checked"] == 2 and report["native_articles_checked"] == 1
    assert report["native_source_files_checked"] == 3
    assert report["original_article_locators_preserved"] is True
    assert report["heldout_MIC_answers_opened"] == 0 and report["training_runs"] == 0
    assert json.loads(report_path.read_text()) == report


@pytest.mark.parametrize("mutation", ["quote", "MIC", "compound_bytes", "article_bytes", "compound_identity", "missing_map", "native_strain", "tool_strain", "subset", "heldout", "article_url"])
def test_verifier_rejects_changed_sources_or_invalid_public_bindings(relocated_sources, mutation):
    dataset, path_map = relocated_sources
    private = [json.loads(line) for line in (dataset / "source_refs.jsonl").read_text().splitlines()]
    reviewed = next(row for row in private if "literature_review" in row)
    review = reviewed["literature_review"]
    if mutation == "quote":
        review["annotation"]["claims"][0]["quotes"][0]["text"] = "Invented direct gyrase binding."
        _rewrite_receipt(dataset, "source_refs.jsonl", private)
    elif mutation == "article_url":
        review["paper_source"]["url"] = "https://example.com/unverified-paper"
        _rewrite_receipt(dataset, "source_refs.jsonl", private)
    elif mutation == "compound_bytes":
        Path(path_map[review["annotation"]["compound_mapping"]["file"]]).write_text('{"compound_records": []}')
    elif mutation == "article_bytes":
        Path(path_map[review["paper_source"]["file"]]).write_text("changed original paper")
    elif mutation == "missing_map":
        del path_map[review["paper_source"]["file"]]
    elif mutation == "compound_identity":
        mapping = review["annotation"]["compound_mapping"]
        path = Path(path_map[mapping["file"]])
        data = json.loads(path.read_text())
        data["compound_records"][0]["molecule_chembl_id"] = "OTHER_DRUG"
        path.write_text(json.dumps(data))
        mapping["sha256"] = _digest(path)
        _rewrite_receipt(dataset, "source_refs.jsonl", private)
    elif mutation == "native_strain":
        old = reviewed["source_refs"][0]["locator"]["path"]
        path = Path(path_map[old])
        data = [json.loads(line) for line in path.read_text().splitlines()]
        data[0]["organism"]["strain"] = "Other strain"
        path.write_text("".join(json.dumps(row) + "\n" for row in data))
        for row in private:
            for item in row["source_refs"]:
                if item["locator"]["path"] == old:
                    item["locator"]["sha256"] = _digest(path)
        _rewrite_receipt(dataset, "source_refs.jsonl", private)
    elif mutation == "subset":
        review["annotation"]["mechanism_case_ids"] = []
        _rewrite_receipt(dataset, "source_refs.jsonl", private)
    elif mutation == "heldout":
        reviewed["split"] = "test"
        _rewrite_receipt(dataset, "source_refs.jsonl", private)
    else:
        train = [json.loads(line) for line in (dataset / "train.jsonl").read_text().splitlines()]
        row = next(row for row in train if row["record_id"] == reviewed["record_id"])
        if mutation == "MIC":
            target = json.loads(row["messages"][-1]["content"])
            target["observations"][0]["value"] = 123.0
            row["messages"][-1]["content"] = json.dumps(target)
        else:
            tool = next(message for message in row["messages"] if message["role"] == "tool")
            reply = json.loads(tool["content"])
            reply["data"]["strain"] = "Different strain"
            tool["content"] = json.dumps(reply)
        _rewrite_receipt(dataset, "train.jsonl", train)
    with pytest.raises(ValueError):
        verify_joint_sources(dataset, path_map)


def test_explicit_nonempty_mechanism_case_subset_is_supported(relocated_sources):
    dataset, path_map = relocated_sources
    rows = [json.loads(line) for line in (dataset / "source_refs.jsonl").read_text().splitlines()]
    reviewed = next(row for row in rows if "literature_review" in row)
    annotation = reviewed["literature_review"]["annotation"]
    annotation["mechanism_case_ids"] = [annotation["case_ids"][0]]
    _rewrite_receipt(dataset, "source_refs.jsonl", rows)
    result = verify_joint_sources(dataset, path_map)
    assert result["mechanism_source_subset_cases_checked"] == 1
    assert result["training_MIC_measurements_checked"] == 3


def test_native_DOI_case_differences_and_public_citations_are_valid(relocated_sources):
    dataset, path_map = relocated_sources
    private = [json.loads(line) for line in (dataset / "source_refs.jsonl").read_text().splitlines()]
    review = next(row["literature_review"] for row in private if "literature_review" in row)
    article = review["paper_source"]
    path = Path(path_map[article["file"]])
    path.write_text(path.read_text().replace("10.1234/paper-a", "10.1234/PAPER-A"))
    article["sha256"] = _digest(path)
    for evidence in review["binding_evidence"]:
        evidence["source_locator"]["sha256"] = article["sha256"]
    _rewrite_receipt(dataset, "source_refs.jsonl", private)
    train = [json.loads(line) for line in (dataset / "train.jsonl").read_text().splitlines()]
    joint = next(row for row in train if row["record_id"] == review["record_id"])
    target = json.loads(joint["messages"][-1]["content"])
    target["mechanism_claims"][0]["sources"][0]["doi"] = "10.1234/Paper-A"
    joint["messages"][-1]["content"] = json.dumps(target)
    _rewrite_receipt(dataset, "train.jsonl", train)
    _rewrite_receipt(dataset, "joint.train.jsonl", [joint])
    result = verify_joint_sources(dataset, path_map)
    assert result["status"] == "passed" and result["native_articles_checked"] == 1
    assert "10.1234/PAPER-A" in path.read_text()
