"""run_tool 的契约:超时/非 0/异常都不抛,结构化返回。"""

from brains._common.lib.run_tool import run_tool


def test_success_returns_ok_true():
    r = run_tool(["python3", "-c", "print('hi')"])
    assert r["ok"] is True
    assert r["returncode"] == 0
    assert r["stdout"].strip() == "hi"
    assert r["wall_sec"] >= 0


def test_nonzero_exit_returns_ok_false():
    r = run_tool(["python3", "-c", "import sys; sys.exit(7)"])
    assert r["ok"] is False
    assert r["returncode"] == 7
    assert "error" in r


def test_command_not_found_returns_structured_err():
    r = run_tool(["definitely-not-a-real-binary-xyz123"])
    assert r["ok"] is False
    assert "error" in r
    assert r["returncode"] == -1


def test_timeout_returns_structured_err():
    r = run_tool(["python3", "-c", "import time; time.sleep(5)"], timeout=1)
    assert r["ok"] is False
    assert "timeout" in r["error"].lower()


def test_stdin_passthrough():
    r = run_tool(["python3", "-c", "import sys; print(sys.stdin.read().upper())"],
                 stdin=b"hello")
    assert r["ok"] is True
    assert r["stdout"].strip() == "HELLO"


def test_dry_host_mode_returns_mock(monkeypatch):
    monkeypatch.setenv("PRAXIS_SKILL_DRY_HOST", "1")
    r = run_tool(["should-never-actually-run"])
    assert r["ok"] is True
    assert r.get("dry") is True
