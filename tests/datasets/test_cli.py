"""Dataset CLI paths are local preparation/scoring operations without a client."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from praxis_virtualcell import cli
from praxis_virtualcell.datasets.evaluation import freeze_evaluation
from praxis_virtualcell.omics.profiles import _data_root
from tests.datasets.test_evaluation import experiment, prediction, rows, write_predictions, write_records


@pytest.fixture(autouse=True)
def forbid_credentials_and_model_clients(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Dataset CLI must not read LLM settings or instantiate an API client")
    class ForbiddenSettings:
        __new__ = forbidden
        load = staticmethod(forbidden)
    monkeypatch.setattr(cli, "LLMSettings", ForbiddenSettings)
    monkeypatch.setattr("praxis_virtualcell.settings.LLMSettings", ForbiddenSettings)
    monkeypatch.setattr("praxis_virtualcell.settings.read_env_file", forbidden)
    monkeypatch.setattr("praxis2.llm.client.LLMClient.__init__", forbidden)


def test_curate_labels_passes_explicit_repository_and_output_without_credentials(tmp_path, monkeypatch, capsys):
    repo, output = tmp_path / "repo", tmp_path / "labels"
    calls = []
    def curate(repository, destination):
        calls.append((repository, destination))
        return {"admitted_records": 3, "paired_omics_records": 0}
    monkeypatch.setattr("praxis_virtualcell.datasets.curation.curate_existing_labels", curate)
    assert cli.main(["curate-labels", "--repo-root", str(repo), "--output", str(output)]) == 0
    assert calls == [(str(repo), str(output))]
    captured = capsys.readouterr()
    assert captured.err == ""
    assert json.loads(captured.out) == {"admitted_records": 3, "paired_omics_records": 0}


def test_freeze_cli_writes_ready_split_with_requested_grouping_and_seed(tmp_path, capsys):
    labels = write_records(tmp_path / "labels.jsonl", [
        experiment("fixture-one", "CCO", study="fixture-study-one"),
        experiment("fixture-two", "CCN", study="fixture-study-two"),
        experiment("fixture-three", "c1ccccc1", study="fixture-study-three"),
    ])
    original = labels.read_bytes()
    output = tmp_path / "frozen"
    assert cli.main(["freeze-evaluation", "--labels", str(labels), "--output", str(output),
                     "--grouping", "study", "--seed", "17"]) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    result = json.loads(captured.out)
    assert result == json.loads((output / "manifest.json").read_text())
    assert result["status"] == "ready"
    assert result["grouping"] == "study" and result["seed"] == 17
    assert result["paired_only"] is False
    assert result["split_counts"] == {"test": 1, "validation": 1, "train": 1}
    assert labels.read_bytes() == original
    for forbidden in ("endpoint", "measured_qualifier", "DO_NOT_EXPOSE_LABEL_SENTINEL", "MIC"):
        assert forbidden not in (output / "inputs.jsonl").read_text()
    assert all(set(row) == {"case_id", "split", "group_id", "record_id"}
               for row in rows(output / "answers.index.jsonl"))


def test_paired_freeze_without_verified_matches_returns_two_and_exposes_readiness(tmp_path, capsys):
    labels = write_records(tmp_path / "labels.jsonl", [
        experiment("unpaired-one", "CCO"), experiment("unpaired-two", "CCN"),
        experiment("unpaired-three", "c1ccccc1"),
    ])
    output = tmp_path / "paired-frozen"
    assert cli.main(["freeze-evaluation", "--labels", str(labels), "--output", str(output), "--paired-only"]) == 2
    captured = capsys.readouterr()
    assert captured.err == ""
    result = json.loads(captured.out)
    assert result["paired_only"] is True
    assert result["status"] == "insufficient_groups"
    assert result["records"] == result["matched_omics_records"] == 0
    assert result["excluded_records"] == 3
    assert (output / "inputs.jsonl").read_text() == ""
    assert json.loads((output / "manifest.json").read_text())["status"] == "insufficient_groups"


def test_score_cli_scores_only_requested_split_and_writes_full_report(tmp_path, capsys):
    labels = write_records(tmp_path / "labels.jsonl", [
        experiment("one", "CCO"), experiment("two", "CCN"), experiment("three", "c1ccccc1"),
    ])
    frozen = tmp_path / "frozen"
    freeze_evaluation(labels, frozen)
    selected = [row for row in rows(frozen / "answers.index.jsonl") if row["split"] == "validation"]
    forecasts = write_predictions(tmp_path / "predictions.jsonl", [prediction(selected[0]["case_id"], 8.0)])
    output = tmp_path / "nested/score.json"
    assert cli.main(["score-evaluation", "--manifest", str(frozen / "manifest.json"),
                     "--predictions", str(forecasts), "--split", "validation", "--output", str(output)]) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    summary = json.loads(captured.out)
    report = json.loads(output.read_text())
    assert "details" not in summary and len(report["details"]) == 1
    assert report["cases"] == report["answered_mic_cases"] == 1
    assert report["numeric_answer_coverage"] == 1.0
    assert report["mean_absolute_log2_error"] == 1.0
    assert report["details"][0]["case_id"] == selected[0]["case_id"]
    assert summary == {key: value for key, value in report.items() if key != "details"}


def test_prepare_seeds_default_root_is_a_real_path_not_none(tmp_path, monkeypatch, capsys):
    calls = []
    def prepare(root, output, *, limit):
        assert isinstance(root, Path)
        assert root == _data_root(None)
        calls.append((root, output, limit))
        return {"record_count": 20, "trainable_record_count": 0}
    monkeypatch.setattr("praxis_virtualcell.datasets.seeds.prepare_seed_queue", prepare)
    output = tmp_path / "seeds"
    assert cli.main(["prepare-seeds", "--output", str(output)]) == 0
    assert calls == [(_data_root(None), str(output), 80)]
    captured = capsys.readouterr()
    assert captured.err == ""
    assert json.loads(captured.out)["trainable_record_count"] == 0


def test_prepare_seeds_explicit_root_and_limit_reach_builder(tmp_path, monkeypatch, capsys):
    calls = []
    def prepare(root, output, *, limit):
        calls.append((root, output, limit))
        return {"record_count": 5, "trainable_record_count": 0}
    monkeypatch.setattr("praxis_virtualcell.datasets.seeds.prepare_seed_queue", prepare)
    root, output = tmp_path / "organisms", tmp_path / "seeds"
    assert cli.main(["--data-root", str(root), "prepare-seeds", "--output", str(output), "--limit", "5"]) == 0
    assert calls == [(root, str(output), 5)]
    assert isinstance(calls[0][0], Path)
    captured = capsys.readouterr()
    assert captured.err == ""
    assert json.loads(captured.out)["record_count"] == 5


@pytest.mark.parametrize("command,target,arguments,expected_args,expected_kwargs", [
    ("build-strain-dataset", "strain_dataset.build_strain_dataset",
     ["--database", "db", "--frozen-manifest", "freeze", "--enrichments", "review", "--output", "out"],
     ("db", "freeze", "out"), {"profile_root": _data_root(None), "enrichments_path": "review"}),
    ("prepare-strain-supervision", "strain_supervision.prepare_strain_supervision",
     ["--dataset", "dataset", "--output", "out"], ("dataset", "out"), {}),
    ("acquire-literature", "literature.acquire_literature",
     ["--cases", "cases", "--limit", "7", "--offline", "--output", "out"],
     ("cases", "out"), {"limit": 7, "offline": True, "skip_supplements": True}),
    ("prepare-joint-supervision", "joint_supervision.prepare_joint_supervision",
     ["--supervision", "sft", "--literature", "papers", "--reviews", "review", "--output", "out"],
     ("sft", "papers", "review", "out"), {}),
])
def test_strain_dataset_commands_do_not_load_credentials_or_clients(monkeypatch, capsys, command, target,
                                                                   arguments, expected_args, expected_kwargs):
    calls = []
    def run(*args, **kwargs):
        calls.append((args, kwargs))
        return {"source_verified": True}
    monkeypatch.setattr("praxis_virtualcell.datasets." + target, run)
    assert cli.main([command, *arguments]) == 0
    assert calls == [(expected_args, expected_kwargs)]
    assert json.loads(capsys.readouterr().out) == {"source_verified": True}
