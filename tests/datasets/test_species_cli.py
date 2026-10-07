"""The frozen species data path works without credentials or a model client."""
from __future__ import annotations

import json

import pytest

from praxis_virtualcell import cli
from praxis_virtualcell.datasets.species_registry import build_species_database
from tests.datasets.test_evaluation import experiment
from tests.datasets.test_species_registry import setup_data


@pytest.fixture(autouse=True)
def no_model_or_credentials(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Data preparation must not access credentials or a model")
    monkeypatch.setattr(cli.LLMSettings, "load", forbidden)
    monkeypatch.setattr("praxis2.llm.client.LLMClient.__init__", forbidden)


def database(tmp_path):
    records = [experiment(f"fixture-{i}", smiles, study=f"DOC{i}").model_dump()
               for i, smiles in enumerate(("CCO", "c1ccccc1", "c1ccncc1", "C1CCCCC1"))]
    root, selection, labels = setup_data(tmp_path, records)
    result = build_species_database(selection, [labels], tmp_path / "db", profile_root=root)
    return result["database"], labels


def test_frozen_species_cli_to_train_queue_and_empty_prediction_scoring(tmp_path, capsys):
    db, _ = database(tmp_path)
    frozen = tmp_path / "frozen"
    assert cli.main(["freeze-species-evaluation", "--database", db, "--output", str(frozen),
                     "--grouping", "scaffold"]) == 0
    manifest = json.loads(capsys.readouterr().out)
    assert manifest["status"] == "ready"
    inputs = [json.loads(line) for line in (frozen / "inputs.jsonl").read_text().splitlines()]
    assert {row["split"] for row in inputs} == {"train", "validation", "test"}
    assert all(set(row["input"]) == {"candidate", "organism", "profile_id", "prediction_scope"} for row in inputs)
    queue = tmp_path / "supervision"
    assert cli.main(["prepare-species-supervision", "--manifest", str(frozen / "manifest.json"),
                     "--output", str(queue), "--limit-per-species", "1"]) == 0
    capsys.readouterr()
    pending = [json.loads(line) for line in (queue / "queue.jsonl").read_text().splitlines()]
    assert len(pending) == 1 and not pending[0]["trainable"]
    predictions = tmp_path / "no_predictions.jsonl"
    predictions.write_text("")
    score = tmp_path / "score.json"
    assert cli.main(["score-species-evaluation", "--manifest", str(frozen / "manifest.json"),
                     "--predictions", str(predictions), "--output", str(score)]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["numeric_answer_coverage"] == 0.0
    assert summary["mean_absolute_log2_error"] is None
    assert json.loads(score.read_text())["details"]


def test_changed_frozen_source_stops_cli_supervision_without_output(tmp_path, capsys):
    db, labels = database(tmp_path)
    frozen = tmp_path / "frozen"
    assert cli.main(["freeze-species-evaluation", "--database", db, "--output", str(frozen)]) == 0
    capsys.readouterr()
    labels.write_text(labels.read_text() + "\n")
    output = tmp_path / "should_not_exist"
    assert cli.main(["prepare-species-supervision", "--manifest", str(frozen / "manifest.json"),
                     "--output", str(output)]) == 1
    captured = capsys.readouterr()
    assert "Operation failed" in captured.err and not output.exists()
