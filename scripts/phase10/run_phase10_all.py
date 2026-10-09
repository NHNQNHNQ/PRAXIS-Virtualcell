from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_OUT = _REPO / "reports" / "phase10"
_TESTS = "praxis_virtualcell/tests"


def _run(junit_name: str, extra_args: list[str]) -> int:
    _OUT.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        _TESTS,
        "-p",
        "no:cacheprovider",
        f"--junitxml={_OUT / junit_name}",
        *extra_args,
    ]
    print(f"[run_phase10_all] {' '.join(cmd)}", flush=True)
    return subprocess.call(cmd, cwd=_REPO)


def main() -> int:

    rc1 = _run("junit-not-llm.xml", ["-m", "not llm"])

    rc2 = _run("junit-full.xml", [])
    print(f"[run_phase10_all] not-llm rc={rc1}  full(including optional LLM network tests) rc={rc2}", flush=True)

    return rc1


if __name__ == "__main__":
    raise SystemExit(main())
