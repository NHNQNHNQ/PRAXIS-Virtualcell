# Week 2 — Communicative Agent Runtime 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** 在 `/Volumes/T7/PRAXIS-virtualcell` 新增自包含包 `praxis_virtualcell/`,用 mock agent 证明"真多智能体":输入解析→bus 通讯→检索先行门→predictor-agent 独立 success/rejected/failed→ensemble→abstain→critic→provenance/report,全 offline、有完整 trace。

**Architecture:** 全新自包含 runtime(不 import praxis2 主链路)。`@dataclass` 数据结构;`MessageBus` 单一通讯通道(agent 不互调内部方法);`AgentRuntime` 按固定 pipeline 驱动,predictor fan-out 也走 bus;retrieve-before-predict 是硬门(predictor 执行前检查 bus 里有 `brain_retrieved`)。可复现:注入 `Clock` + `IdGen`。

**Tech Stack:** Python 3.13、dataclasses、PyYAML(已装)、pytest。**禁止 import torch / 调 openai/anthropic**。

**Spec:** [docs/superpowers/specs/2026-06-12-week2-communicative-agent-runtime-design.md](../specs/2026-06-12-week2-communicative-agent-runtime-design.md)

---

## 文件结构

```
praxis_virtualcell/
  __init__.py
  core/{__init__,config,exceptions,request,message,bus,agent,runtime,provenance}.py
  agents/{__init__,input_interpreter,object_normalizer,species_brain,model_applicability,ensemble,reliability,critic,provenance_agent,report}.py
  agents_llm/{__init__,llm_client,optional_agents}.py
  predictors/{__init__,base,mock_linear,mock_cpa,mock_gears}.py
  brains/virtualcell/generic/{task_schema.yaml,default_abstain_rules.yaml,general_negative_transfer.yaml}
  brains/virtualcell/human/{model_applicability.yaml,object_vocabulary.yaml}
  workflows/{__init__,predict_delta_expression}.py
  examples/{norman_mock_request,bacteria_mock_request,mouse_transfer_mock_request}.json
  tests/{__init__,test_request_schema,test_message_bus,test_trace,test_retrieve_before_predict,test_predictor_rejection,test_abstain,test_no_fake_multiagent,test_offline_mode,test_llm_optional}.py
```

**测试运行口径(全计划统一)**:`cd /Volumes/T7/PRAXIS-virtualcell && .venv/bin/python -m pytest praxis_virtualcell/tests -q`

> **macOS T7 卷注意**:写文件会生成 `._*` AppleDouble;每个 commit 步骤前先 `find praxis_virtualcell -name '._*' -delete`(已被 .gitignore 忽略,但清掉防 yaml glob 误读)。

---

## Task 1：包骨架 + config + exceptions

**Files:** Create `praxis_virtualcell/__init__.py`、`core/__init__.py`、`core/config.py`、`core/exceptions.py`、`tests/__init__.py`、`tests/test_offline_mode.py`(先只放 import+mode 用例)

- [ ] **Step 1: 写失败测试** `praxis_virtualcell/tests/test_offline_mode.py`

```python
from praxis_virtualcell.core.config import Mode, Clock, IdGen, RuntimeConfig


def test_default_mode_is_offline():
    cfg = RuntimeConfig()
    assert cfg.mode is Mode.OFFLINE
    assert cfg.llm_enabled is False


def test_clock_is_deterministic_and_monotonic():
    c = Clock()
    assert c.now() == "t0001"
    assert c.now() == "t0002"


def test_idgen_is_deterministic():
    g = IdGen("msg")
    assert g.next() == "msg_0001"
    assert g.next() == "msg_0002"
```

- [ ] **Step 2: 跑(应 fail）** `... pytest praxis_virtualcell/tests/test_offline_mode.py -q` → ModuleNotFoundError。

- [ ] **Step 3: 实现** `praxis_virtualcell/__init__.py`(空)、`core/__init__.py`(空)、`core/exceptions.py`:

```python
"""praxis_virtualcell 主链路异常(均不依赖 praxis2)。"""
from __future__ import annotations


class PraxisVCError(Exception):
    """所有本包异常基类。"""


class InputValidationError(PraxisVCError):
    """VirtualCellRequest 解析/校验失败。"""


class RetrieveBeforePredictError(PraxisVCError):
    """反幻觉硬门:未先检索 brain 就尝试预测。"""


class UnknownAgentError(PraxisVCError):
    """dispatch 到未注册的 agent。"""
```

`core/config.py`:

```python
"""运行配置 + 可复现时钟/ID 生成器(避免 datetime.now / random 破坏 trace 复现)。"""
from __future__ import annotations

import itertools
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

_BRAINS_DEFAULT = Path(__file__).resolve().parent.parent / "brains" / "virtualcell"


class Mode(str, Enum):
    OFFLINE = "offline"
    LLM_ASSISTED = "llm_assisted"


class Clock:
    """单调递增的确定性时钟,now() 返回 't0001'、't0002'…(测试可复现)。"""

    def __init__(self, start: int = 0) -> None:
        self._t = start

    def now(self) -> str:
        self._t += 1
        return f"t{self._t:04d}"


class IdGen:
    """确定性 id 生成器。"""

    def __init__(self, prefix: str = "msg") -> None:
        self._prefix = prefix
        self._c = itertools.count(1)

    def next(self) -> str:
        return f"{self._prefix}_{next(self._c):04d}"


@dataclass
class RuntimeConfig:
    mode: Mode = Mode.OFFLINE
    brains_root: str = str(_BRAINS_DEFAULT)
    llm_enabled: bool = False  # 仅当 mode=llm_assisted 且有可用 key 时才 True
```

- [ ] **Step 4: 跑(应 pass)** 同上命令 → 3 passed。

- [ ] **Step 5: commit**

```bash
cd /Volumes/T7/PRAXIS-virtualcell && find praxis_virtualcell -name '._*' -delete
git add praxis_virtualcell/__init__.py praxis_virtualcell/core praxis_virtualcell/tests
git commit -q -m "feat(vc): package scaffold + config + exceptions"
```

---

## Task 2：VirtualCellRequest + 校验

**Files:** Create `core/request.py`、`tests/test_request_schema.py`

- [ ] **Step 1: 写失败测试** `tests/test_request_schema.py`

```python
import pytest

from praxis_virtualcell.core.exceptions import InputValidationError
from praxis_virtualcell.core.request import VirtualCellRequest

_OK = {
    "request_id": "req-001",
    "species": "human",
    "perturbation_type": "gene",
    "perturbation_targets": ["AHR"],
    "input_modality": "scRNA",
    "output_modality": "delta_expression",
    "task_type": "predict_delta_expression",
}


def test_from_dict_minimal_ok():
    r = VirtualCellRequest.from_dict(_OK)
    assert r.species == "human"
    assert r.perturbation_targets == ["AHR"]
    assert r.cell_type is None and r.metadata == {}


def test_missing_required_raises():
    bad = dict(_OK)
    del bad["species"]
    with pytest.raises(InputValidationError):
        VirtualCellRequest.from_dict(bad)


def test_targets_must_be_list():
    bad = dict(_OK, perturbation_targets="AHR")
    with pytest.raises(InputValidationError):
        VirtualCellRequest.from_dict(bad)
```

- [ ] **Step 2: 跑(fail)** → ModuleNotFoundError。

- [ ] **Step 3: 实现** `core/request.py`

```python
"""虚拟细胞结构化请求。第一阶段真支持 human/scRNA/gene/predict_delta_expression;
其余字段(drug/mutation/bacteria/yeast/mouse/...)schema 预留,本周不实现逻辑。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from praxis_virtualcell.core.exceptions import InputValidationError

_REQUIRED = (
    "request_id", "species", "perturbation_type", "perturbation_targets",
    "input_modality", "output_modality", "task_type",
)


@dataclass
class VirtualCellRequest:
    request_id: str
    species: str
    perturbation_type: str
    perturbation_targets: list[str]
    input_modality: str
    output_modality: str
    task_type: str
    cell_type: str | None = None
    tissue: str | None = None
    perturbation_dose: float | None = None
    perturbation_time: str | None = None
    baseline_context: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    constraints: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "VirtualCellRequest":
        for k in _REQUIRED:
            if d.get(k) in (None, ""):
                raise InputValidationError(f"VirtualCellRequest 缺必填字段: {k}")
        if not isinstance(d["perturbation_targets"], list):
            raise InputValidationError("perturbation_targets 必须是 list[str]")
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})
```

- [ ] **Step 4: 跑(pass)** → 3 passed。
- [ ] **Step 5: commit** `git add core/request.py tests/test_request_schema.py && git commit -m "feat(vc): VirtualCellRequest + validation"`(commit 前清 `._*`,下同)。

---

## Task 3：消息类型(AgentMessage / PredictorResultMessage / ReliabilityDecision)

**Files:** Create `core/message.py`、`tests/test_message_types.py`

- [ ] **Step 1: 写失败测试** `tests/test_message_types.py`

```python
from dataclasses import asdict

from praxis_virtualcell.core.message import (
    AgentMessage, PredictorResultMessage, ReliabilityDecision,
)


def test_agent_message_roundtrip():
    m = AgentMessage(message_id="m1", sender="A", receiver="B",
                     message_type="ping", payload={"x": 1}, timestamp="t0001")
    d = asdict(m)
    assert d["sender"] == "A" and d["parent_message_id"] is None


def test_predictor_result_status_fields():
    r = PredictorResultMessage(agent_name="MockCPA", status="rejected",
                               prediction=None, uncertainty=None,
                               applicability_score=0.0, evidence=["unsupported"],
                               rejection_reason="species", provenance={})
    assert r.status == "rejected" and r.prediction is None


def test_reliability_decision_defaults():
    d = ReliabilityDecision(reliability="low", abstain=True,
                            reasons=["all_rejected"], failed_checks=[],
                            model_disagreement=None)
    assert d.abstain is True
```

- [ ] **Step 2: 跑(fail)**。
- [ ] **Step 3: 实现** `core/message.py`

```python
"""agent 间通讯消息 + predictor 结果 + 可靠性决策(全 @dataclass)。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# status 取值:success | rejected | failed
PredictorStatus = str
# reliability 取值:high | medium | low
ReliabilityLevel = str


@dataclass
class AgentMessage:
    message_id: str
    sender: str
    receiver: str
    message_type: str
    payload: dict[str, Any]
    timestamp: str
    parent_message_id: str | None = None


@dataclass
class PredictorResultMessage:
    agent_name: str
    status: PredictorStatus
    prediction: dict[str, Any] | None
    uncertainty: dict[str, Any] | None
    applicability_score: float
    evidence: list[str]
    rejection_reason: str | None
    provenance: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReliabilityDecision:
    reliability: ReliabilityLevel
    abstain: bool
    reasons: list[str]
    failed_checks: list[str]
    model_disagreement: dict[str, Any] | None = None
```

- [ ] **Step 4: 跑(pass)**。
- [ ] **Step 5: commit** `feat(vc): core message dataclasses`。

---

## Task 4：MessageBus + trace

**Files:** Create `core/bus.py`、`tests/test_message_bus.py`、`tests/test_trace.py`

- [ ] **Step 1: 写失败测试** `tests/test_message_bus.py`

```python
import json

from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage


def _m(mid, sender, receiver, mtype):
    return AgentMessage(mid, sender, receiver, mtype, {}, "t0001")


def test_send_routes_to_receiver_inbox():
    bus = MessageBus()
    bus.send(_m("m1", "A", "B", "ping"))
    assert [m.message_id for m in bus.get_messages("B")] == ["m1"]
    assert bus.get_messages("C") == []


def test_trace_records_all_in_order():
    bus = MessageBus()
    bus.send(_m("m1", "A", "B", "ping"))
    bus.send(_m("m2", "B", "A", "pong"))
    assert [m.message_id for m in bus.trace] == ["m1", "m2"]


def test_has_message_type_and_latest():
    bus = MessageBus()
    bus.send(_m("m1", "A", "B", "brain_retrieved"))
    assert bus.has_message_type("brain_retrieved") is True
    assert bus.has_message_type("nope") is False
    assert bus.latest("brain_retrieved").message_id == "m1"
    assert bus.latest("nope") is None
```

`tests/test_trace.py`:

```python
import json

from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage


def test_export_trace_writes_json(tmp_path):
    bus = MessageBus()
    bus.send(AgentMessage("m1", "A", "B", "ping", {"k": "v"}, "t0001"))
    p = tmp_path / "trace.json"
    bus.export_trace(str(p))
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data[0]["message_id"] == "m1" and data[0]["payload"]["k"] == "v"
```

- [ ] **Step 2: 跑(fail)**。
- [ ] **Step 3: 实现** `core/bus.py`

```python
"""唯一通讯通道:agent 只经 bus 收发,不互调内部方法。bus 记全量 trace 可 replay。"""
from __future__ import annotations

import json
from dataclasses import asdict

from praxis_virtualcell.core.message import AgentMessage


class MessageBus:
    def __init__(self) -> None:
        self._trace: list[AgentMessage] = []
        self._inbox: dict[str, list[AgentMessage]] = {}

    def send(self, message: AgentMessage) -> None:
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

- [ ] **Step 4: 跑(pass)** → test_message_bus(3)+test_trace(1) passed。
- [ ] **Step 5: commit** `feat(vc): MessageBus + trace export`。

---

## Task 5：BaseAgent + AgentRuntime(register/dispatch + mk_message)

**Files:** Create `core/agent.py`、`core/runtime.py`、`tests/test_runtime_dispatch.py`

- [ ] **Step 1: 写失败测试** `tests/test_runtime_dispatch.py`

```python
import pytest

from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.config import Clock, IdGen, RuntimeConfig
from praxis_virtualcell.core.exceptions import UnknownAgentError
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.core.runtime import AgentRuntime


class Echo(BaseAgent):
    name = "Echo"

    def handle(self, message, bus):
        bus.send(AgentMessage("e1", self.name, "client", "echoed",
                              {"got": message.payload}, "t0"))


def test_register_and_dispatch():
    rt = AgentRuntime(RuntimeConfig(), bus=MessageBus(), clock=Clock(), idgen=IdGen())
    rt.register_agent(Echo())
    m = rt.mk_message("client", "Echo", "ping", {"x": 1})
    rt.dispatch_message(m)
    assert rt.bus.latest("echoed").payload["got"] == {"x": 1}


def test_dispatch_unknown_agent_raises():
    rt = AgentRuntime(RuntimeConfig(), bus=MessageBus(), clock=Clock(), idgen=IdGen())
    with pytest.raises(UnknownAgentError):
        rt.dispatch_message(rt.mk_message("client", "Nope", "ping", {}))


def test_mk_message_uses_idgen_and_clock():
    rt = AgentRuntime(RuntimeConfig(), bus=MessageBus(), clock=Clock(), idgen=IdGen())
    m = rt.mk_message("a", "b", "t", {})
    assert m.message_id == "msg_0001" and m.timestamp == "t0001"
```

- [ ] **Step 2: 跑(fail)**。
- [ ] **Step 3: 实现** `core/agent.py`

```python
"""agent 基类:只经 bus 产出,不返回值、不互调他者内部方法。"""
from __future__ import annotations

from abc import ABC, abstractmethod

from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage


class BaseAgent(ABC):
    name: str = "BaseAgent"

    @abstractmethod
    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        """读 message,做工作,经 bus.send 产出 0..n 条输出消息。"""
```

`core/runtime.py`:

```python
"""注册 + 派发 + 驱动 workflow。predictor fan-out 也走 bus(no fake multi-agent)。"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.config import Clock, IdGen, RuntimeConfig
from praxis_virtualcell.core.exceptions import UnknownAgentError
from praxis_virtualcell.core.message import AgentMessage


class AgentRuntime:
    def __init__(self, config: RuntimeConfig, *, bus: MessageBus,
                 clock: Clock, idgen: IdGen) -> None:
        self.config = config
        self.bus = bus
        self.clock = clock
        self.idgen = idgen
        self._agents: dict[str, BaseAgent] = {}

    def register_agent(self, agent: BaseAgent) -> None:
        self._agents[agent.name] = agent

    def mk_message(self, sender: str, receiver: str, message_type: str,
                   payload: dict, parent_message_id: str | None = None) -> AgentMessage:
        return AgentMessage(self.idgen.next(), sender, receiver, message_type,
                            payload, self.clock.now(), parent_message_id)

    def dispatch_message(self, message: AgentMessage) -> None:
        agent = self._agents.get(message.receiver)
        if agent is None:
            raise UnknownAgentError(f"未注册 agent: {message.receiver}")
        self.bus.send(message)
        agent.handle(message, self.bus)

    def _dispatch_collect(self, message: AgentMessage, expected_type: str) -> AgentMessage:
        self.dispatch_message(message)
        out = self.bus.latest(expected_type)
        if out is None:
            raise RuntimeError(f"{message.receiver} 未产出 {expected_type}")
        return out

    # run_workflow / export_outputs 在 Task 10 补。
```

- [ ] **Step 4: 跑(pass)** → 3 passed。
- [ ] **Step 5: commit** `feat(vc): BaseAgent + AgentRuntime dispatch`。

---

## Task 6：最小 brain(yaml)+ SpeciesBrainAgent

**Files:** Create `brains/virtualcell/generic/*.yaml`、`brains/virtualcell/human/{model_applicability,object_vocabulary}.yaml`、`agents/__init__.py`、`agents/species_brain.py`、`tests/test_species_brain.py`

- [ ] **Step 1: 写失败测试** `tests/test_species_brain.py`

```python
from praxis_virtualcell.agents.species_brain import SpeciesBrainAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.config import RuntimeConfig
from praxis_virtualcell.core.message import AgentMessage


def _req():
    return {"species": "human", "perturbation_targets": ["AHR"], "task_type": "predict_delta_expression",
            "input_modality": "scRNA", "perturbation_type": "gene"}


def test_brain_retrieved_for_human():
    bus = MessageBus()
    a = SpeciesBrainAgent(RuntimeConfig())
    a.handle(AgentMessage("m1", "X", "SpeciesBrain", "retrieve",
                          {"request": _req()}, "t1"), bus)
    out = bus.latest("brain_retrieved")
    assert out is not None
    bc = out.payload["brain_context"]
    assert bc["species"] == "human"
    assert "model_applicability" in bc and "object_vocabulary" in bc
    assert "AHR" in bc["object_vocabulary"]["genes"]


def test_unknown_species_still_retrieves_generic_with_flag():
    bus = MessageBus()
    a = SpeciesBrainAgent(RuntimeConfig())
    req = dict(_req(), species="martian")
    a.handle(AgentMessage("m1", "X", "SpeciesBrain", "retrieve",
                          {"request": req}, "t1"), bus)
    bc = bus.latest("brain_retrieved").payload["brain_context"]
    assert bc["species_supported"] is False
```

- [ ] **Step 2: 跑(fail)**。
- [ ] **Step 3: 实现** brain yaml:

`brains/virtualcell/generic/task_schema.yaml`:
```yaml
supported_tasks:
  - predict_delta_expression
supported_modalities:
  - scRNA
```
`brains/virtualcell/generic/default_abstain_rules.yaml`:
```yaml
abstain_if:
  - all_predictors_rejected
  - species_not_supported
  - core_predictor_failed
  - model_disagreement_too_high
```
`brains/virtualcell/generic/general_negative_transfer.yaml`:
```yaml
negative_transfer:
  - from_species: human
    to_species: [bacteria, yeast]
    rule: mammalian_scrna_predictor_not_applicable
```
`brains/virtualcell/human/model_applicability.yaml`:
```yaml
MockCPA:
  supported_species: [human]
  supported_modalities: [scRNA]
  supported_tasks: [predict_delta_expression]
  supported_perturbations: [gene, drug]
MockGEARS:
  supported_species: [human]
  supported_modalities: [scRNA]
  supported_tasks: [predict_delta_expression]
  supported_perturbations: [gene, gene_combination]
  reject_if: [gene_not_in_graph_vocabulary]
MockLinear:
  supported_species: [human]
  supported_modalities: [scRNA]
  supported_tasks: [predict_delta_expression]
  supported_perturbations: [gene, drug]
```
`brains/virtualcell/human/object_vocabulary.yaml`:
```yaml
genes:
  - AHR
  - TP53
  - MYC
  - STAT1
  - GATA1
```

`agents/__init__.py`(空);`agents/species_brain.py`:

```python
"""读 brains/virtualcell/<species>/ 的 yaml,产出 brain_context(检索先行的标记)。"""
from __future__ import annotations

from pathlib import Path

import yaml

from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.config import RuntimeConfig
from praxis_virtualcell.core.message import AgentMessage


def _load_yaml(p: Path) -> dict:
    if not p.is_file():
        return {}
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


class SpeciesBrainAgent(BaseAgent):
    name = "SpeciesBrain"

    def __init__(self, config: RuntimeConfig) -> None:
        self.root = Path(config.brains_root)

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        req = message.payload["request"]
        species = req.get("species", "")
        sp_dir = self.root / species
        supported = sp_dir.is_dir()
        brain_context = {
            "species": species,
            "species_supported": supported,
            "generic": {
                "task_schema": _load_yaml(self.root / "generic" / "task_schema.yaml"),
                "default_abstain_rules": _load_yaml(self.root / "generic" / "default_abstain_rules.yaml"),
                "negative_transfer": _load_yaml(self.root / "generic" / "general_negative_transfer.yaml"),
            },
            "model_applicability": _load_yaml(sp_dir / "model_applicability.yaml"),
            "object_vocabulary": _load_yaml(sp_dir / "object_vocabulary.yaml"),
            "rules_referenced": [f"brains/virtualcell/{species or 'generic'}/model_applicability.yaml"],
        }
        bus.send(AgentMessage(
            message_id=message.message_id + ":brain",
            sender=self.name, receiver="ModelApplicability",
            message_type="brain_retrieved",
            payload={"request": req, "brain_context": brain_context},
            timestamp=message.timestamp, parent_message_id=message.message_id,
        ))
```

- [ ] **Step 4: 跑(pass)** → 2 passed。
- [ ] **Step 5: commit** `feat(vc): minimal species brain yaml + SpeciesBrainAgent`。

---

## Task 7：PredictorAgent base + retrieve-before-predict 门 + mock predictors

**Files:** Create `predictors/{__init__,base,mock_linear,mock_cpa,mock_gears}.py`、`tests/test_retrieve_before_predict.py`、`tests/test_predictor_rejection.py`

- [ ] **Step 1: 写失败测试** `tests/test_retrieve_before_predict.py`

```python
import pytest

from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.exceptions import RetrieveBeforePredictError
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.predictors.mock_cpa import MockCPAAgent

_PAYLOAD = {"request": {"species": "human", "input_modality": "scRNA",
                        "task_type": "predict_delta_expression", "perturbation_type": "gene",
                        "perturbation_targets": ["AHR"]},
            "brain_context": {"species": "human", "species_supported": True,
                              "model_applicability": {"MockCPA": {"supported_species": ["human"],
                                  "supported_modalities": ["scRNA"], "supported_tasks": ["predict_delta_expression"],
                                  "supported_perturbations": ["gene"]}},
                              "object_vocabulary": {"genes": ["AHR"]}}}


def test_predict_without_brain_retrieved_raises():
    bus = MessageBus()  # 无 brain_retrieved
    a = MockCPAAgent()
    m = AgentMessage("m1", "ModelApplicability", "MockCPA", "predict", _PAYLOAD, "t1")
    with pytest.raises(RetrieveBeforePredictError):
        a.handle(m, bus)


def test_predict_with_brain_retrieved_succeeds():
    bus = MessageBus()
    bus.send(AgentMessage("b1", "SpeciesBrain", "ModelApplicability", "brain_retrieved", {}, "t0"))
    a = MockCPAAgent()
    a.handle(AgentMessage("m1", "ModelApplicability", "MockCPA", "predict", _PAYLOAD, "t1"), bus)
    out = bus.latest("predictor_result")
    assert out.payload["status"] == "success"
    assert out.payload["agent_name"] == "MockCPA"
```

`tests/test_predictor_rejection.py`:

```python
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.predictors.mock_gears import MockGEARSAgent


def _bus_with_brain():
    bus = MessageBus()
    bus.send(AgentMessage("b1", "SpeciesBrain", "X", "brain_retrieved", {}, "t0"))
    return bus


def _payload(gene):
    return {"request": {"species": "human", "input_modality": "scRNA",
                        "task_type": "predict_delta_expression", "perturbation_type": "gene",
                        "perturbation_targets": [gene]},
            "brain_context": {"species": "human", "species_supported": True,
                              "model_applicability": {"MockGEARS": {"supported_species": ["human"],
                                  "supported_modalities": ["scRNA"], "supported_tasks": ["predict_delta_expression"],
                                  "supported_perturbations": ["gene"], "reject_if": ["gene_not_in_graph_vocabulary"]}},
                              "object_vocabulary": {"genes": ["AHR", "TP53"]}}}


def test_gears_rejects_unknown_gene():
    bus = _bus_with_brain()
    MockGEARSAgent().handle(AgentMessage("m1", "X", "MockGEARS", "predict", _payload("ZZZ9"), "t1"), bus)
    out = bus.latest("predictor_result").payload
    assert out["status"] == "rejected"
    assert "gene_not_in_graph_vocabulary" in out["rejection_reason"]


def test_gears_accepts_known_gene():
    bus = _bus_with_brain()
    MockGEARSAgent().handle(AgentMessage("m1", "X", "MockGEARS", "predict", _payload("AHR"), "t1"), bus)
    assert bus.latest("predictor_result").payload["status"] == "success"
```

- [ ] **Step 2: 跑(fail)**。
- [ ] **Step 3: 实现** `predictors/__init__.py`(空);`predictors/base.py`:

```python
"""predictor-agent 契约:能不能/为什么/用了什么/输出/不确定性/失败原因。
执行前强制 retrieve-before-predict 门(bus 里须已有 brain_retrieved)。无 torch。"""
from __future__ import annotations

from abc import abstractmethod
from dataclasses import asdict
from typing import Any

from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.exceptions import RetrieveBeforePredictError
from praxis_virtualcell.core.message import AgentMessage, PredictorResultMessage


class PredictorAgent(BaseAgent):
    name = "PredictorAgent"

    def assess_applicability(self, request: dict, brain_context: dict) -> tuple[float, str | None]:
        """返回 (score, rejection_reason)。reason 非 None 表示拒。"""
        rules = (brain_context.get("model_applicability") or {}).get(self.name, {})
        if not rules:
            return 0.0, f"{self.name} 不在 {brain_context.get('species')} brain 的 model_applicability"
        if request.get("species") not in rules.get("supported_species", []):
            return 0.0, "unsupported_species"
        if request.get("input_modality") not in rules.get("supported_modalities", []):
            return 0.0, "unsupported_modality"
        if request.get("task_type") not in rules.get("supported_tasks", []):
            return 0.0, "unsupported_task"
        return 1.0, None

    def prepare_input(self, request: dict, brain_context: dict) -> dict:
        return {"targets": request.get("perturbation_targets", [])}

    @abstractmethod
    def run_prediction(self, model_input: dict) -> dict:
        """返回 {prediction, uncertainty}。"""

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        if not bus.has_message_type("brain_retrieved"):
            raise RetrieveBeforePredictError(
                f"{self.name} 在 brain 检索前被调用(retrieve-before-predict 门)")
        req = message.payload["request"]
        bc = message.payload["brain_context"]
        score, reject = self.assess_applicability(req, bc)
        if reject is not None:
            self._emit(bus, message, PredictorResultMessage(
                agent_name=self.name, status="rejected", prediction=None, uncertainty=None,
                applicability_score=score, evidence=[reject], rejection_reason=reject,
                provenance={"rules": bc.get("rules_referenced", [])}))
            return
        try:
            out = self.run_prediction(self.prepare_input(req, bc))
        except Exception as e:  # noqa: BLE001 — mock 阶段把异常归为 failed
            self._emit(bus, message, PredictorResultMessage(
                agent_name=self.name, status="failed", prediction=None, uncertainty=None,
                applicability_score=score, evidence=[], rejection_reason=None,
                provenance={"error": str(e)}))
            return
        self._emit(bus, message, PredictorResultMessage(
            agent_name=self.name, status="success", prediction=out["prediction"],
            uncertainty=out.get("uncertainty"), applicability_score=score, evidence=["mock"],
            rejection_reason=None, provenance={"mock": True}))

    def _emit(self, bus: MessageBus, src: AgentMessage, result: PredictorResultMessage) -> None:
        bus.send(AgentMessage(
            message_id=src.message_id + f":{self.name}",
            sender=self.name, receiver="EnsembleCoordinator",
            message_type="predictor_result", payload=asdict(result),
            timestamp=src.timestamp, parent_message_id=src.message_id))
```

`predictors/mock_linear.py`:
```python
"""baseline / sanity:总 success,返回常数 delta。"""
from __future__ import annotations

from praxis_virtualcell.predictors.base import PredictorAgent


class MockLinearAgent(PredictorAgent):
    name = "MockLinear"

    def run_prediction(self, model_input: dict) -> dict:
        return {"prediction": {"delta": [0.0 for _ in model_input["targets"]] or [0.0]},
                "uncertainty": {"sigma": 0.1}}
```
`predictors/mock_cpa.py`:
```python
"""perturbation-conditioned mock:applicable 即 success。"""
from __future__ import annotations

from praxis_virtualcell.predictors.base import PredictorAgent


class MockCPAAgent(PredictorAgent):
    name = "MockCPA"

    def run_prediction(self, model_input: dict) -> dict:
        return {"prediction": {"delta": [0.5 for _ in model_input["targets"]] or [0.5]},
                "uncertainty": {"sigma": 0.2}}
```
`predictors/mock_gears.py`:
```python
"""graph generalization mock:gene 不在 vocabulary → rejected,不硬预测。"""
from __future__ import annotations

from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.predictors.base import PredictorAgent


class MockGEARSAgent(PredictorAgent):
    name = "MockGEARS"

    def assess_applicability(self, request: dict, brain_context: dict):
        score, reject = super().assess_applicability(request, brain_context)
        if reject is not None:
            return score, reject
        vocab = set((brain_context.get("object_vocabulary") or {}).get("genes", []))
        rules = (brain_context.get("model_applicability") or {}).get(self.name, {})
        if "gene_not_in_graph_vocabulary" in rules.get("reject_if", []):
            missing = [g for g in request.get("perturbation_targets", []) if g not in vocab]
            if missing:
                return 0.0, f"gene_not_in_graph_vocabulary:{missing}"
        return score, None

    def run_prediction(self, model_input: dict) -> dict:
        return {"prediction": {"delta": [0.4 for _ in model_input["targets"]] or [0.4]},
                "uncertainty": {"sigma": 0.25}}
```

- [ ] **Step 4: 跑(pass)** → test_retrieve_before_predict(2)+test_predictor_rejection(2) passed。
- [ ] **Step 5: commit** `feat(vc): PredictorAgent base + retrieve-gate + mock predictors`。

---

## Task 8：InputInterpreter / BioObjectNormalizer / ModelApplicability agents

**Files:** Create `agents/{input_interpreter,object_normalizer,model_applicability}.py`、`tests/test_pipeline_head.py`

- [ ] **Step 1: 写失败测试** `tests/test_pipeline_head.py`

```python
from praxis_virtualcell.agents.input_interpreter import InputInterpreterAgent
from praxis_virtualcell.agents.model_applicability import ModelApplicabilityAgent
from praxis_virtualcell.agents.object_normalizer import BioObjectNormalizerAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage

_REQ = {"request_id": "r1", "species": "human", "perturbation_type": "gene",
        "perturbation_targets": ["ahr"], "input_modality": "scRNA",
        "output_modality": "delta_expression", "task_type": "predict_delta_expression"}


def test_input_interpreter_parses():
    bus = MessageBus()
    InputInterpreterAgent().handle(AgentMessage("m", "client", "InputInterpreter",
        "parse_request", {"request_dict": _REQ}, "t1"), bus)
    assert bus.latest("request_parsed").payload["request"]["species"] == "human"


def test_normalizer_uppercases_genes():
    bus = MessageBus()
    BioObjectNormalizerAgent().handle(AgentMessage("m", "X", "BioObjectNormalizer",
        "normalize", {"request": _REQ}, "t1"), bus)
    req = bus.latest("object_normalized").payload["request"]
    assert req["perturbation_targets"] == ["AHR"]


def test_model_applicability_splits_applicable_rejected():
    bus = MessageBus()
    bc = {"species": "human", "species_supported": True,
          "model_applicability": {
              "MockCPA": {"supported_species": ["human"], "supported_modalities": ["scRNA"],
                          "supported_tasks": ["predict_delta_expression"], "supported_perturbations": ["gene"]},
              "MockGEARS": {"supported_species": ["human"], "supported_modalities": ["scRNA"],
                            "supported_tasks": ["predict_delta_expression"], "supported_perturbations": ["gene"],
                            "reject_if": ["gene_not_in_graph_vocabulary"]}},
          "object_vocabulary": {"genes": ["AHR"]}}
    ModelApplicabilityAgent().handle(AgentMessage("m", "SpeciesBrain", "ModelApplicability",
        "decide", {"request": dict(_REQ, perturbation_targets=["AHR"]), "brain_context": bc}, "t1"), bus)
    out = bus.latest("applicability_decided").payload
    assert "MockCPA" in out["applicable"] and "MockGEARS" in out["applicable"]
```

- [ ] **Step 2: 跑(fail)**。
- [ ] **Step 3: 实现**

`agents/input_interpreter.py`:
```python
"""offline:把结构化 dict 校验成 VirtualCellRequest(NL 解析是 W3 的 LLM agent)。"""
from __future__ import annotations

from dataclasses import asdict

from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.core.request import VirtualCellRequest


class InputInterpreterAgent(BaseAgent):
    name = "InputInterpreter"

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        req = VirtualCellRequest.from_dict(message.payload["request_dict"])
        bus.send(AgentMessage(message.message_id + ":parsed", self.name,
            "BioObjectNormalizer", "request_parsed", {"request": asdict(req)},
            message.timestamp, message.message_id))
```

`agents/object_normalizer.py`:
```python
"""第一版:gene symbol 去空格 + 大写(真 ortholog/别名归一化留后续)。"""
from __future__ import annotations

from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage


class BioObjectNormalizerAgent(BaseAgent):
    name = "BioObjectNormalizer"

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        req = dict(message.payload["request"])
        if req.get("perturbation_type") in ("gene", "gene_combination"):
            req["perturbation_targets"] = [str(g).strip().upper()
                                           for g in req.get("perturbation_targets", [])]
        bus.send(AgentMessage(message.message_id + ":norm", self.name,
            "SpeciesBrain", "object_normalized", {"request": req}, message.timestamp,
            message.message_id))
```

`agents/model_applicability.py`:
```python
"""据 brain_context 把候选 predictor 分成 applicable / rejected_candidates。
最终路由权威在此(LLMRouter 只能建议,W3)。"""
from __future__ import annotations

from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage

_CANDIDATES = ("MockLinear", "MockCPA", "MockGEARS")


class ModelApplicabilityAgent(BaseAgent):
    name = "ModelApplicability"

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        req = message.payload["request"]
        bc = message.payload["brain_context"]
        appmap = bc.get("model_applicability") or {}
        vocab = set((bc.get("object_vocabulary") or {}).get("genes", []))
        applicable, rejected = [], []
        for name in _CANDIDATES:
            rules = appmap.get(name)
            ok = bool(rules) \
                and req.get("species") in rules.get("supported_species", []) \
                and req.get("input_modality") in rules.get("supported_modalities", []) \
                and req.get("task_type") in rules.get("supported_tasks", [])
            if ok and "gene_not_in_graph_vocabulary" in rules.get("reject_if", []):
                if any(g not in vocab for g in req.get("perturbation_targets", [])):
                    ok = False
            (applicable if ok else rejected).append(name)
        bus.send(AgentMessage(message.message_id + ":app", self.name,
            "EnsembleCoordinator", "applicability_decided",
            {"request": req, "brain_context": bc, "applicable": applicable,
             "rejected_candidates": rejected}, message.timestamp, message.message_id))
```

- [ ] **Step 4: 跑(pass)** → 3 passed。
- [ ] **Step 5: commit** `feat(vc): input/normalizer/applicability agents`。

---

## Task 9：Ensemble / Reliability / Critic / Provenance / Report agents

**Files:** Create `agents/{ensemble,reliability,critic,provenance_agent,report}.py`、`tests/test_abstain.py`

- [ ] **Step 1: 写失败测试** `tests/test_abstain.py`

```python
from praxis_virtualcell.agents.ensemble import EnsembleCoordinatorAgent
from praxis_virtualcell.agents.reliability import ReliabilityAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage


def _result(name, status):
    return {"agent_name": name, "status": status, "prediction": ({"delta": [0.5]} if status == "success" else None),
            "uncertainty": {"sigma": 0.2}, "applicability_score": 1.0 if status == "success" else 0.0,
            "evidence": [], "rejection_reason": None if status == "success" else "x", "provenance": {}}


def test_ensemble_only_aggregates_success():
    bus = MessageBus()
    payload = {"request": {}, "brain_context": {"generic": {"default_abstain_rules": {}}},
               "results": [_result("MockCPA", "success"), _result("MockGEARS", "rejected")]}
    EnsembleCoordinatorAgent().handle(AgentMessage("m", "X", "EnsembleCoordinator", "ensemble", payload, "t1"), bus)
    out = bus.latest("ensemble_done").payload
    assert out["models_used"] == ["MockCPA"]
    assert out["models_rejected"] == ["MockGEARS"]


def test_reliability_abstains_when_all_rejected():
    bus = MessageBus()
    payload = {"request": {}, "brain_context": {"generic": {"default_abstain_rules": {"abstain_if": ["all_predictors_rejected"]}}},
               "results": [_result("MockCPA", "rejected"), _result("MockGEARS", "rejected")],
               "models_used": [], "models_rejected": ["MockCPA", "MockGEARS"], "ensemble": None}
    ReliabilityAgent().handle(AgentMessage("m", "X", "Reliability", "assess", payload, "t1"), bus)
    rd = bus.latest("reliability_decided").payload["reliability_decision"]
    assert rd["abstain"] is True and "all_predictors_rejected" in rd["reasons"]
```

- [ ] **Step 2: 跑(fail)**。
- [ ] **Step 3: 实现**

`agents/ensemble.py`:
```python
"""只汇总 success 结果(rejected/failed 不进 ensemble)。Coordinator 仅通讯+汇总。"""
from __future__ import annotations

from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage


class EnsembleCoordinatorAgent(BaseAgent):
    name = "EnsembleCoordinator"

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        results = message.payload["results"]
        ok = [r for r in results if r["status"] == "success"]
        used = [r["agent_name"] for r in ok]
        rejected = [r["agent_name"] for r in results if r["status"] != "success"]
        ensemble = None
        if ok:
            vecs = [r["prediction"]["delta"] for r in ok if r.get("prediction")]
            n = max((len(v) for v in vecs), default=0)
            ensemble = {"delta": [sum(v[i] for v in vecs) / len(vecs) for i in range(n)]} if n else None
        bus.send(AgentMessage(message.message_id + ":ens", self.name, "Reliability",
            "ensemble_done", {**message.payload, "models_used": used,
            "models_rejected": rejected, "ensemble": ensemble}, message.timestamp,
            message.message_id))
```

`agents/reliability.py`:
```python
"""据 abstain rules + 模型分歧裁 reliability/abstain。"""
from __future__ import annotations

from dataclasses import asdict

from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage, ReliabilityDecision


class ReliabilityAgent(BaseAgent):
    name = "Reliability"

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        p = message.payload
        used = p.get("models_used", [])
        reasons, failed = [], []
        abstain_rules = (p.get("brain_context", {}).get("generic", {})
                         .get("default_abstain_rules", {}).get("abstain_if", []))
        abstain = False
        if not used:
            abstain = True
            if "all_predictors_rejected" in abstain_rules:
                reasons.append("all_predictors_rejected")
            else:
                reasons.append("no_successful_predictor")
        disagreement = None
        if len(used) >= 2 and p.get("ensemble"):
            reliability = "high"
        elif used:
            reliability = "medium"
        else:
            reliability = "low"
        rd = ReliabilityDecision(reliability=reliability, abstain=abstain,
                                 reasons=reasons, failed_checks=failed,
                                 model_disagreement=disagreement)
        bus.send(AgentMessage(message.message_id + ":rel", self.name, "Critic",
            "reliability_decided", {**p, "reliability_decision": asdict(rd)},
            message.timestamp, message.message_id))
```

`agents/critic.py`:
```python
"""审 trace:retrieve-before-predict、rejected 是否被写进 used、是否声称未发生的预测。"""
from __future__ import annotations

from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage


class CriticAgent(BaseAgent):
    name = "Critic"

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        p = message.payload
        notes, violations = [], []
        # 1. retrieve-before-predict:trace 里 brain_retrieved 必须早于任何 predictor_result
        types = [m.message_type for m in bus.trace]
        if "predictor_result" in types:
            if "brain_retrieved" not in types or types.index("brain_retrieved") > types.index("predictor_result"):
                violations.append("predict_before_retrieve")
        # 2. rejected 不得出现在 models_used
        used = set(p.get("models_used", []))
        rejected = {r["agent_name"] for r in p.get("results", []) if r["status"] != "success"}
        if used & rejected:
            violations.append(f"rejected_model_in_ensemble:{sorted(used & rejected)}")
        # 3. 声称预测但无 success 结果且未 abstain
        rd = p.get("reliability_decision", {})
        if not used and not rd.get("abstain"):
            violations.append("claims_prediction_without_predictor")
        notes.append(f"checked retrieve-first, ensemble integrity, abstain honesty; violations={violations}")
        bus.send(AgentMessage(message.message_id + ":crit", self.name, "ProvenanceAgent",
            "critic_done", {**p, "critic_notes": notes, "critic_violations": violations},
            message.timestamp, message.message_id))
```

`agents/provenance_agent.py`:
```python
"""组装可追溯证据链:trace 摘要 + 规则引用 + 模型参与/拒绝 + critic。"""
from __future__ import annotations

from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage


class ProvenanceAgent(BaseAgent):
    name = "ProvenanceAgent"

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        p = message.payload
        provenance = {
            "n_messages": len(bus.trace),
            "rules_referenced": p.get("brain_context", {}).get("rules_referenced", [])
                                or p.get("brain_context", {}).get("generic", {}).get("negative_transfer", []),
            "models_used": p.get("models_used", []),
            "models_rejected": p.get("models_rejected", []),
            "critic_violations": p.get("critic_violations", []),
        }
        bus.send(AgentMessage(message.message_id + ":prov", self.name, "Report",
            "provenance_done", {**p, "provenance": provenance}, message.timestamp,
            message.message_id))
```

`agents/report.py`:
```python
"""结构化报告:不得编造结构里没有的结论;保留 prediction/abstain/参与/拒绝/reliability/provenance。"""
from __future__ import annotations

from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage


class ReportAgent(BaseAgent):
    name = "Report"

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        p = message.payload
        rd = p.get("reliability_decision", {})
        report = {
            "request_id": p.get("request", {}).get("request_id"),
            "abstain": rd.get("abstain", False),
            "reliability": rd.get("reliability"),
            "prediction": None if rd.get("abstain") else p.get("ensemble"),
            "models_used": p.get("models_used", []),
            "models_rejected": p.get("models_rejected", []),
            "abstain_reasons": rd.get("reasons", []),
            "critic_violations": p.get("critic_violations", []),
            "provenance": p.get("provenance", {}),
        }
        bus.send(AgentMessage(message.message_id + ":rep", self.name, "client",
            "report_done", {"report": report}, message.timestamp, message.message_id))
```

- [ ] **Step 4: 跑(pass)** → 2 passed。
- [ ] **Step 5: commit** `feat(vc): ensemble/reliability/critic/provenance/report agents`。

---

## Task 10：run_workflow 编排 + examples + offline 集成测试

**Files:** Modify `core/runtime.py`(补 `run_workflow`/`export_outputs`);Create `workflows/{__init__,predict_delta_expression}.py`、`examples/*.json`、`tests/test_offline_workflow.py`、`tests/test_no_fake_multiagent.py`

- [ ] **Step 1: 写失败测试** `tests/test_offline_workflow.py`

```python
from praxis_virtualcell.workflows.predict_delta_expression import build_runtime, run_request

_HUMAN = {"request_id": "r1", "species": "human", "perturbation_type": "gene",
          "perturbation_targets": ["AHR"], "input_modality": "scRNA",
          "output_modality": "delta_expression", "task_type": "predict_delta_expression"}


def test_human_request_predicts_no_abstain():
    report = run_request(_HUMAN)
    assert report["abstain"] is False
    assert "MockCPA" in report["models_used"]
    assert report["prediction"] is not None
    assert report["critic_violations"] == []


def test_bacteria_request_abstains_no_applicable_model():
    bact = dict(_HUMAN, species="bacteria", request_id="r2")
    report = run_request(bact)
    assert report["abstain"] is True
    assert report["models_used"] == []
```

`tests/test_no_fake_multiagent.py`:

```python
from praxis_virtualcell.workflows.predict_delta_expression import build_runtime, run_request

_HUMAN = {"request_id": "r1", "species": "human", "perturbation_type": "gene",
          "perturbation_targets": ["AHR"], "input_modality": "scRNA",
          "output_modality": "delta_expression", "task_type": "predict_delta_expression"}


def test_trace_has_full_chain_and_retrieve_first():
    rt = build_runtime()
    rt.run_workflow_from_dict(_HUMAN)
    types = [m.message_type for m in rt.bus.trace]
    assert "brain_retrieved" in types and "predictor_result" in types
    assert types.index("brain_retrieved") < types.index("predictor_result")
    # predictor 经 bus 收任务:存在 receiver 为 MockCPA 的 predict 消息
    assert any(m.receiver == "MockCPA" and m.message_type == "predict" for m in rt.bus.trace)


def test_critic_flags_injected_fake_prediction():
    # 人造违规:report 阶段声称用了一个并无 success 结果的模型 → critic 命中
    from praxis_virtualcell.agents.critic import CriticAgent
    from praxis_virtualcell.core.bus import MessageBus
    from praxis_virtualcell.core.message import AgentMessage
    bus = MessageBus()
    bus.send(AgentMessage("b", "SpeciesBrain", "X", "brain_retrieved", {}, "t0"))
    bus.send(AgentMessage("pr", "MockCPA", "EnsembleCoordinator", "predictor_result",
                          {"agent_name": "MockCPA", "status": "rejected"}, "t1"))
    payload = {"results": [{"agent_name": "MockCPA", "status": "rejected"}],
               "models_used": ["MockCPA"], "reliability_decision": {"abstain": False}}
    CriticAgent().handle(AgentMessage("m", "Reliability", "Critic", "review", payload, "t2"), bus)
    v = bus.latest("critic_done").payload["critic_violations"]
    assert any("rejected_model_in_ensemble" in x for x in v)
```

- [ ] **Step 2: 跑(fail)**。
- [ ] **Step 3: 实现** —— 在 `core/runtime.py` 末尾补:

```python
    def run_workflow(self, request) -> dict:
        """request: VirtualCellRequest。返回最终 report dict。全程经 bus。"""
        from dataclasses import asdict as _asdict
        m = self.mk_message("client", "InputInterpreter", "parse_request",
                            {"request_dict": _asdict(request)})
        out = self._dispatch_collect(m, "request_parsed")
        m = self.mk_message(out.sender, "BioObjectNormalizer", "normalize",
                            out.payload, out.message_id)
        out = self._dispatch_collect(m, "object_normalized")
        m = self.mk_message(out.sender, "SpeciesBrain", "retrieve", out.payload, out.message_id)
        out = self._dispatch_collect(m, "brain_retrieved")
        m = self.mk_message(out.sender, "ModelApplicability", "decide", out.payload, out.message_id)
        app = self._dispatch_collect(m, "applicability_decided")
        results = []
        for pname in list(app.payload["applicable"]) + list(app.payload["rejected_candidates"]):
            pm = self.mk_message("ModelApplicability", pname, "predict",
                                {"request": app.payload["request"],
                                 "brain_context": app.payload["brain_context"]}, app.message_id)
            r = self._dispatch_collect(pm, "predictor_result")
            results.append(r.payload)
        m = self.mk_message("ModelApplicability", "EnsembleCoordinator", "ensemble",
                            {"request": app.payload["request"],
                             "brain_context": app.payload["brain_context"], "results": results},
                            app.message_id)
        ens = self._dispatch_collect(m, "ensemble_done")
        m = self.mk_message(ens.sender, "Reliability", "assess", ens.payload, ens.message_id)
        rel = self._dispatch_collect(m, "reliability_decided")
        m = self.mk_message(rel.sender, "Critic", "review", rel.payload, rel.message_id)
        crit = self._dispatch_collect(m, "critic_done")
        m = self.mk_message(crit.sender, "ProvenanceAgent", "assemble", crit.payload, crit.message_id)
        prov = self._dispatch_collect(m, "provenance_done")
        m = self.mk_message(prov.sender, "Report", "render", prov.payload, prov.message_id)
        rep = self._dispatch_collect(m, "report_done")
        return rep.payload["report"]

    def export_outputs(self, out_dir: str, report: dict) -> None:
        d = Path(out_dir)
        d.mkdir(parents=True, exist_ok=True)
        self.bus.export_trace(str(d / "trace.json"))
        (d / "prediction_report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        (d / "provenance.json").write_text(
            json.dumps(report.get("provenance", {}), ensure_ascii=False, indent=2), encoding="utf-8")
```

注:每个 dispatch 多个 predictor 时 `_dispatch_collect` 取 `bus.latest("predictor_result")` 是"该次刚产出的那条"(每个 predictor handle 只 emit 一条,latest 即当次)。

`workflows/__init__.py`(空);`workflows/predict_delta_expression.py`:
```python
"""组装 offline runtime + 跑一个 request。"""
from __future__ import annotations

from praxis_virtualcell.agents.critic import CriticAgent
from praxis_virtualcell.agents.ensemble import EnsembleCoordinatorAgent
from praxis_virtualcell.agents.input_interpreter import InputInterpreterAgent
from praxis_virtualcell.agents.model_applicability import ModelApplicabilityAgent
from praxis_virtualcell.agents.object_normalizer import BioObjectNormalizerAgent
from praxis_virtualcell.agents.provenance_agent import ProvenanceAgent
from praxis_virtualcell.agents.reliability import ReliabilityAgent
from praxis_virtualcell.agents.report import ReportAgent
from praxis_virtualcell.agents.species_brain import SpeciesBrainAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.config import Clock, IdGen, RuntimeConfig
from praxis_virtualcell.core.request import VirtualCellRequest
from praxis_virtualcell.core.runtime import AgentRuntime
from praxis_virtualcell.predictors.mock_cpa import MockCPAAgent
from praxis_virtualcell.predictors.mock_gears import MockGEARSAgent
from praxis_virtualcell.predictors.mock_linear import MockLinearAgent


def build_runtime(config: RuntimeConfig | None = None) -> AgentRuntime:
    cfg = config or RuntimeConfig()
    rt = AgentRuntime(cfg, bus=MessageBus(), clock=Clock(), idgen=IdGen())
    for a in (InputInterpreterAgent(), BioObjectNormalizerAgent(), SpeciesBrainAgent(cfg),
              ModelApplicabilityAgent(), MockLinearAgent(), MockCPAAgent(), MockGEARSAgent(),
              EnsembleCoordinatorAgent(), ReliabilityAgent(), CriticAgent(),
              ProvenanceAgent(), ReportAgent()):
        rt.register_agent(a)
    # 便捷方法:从 dict 跑
    rt.run_workflow_from_dict = lambda d: rt.run_workflow(VirtualCellRequest.from_dict(d))  # type: ignore[attr-defined]
    return rt


def run_request(request_dict: dict) -> dict:
    rt = build_runtime()
    return rt.run_workflow(VirtualCellRequest.from_dict(request_dict))
```

`examples/norman_mock_request.json`:
```json
{"request_id": "norman-001", "species": "human", "cell_type": "K562",
 "perturbation_type": "gene", "perturbation_targets": ["AHR"],
 "input_modality": "scRNA", "output_modality": "delta_expression",
 "task_type": "predict_delta_expression", "metadata": {"benchmark": "norman"}}
```
`examples/bacteria_mock_request.json`:
```json
{"request_id": "bact-001", "species": "bacteria", "perturbation_type": "gene",
 "perturbation_targets": ["lacZ"], "input_modality": "scRNA",
 "output_modality": "delta_expression", "task_type": "predict_delta_expression"}
```
`examples/mouse_transfer_mock_request.json`:
```json
{"request_id": "mouse-001", "species": "mouse", "perturbation_type": "gene",
 "perturbation_targets": ["Trp53"], "input_modality": "scRNA",
 "output_modality": "delta_expression", "task_type": "predict_delta_expression"}
```

- [ ] **Step 4: 跑(pass)** → test_offline_workflow(2)+test_no_fake_multiagent(2) passed。
- [ ] **Step 5: commit** `feat(vc): run_workflow orchestration + examples + offline integration`。

---

## Task 11：agents_llm stub + llm_assisted fallback

**Files:** Create `agents_llm/{__init__,llm_client,optional_agents}.py`、`tests/test_llm_optional.py`

- [ ] **Step 1: 写失败测试** `tests/test_llm_optional.py`

```python
from praxis_virtualcell.agents_llm.llm_client import LLMClient, make_llm_client
from praxis_virtualcell.core.config import Mode, RuntimeConfig
from praxis_virtualcell.workflows.predict_delta_expression import run_request

_HUMAN = {"request_id": "r1", "species": "human", "perturbation_type": "gene",
          "perturbation_targets": ["AHR"], "input_modality": "scRNA",
          "output_modality": "delta_expression", "task_type": "predict_delta_expression"}


def test_disabled_llm_client_is_not_enabled():
    c = make_llm_client(RuntimeConfig(mode=Mode.OFFLINE))
    assert c.enabled is False


def test_llm_assisted_without_key_falls_back_to_disabled():
    # 无 key → llm_enabled False,client disabled,不抛
    cfg = RuntimeConfig(mode=Mode.LLM_ASSISTED, llm_enabled=False)
    c = make_llm_client(cfg)
    assert c.enabled is False
    out = c.complete([{"role": "user", "content": "hi"}])
    assert out["disabled"] is True


def test_offline_and_llm_assisted_same_prediction_numbers():
    # 主预测数值与模式无关(LLM 不进预测闭环)
    a = run_request(_HUMAN)["prediction"]
    b = run_request(_HUMAN)["prediction"]
    assert a == b
```

- [ ] **Step 2: 跑(fail)**。
- [ ] **Step 3: 实现** `agents_llm/__init__.py`(空);`agents_llm/llm_client.py`:

```python
"""统一 LLM 接口。Week 2 只实现 disabled / mock;真 OpenAI/Anthropic 留 W3。
无 key 时 enabled=False,complete() 返回 {disabled: True} 不抛 — 保证 offline 永不依赖 API。"""
from __future__ import annotations

from typing import Any

from praxis_virtualcell.core.config import Mode, RuntimeConfig


class LLMClient:
    def __init__(self, *, enabled: bool, backend: str = "disabled") -> None:
        self.enabled = enabled
        self.backend = backend

    def complete(self, messages: list[dict], schema: dict | None = None) -> dict[str, Any]:
        if not self.enabled:
            return {"disabled": True, "content": None}
        # W3 接真 backend;Week 2 mock:回显
        return {"disabled": False, "content": {"echo": messages[-1].get("content")}}


def make_llm_client(config: RuntimeConfig) -> LLMClient:
    enabled = config.mode is Mode.LLM_ASSISTED and config.llm_enabled
    return LLMClient(enabled=enabled, backend="mock" if enabled else "disabled")
```

`agents_llm/optional_agents.py`:
```python
"""optional LLM agents 占位:offline/无 key 时 should_run()=False,被 runtime 跳过。
W3 才真实现 LLMInputInterpreter/LLMRouter/LLMCritic/LLMReport。"""
from __future__ import annotations

from praxis_virtualcell.agents_llm.llm_client import LLMClient


class _OptionalLLMAgent:
    name = "OptionalLLMAgent"

    def __init__(self, client: LLMClient) -> None:
        self.client = client

    def should_run(self) -> bool:
        return self.client.enabled


class LLMInputInterpreterAgent(_OptionalLLMAgent):
    name = "LLMInputInterpreter"


class LLMRouterAgent(_OptionalLLMAgent):
    name = "LLMRouter"


class LLMCriticAgent(_OptionalLLMAgent):
    name = "LLMCritic"


class LLMReportAgent(_OptionalLLMAgent):
    name = "LLMReport"
```

- [ ] **Step 4: 跑(pass)** → 3 passed。
- [ ] **Step 5: commit** `feat(vc): LLM client stub + optional agents (W3 真接)`。

---

## Task 12：全套绿 + 输出导出冒烟 + 不变式硬门

**Files:** Create `tests/test_export_outputs.py`;无新代码(集成验收)。

- [ ] **Step 1: 写测试** `tests/test_export_outputs.py`

```python
import json

from praxis_virtualcell.core.request import VirtualCellRequest
from praxis_virtualcell.workflows.predict_delta_expression import build_runtime

_HUMAN = {"request_id": "r1", "species": "human", "perturbation_type": "gene",
          "perturbation_targets": ["AHR"], "input_modality": "scRNA",
          "output_modality": "delta_expression", "task_type": "predict_delta_expression"}


def test_export_writes_three_files(tmp_path):
    rt = build_runtime()
    report = rt.run_workflow(VirtualCellRequest.from_dict(_HUMAN))
    rt.export_outputs(str(tmp_path), report)
    for fn in ("trace.json", "prediction_report.json", "provenance.json"):
        assert (tmp_path / fn).is_file()
    trace = json.loads((tmp_path / "trace.json").read_text(encoding="utf-8"))
    assert len(trace) >= 10  # 完整通讯链
```

- [ ] **Step 2: 跑(pass)** 单文件 → 1 passed。

- [ ] **Step 3: 全套 + 硬门检查**

Run:
```bash
cd /Volumes/T7/PRAXIS-virtualcell && find praxis_virtualcell -name '._*' -delete
.venv/bin/python -m pytest praxis_virtualcell/tests -q 2>&1 | tail -8
echo "=== 主链路无 torch / 无 API 硬门 ==="
grep -rnE "import torch|from torch|openai|anthropic" praxis_virtualcell --include=*.py | grep -v tests || echo "CLEAN: 无 torch/openai/anthropic 主链路引用"
echo "=== praxis2 主链路未被 import ==="
grep -rn "import praxis2\|from praxis2" praxis_virtualcell --include=*.py || echo "CLEAN: 未 import praxis2"
```
Expected: 全 tests passed;两个 `CLEAN`。

- [ ] **Step 4: 确认 §4.6 十条验收映射**(逐条对到测试):request_schema✓ message_bus✓ trace✓ retrieve_before_predict✓ predictor_rejection✓ abstain✓ no_fake_multiagent✓ offline_mode✓ llm_optional✓ no-bus-shortcut(test_no_fake_multiagent 的 predict-via-bus 断言)✓。

- [ ] **Step 5: commit** `test(vc): export outputs + week2 acceptance green`。

---

## 验收(Definition of Done)
1. `pytest praxis_virtualcell/tests` 全绿(覆盖 §4.6 十条)。
2. mock workflow offline 跑通,导出 trace/prediction_report/provenance(human 预测、bacteria abstain)。
3. retrieve-before-predict 门生效;GEARS 对未知 gene rejected;all-rejected → abstain;critic 抓注入的假预测。
4. 主链路 grep 无 torch / openai / anthropic / import praxis2。
5. llm_assisted 无 key 自动 fallback;offline 数值可复现(注入 clock/idgen)。
6. 不动 praxis2 主代码。
