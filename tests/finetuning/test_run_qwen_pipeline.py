import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.finetuning import run_qwen_pipeline as pipeline


def write_rows(path, identifiers):
    path.write_text("".join(json.dumps({"record_id": value}) + "\n" for value in identifiers))


def test_completed_count_keeps_failures_and_rejects_duplicate_or_unexpected_ids(tmp_path):
    inputs, output = tmp_path / "validation.inputs.jsonl", tmp_path / "out.jsonl"
    write_rows(inputs, ["a", "b"])
    output.write_text('{"record_id":"a","status":"error"}\n')
    assert pipeline.completed_count(inputs, output) == (1, 2)
    write_rows(output, ["a", "a"])
    with pytest.raises(ValueError, match="duplicate_or_unknown"):
        pipeline.completed_count(inputs, output)
    write_rows(output, ["elsewhere"])
    with pytest.raises(ValueError, match="duplicate_or_unknown"):
        pipeline.completed_count(inputs, output)


def test_evaluation_halts_after_failed_guard_without_retry(tmp_path, monkeypatch):
    inputs = tmp_path / "validation.inputs.jsonl"
    write_rows(inputs, ["a"])
    args = SimpleNamespace(root=tmp_path, reports=tmp_path, port=8790)
    commands = []

    def failed(command, **kwargs):
        commands.append(command)
        Path(command[command.index("--report") + 1]).write_text('{"outcome":"cgroup_oom"}')

    monkeypatch.setattr(pipeline, "checked_command", failed)
    with pytest.raises(RuntimeError, match="guard_failed"):
        pipeline.evaluate(args, "base", inputs)
    assert len(commands) == 1
    with pytest.raises(RuntimeError, match="review_before_retry"):
        pipeline.evaluate(args, "base", inputs)
    assert len(commands) == 1


def test_baseline_failure_prevents_formal_training(tmp_path, monkeypatch):
    pilot = tmp_path / "pilot"
    pilot.mkdir()
    for name in ("validation", "without_omics", "without_structure"):
        write_rows(pilot / f"{name}.inputs.jsonl", ["a"])
    config, audit, mapping = (tmp_path / name for name in ("config.yaml", "audit.json", "map.json"))
    for path in (config, audit, mapping):
        path.write_text("{}")
    args = SimpleNamespace(root=tmp_path, reports=tmp_path / "reports", pilot=pilot,
                           config=config, audit=audit, source_path_map=mapping,
                           scoring_dataset=tmp_path / "data", port=8790)
    commands = []
    monkeypatch.setattr(pipeline, "checked_command", lambda *a, **kw: commands.append(a))
    monkeypatch.setattr(pipeline, "evaluate", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("baseline_failed")))
    with pytest.raises(RuntimeError, match="baseline_failed"):
        pipeline.run_pipeline(args)
    status = json.loads((args.reports / "pipeline.json").read_text())
    assert status["status"] == "failed" and status["stage"] == "baseline"
    assert not commands


def test_public_input_change_refuses_resuming_old_pipeline(tmp_path):
    pilot = tmp_path / "pilot"
    pilot.mkdir()
    for name in ("validation", "without_omics", "without_structure"):
        write_rows(pilot / f"{name}.inputs.jsonl", ["a"])
    args = SimpleNamespace(root=tmp_path, reports=tmp_path / "reports", pilot=pilot,
                           config=tmp_path / "config.yaml", audit=tmp_path / "audit.json",
                           source_path_map=tmp_path / "map.json", scoring_dataset=tmp_path)
    for path in (args.config, args.audit, args.source_path_map):
        path.write_text("{}")
    args.reports.mkdir()
    (args.reports / "pipeline.json").write_text('{"identity":{"wrong":"snapshot"},"status":"running"}')
    with pytest.raises(ValueError, match="identity_changed"):
        pipeline.run_pipeline(args)
