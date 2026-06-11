"""Counter-examples for the QA pipeline — verify each layer correctly REJECTS bad cases.

These are adversarial fixtures crafted to violate exactly one QA rule each. If the
QA pipeline silently passes any of them, that's a real regression.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.distill.qa import run_qa

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BAD_CASES = PROJECT_ROOT / "tests" / "fixtures" / "bad_cases"


def _check_status(case_path: Path, network: bool, layer_name: str, expected_status: str) -> dict:
    rep = run_qa(case_path, network=network)
    layer = next((c for c in rep["checks"] if c["name"] == layer_name), None)
    assert layer is not None, f"{layer_name} layer missing from report for {case_path.name}"
    assert layer["status"] == expected_status, (
        f"{case_path.name}: expected {layer_name}={expected_status}, got {layer['status']} "
        f"(message: {layer['message']})"
    )
    return rep


def test_qa_rejects_fake_doi():
    """Layer 2 (doi_crossref) must FAIL on a CrossRef-unresolvable DOI."""
    rep = _check_status(BAD_CASES / "synth-bad-001-fake-doi.md", network=True,
                        layer_name="doi_crossref", expected_status="fail")
    assert rep["overall"] == "fail"


def test_qa_rejects_missing_mandatory_body():
    """Layer 7 (mandatory_body) must FAIL when ★ 排除 / ★ 失败 sections absent."""
    rep = _check_status(BAD_CASES / "synth-bad-002-missing-mandatory.md", network=False,
                        layer_name="mandatory_body", expected_status="fail")
    assert rep["overall"] == "fail"


def test_qa_rejects_bad_task_enum():
    """Layer 1 (schema) must FAIL when `task` is not in canonical synth_task enum."""
    rep = _check_status(BAD_CASES / "synth-bad-003-bad-task-enum.md", network=False,
                        layer_name="schema", expected_status="fail")
    assert rep["overall"] == "fail"


def test_qa_rejects_empty_tools_list():
    """Layer 1 (schema) must FAIL when `tools` is empty (soft-required)."""
    rep = _check_status(BAD_CASES / "synth-bad-004-empty-tools.md", network=False,
                        layer_name="schema", expected_status="fail")
    assert rep["overall"] == "fail"


def test_qa_rejects_missing_required_frontmatter():
    """Layer 1 (schema) must FAIL when key_paper_doi / task / host_organism missing."""
    rep = _check_status(BAD_CASES / "synth-bad-005-missing-required-fields.md", network=False,
                        layer_name="schema", expected_status="fail")
    assert rep["overall"] == "fail"


def test_qa_strict_mode_returns_nonzero_for_failures():
    """The CLI's --strict flag must propagate failures via exit code."""
    import subprocess, sys
    bad = BAD_CASES / "synth-bad-002-missing-mandatory.md"
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "distill" / "qa.py"),
         "--case", str(bad), "--no-network", "--strict"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode != 0, (
        f"QA --strict should return non-zero for failing case;\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
