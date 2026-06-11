#!/usr/bin/env python3
"""GAP-AH-3 ship 前门:全量 pytest 回归 + 反幻觉 KPI(best-of-2),任一 fail 非零退出。

用法(controller ship 前):
    PRAXIS_EVAL_EMAIL=… PRAXIS_EVAL_PASSWORD=… .venv/bin/python scripts/ship_gate.py
exit 0=全过可 ship;1=回归或 KPI 不达线;2=凭证缺/KPI 无法运行。
C/D 人工复核见 /tmp/ship_gate_kpi.json + eval --dump-dir。
"""
from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
KPI_BASE = "http://10.102.106.40:8080"
KPI_JSON = "/tmp/ship_gate_kpi.json"


class GateError(Exception):
    """门无法判定(凭证/用法错,exit≥2,不可重跑)。"""


@dataclass
class GateResult:
    pytest_ok: bool
    kpi_ok: bool
    kpi_rcs: list[int] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.pytest_ok and self.kpi_ok


def decide_pytest(run_pytest: Callable[[], int]) -> bool:
    """回归退出码==0 才过(确定性,单跑)。"""
    return run_pytest() == 0


def decide_kpi(run_kpi: Callable[[], int]) -> tuple[bool, list[int]]:
    """best-of-2:run1==0 过;==1 重跑一次(再过则过);≥2 抛 GateError(不重跑)。"""
    rc1 = run_kpi()
    if rc1 == 0:
        return True, [0]
    if rc1 >= 2:
        raise GateError(f"KPI 无法运行(eval exit {rc1}:凭证/用法错,不重跑)")
    rc2 = run_kpi()
    return rc2 == 0, [rc1, rc2]


def run_gate(
    run_pytest: Callable[[], int], run_kpi: Callable[[], int]
) -> GateResult:
    """先全量回归(硬,fail 则短路不跑 KPI),再 KPI(best-of-2)。"""
    if not decide_pytest(run_pytest):
        return GateResult(pytest_ok=False, kpi_ok=False, kpi_rcs=[])
    kpi_ok, rcs = decide_kpi(run_kpi)
    return GateResult(pytest_ok=True, kpi_ok=kpi_ok, kpi_rcs=rcs)


def _pytest_env() -> dict[str, str]:
    """pytest 子进程的 env:剥离 PRAXIS_EVAL_*(门为 KPI 设的凭证)。
    否则 praxis2.config 的严格校验(§6⑤ 拒未知 PRAXIS_* 键)会让实例化 config 的
    测试因 PRAXIS_EVAL_EMAIL/PASSWORD 报 ConfigError(KPI 步保留这俩,pytest 步不需要)。"""
    return {k: v for k, v in os.environ.items() if not k.startswith("PRAXIS_EVAL_")}


def _run_pytest() -> int:
    return subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "--ignore=tests/integration", "-q"],
        cwd=REPO,
        env=_pytest_env(),
    ).returncode


def _run_kpi() -> int:
    # --out/--dump-dir 也指 /tmp:否则 eval 默认 --out 写进 repo 的 docs/test-plans/
    # eval-report.md(spec §10:报告不入库)。
    return subprocess.run(
        [sys.executable, "scripts/eval_v0160.py", "--base", KPI_BASE,
         "--json-out", KPI_JSON, "--out", "/tmp/ship_gate_eval.md",
         "--dump-dir", "/tmp/ship_gate_dump"],
        cwd=REPO,
    ).returncode


def main() -> None:
    if not os.environ.get("PRAXIS_EVAL_EMAIL") or not os.environ.get("PRAXIS_EVAL_PASSWORD"):
        print(
            "缺凭证:设 PRAXIS_EVAL_EMAIL / PRAXIS_EVAL_PASSWORD 后重跑 ship_gate",
            file=sys.stderr,
        )
        raise SystemExit(2)
    try:
        result = run_gate(_run_pytest, _run_kpi)
    except GateError as e:
        print(f"[ship_gate] {e}", file=sys.stderr)
        raise SystemExit(2) from e
    print(
        f"[ship_gate] pytest={'OK' if result.pytest_ok else 'FAIL'} "
        f"KPI={'OK' if result.kpi_ok else 'FAIL'}(KPI rcs={result.kpi_rcs})"
    )
    print(f"  KPI 结构化摘要:{KPI_JSON};C/D dump 见 eval --dump-dir,人工复核")
    raise SystemExit(0 if result.passed else 1)


if __name__ == "__main__":
    main()
