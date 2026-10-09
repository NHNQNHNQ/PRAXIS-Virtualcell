import json
import subprocess
import sys
import textwrap
from pathlib import Path

from scripts.uplift.regen_simulate import build_simulate_fn, rewrite_run_py


def test_build_simulate_for_flat_schema():
    code = build_simulate_fn({"x": 1, "y": "abc", "z": 0.5})
    assert "def simulate" in code
    ns = {"ARCHETYPE": "X", "BRAIN": "b", "SKILL": "s"}
    exec(code, ns)
    out = ns["simulate"]({})
    assert set(out.keys()) >= {"x", "y", "z"}


def test_build_simulate_for_nested_schema_preserves_keys():
    schema = {"poses": [{"rank": 1, "score": -8.0}], "best_affinity": -8.0}
    code = build_simulate_fn(schema)
    ns = {"ARCHETYPE": "X", "BRAIN": "b", "SKILL": "s"}
    exec(code, ns)
    out = ns["simulate"]({})
    assert "poses" in out and "best_affinity" in out
    assert isinstance(out["poses"], list)
    assert "rank" in out["poses"][0]


def test_rewrite_run_py_replaces_only_simulate(tmp_path: Path):
    rp = tmp_path / "run.py"
    rp.write_text(textwrap.dedent('''
        import json, sys
        ARCHETYPE = "X"
        BRAIN = "b"
        SKILL = "s"

        def simulate(payload):
            return {"old": True}

        def real(payload):
            return {"ok": False, "error": "stub"}

        def main():
            payload = {"simulate": True}
            if not sys.stdin.isatty():
                try:
                    payload = json.load(sys.stdin)
                except Exception:
                    pass
            out = simulate(payload) if payload.get("simulate", True) else real(payload)
            json.dump(out, sys.stdout)
            return 0

        if __name__ == "__main__":
            sys.exit(main())
    ''').lstrip())
    res = rewrite_run_py(rp, {"new_key": 1})
    assert res["action"] == "rewritten"
    txt = rp.read_text()
    assert "def real(payload)" in txt and 'error": "stub"' in txt
    assert "new_key" in txt
    proc = subprocess.run([sys.executable, str(rp)],
                          input=json.dumps({"simulate": True}),
                          capture_output=True, text=True, timeout=5)
    assert proc.returncode == 0, proc.stderr
    j = json.loads(proc.stdout)
    assert "new_key" in j


def test_rewrite_skips_hand_written_long_file(tmp_path: Path):
    rp = tmp_path / "run.py"
    big = ["ARCHETYPE = \"X\"", "BRAIN = \"b\"", "SKILL = \"s\""]
    big.append("def simulate(payload):")
    for i in range(250):
        big.append(f"    # padding line {i}")
    big.append("    return {'old': True}")
    big.append("def real(payload): return {}")
    rp.write_text("\n".join(big) + "\n")
    res = rewrite_run_py(rp, {"new_key": 1})
    assert res["action"] == "skip-hand-written"
