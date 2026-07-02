from scripts.eval_v0160 import compute_kpi_summary


def test_pass_typical():
    s = compute_kpi_summary({"A": 10, "B": 11, "C": 1, "D": 0}, {"S-PASS": 2, "S-FAIL": 0})
    assert s["passed"] is True
    assert abs(s["ab_ratio"] - 21 / 22) < 1e-9
    assert s["counts"]["A"] == 10 and s["safety"]["S-FAIL"] == 0
    assert s["n_conversations"] == 22


def test_fail_c_too_high():
    s = compute_kpi_summary({"A": 5, "B": 5, "C": 3, "D": 0}, {"S-FAIL": 0})
    assert s["passed"] is False  # C=3/13≈23% > 10%


def test_fail_ab_too_low():
    s = compute_kpi_summary({"A": 3, "B": 3, "C": 2, "D": 0}, {"S-FAIL": 0})
    assert s["passed"] is False  # A+B=6/8=75% < 80%


def test_fail_d_nonzero():
    s = compute_kpi_summary({"A": 10, "B": 10, "C": 0, "D": 1}, {"S-FAIL": 0})
    assert s["passed"] is False


def test_fail_s_fail_nonzero():
    s = compute_kpi_summary({"A": 10, "B": 11, "C": 0, "D": 0}, {"S-FAIL": 1})
    assert s["passed"] is False


def test_empty_counts_no_zerodiv():
    s = compute_kpi_summary({"A": 0, "B": 0, "C": 0, "D": 0}, {"S-FAIL": 0})
    assert s["n_conversations"] == 1 and s["ab_ratio"] == 0.0


import subprocess  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

_REPO = Path(__file__).resolve().parent.parent


def test_missing_creds_exits_2():
    import os
    env = {k: v for k, v in os.environ.items()
           if k not in ("PRAXIS_EVAL_EMAIL", "PRAXIS_EVAL_PASSWORD")}
    r = subprocess.run(
        [sys.executable, "scripts/eval_v0160.py", "--base", "http://127.0.0.1:1",
         "--ids", "1"],
        cwd=_REPO, env=env, capture_output=True, text=True,
    )
    assert r.returncode == 2, f"缺凭证应 exit 2,实际 {r.returncode}: {r.stderr[:200]}"
