# P10.A 设计规格:内核固化 + 测试脚手架(T10.1)

> Phase 10 第一子相位。上游:`docs/superpowers/plans/2026-07-08-phase10-deep-validation-roadmap.md`。
> 决策来源:2026-07-08 brainstorm —— message schema 走**扩展内核字段(野心版)**,以**最小侵入策略**落地。

## 一、目标

1. 用测试把 offline 确定性内核焊死(trace/report 重跑字节等价、message schema 合规),为后续 P10.B/C/D 的功能建设立护栏。
2. 把"结构化 schema 化 handoff"从隐性约定升级为**内核显式契约 + bus 强制校验**。
3. 铺好 Phase 10 的测试/benchmark/scripts/reports 目录脚手架。

## 二、范围

**In scope(P10.A)**
- `AgentMessage` 扩展 3 字段(schema_version / trace_id / task_id)+ 确定性生成。
- `MessageBus` run 上下文 + `send()` 回填与校验(拒绝自由文本 handoff)。
- T10.1 三类测试:重跑字节等价、message schema 合规/拒绝、provenance 字段测量。
- 目录脚手架 + baseline 重建 + 全量回归复绿。

**Out of scope(明确划走,避免范围蔓延)**
- **provenance 运行时硬门**("缺 provenance 不进 final report"、per-call hash)→ **P10.C**。P10.A 只做 report 级 provenance 字段的**测试断言(测量)**,不改 runtime 主链。
- 用户 T10.1 清单里的 `provenance`/`status` 字段**不加进 `AgentMessage`**——provenance 属 report 层、status 属 `PredictorResultMessage` 层(已存在),加进通用 message 语义不自然(2026-07-08 决策)。
- 跨模块冲突检测、8 模块接入、前端 e2e → 各自后续子相位。

## 三、现状与影响面(2026-07-08 实测)

- `core/message.py:14` `AgentMessage` 现有 **7 字段**:message_id / sender / receiver / message_type / payload / timestamp / parent_message_id。
- `core/bus.py` `MessageBus.send()` **无任何校验**,仅 record_trace + inbox append。
- 确定性 id 源:`core/config.py:26` `Clock`(`t0001` 递增)、`:37` `IdGen.next()`(`msg_0001`)。
- **offline 两跑已天然字节等价**(probe 证实:`structured_report` + `trace` sha256 全等)——因 Clock/IdGen 确定性、无 wall-clock/随机。
- **构造点**:源码 **23 处** `AgentMessage(...)`(runtime + 15 agents + 4 llm agents + predictors/base 等);tests **37 文件**。
- **baseline 快照**:`tests/baseline/test_baseline_offline_report.py`、`test_baseline_routing_snapshot.py`。

## 四、设计

### 4.1 AgentMessage 扩展(`core/message.py`)

新增 3 字段,**均带 default**(关键:避免炸 23 处构造点):

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
    schema_version: str = "vc.msg.v1"      # 统一 schema 版本
    trace_id: str | None = None            # per-run 追踪 id(整个 workflow 共享),send 时回填
    task_id: str | None = None             # 任务标识,send 时回填
```

语义分层:`message_id` = per-message;`trace_id` = per-run(一次 workflow 内所有 message 同一值);`task_id` = 任务标识(可复用现有 request_id 概念)。

### 4.2 确定性 id 生成(守住字节等价)

- `trace_id` / `task_id` **必须确定性**,否则两跑不等价。
- 生成策略:runtime `build_runtime` 时,从 **request 内容的 canonical hash** 派生:`trace_id = "trace_" + sha256(canonical_request)[:8]`;`task_id` 同源或复用现有 request_id。
- 契约:**同一 request 两跑 → 相同 trace_id/task_id**;不同 request → 不同。→ 新结构下 offline 两跑仍字节等价。

### 4.3 MessageBus 上下文 + send 回填 + 校验(`core/bus.py`)

**两级策略**(平衡"校验严格"与"不炸 37 测试"):

```python
class MessageBus:
    def __init__(self):
        self._trace = []; self._inbox = {}
        self._ctx = {}   # {trace_id, task_id}

    def set_context(self, *, trace_id: str, task_id: str) -> None:
        self._ctx = {"trace_id": trace_id, "task_id": task_id}

    def send(self, message: AgentMessage) -> None:
        self._backfill(message)   # trace_id/task_id 为 None → 从 ctx 回填;ctx 空 → 确定性兜底
        self._validate(message)   # 硬校验:缺硬字段 / payload 非 dict → raise SchemaError
        self.record_trace(message)
        self._inbox.setdefault(message.receiver, []).append(message)
```

- **回填(不 raise)**:`trace_id`/`task_id` 为 None → 从 `_ctx` 取;`_ctx` 空(如未 set_context 的单元测试)→ 确定性兜底(如 `trace_id = f"trace_{message.message_id}"`)。保证非空,不炸 37 测试。
- **硬校验(raise `SchemaError`)**:`message_id`/`sender`/`receiver`/`message_type`/`timestamp`/`schema_version` 任一空 → raise;**`payload` 非 dict(如裸字符串=自由文本 handoff)→ raise**。这些现状构造全满足,不破现有测试;负例测试专门喂非法样本验证拒绝。
- `SchemaError` 复用 `core/exceptions.py` 现有异常(实现时确认;无则新增)。

### 4.4 拒绝语义对齐用户 T10.1 通过标准

| 用户标准 | P10.A 落点 |
|---|---|
| schema compliance = 100% | 每条 message 硬字段齐 + trace_id/task_id 回填保证非空 |
| 自由文本 handoff 必须被拒绝 | `payload` 非 dict → `send` raise SchemaError ✅ |
| 缺 provenance 的 message 必须被拒绝 | **归属澄清**:provenance 是 **report 级**非 message 级;此标准 = P10.C 的 provenance 运行时硬门,不在 P10.A message 校验 |
| 同输入重复运行结果 hash 一致 | T10.1 重跑测试(4.已证天然等价) |

## 五、测试脚手架目录

```
praxis_virtualcell/tests/phase10/__init__.py
praxis_virtualcell/tests/phase10/test_t10_1_runtime_determinism.py
praxis_virtualcell/benchmarks/phase10/        # case yaml,P10.B/C 填(P10.A 建空目录 + README)
praxis_virtualcell/scripts/phase10/           # run_phase10_all/summarize/export_trace_bundle 骨架(占位可跑)
reports/phase10/                              # 生成物目录(.gitkeep)
```
(scripts/reports 顶层位置实现时对齐项目现有 scripts/ 布局;测试与 benchmark 落 `praxis_virtualcell/` 口径下。)

## 六、T10.1 测试清单(`test_t10_1_runtime_determinism.py`)

1. **重跑字节等价**:代表性 req(单模块 accept / abstain / 负例)各跑 3 次 → `structured_report` 与 `trace` 的 canonical-JSON sha256 全等。
2. **message schema 合规**:一次 offline run 后,`bus.trace` 每条 message 经校验器全部合规(硬字段齐 + payload dict + schema_version/trace_id/task_id 非空)。
3. **message schema 拒绝**:构造非法样本 —— payload=裸字符串、缺 sender、payload 非 dict —— 断言 `bus.send` raise `SchemaError`。
4. **trace_id per-run 一致**:同一 run 内所有 message 的 `trace_id` 相同;两跑同 req → trace_id 相同(确定性)。
5. **provenance 字段测量**:offline report 的 provenance 现有必需字段(rules_referenced / models_used / n_messages 等)齐全,缺则 fail(测量级)。

## 七、baseline 重建 + 全量回归(明确 task)

- `AgentMessage` asdict 多 3 字段 → `trace` 序列化结构变 → `test_baseline_offline_report` / `test_baseline_routing_snapshot` 快照**必然变化**:核对新结构仍确定性后**重建快照**。
- 37 个构造 `AgentMessage` 的测试:多数直接构造不经 `send`(不触发校验)、或经 `send` 被回填 → 预期不破;逐一跑通,断言 trace 精确结构的少数测试同步更新。
- **`pytest praxis_virtualcell/tests` 回到全绿**(657+ 基线),新结构下 offline 两跑字节等价重新确立。

## 八、P10.A 完成标准(gate)

1. `AgentMessage` 3 字段扩展 + 确定性生成落地。
2. `MessageBus` set_context + send 回填/校验 + SchemaError 拒绝落地。
3. T10.1 五类测试全绿。
4. baseline 快照重建、`pytest praxis_virtualcell/tests` 全量回归全绿(≥657 passed)。
5. offline 两跑字节等价在新结构下仍成立(测试锁定)。
6. 目录脚手架就位(benchmarks/scripts/reports)。
7. 后端确定性内核未被破坏;根 `tests/` 零触碰;commit trailer 恒 `Co-Authored-By: Claude Opus 4.8`。

## 九、红线

- 改动限 `core/message.py`、`core/bus.py`、`core/runtime.py`(注入 context)+ 必要的构造点微调 + `tests/phase10/` 新增 + baseline 重建;**不碰治理裁决/预测/LLM 边界逻辑**。
- 确定性:新字段确定性生成,不引入 wall-clock/随机,守 offline 字节等价。
- provenance 运行时硬门、per-call hash **不在 P10.A**(P10.C)。
- 不 push;里程碑 tag 本地。

## 十、风险与迁移

- **主风险**:trace 结构变波及 baseline + 断言 trace 的测试。缓解:default 字段 + send 回填把构造点侵入降到最小(核心 3 文件);baseline 重建列为明确 task;全量回归复绿作为 gate 硬指标。
- **确定性风险**:trace_id/task_id 若用非确定性源会打破字节等价。缓解:强制 canonical-hash 派生 + T10.1 测试 4 锁定。
- **测试兼容风险**:未 set_context 的单元测试经 send 时 trace_id 空。缓解:send 回填的确定性兜底(`trace_{message_id}`),不 raise。
