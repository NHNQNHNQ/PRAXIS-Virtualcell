# P10.A 内核固化 + 测试脚手架(T10.1)Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给 `AgentMessage` 扩展 schema_version/trace_id/task_id 三字段并由 `MessageBus.send` 强制 schema 校验(拒绝自由文本 handoff),用 T10.1 测试套件把 offline 确定性内核焊死,铺好 Phase 10 目录脚手架。

**Architecture:** 最小侵入——3 字段带 default 不炸 23 处构造点;`MessageBus` 持 run 上下文,`send()` 两级(trace_id/task_id 缺→回填、硬字段缺/payload 非 dict→raise SchemaError);trace_id 从 request canonical-hash 确定性派生,守住 offline 两跑字节等价。

**Tech Stack:** Python 3、dataclasses、hashlib、pytest。测试口径 `praxis_virtualcell/tests`(裸 `pytest` 会卷入根 tests/,永远显式 `pytest praxis_virtualcell/tests`)。

**上游文档:** spec `docs/superpowers/specs/2026-07-08-phase10a-runtime-determinism-design.md`;roadmap `docs/superpowers/plans/2026-07-08-phase10-deep-validation-roadmap.md`。

**红线:** 后端确定性内核不被破坏;根 `tests/` 零触碰;不引入 wall-clock/随机;不 push;commit trailer 恒 `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`。provenance 运行时硬门/per-call hash 不在本计划(P10.C)。

---

## File Structure

- **Create** `praxis_virtualcell/tests/phase10/__init__.py` — phase10 测试包
- **Create** `praxis_virtualcell/tests/phase10/test_t10_1_runtime_determinism.py` — T10.1 测试套件
- **Create** `praxis_virtualcell/benchmarks/phase10/README.md` — benchmark case 目录占位(P10.B/C 填)
- **Create** `scripts/phase10/__init__.py` + `run_phase10_all.py` / `summarize_phase10.py` / `export_trace_bundle.py` — 骨架(占位可 import,真正实现 P10.D)
- **Create** `reports/phase10/.gitkeep` — 生成物目录
- **Modify** `praxis_virtualcell/core/exceptions.py` — 加 `SchemaError`
- **Modify** `praxis_virtualcell/core/message.py:14` — `AgentMessage` 加 3 字段
- **Modify** `praxis_virtualcell/core/bus.py` — `set_context` + `send` 回填/校验
- **Modify** `praxis_virtualcell/core/runtime.py:46` — `run_workflow` 生成 trace_id/task_id + `bus.set_context`
- **Modify**(如回归暴露)断言 trace asdict 精确结构的少数测试 — Task 7 定位后更新

---

## Task 1: 目录脚手架

**Files:**
- Create: `praxis_virtualcell/tests/phase10/__init__.py`
- Create: `praxis_virtualcell/benchmarks/phase10/README.md`
- Create: `scripts/phase10/__init__.py`
- Create: `scripts/phase10/run_phase10_all.py`
- Create: `scripts/phase10/summarize_phase10.py`
- Create: `scripts/phase10/export_trace_bundle.py`
- Create: `reports/phase10/.gitkeep`

- [ ] **Step 1: 建目录与占位文件**

`praxis_virtualcell/tests/phase10/__init__.py`:空文件。

`praxis_virtualcell/benchmarks/phase10/README.md`:
```markdown
# Phase 10 benchmark cases

case YAML 目录。P10.B 填 module_cases.yaml / end_to_end_cases.yaml;
P10.C 填 negative_cases.yaml / conflict_cases.yaml / llm_assisted_cases.yaml。
P10.A 仅占位。
```

`scripts/phase10/__init__.py`:空文件。

`scripts/phase10/run_phase10_all.py`:
```python
"""Phase 10 全量测试驱动(骨架,真正实现见 P10.D)。"""
from __future__ import annotations

import subprocess
import sys


def main() -> int:
    """当前只跑 phase10 测试子集(占位)。P10.D 扩为全 T10.1-T10.7 编排 + 指标汇总。"""
    return subprocess.call(
        [sys.executable, "-m", "pytest", "praxis_virtualcell/tests/phase10", "-q"]
    )


if __name__ == "__main__":
    raise SystemExit(main())
```

`scripts/phase10/summarize_phase10.py`:
```python
"""Phase 10 结果汇总(骨架,P10.D 实现 PHASE10_SUMMARY.md 生成)。"""
from __future__ import annotations


def main() -> int:
    print("summarize_phase10: 骨架占位,P10.D 实现")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

`scripts/phase10/export_trace_bundle.py`:
```python
"""trace/provenance audit bundle 导出(骨架,P10.D 实现)。"""
from __future__ import annotations


def main() -> int:
    print("export_trace_bundle: 骨架占位,P10.D 实现")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

`reports/phase10/.gitkeep`:空文件。

- [ ] **Step 2: 验证骨架可 import 跑**

Run: `cd /Volumes/T7/PRAXIS-virtualcell && .venv/bin/python scripts/phase10/summarize_phase10.py`
Expected: 打印 `summarize_phase10: 骨架占位,P10.D 实现`,exit 0。

- [ ] **Step 3: Commit**

```bash
git add praxis_virtualcell/tests/phase10 praxis_virtualcell/benchmarks/phase10 scripts/phase10 reports/phase10
git commit -m "chore(phase10a): Task 1 目录脚手架(tests/benchmarks/scripts/reports)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: SchemaError 异常

**Files:**
- Modify: `praxis_virtualcell/core/exceptions.py`
- Test: `praxis_virtualcell/tests/phase10/test_t10_1_runtime_determinism.py`

- [ ] **Step 1: Write the failing test**

在 `test_t10_1_runtime_determinism.py` 写(文件此时新建,顶部加 imports):
```python
from praxis_virtualcell.core.exceptions import PraxisVCError, SchemaError


def test_schema_error_is_praxisvc_error():
    assert issubclass(SchemaError, PraxisVCError)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Volumes/T7/PRAXIS-virtualcell && PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_1_runtime_determinism.py::test_schema_error_is_praxisvc_error -v`
Expected: FAIL — `ImportError: cannot import name 'SchemaError'`。

- [ ] **Step 3: Write minimal implementation**

在 `praxis_virtualcell/core/exceptions.py` 末尾追加:
```python
class SchemaError(PraxisVCError):
    """message/handoff schema 校验失败(缺必需字段 / payload 非 dict / 自由文本 handoff)。"""
```

- [ ] **Step 4: Run test to verify it passes**

Run: 同 Step 2 命令。Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add praxis_virtualcell/core/exceptions.py praxis_virtualcell/tests/phase10/test_t10_1_runtime_determinism.py
git commit -m "feat(phase10a): Task 2 SchemaError 异常(message schema 校验用)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: AgentMessage 3 字段扩展

**Files:**
- Modify: `praxis_virtualcell/core/message.py:14`
- Test: `praxis_virtualcell/tests/phase10/test_t10_1_runtime_determinism.py`

- [ ] **Step 1: Write the failing test**

追加:
```python
from dataclasses import asdict

from praxis_virtualcell.core.message import AgentMessage


def test_agent_message_new_fields_defaults():
    m = AgentMessage("msg_0001", "A", "B", "ping", {"k": 1}, "t0001")
    assert m.schema_version == "vc.msg.v1"
    assert m.trace_id is None
    assert m.task_id is None
    d = asdict(m)
    assert {"schema_version", "trace_id", "task_id"} <= set(d)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Volumes/T7/PRAXIS-virtualcell && PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_1_runtime_determinism.py::test_agent_message_new_fields_defaults -v`
Expected: FAIL — `AttributeError: 'AgentMessage' object has no attribute 'schema_version'`。

- [ ] **Step 3: Write minimal implementation**

`praxis_virtualcell/core/message.py` 的 `AgentMessage` 改为(在 `parent_message_id` 后加 3 字段):
```python
@dataclass
class AgentMessage:
    message_id: str
    sender: str
    receiver: str
    message_type: str
    payload: dict[str, Any]
    timestamp: str
    parent_message_id: str | None = None
    schema_version: str = "vc.msg.v1"   # 统一 message schema 版本
    trace_id: str | None = None         # per-run 追踪 id(bus.send 回填)
    task_id: str | None = None          # 任务标识(bus.send 回填)
```

- [ ] **Step 4: Run test to verify it passes**

Run: 同 Step 2。Expected: PASS。

- [ ] **Step 5: 冒烟确认现有 message/trace 测试未破**

Run: `cd /Volumes/T7/PRAXIS-virtualcell && PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_message_bus.py praxis_virtualcell/tests/test_message_types.py praxis_virtualcell/tests/test_trace.py -q`
Expected: 全 PASS(新字段带 default,现有构造不受影响)。若有 FAIL,记录待 Task 7 统一处理,先不改。

- [ ] **Step 6: Commit**

```bash
git add praxis_virtualcell/core/message.py praxis_virtualcell/tests/phase10/test_t10_1_runtime_determinism.py
git commit -m "feat(phase10a): Task 3 AgentMessage 加 schema_version/trace_id/task_id(带 default)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: MessageBus set_context + send 回填

**Files:**
- Modify: `praxis_virtualcell/core/bus.py`
- Test: `praxis_virtualcell/tests/phase10/test_t10_1_runtime_determinism.py`

- [ ] **Step 1: Write the failing test**

追加:
```python
from praxis_virtualcell.core.bus import MessageBus


def test_bus_backfills_trace_and_task_from_context():
    bus = MessageBus()
    bus.set_context(trace_id="trace_abc", task_id="task_xyz")
    bus.send(AgentMessage("msg_0001", "A", "B", "ping", {"k": 1}, "t0001"))
    m = bus.trace[0]
    assert m.trace_id == "trace_abc"
    assert m.task_id == "task_xyz"


def test_bus_backfills_deterministic_fallback_without_context():
    bus = MessageBus()  # 未 set_context
    bus.send(AgentMessage("msg_0007", "A", "B", "ping", {"k": 1}, "t0001"))
    m = bus.trace[0]
    assert m.trace_id == "trace_msg_0007"   # 确定性兜底,不 raise
    assert m.task_id == "task_msg_0007"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Volumes/T7/PRAXIS-virtualcell && PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_1_runtime_determinism.py -k backfill -v`
Expected: FAIL — `AttributeError: 'MessageBus' object has no attribute 'set_context'`。

- [ ] **Step 3: Write minimal implementation**

`praxis_virtualcell/core/bus.py`:`__init__` 加 `self._ctx`,新增 `set_context`/`_backfill`,`send` 先回填。改动后 `bus.py`:
```python
"""唯一通讯通道:agent 只经 bus 收发,不互调内部方法。bus 记全量 trace 可 replay。"""
from __future__ import annotations

import json
from dataclasses import asdict

from praxis_virtualcell.core.exceptions import SchemaError
from praxis_virtualcell.core.message import AgentMessage

_REQUIRED = ("message_id", "sender", "receiver", "message_type", "timestamp", "schema_version")


class MessageBus:
    def __init__(self) -> None:
        self._trace: list[AgentMessage] = []
        self._inbox: dict[str, list[AgentMessage]] = {}
        self._ctx: dict[str, str] = {}

    def set_context(self, *, trace_id: str, task_id: str) -> None:
        """runtime build/run 时注入本次 run 的 trace_id/task_id,供 send 回填。"""
        self._ctx = {"trace_id": trace_id, "task_id": task_id}

    def _backfill(self, message: AgentMessage) -> None:
        if message.trace_id is None:
            message.trace_id = self._ctx.get("trace_id") or f"trace_{message.message_id}"
        if message.task_id is None:
            message.task_id = self._ctx.get("task_id") or f"task_{message.message_id}"

    def send(self, message: AgentMessage) -> None:
        self._backfill(message)
        self.record_trace(message)
        self._inbox.setdefault(message.receiver, []).append(message)

    def record_trace(self, message: AgentMessage) -> None:
        self._trace.append(message)

    def get_messages(self, agent_name: str) -> list[AgentMessage]:
        return list(self._inbox.get(agent_name, []))

    @property
    def trace(self) -> list[AgentMessage]:
        return list(self._trace)

    def has_message_type(self, message_type: str) -> bool:
        return any(m.message_type == message_type for m in self._trace)

    def latest(self, message_type: str) -> AgentMessage | None:
        for m in reversed(self._trace):
            if m.message_type == message_type:
                return m
        return None

    def export_trace(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump([asdict(m) for m in self._trace], f, ensure_ascii=False, indent=2)
```
(注:`_REQUIRED` 与 `SchemaError` import 供 Task 5 的 `_validate` 用,本 Task 先落地。)

- [ ] **Step 4: Run test to verify it passes**

Run: 同 Step 2。Expected: PASS(两个 backfill 测试)。

- [ ] **Step 5: Commit**

```bash
git add praxis_virtualcell/core/bus.py praxis_virtualcell/tests/phase10/test_t10_1_runtime_determinism.py
git commit -m "feat(phase10a): Task 4 MessageBus set_context + send 回填(trace_id/task_id)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: MessageBus send schema 校验(拒绝自由文本 handoff)

**Files:**
- Modify: `praxis_virtualcell/core/bus.py`(`send` 加 `_validate`)
- Test: `praxis_virtualcell/tests/phase10/test_t10_1_runtime_determinism.py`

- [ ] **Step 1: Write the failing test**

追加:
```python
import pytest

from praxis_virtualcell.core.exceptions import SchemaError


def test_bus_rejects_non_dict_payload():
    bus = MessageBus()
    bus.set_context(trace_id="trace_abc", task_id="task_xyz")
    bad = AgentMessage("msg_0001", "A", "B", "ping", "free text handoff", "t0001")  # payload 非 dict
    with pytest.raises(SchemaError):
        bus.send(bad)


def test_bus_rejects_missing_hard_field():
    bus = MessageBus()
    bus.set_context(trace_id="trace_abc", task_id="task_xyz")
    bad = AgentMessage("msg_0001", "", "B", "ping", {"k": 1}, "t0001")  # sender 空
    with pytest.raises(SchemaError):
        bus.send(bad)


def test_bus_accepts_valid_message():
    bus = MessageBus()
    bus.set_context(trace_id="trace_abc", task_id="task_xyz")
    bus.send(AgentMessage("msg_0001", "A", "B", "ping", {"k": 1}, "t0001"))
    assert len(bus.trace) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Volumes/T7/PRAXIS-virtualcell && PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_1_runtime_determinism.py -k "rejects or accepts_valid" -v`
Expected: FAIL — `test_bus_rejects_non_dict_payload`/`missing_hard_field` 未 raise(send 目前不校验)。

- [ ] **Step 3: Write minimal implementation**

`bus.py` 加 `_validate` 并在 `send` 回填后调用(payload 校验用 `isinstance(dict)`):
```python
    def _validate(self, message: AgentMessage) -> None:
        for f in _REQUIRED:
            if not getattr(message, f):
                raise SchemaError(f"message 缺必需字段: {f}")
        if not isinstance(message.payload, dict):
            raise SchemaError(
                f"payload 必须是 dict(禁止自由文本 handoff),实际: {type(message.payload).__name__}")

    def send(self, message: AgentMessage) -> None:
        self._backfill(message)
        self._validate(message)
        self.record_trace(message)
        self._inbox.setdefault(message.receiver, []).append(message)
```

- [ ] **Step 4: Run test to verify it passes**

Run: 同 Step 2。Expected: PASS(3 个校验测试)。

- [ ] **Step 5: Commit**

```bash
git add praxis_virtualcell/core/bus.py praxis_virtualcell/tests/phase10/test_t10_1_runtime_determinism.py
git commit -m "feat(phase10a): Task 5 MessageBus send schema 校验(拒绝非 dict payload/缺硬字段)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: runtime 生成确定性 trace_id/task_id + set_context

**Files:**
- Modify: `praxis_virtualcell/core/runtime.py`(`run_workflow` 开头)
- Test: `praxis_virtualcell/tests/phase10/test_t10_1_runtime_determinism.py`

- [ ] **Step 1: Write the failing test**

追加(用 offline 端到端跑 + 检查 trace 的 trace_id):
```python
from praxis_virtualcell.core.config import Mode, RuntimeConfig
from praxis_virtualcell.workflows.run_virtualcell_query import run_query

_REQ = {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["AHR"],
        "input_modality": "scRNA", "output_modality": "delta_expression",
        "task_type": "predict_delta_expression"}
_CFG = RuntimeConfig(mode=Mode.OFFLINE)


def _trace_ids(out):
    return {step.get("trace_id") for step in out["trace"] if isinstance(step, dict)}


def test_trace_id_is_per_run_consistent():
    out = run_query(dict(_REQ), config=_CFG)
    ids = _trace_ids(out)
    assert len(ids) == 1                 # 同一 run 所有 message 同一 trace_id
    assert None not in ids               # 已回填
    assert next(iter(ids)).startswith("trace_")


def test_trace_id_deterministic_across_runs():
    a = _trace_ids(run_query(dict(_REQ), config=_CFG))
    b = _trace_ids(run_query(dict(_REQ), config=_CFG))
    assert a == b                        # 两跑同 req → 同 trace_id
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Volumes/T7/PRAXIS-virtualcell && PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_1_runtime_determinism.py -k "trace_id" -v`
Expected: FAIL — 当前 trace_id 靠 send 兜底 `trace_{message_id}`,每条 message 的 message_id 不同 → `len(ids)` != 1。

- [ ] **Step 3: Write minimal implementation**

`praxis_virtualcell/core/runtime.py`:顶部 import 加 `hashlib`;`run_workflow` 开头(`:47` 的 docstring 后、第一个 `mk_message` 前)插入 trace_id/task_id 生成 + `set_context`:
```python
    def run_workflow(self, request) -> dict:
        """request: VirtualCellRequest。返回最终 report dict。全程经 bus。"""
        _req_dict = asdict(request)
        _h = hashlib.sha256(
            json.dumps(_req_dict, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()[:8]
        self.bus.set_context(trace_id=f"trace_{_h}", task_id=f"task_{_h}")
        m = self.mk_message("client", "InputInterpreter", "parse_request",
                            {"request_dict": _req_dict})
        # ...(其余不变)
```
(注:`json`/`asdict` 已在 runtime.py 顶部 import;只需新增 `import hashlib`。复用 `_req_dict` 替代原 `asdict(request)`。)

- [ ] **Step 4: Run test to verify it passes**

Run: 同 Step 2。Expected: PASS(per-run 一致 + 两跑确定性)。

- [ ] **Step 5: Commit**

```bash
git add praxis_virtualcell/core/runtime.py praxis_virtualcell/tests/phase10/test_t10_1_runtime_determinism.py
git commit -m "feat(phase10a): Task 6 runtime 生成确定性 trace_id/task_id(request canonical-hash)+ set_context

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 7: 全量回归 + 修复受 trace 结构影响的测试

**Files:**
- Modify:(回归暴露的、直接断言 trace asdict 精确结构的测试,逐个核对)

- [ ] **Step 1: 跑全量回归定位受影响测试**

Run: `cd /Volumes/T7/PRAXIS-virtualcell && PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q 2>&1 | tail -30`
Expected:绝大多数 PASS;可能少数断言 trace/message asdict 精确字段集或 export_trace 输出结构的测试 FAIL(因多了 schema_version/trace_id/task_id)。记录 FAIL 清单。

- [ ] **Step 2: 逐个核对并更新受影响断言**

对每个 FAIL:确认失败原因是"新增 3 字段导致 asdict/结构断言不匹配"(**非** 语义回归),核对新结构正确后更新断言使其接纳新字段(如把精确字段集断言改为 `⊇` 子集断言,或补上 3 个新键)。**若发现任何非新增字段导致的语义变化(如某 message 丢失、trace 步数变、reliability 变),停下排查——那是真实回归,不改测试迁就。**

- [ ] **Step 3: 全量回归复绿**

Run: `cd /Volumes/T7/PRAXIS-virtualcell && PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q 2>&1 | tail -5`
Expected: `657+ passed`(至少不低于基线 657 passed/39 skipped/0 failed;新增 phase10 测试使 passed 上升),0 failed。

- [ ] **Step 4: Commit**

```bash
git add -A praxis_virtualcell/tests
git commit -m "test(phase10a): Task 7 全量回归复绿(受 message 3 字段影响的 trace 断言更新)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 8: T10.1 确定性重放 + provenance 测量 + P10.A gate 勾账

**Files:**
- Modify: `praxis_virtualcell/tests/phase10/test_t10_1_runtime_determinism.py`(补重跑等价 + schema 合规 + provenance 测量)
- Modify: `docs/superpowers/plans/UPGRADE-PROGRESS.md`(P10.A 勾账 + 事件日志)

- [ ] **Step 1: Write the T10.1 determinism/compliance/provenance tests**

追加:
```python
import hashlib
import json as _json


def _canon_hash(obj) -> str:
    return hashlib.sha256(
        _json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    ).hexdigest()


_ACCEPT = dict(_REQ)
_ABSTAIN = {"species": "bacteria", "perturbation_type": "gene", "perturbation_targets": ["b0720"],
            "input_modality": "scRNA", "output_modality": "delta_expression",
            "task_type": "predict_delta_expression"}


@pytest.mark.parametrize("req", [_ACCEPT, _ABSTAIN], ids=["accept", "abstain"])
def test_offline_rerun_byte_equal(req):
    outs = [run_query(dict(req), config=_CFG) for _ in range(3)]
    sr_hashes = {_canon_hash(o["structured_report"]) for o in outs}
    tr_hashes = {_canon_hash(o["trace"]) for o in outs}
    assert len(sr_hashes) == 1, "structured_report 三跑不一致"
    assert len(tr_hashes) == 1, "trace 三跑不一致"


def test_trace_messages_schema_compliant():
    out = run_query(dict(_ACCEPT), config=_CFG)
    for step in out["trace"]:
        assert isinstance(step, dict)
        for f in ("message_id", "sender", "receiver", "message_type", "timestamp",
                  "schema_version", "trace_id", "task_id"):
            assert step.get(f), f"trace message 缺 {f}: {step}"
        assert isinstance(step["payload"], dict)


def test_offline_report_provenance_fields_present():
    out = run_query(dict(_ACCEPT), config=_CFG)
    prov = out["provenance"]
    for f in ("rules_referenced", "models_used", "n_messages"):
        assert f in prov, f"provenance 缺字段 {f}"
```
(注:`out["trace"]` 是 asdict 列表还是 AgentMessage 列表,取决于 `run_query` 序列化;若为对象则改 `step.trace_id`/`getattr`。执行时先 `print(type(out["trace"][0]))` 确认,再定 `step.get` vs `getattr`——probe 已知 run_query 的 trace 单步是 dict。)

- [ ] **Step 2: Run T10.1 suite**

Run: `cd /Volumes/T7/PRAXIS-virtualcell && PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_1_runtime_determinism.py -v`
Expected: 全 PASS(重跑等价 accept+abstain、schema 合规、provenance 字段齐、Task 2-6 的既有断言)。

- [ ] **Step 3: 全量回归最终确认**

Run: `cd /Volumes/T7/PRAXIS-virtualcell && PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q 2>&1 | tail -5`
Expected: 0 failed;passed ≥ 657 + phase10 新增。

- [ ] **Step 4: 台账勾账 P10.A**

在 `docs/superpowers/plans/UPGRADE-PROGRESS.md` 事件日志末尾追加一行(格式对齐现有):记 P10.A 完成(message 3 字段扩展 + bus 校验 + T10.1 套件 + 全量回归复绿的实际 passed 数 + 提交范围仅 core/tests/scripts/docs 后端确定性内核未破坏)。相位表 Phase 10 行状态更新为 `P10.A✓ → 进 P10.B`。

- [ ] **Step 5: Commit**

```bash
git add praxis_virtualcell/tests/phase10/test_t10_1_runtime_determinism.py docs/superpowers/plans/UPGRADE-PROGRESS.md
git commit -m "test(phase10a): Task 8 T10.1 重跑字节等价+schema 合规+provenance 测量 + P10.A 勾账

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review(计划 vs spec 覆盖)

- **spec §4.1 AgentMessage 3 字段** → Task 3 ✅
- **spec §4.2 确定性 id** → Task 6(canonical-hash 派生)+ Task 8(两跑等价锁定)✅
- **spec §4.3 set_context + 回填 + 校验** → Task 4(回填)+ Task 5(校验)✅
- **spec §4.4 拒绝自由文本 handoff** → Task 5(payload 非 dict raise)✅
- **spec §五 脚手架目录** → Task 1 ✅
- **spec §六 T10.1 五类测试** → Task 3-6 分散 + Task 8 集中(重跑等价/schema 合规/拒绝/trace_id 一致/provenance 测量)✅
- **spec §七 baseline 重建 + 全量回归** → Task 7 ✅(勘察后确认两 baseline 不 hash trace,回归面收敛为"少数 trace 断言测试更新")
- **spec §八 完成标准** → Task 8 gate ✅
- **provenance 运行时硬门划走 P10.C** → 计划仅 Task 8 做 report 级字段测量,未碰 runtime provenance 门 ✅

无占位;类型一致(`SchemaError`/`set_context`/`trace_id`/`task_id`/`_validate`/`_backfill` 跨 Task 命名一致)。
