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


def failed_formal_run(tmp_path, monkeypatch):
    pilot, reports, output = tmp_path / "pilot", tmp_path / "reports", tmp_path / "output"
    pilot.mkdir()
    reports.mkdir()
    for name in ("validation", "without_omics", "without_structure"):
        write_rows(pilot / f"{name}.inputs.jsonl", ["a", "b"])
    config, audit, mapping = (tmp_path / name for name in ("config.yaml", "audit.json", "map.json"))
    config.write_text(f"output_dir: {output}\n")
    audit.write_text("{}")
    mapping.write_text("{}")
    write_rows(reports / "baseline.predictions.jsonl", ["a", "b"])
    pipeline.write_json(reports / "baseline.score.json", {"status": "scored"})
    args = SimpleNamespace(root=tmp_path, reports=reports, pilot=pilot, config=config,
                           audit=audit, source_path_map=mapping, scoring_dataset=tmp_path / "data", port=8790)
    monkeypatch.setattr(pipeline, "checked_command", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("first_formal_stop")))
    with pytest.raises(RuntimeError, match="first_formal_stop"):
        pipeline.run_pipeline(args)
    return args, output


def test_reviewed_checkpoint_recovery_reuses_baseline_and_preserves_failed_attempt(tmp_path, monkeypatch):
    args, output = failed_formal_run(tmp_path, monkeypatch)
    original = (args.reports / "baseline.predictions.jsonl").read_bytes()
    args.resume_from_checkpoint = output / "checkpoint-3"
    args.resume_from_checkpoint.mkdir(parents=True)
    pipeline.write_json(args.resume_from_checkpoint / "praxis_checkpoint.json", {
        "schema": "praxis.fsdp-lora-checkpoint.v1", "world_size": 8, "global_step": 3})
    args.training_reports = args.reports / "training_recovery"
    commands = []

    def dispatched(command, **kwargs):
        commands.append(command)
        raise RuntimeError("resume_dispatched")

    monkeypatch.setattr(pipeline, "checked_command", dispatched)
    with pytest.raises(RuntimeError, match="resume_dispatched"):
        pipeline.run_pipeline(args)
    assert len(commands) == 1 and "run_qwen_formal.py" in commands[0][2]
    assert commands[0][commands[0].index("--resume-from-checkpoint") + 1] == str(args.resume_from_checkpoint)
    assert commands[0][commands[0].index("--reports") + 1] == str(args.training_reports)
    assert (args.reports / "baseline.predictions.jsonl").read_bytes() == original
    archive = json.loads((args.reports / "pipeline.attempt-1.json").read_text())
    assert archive["status"] == "failed" and archive["failure_reason"] == "first_formal_stop"
    current = json.loads((args.reports / "pipeline.json").read_text())
    assert current["recoveries"][0]["from_optimizer_step"] == 3


def test_failed_formal_stage_is_never_retried_without_explicit_checkpoint(tmp_path, monkeypatch):
    args, _ = failed_formal_run(tmp_path, monkeypatch)
    monkeypatch.setattr(pipeline, "checked_command", lambda *a, **kw: pytest.fail("unreviewed retry launched"))
    with pytest.raises(ValueError, match="review_before_retry"):
        pipeline.run_pipeline(args)


def test_recovery_rejects_partial_baseline_before_launch(tmp_path, monkeypatch):
    args, _ = failed_formal_run(tmp_path, monkeypatch)
    args.resume_from_checkpoint = tmp_path / "missing-checkpoint"
    args.training_reports = args.reports / "training_recovery"
    write_rows(args.reports / "baseline.predictions.jsonl", ["a"])
    monkeypatch.setattr(pipeline, "checked_command", lambda *a, **kw: pytest.fail("partial baseline launched recovery"))
    with pytest.raises(ValueError, match="completed_scored_baseline"):
        pipeline.run_pipeline(args)
