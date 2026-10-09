"""Confirmed CLI questions persist the submitted request with execution identity."""

import json

from praxis_virtualcell.cli import main


def test_confirmed_offline_question_exports_a_value_free_job(tmp_path, capsys):
    out = tmp_path / "question"
    assert main([
        "ask", "--text", "Knock out AHR in human K562 cells",
        "--mode", "offline", "--yes", "--out", str(out),
    ]) == 0
    capsys.readouterr()
    request = json.loads((out / "request.json").read_text())
    report = json.loads((out / "report.json").read_text())
    identity = json.loads((out / "execution_identity.json").read_text())
    assert request["perturbation_targets"] == ["AHR"]
    assert report["abstain"] is True
    assert report["prediction"] is None
    assert report["request_id"] == request["request_id"]
    assert identity["outcome"]["abstain"] is True
    assert identity["outcome"]["prediction_present"] is False
    assert (out / "report.md").is_file()
