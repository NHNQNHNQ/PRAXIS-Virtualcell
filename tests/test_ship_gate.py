import pytest

from scripts.ship_gate import GateError, decide_kpi, decide_pytest, run_gate


def test_decide_pytest_pass():
    assert decide_pytest(lambda: 0) is True


def test_decide_pytest_fail():
    assert decide_pytest(lambda: 1) is False


def test_decide_kpi_pass_first():
    assert decide_kpi(lambda: 0) == (True, [0])


def test_decide_kpi_fail_then_pass():
    rcs = iter([1, 0])
    assert decide_kpi(lambda: next(rcs)) == (True, [1, 0])


def test_decide_kpi_fail_twice():
    rcs = iter([1, 1])
    assert decide_kpi(lambda: next(rcs)) == (False, [1, 1])


def test_decide_kpi_error_no_rerun():
    calls = []

    def runner():
        calls.append(1)
        return 2

    with pytest.raises(GateError):
        decide_kpi(runner)
    assert len(calls) == 1  # exit≥2 不重跑


def test_run_gate_pytest_fail_shortcircuits_kpi():
    kpi_calls = []
    r = run_gate(lambda: 1, lambda: kpi_calls.append(1) or 0)
    assert r.passed is False and r.pytest_ok is False
    assert kpi_calls == []  # 回归 fail → 不跑 KPI


def test_run_gate_all_pass():
    r = run_gate(lambda: 0, lambda: 0)
    assert r.passed is True and r.kpi_rcs == [0]


def test_run_gate_kpi_fail_twice():
    rcs = iter([1, 1])
    r = run_gate(lambda: 0, lambda: next(rcs))
    assert r.passed is False and r.kpi_rcs == [1, 1]


def test_main_missing_creds_exit_2(monkeypatch):
    monkeypatch.delenv("PRAXIS_EVAL_EMAIL", raising=False)
    monkeypatch.delenv("PRAXIS_EVAL_PASSWORD", raising=False)
    from scripts.ship_gate import main
    with pytest.raises(SystemExit) as ei:
        main()
    assert ei.value.code == 2


def test_main_kpi_error_exits_2(monkeypatch):
    """凭证齐 + 回归过 + KPI eval 返 exit≥2(凭证/用法错)→ GateError → main exit 2。"""
    monkeypatch.setenv("PRAXIS_EVAL_EMAIL", "x@y.z")
    monkeypatch.setenv("PRAXIS_EVAL_PASSWORD", "pw")
    import scripts.ship_gate as mod
    monkeypatch.setattr(mod, "_run_pytest", lambda: 0)
    monkeypatch.setattr(mod, "_run_kpi", lambda: 2)  # eval exit≥2 → GateError(不重跑)
    with pytest.raises(SystemExit) as ei:
        mod.main()
    assert ei.value.code == 2


def test_pytest_env_strips_eval_creds(monkeypatch):
    """门跑 pytest 的子进程 env 必须剥离 PRAXIS_EVAL_*——否则 praxis2.config 严格校验
    (§6⑤ 拒未知 PRAXIS_* 键)会让实例化 config 的测试因 PRAXIS_EVAL_EMAIL/PASSWORD 报
    ConfigError。回归用真实 ship_gate 实跑暴露:门设凭证后 pytest 段误失败 2 个测试。"""
    monkeypatch.setenv("PRAXIS_EVAL_EMAIL", "x@y.z")
    monkeypatch.setenv("PRAXIS_EVAL_PASSWORD", "pw")
    monkeypatch.setenv("PATH", "/usr/bin")
    from scripts.ship_gate import _pytest_env
    env = _pytest_env()
    assert "PRAXIS_EVAL_EMAIL" not in env and "PRAXIS_EVAL_PASSWORD" not in env
    assert env.get("PATH") == "/usr/bin"  # 非 EVAL 的 env 保留
