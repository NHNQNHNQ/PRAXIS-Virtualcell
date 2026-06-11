import textwrap
from pathlib import Path

from scripts.uplift.regen_real import build_real_fn_green, build_real_fn_na, rewrite_real


def test_real_na_returns_structured_dict():
    code = build_real_fn_na("license blocked: Schrodinger")
    ns = {"ARCHETYPE": "x", "BRAIN": "y", "SKILL": "z"}
    exec(code, ns)
    out = ns["real"]({})
    assert out["ok"] is False
    assert "N/A" in out["error"]


def test_real_green_calls_run_tool_and_returns_dict():
    code = build_real_fn_green(archetype="generic")
    ns = {
        "ARCHETYPE": "x", "BRAIN": "y", "SKILL": "z",
        "run_tool": lambda *a, **kw: {
            "ok": True, "stdout": "", "stderr": "", "returncode": 0,
            "wall_sec": 0.0, "cmd": "", "dry": True,
        },
    }
    exec(code, ns)
    out = ns["real"]({})
    assert isinstance(out, dict)
    assert "diagnostics" in out


def test_rewrite_real_replaces_only_real_fn(tmp_path: Path):
    rp = tmp_path / "run.py"
    rp.write_text(textwrap.dedent('''
        ARCHETYPE = "generic"
        BRAIN = "b"
        SKILL = "s"

        def simulate(payload):
            return {"a": 1}

        def real(payload):
            return {"ok": False, "error": "old stub"}

        def main():
            pass
    ''').lstrip())
    res = rewrite_real(rp, bucket="N_A", reason="test reason")
    assert res["action"] == "rewritten"
    txt = rp.read_text()
    assert "def simulate" in txt and 'a": 1' in txt  # simulate untouched
    assert "test reason" in txt
