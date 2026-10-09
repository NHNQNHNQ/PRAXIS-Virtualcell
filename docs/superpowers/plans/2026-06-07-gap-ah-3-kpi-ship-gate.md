# GAP-AH-3 反幻觉 KPI 纳 ship 前门 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 提供本地 pre-ship 门 `scripts/ship_gate.py`(全量 pytest 回归 + 反幻觉 KPI best-of-2,任一 fail 非零退出),并让 `eval_v0160.py` 可被脚本断言(退出码)+ 输出结构化摘要。

**Architecture:** eval 抽纯函数 `compute_kpi_summary` 算通过线 + 加退出码(0过/1不达线/2凭证错)+ `--json-out`;新 `scripts/ship_gate.py` 用注入式 runner 实现 best-of-2 决策(纯函数可单测),CLI 壳用真 subprocess 跑 pytest + eval;HANDOFF 部署 SOP 加门步骤。现有 GitHub Actions(hermetic 够不到 staging)不动。

**Tech Stack:** Python 3.11、pytest、subprocess、argparse。参考 spec:`docs/superpowers/specs/2026-06-07-gap-ah-3-kpi-ship-gate-design.md`。流程:main 直接干(无 worktree),逐 task TDD;门自身实跑验证 controller 亲做。commit 末尾 `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`。

---

## 文件结构

| 文件 | 职责 | 动作 |
|---|---|---|
| `scripts/eval_v0160.py` | KPI 评测 | 抽 `compute_kpi_summary` 纯函数 + 退出码(0/1/2)+ `--json-out` |
| `scripts/ship_gate.py` | ship 前门 | 新建:best-of-2 决策(纯函数)+ CLI(真跑 pytest+eval) |
| `HANDOFF.md` | 部署 SOP | 加"ship 前必跑门"一步 |
| `tests/test_eval_kpi_summary.py` | 新:compute_kpi_summary + 退出码 |
| `tests/test_ship_gate.py` | 新:门决策矩阵 + CLI 凭证校验 |

测试运行:`.venv/bin/python -m pytest <path> -v`。全量回归:`.venv/bin/python -m pytest tests/ --ignore=tests/integration -q`。

---

## Task 1: eval_v0160.py — compute_kpi_summary 纯函数 + 退出码 + --json-out

**Files:**
- Modify: `scripts/eval_v0160.py`(import sys;新增 `compute_kpi_summary`;`main()` 用它;退出码;`--json-out`)
- Test: `tests/test_eval_kpi_summary.py`(新)

- [ ] **Step 1: 写失败测试**

新建 `tests/test_eval_kpi_summary.py`:
```python
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
```
注:`from scripts.eval_v0160 import ...` 需 scripts 可 import。先确认仓库根有 `pyproject.toml`/`conftest` 使 `scripts/` 可导入(本仓库 test 用 `from scripts.xxx` 形式已有先例则照搬;若不行,改 `import importlib.util` 加载,或在 `tests/conftest.py` 加 `sys.path`。先 grep `from scripts` 看现有 test 怎么导 scripts 模块)。

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv/bin/python -m pytest tests/test_eval_kpi_summary.py -v`
Expected: FAIL(`ImportError: cannot import name 'compute_kpi_summary'`)

- [ ] **Step 3: 实现 compute_kpi_summary + 重构 main 使用它**

在 `scripts/eval_v0160.py` 顶部 import 区(现有 `import re` 等之间)加 `import sys`。

在 `main()` 之前(模块级)加纯函数:
```python
def compute_kpi_summary(counts: dict, safety_counts: dict) -> dict:
    """从 A/B/C/D 计数 + 安全计数算通过线判定 + 各比率。纯函数,可单测。
    通过线:A+B≥80% / C≤10% / D=0 / S-FAIL=0(§6.2)。"""
    n = sum(counts.values()) or 1  # 主 KPI 只统计 A/B/C/D(排除 safety)
    ab_ratio = (counts.get("A", 0) + counts.get("B", 0)) / n
    c_ratio = counts.get("C", 0) / n
    d_ratio = counts.get("D", 0) / n
    passed = (
        ab_ratio >= 0.80 and c_ratio <= 0.10
        and counts.get("D", 0) == 0 and safety_counts.get("S-FAIL", 0) == 0
    )
    return {
        "passed": passed, "ab_ratio": ab_ratio, "c_ratio": c_ratio, "d_ratio": d_ratio,
        "counts": dict(counts), "safety": dict(safety_counts), "n_conversations": n,
    }
```

在 `main()` 内,把现有计算块(约行 472-479):
```python
    n = sum(counts.values()) or 1  # 主 KPI 只统计 A/B/C/D case(排除 safety)
    ab_ratio = (counts["A"] + counts["B"]) / n
    c_ratio = counts["C"] / n
    d_ratio = counts["D"] / n
    passed = (
        ab_ratio >= 0.80 and c_ratio <= 0.10
        and counts["D"] == 0 and safety_counts["S-FAIL"] == 0
    )
```
替换为:
```python
    _summary = compute_kpi_summary(counts, safety_counts)
    n = _summary["n_conversations"]
    ab_ratio = _summary["ab_ratio"]
    c_ratio = _summary["c_ratio"]
    d_ratio = _summary["d_ratio"]
    passed = _summary["passed"]
```
(下方 markdown 构建沿用 `n`/`ab_ratio`/`c_ratio`/`d_ratio`/`passed`,不变。)

- [ ] **Step 4: 跑测试确认通过 + 全量 eval 测试无回归**

Run: `.venv/bin/python -m pytest tests/test_eval_kpi_summary.py -v`
Expected: PASS(6 passed)
Run: `.venv/bin/python -m pytest tests/ -k "eval" -q`
Expected: PASS(确认 eval 相关现有测试无回归)

- [ ] **Step 5: 加 --json-out 参数 + 写结构化摘要**

在 argparse 段(`p.add_argument("--ids", …)` 附近)加:
```python
    p.add_argument("--json-out", default="", help="(可选)结构化摘要 JSON 输出路径(供 ship_gate 解析)")
```
在 `main()` 末尾、现有 `print(f"\n📄 报告:{args.out}")` 之前,加(复用 `_summary`):
```python
    if args.json_out:
        from pathlib import Path as _Path  # 顶部已 import Path 则用现有
        _payload = {**_summary, "commit": _commit, "model": args.model}
        _Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        _Path(args.json_out).write_text(
            json.dumps(_payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
```
(`_commit` 在行 482-485 已算出;若 `--json-out` 写入点在 `_commit` 计算之后即可,确认顺序——把 json-out 写入放在 markdown 报告写入附近、`_commit` 之后。)

- [ ] **Step 6: 加退出码(0/1/2)**

把现有凭证缺失(约行 438-443):
```python
    if not args.session and (not args.email or not args.password):
        raise SystemExit(
            "缺凭证:传 --session,或同时传 --email/--password,"
            "或设环境变量 PRAXIS_EVAL_EMAIL / PRAXIS_EVAL_PASSWORD"
        )
```
改为(显式 exit 2,区分于 KPI 不达线的 exit 1):
```python
    if not args.session and (not args.email or not args.password):
        print(
            "缺凭证:传 --session,或同时传 --email/--password,"
            "或设环境变量 PRAXIS_EVAL_EMAIL / PRAXIS_EVAL_PASSWORD",
            file=sys.stderr,
        )
        raise SystemExit(2)
```
在 `main()` 最末(现有 `print(f"   通过: {passed}…")` 之后)加:
```python
    raise SystemExit(0 if passed else 1)
```

- [ ] **Step 7: 验证退出码(creds-missing → 2)**

在 `tests/test_eval_kpi_summary.py` 追加(subprocess 实测,不联网——凭证检查在 run 循环之前):
```python
import subprocess
import sys
from pathlib import Path

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
```
Run: `.venv/bin/python -m pytest tests/test_eval_kpi_summary.py -v`
Expected: PASS(7 passed)

- [ ] **Step 8: commit**

```bash
git add scripts/eval_v0160.py tests/test_eval_kpi_summary.py
git commit -m "feat(eval): compute_kpi_summary 纯函数 + 退出码(0/1/2) + --json-out(GAP-AH-3)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: scripts/ship_gate.py — best-of-2 门(纯核心 + CLI)

**Files:**
- Create: `scripts/ship_gate.py`
- Test: `tests/test_ship_gate.py`(新)

- [ ] **Step 1: 写失败测试**

新建 `tests/test_ship_gate.py`:
```python
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
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv/bin/python -m pytest tests/test_ship_gate.py -v`
Expected: FAIL(`ModuleNotFoundError: No module named 'scripts.ship_gate'`)

- [ ] **Step 3: 实现 scripts/ship_gate.py**

```python
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


def _run_pytest() -> int:
    return subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "--ignore=tests/integration", "-q"],
        cwd=REPO,
    ).returncode


def _run_kpi() -> int:
    return subprocess.run(
        [sys.executable, "scripts/eval_v0160.py", "--base", KPI_BASE,
         "--json-out", KPI_JSON],
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
```

- [ ] **Step 4: 跑测试确认通过**

Run: `.venv/bin/python -m pytest tests/test_ship_gate.py -v`
Expected: PASS(10 passed)

- [ ] **Step 5: commit**

```bash
git add scripts/ship_gate.py tests/test_ship_gate.py
git commit -m "feat(ship_gate): ship 前门 pytest 回归 + KPI best-of-2(GAP-AH-3)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: HANDOFF.md — 部署 SOP 加门步骤

**Files:**
- Modify: `HANDOFF.md`(部署 SOP 段,约行 56+)

- [ ] **Step 1: 编辑**

在 `HANDOFF.md` 的 "## 部署 SOP" 段开头(全量回归命令之前或之后)插入:
```markdown
- **ship 前必跑门(GAP-AH-3)**:`PRAXIS_EVAL_EMAIL=… PRAXIS_EVAL_PASSWORD=… .venv/bin/python scripts/ship_gate.py`
  跑全量 pytest 回归 + 反幻觉 KPI(best-of-2,fail 自动重跑一次);exit 0 才 ship。
  凭证问用户取(不入库)。C/D 人工复核见 `/tmp/ship_gate_kpi.json` + eval dump。
  (KPI 跑不进 hermetic GitHub Actions——够不到内网 staging;故本地门。)
```

- [ ] **Step 2: 确认渲染 + commit**

Run: `grep -n "ship_gate" HANDOFF.md`
Expected: 命中新增行
```bash
git add HANDOFF.md
git commit -m "docs(handoff): 部署 SOP 加 ship 前门 scripts/ship_gate.py(GAP-AH-3)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4(controller 亲做,非 subagent):门自身实跑验证 + 全量回归

- [ ] 全量回归零失败:`.venv/bin/python -m pytest tests/ --ignore=tests/integration -q --tb=short --junit-xml=/tmp/r.xml >/dev/null 2>&1; echo EXIT=$?` + 解析 junit `failures=0`。
- [ ] 设真凭证实跑门一次:`PRAXIS_EVAL_EMAIL=… PRAXIS_EVAL_PASSWORD=… .venv/bin/python scripts/ship_gate.py`;确认 ① pytest 段过 ② KPI 段 best-of-2 行为(若首跑不达线自动重跑)③ 退出码正确 ④ `/tmp/ship_gate_kpi.json` 产出且字段正确。
- [ ] 更新 memory(GAP-AH-3 ship)+ MEMORY.md。

---

## Self-Review(计划对 spec 覆盖核对)

- **spec §4.1 eval 退出码 + compute_kpi_summary + --json-out** → Task 1(Step 3 纯函数 + Step 5 json-out + Step 6 退出码 + Step 7 creds-exit-2 验证)✅
- **spec §4.2 ship_gate.py best-of-2 纯核心 + CLI** → Task 2(decide_kpi/decide_pytest/run_gate 纯函数 + CLI + 单测矩阵)✅
- **spec §4.3 HANDOFF SOP** → Task 3 ✅
- **spec §7 测试**:compute_kpi_summary 矩阵 + creds-exit-2(Task 1)/ best-of-2 矩阵 + pytest-fail 短路 + CLI 缺凭证 exit2(Task 2)✅
- **spec §8 验收 / 门实跑** → Task 4(controller)✅
- **占位扫描**:每步真代码/真命令/预期;唯一需执行期确认的是"scripts/ 可 import"(Task 1 Step 1 已给排查指引:grep 现有 `from scripts` 用法,不行则 conftest 加 sys.path)——非占位,是显式校验点。
- **类型/命名一致**:`compute_kpi_summary`(Task1 定义、Task2 间接经 eval 退出码用)/ `decide_kpi`/`decide_pytest`/`run_gate`/`GateResult`/`GateError`(Task2 定义+测试)跨 task 命名一致;退出码语义(0/1/2)eval 与 ship_gate 一致(ship_gate `decide_kpi` 按 eval 的 0/1/≥2 分支)。

**执行期微调点(非占位)**:`from scripts.xxx` 的可导入性(Task1 Step1 已指引);`--json-out` 写入点相对 `_commit` 计算的顺序(Task1 Step5 已注明放 `_commit` 之后)。
