"""QA pipeline tests — verify all 10 cases pass the 6-layer QA (offline)."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.distill.qa import run_qa, CASES_DIR

CASE_PATHS = sorted(CASES_DIR.glob("synth-*.md"))


@pytest.mark.parametrize("case_path", CASE_PATHS, ids=[p.stem for p in CASE_PATHS])
def test_case_passes_offline_qa(case_path):
    rep = run_qa(case_path, network=False)
    assert rep["overall"] != "fail", rep
    # mandatory_body must be PASS for every case (★排除 + ★失败 sections)
    body = next((c for c in rep["checks"] if c["name"] == "mandatory_body"), None)
    assert body and body["status"] == "pass", body
    # schema must be PASS
    sc = next((c for c in rep["checks"] if c["name"] == "schema"), None)
    assert sc and sc["status"] == "pass", sc


def test_we_have_10_cases():
    assert len(CASE_PATHS) == 10
