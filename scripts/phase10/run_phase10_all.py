"""Phase 10 全量测试编排 —— 两口径 + junitxml(pytest 核心自带,无新插件)。

产出 reports/phase10/junit-not-llm.xml + junit-full.xml 供 summarize 消费。
**口径纪律(UPGRADE-PROGRESS 血泪)**:稳定基线 -m "not llm";裸口径含 9 条 @pytest.mark.llm
真实网络测试(网络挂时 FAIL 不 skip → 看退出码给假红)。两口径都跑、都存、都显式标注。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_OUT = _REPO / "reports" / "phase10"
_TESTS = "praxis_virtualcell/tests"


def _run(junit_name: str, extra_args: list[str]) -> int:
    _OUT.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-m", "pytest", _TESTS, "-p", "no:cacheprovider",
           f"--junitxml={_OUT / junit_name}", *extra_args]
    print(f"[run_phase10_all] {' '.join(cmd)}", flush=True)
    return subprocess.call(cmd, cwd=_REPO)


def main() -> int:
    # 口径 1:稳定基线(-m "not llm")—— 完成门槛的权威口径
    rc1 = _run("junit-not-llm.xml", ["-m", "not llm"])
    # 口径 2:裸口径(含 llm 真实网络测试)—— 如实标口径,网络挂时可能红
    rc2 = _run("junit-full.xml", [])
    print(f"[run_phase10_all] not-llm rc={rc1}  full(含llm网络) rc={rc2}", flush=True)
    # 稳定基线必须绿;裸口径红可能是网络(summarize 会按测试名区分)
    return rc1


if __name__ == "__main__":
    raise SystemExit(main())
