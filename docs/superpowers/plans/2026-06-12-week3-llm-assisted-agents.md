# Week 3 — LLM-assisted agents(纯 DeepSeek)实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps 用 checkbox(`- [ ]`)。

**Goal:** 在 Week 2 runtime 上加纯 DeepSeek 的 LLM-assisted 层(4 个 LLM agent + client + runtime seam),LLM 只增强/建议、绝不进数值路径;offline 底座零改动、无 key 也绿。

**Architecture:** LLMClient 用 httpx 直打 `api.deepseek.com/chat/completions`(无 openai/anthropic SDK,JSON mode + temp=0)。4 个 LLM agent 都是 BaseAgent 走 bus。runtime 在 `llm_assisted+key` 时于 applicability/report 两处加 seam(只往 provenance/report 加 narrative/route_suggestion/critic_notes,数值路径不变)。LLM 测试真打 DeepSeek,标 `llm`,无 key skip。

**Tech Stack:** Python 3.13、httpx(现成依赖)、pytest。**禁止 import openai/anthropic SDK**。

**Spec:** [docs/superpowers/specs/2026-06-12-week3-llm-assisted-agents-design.md](../specs/2026-06-12-week3-llm-assisted-agents-design.md)

**测试口径:** `cd /Volumes/T7/PRAXIS-virtualcell && .venv/bin/python -m pytest praxis_virtualcell/tests -q`(本机 `.env` 有 key → `llm` 测试真跑;commit 前 `find praxis_virtualcell -name '._*' -delete`)。

---

## 文件结构

```
praxis_virtualcell/
  core/config.py            # 改:+deepseek 字段 + load_env + from_env
  core/runtime.py           # 改:+llm_assisted seam + run_workflow_from_text
  agents_llm/
    llm_client.py           # 改:纯 DeepSeek httpx 实现
    llm_input_interpreter.py # 新
    llm_router.py            # 新
    llm_critic.py            # 新
    llm_report.py            # 新
    optional_agents.py       # 删(被上面 4 个真 agent 取代;无测试引用)
  workflows/predict_delta_expression.py  # 改:llm 模式注册 4 agent + build_llm helper
  examples/free_text_request.txt          # 新
  tests/
    conftest.py             # 新:llm marker + 无 key skip
    test_llm_client_offline.py     # 新(offline)
    test_llm_connectivity.py       # 新(llm)
    test_llm_input_interpreter.py  # 新(llm)
    test_llm_router.py             # 新(llm)
    test_llm_critic.py             # 新(llm)
    test_llm_report.py             # 新(llm)
    test_llm_e2e_demo.py           # 新(llm)
    test_llm_numeric_invariance.py # 新(llm)
    test_llm_fallback_offline.py   # 新(offline)
.env.example                # 新(占位,提交)
```

---

## Task 1:config 扩展(deepseek 字段 + load_env + from_env)+ conftest

**Files:** Modify `core/config.py`;Create `tests/conftest.py`、`tests/test_llm_client_offline.py`

- [ ] **Step 1: 写测试** `tests/test_llm_client_offline.py`

```python
import os

from praxis_virtualcell.agents_llm.llm_client import make_llm_client
from praxis_virtualcell.core.config import Mode, RuntimeConfig, load_env


def test_load_env_injects_without_override(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("FOO_K1=v1\n# comment\nFOO_K2=v2\n", encoding="utf-8")
    monkeypatch.delenv("FOO_K1", raising=False)
    monkeypatch.setenv("FOO_K2", "preset")
    load_env(str(env))
    assert os.environ["FOO_K1"] == "v1"
    assert os.environ["FOO_K2"] == "preset"  # 已存在不覆盖


def test_config_has_deepseek_fields_defaults():
    cfg = RuntimeConfig()
    assert cfg.deepseek_base_url == "https://api.deepseek.com"
    assert cfg.deepseek_model == "deepseek-chat"
    assert cfg.deepseek_api_key == ""


def test_make_llm_client_disabled_without_key():
    assert make_llm_client(RuntimeConfig(mode=Mode.LLM_ASSISTED)).enabled is False
    assert make_llm_client(RuntimeConfig(mode=Mode.OFFLINE)).enabled is False
```

- [ ] **Step 2: 跑(fail)** `... pytest praxis_virtualcell/tests/test_llm_client_offline.py -q` → AttributeError(无 deepseek 字段)。

- [ ] **Step 3: 实现** —— `core/config.py` 顶部加 `import os`,在文件末尾加 `load_env`,并把 `RuntimeConfig` 替换为下面这版:

```python
@dataclass
class RuntimeConfig:
    mode: Mode = Mode.OFFLINE
    brains_root: str = str(_BRAINS_DEFAULT)
    llm_enabled: bool = False
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    @classmethod
    def from_env(cls, *, env_path: str = ".env") -> "RuntimeConfig":
        load_env(env_path)
        mode = (Mode.LLM_ASSISTED
                if os.environ.get("PRAXIS_VIRTUALCELL_MODE") == "llm_assisted"
                else Mode.OFFLINE)
        key = os.environ.get("DEEPSEEK_API_KEY", "")
        return cls(
            mode=mode,
            deepseek_api_key=key,
            deepseek_base_url=os.environ.get("PRAXIS_VC_LLM_BASE_URL", "https://api.deepseek.com"),
            deepseek_model=os.environ.get("PRAXIS_VC_LLM_MODEL", "deepseek-chat"),
            llm_enabled=(mode is Mode.LLM_ASSISTED and bool(key)),
        )


def load_env(path: str = ".env") -> None:
    """读 .env 的 K=V 注入 os.environ(已存在的不覆盖;无文件 noop)。无新依赖。"""
    p = Path(path)
    if not p.is_file():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())
```

（保留 `Mode`/`Clock`/`IdGen` 不动。)

`tests/conftest.py`:

```python
import os

import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "llm: 需要真实 DEEPSEEK_API_KEY + 网络(无 key 自动 skip)")


def pytest_collection_modifyitems(config, items):
    from praxis_virtualcell.core.config import load_env
    load_env()  # 本地有 .env 则把 key 注入 env,llm 测试就能真跑
    if os.environ.get("DEEPSEEK_API_KEY"):
        return
    skip = pytest.mark.skip(reason="无 DEEPSEEK_API_KEY,跳过 llm 测试")
    for item in items:
        if "llm" in item.keywords:
            item.add_marker(skip)
```

- [ ] **Step 4: 跑(pass)** `... pytest praxis_virtualcell/tests/test_llm_client_offline.py praxis_virtualcell/tests/test_llm_optional.py -q` → 全 pass(Week 2 test_llm_optional 不回归:其 `make_llm_client` 仍 Week2 stub,llm_enabled=False → disabled)。

- [ ] **Step 5: commit** `git add praxis_virtualcell/core/config.py praxis_virtualcell/tests/conftest.py praxis_virtualcell/tests/test_llm_client_offline.py && git commit -m "feat(vc-llm): config deepseek fields + load_env + llm test gating"`

---

## Task 2:LLMClient 纯 DeepSeek(httpx)

**Files:** Modify `agents_llm/llm_client.py`;Create `tests/test_llm_connectivity.py`

- [ ] **Step 1: 写测试** `tests/test_llm_connectivity.py`

```python
import os

import pytest

from praxis_virtualcell.core.config import Mode, RuntimeConfig, load_env


def _cfg():
    load_env()
    return RuntimeConfig(mode=Mode.LLM_ASSISTED, deepseek_api_key=os.environ.get("DEEPSEEK_API_KEY", ""))


@pytest.mark.llm
def test_deepseek_real_completion_roundtrip():
    from praxis_virtualcell.agents_llm.llm_client import make_llm_client
    client = make_llm_client(_cfg())
    assert client.enabled is True
    res = client.complete([{"role": "user", "content": "reply with exactly: pong"}], max_tokens=5)
    assert res["disabled"] is False
    assert res.get("error") is None, res
    assert "pong" in (res["content"] or "").lower()


@pytest.mark.llm
def test_deepseek_json_mode_returns_parseable():
    import json
    from praxis_virtualcell.agents_llm.llm_client import make_llm_client
    client = make_llm_client(_cfg())
    res = client.complete(
        [{"role": "system", "content": "只输出 JSON"},
         {"role": "user", "content": '返回 {"ok": true}'}], json_mode=True)
    assert json.loads(res["content"])["ok"] is True
```

- [ ] **Step 2: 跑(fail)** → 旧 stub complete() 不打网络,断言失败(无真 content)。

- [ ] **Step 3: 实现** —— 整文件替换 `agents_llm/llm_client.py`:

```python
"""纯 DeepSeek LLM client(httpx,OpenAI 兼容 /chat/completions)。
无 openai/anthropic SDK;无 key → disabled;complete() 不抛,失败返回 {error}。"""
from __future__ import annotations

from typing import Any

import httpx

from praxis_virtualcell.core.config import Mode, RuntimeConfig


class LLMClient:
    def __init__(self, *, enabled: bool, api_key: str = "",
                 base_url: str = "https://api.deepseek.com",
                 model: str = "deepseek-chat", timeout: float = 60.0) -> None:
        self.enabled = enabled
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def complete(self, messages: list[dict], *, json_mode: bool = False,
                 max_tokens: int = 1024) -> dict[str, Any]:
        if not self.enabled:
            return {"disabled": True, "content": None, "error": None}
        body: dict[str, Any] = {"model": self.model, "messages": messages,
                                "temperature": 0, "max_tokens": max_tokens}
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        try:
            r = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}",
                         "Content-Type": "application/json"},
                json=body, timeout=self.timeout)
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"]
            return {"disabled": False, "content": content, "error": None}
        except Exception as e:  # noqa: BLE001 — 不抛,调用方 fallback
            return {"disabled": False, "content": None, "error": str(e)}


def make_llm_client(config: RuntimeConfig) -> LLMClient:
    enabled = config.mode is Mode.LLM_ASSISTED and bool(config.deepseek_api_key)
    return LLMClient(enabled=enabled, api_key=config.deepseek_api_key,
                     base_url=config.deepseek_base_url, model=config.deepseek_model)
```

- [ ] **Step 4: 跑(pass)** `... pytest praxis_virtualcell/tests/test_llm_connectivity.py praxis_virtualcell/tests/test_llm_optional.py praxis_virtualcell/tests/test_llm_client_offline.py -q` → llm 2 个真跑 pass,Week2 test_llm_optional 仍 pass(disabled 时 content=None/disabled=True)。
- [ ] **Step 5: commit** `feat(vc-llm): pure DeepSeek LLMClient via httpx`

---

## Task 3:LLMInputInterpreterAgent

**Files:** Create `agents_llm/llm_input_interpreter.py`、`tests/test_llm_input_interpreter.py`;Delete `agents_llm/optional_agents.py`

- [ ] **Step 1: 写测试** `tests/test_llm_input_interpreter.py`

```python
import os

import pytest

from praxis_virtualcell.agents_llm.llm_client import make_llm_client
from praxis_virtualcell.agents_llm.llm_input_interpreter import LLMInputInterpreterAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.config import Mode, RuntimeConfig, load_env
from praxis_virtualcell.core.message import AgentMessage


def _client():
    load_env()
    return make_llm_client(RuntimeConfig(mode=Mode.LLM_ASSISTED,
                                         deepseek_api_key=os.environ.get("DEEPSEEK_API_KEY", "")))


@pytest.mark.llm
def test_parses_chinese_experiment_description():
    bus = MessageBus()
    LLMInputInterpreterAgent(_client()).handle(
        AgentMessage("m1", "client", "LLMInputInterpreter", "parse_text",
                     {"text": "在 K562 细胞里敲除 AHR 基因,预测单细胞转录组变化"}, "t1"), bus)
    out = bus.latest("request_parsed")
    assert out is not None, "应解析成功 emit request_parsed"
    req = out.payload["request"]
    assert req["species"] == "human"
    assert "AHR" in [g.upper() for g in req["perturbation_targets"]]
    assert req["task_type"] == "predict_delta_expression"


@pytest.mark.llm
def test_garbage_input_falls_back():
    bus = MessageBus()
    LLMInputInterpreterAgent(_client()).handle(
        AgentMessage("m1", "client", "LLMInputInterpreter", "parse_text",
                     {"text": "今天天气怎么样"}, "t1"), bus)
    # 非实验描述:要么 fallback,要么解析出的 request 缺 target —— 不应崩
    assert bus.latest("request_parsed") is not None or bus.latest("llm_input_failed") is not None
```

- [ ] **Step 2: 跑(fail)** → ModuleNotFoundError。
- [ ] **Step 3: 实现** `agents_llm/llm_input_interpreter.py`:

```python
"""free-text → VirtualCellRequest JSON(DeepSeek json_mode)→ from_dict 校验 → request_parsed。
失败(LLM error / JSON / 校验)→ llm_input_failed(runtime fallback)。"""
from __future__ import annotations

import json
from dataclasses import asdict

from praxis_virtualcell.agents_llm.llm_client import LLMClient
from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.exceptions import InputValidationError
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.core.request import VirtualCellRequest

_SYS = (
    "你把用户的虚拟细胞实验描述解析成 JSON。字段:request_id, species, perturbation_type, "
    "perturbation_targets(数组), input_modality, output_modality, task_type, cell_type。"
    "约定:species 用小写英文(human/mouse/bacteria/yeast);基因敲除→perturbation_type='gene'、"
    "input_modality='scRNA'、output_modality='delta_expression'、task_type='predict_delta_expression'。"
    "无法判断的字段省略。只输出 JSON,不要解释。"
)


class LLMInputInterpreterAgent(BaseAgent):
    name = "LLMInputInterpreter"

    def __init__(self, client: LLMClient) -> None:
        self.client = client

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        text = message.payload["text"]
        res = self.client.complete(
            [{"role": "system", "content": _SYS}, {"role": "user", "content": text}],
            json_mode=True)
        reason = res.get("error") or "llm_disabled"
        if res.get("content"):
            try:
                d = json.loads(res["content"])
                d.setdefault("request_id", "llm-" + message.message_id)
                req = VirtualCellRequest.from_dict(d)
                bus.send(AgentMessage(message.message_id + ":llmparsed", self.name,
                    "BioObjectNormalizer", "request_parsed", {"request": asdict(req)},
                    message.timestamp, message.message_id))
                return
            except (json.JSONDecodeError, InputValidationError, KeyError, TypeError) as e:
                reason = f"llm_parse_invalid: {e}"
        bus.send(AgentMessage(message.message_id + ":llmfail", self.name, "client",
            "llm_input_failed", {"reason": reason, "text": text},
            message.timestamp, message.message_id))
```

`rm praxis_virtualcell/agents_llm/optional_agents.py`(无测试引用;被真 agent 取代)。

- [ ] **Step 4: 跑(pass)** `... pytest praxis_virtualcell/tests/test_llm_input_interpreter.py -q` → 2 pass。
- [ ] **Step 5: commit** `feat(vc-llm): LLMInputInterpreterAgent (NL→request, validated)`

---

## Task 4:LLMRouterAgent(只建议)

**Files:** Create `agents_llm/llm_router.py`、`tests/test_llm_router.py`

- [ ] **Step 1: 写测试** `tests/test_llm_router.py`

```python
import os

import pytest

from praxis_virtualcell.agents_llm.llm_client import make_llm_client
from praxis_virtualcell.agents_llm.llm_router import LLMRouterAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.config import Mode, RuntimeConfig, load_env
from praxis_virtualcell.core.message import AgentMessage


def _client():
    load_env()
    return make_llm_client(RuntimeConfig(mode=Mode.LLM_ASSISTED,
                                         deepseek_api_key=os.environ.get("DEEPSEEK_API_KEY", "")))


@pytest.mark.llm
def test_router_suggestion_subset_of_candidates():
    bus = MessageBus()
    payload = {"request": {"species": "human", "perturbation_targets": ["AHR"],
                           "task_type": "predict_delta_expression"},
               "brain_context": {}, "applicable": ["MockCPA", "MockGEARS"],
               "rejected_candidates": ["MockLinear"]}
    LLMRouterAgent(_client()).handle(
        AgentMessage("m1", "ModelApplicability", "LLMRouter", "route_suggest", payload, "t1"), bus)
    s = bus.latest("llm_route_suggestion").payload["suggestion"]
    cands = {"MockCPA", "MockGEARS", "MockLinear"}
    assert set(s["recommended_agents"]) <= cands
    assert set(s["excluded_agents"]) <= cands
```

- [ ] **Step 2: 跑(fail)**。
- [ ] **Step 3: 实现** `agents_llm/llm_router.py`:

```python
"""出路由建议(只建议,不裁决)。只能从候选里选;emit llm_route_suggestion。"""
from __future__ import annotations

import json

from praxis_virtualcell.agents_llm.llm_client import LLMClient
from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage

_SYS = (
    "你给虚拟细胞预测的模型路由建议。只输出 JSON:"
    '{"recommended_agents":[],"excluded_agents":[],"reasoning_summary":"","risk_flags":[]}。'
    "agent 名必须来自给定 candidates,不要发明新名字。只输出 JSON。"
)


class LLMRouterAgent(BaseAgent):
    name = "LLMRouter"

    def __init__(self, client: LLMClient) -> None:
        self.client = client

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        p = message.payload
        candidates = list(p.get("applicable", [])) + list(p.get("rejected_candidates", []))
        user = json.dumps({"request": p.get("request"), "candidates": candidates,
                           "rule_applicable": p.get("applicable")}, ensure_ascii=False)
        res = self.client.complete(
            [{"role": "system", "content": _SYS}, {"role": "user", "content": user}],
            json_mode=True)
        sug = {"recommended_agents": [], "excluded_agents": [],
               "reasoning_summary": "", "risk_flags": []}
        if res.get("content"):
            try:
                d = json.loads(res["content"])
                sug["recommended_agents"] = [a for a in (d.get("recommended_agents") or []) if a in candidates]
                sug["excluded_agents"] = [a for a in (d.get("excluded_agents") or []) if a in candidates]
                sug["reasoning_summary"] = str(d.get("reasoning_summary", ""))[:500]
                sug["risk_flags"] = list(d.get("risk_flags") or [])
            except json.JSONDecodeError:
                sug["risk_flags"] = ["llm_parse_failed"]
        else:
            sug["risk_flags"] = ["llm_unavailable"]
        conflict = bool(set(sug["excluded_agents"]) & set(p.get("applicable", [])))
        bus.send(AgentMessage(message.message_id + ":llmroute", self.name, "client",
            "llm_route_suggestion", {"suggestion": sug, "conflict_with_rule": conflict},
            message.timestamp, message.message_id))
```

- [ ] **Step 4: 跑(pass)**。
- [ ] **Step 5: commit** `feat(vc-llm): LLMRouterAgent (suggest-only, candidate-bounded)`

---

## Task 5:LLMCriticAgent(只出 notes)

**Files:** Create `agents_llm/llm_critic.py`、`tests/test_llm_critic.py`

- [ ] **Step 1: 写测试** `tests/test_llm_critic.py`

```python
import os

import pytest

from praxis_virtualcell.agents_llm.llm_client import make_llm_client
from praxis_virtualcell.agents_llm.llm_critic import LLMCriticAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.config import Mode, RuntimeConfig, load_env
from praxis_virtualcell.core.message import AgentMessage


def _client():
    load_env()
    return make_llm_client(RuntimeConfig(mode=Mode.LLM_ASSISTED,
                                         deepseek_api_key=os.environ.get("DEEPSEEK_API_KEY", "")))


@pytest.mark.llm
def test_critic_returns_structured_notes():
    bus = MessageBus()
    report = {"abstain": False, "models_used": ["MockGEARS"],
              "models_rejected": ["MockGEARS"],  # 矛盾:既 used 又 rejected
              "prediction": {"delta": [0.9]}, "reliability": "high", "provenance": {}}
    LLMCriticAgent(_client()).handle(
        AgentMessage("m1", "Report", "LLMCritic", "llm_review", {"report": report}, "t1"), bus)
    out = bus.latest("llm_critic_notes").payload
    assert isinstance(out.get("notes"), list)
    assert isinstance(out.get("flags"), list)
    # LLM 不改 prediction:输入 report 对象未被修改
    assert report["prediction"] == {"delta": [0.9]}
```

- [ ] **Step 2: 跑(fail)**。
- [ ] **Step 3: 实现** `agents_llm/llm_critic.py`:

```python
"""审报告(夸大/违规/漏不确定性/rejected 写成 used)→ 只出 notes+flags,不改 prediction。"""
from __future__ import annotations

import json

from praxis_virtualcell.agents_llm.llm_client import LLMClient
from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage

_SYS = (
    "你审查虚拟细胞预测报告的诚实性。检查:是否把 rejected 模型写成 used、是否夸大、"
    "是否漏报不确定性、是否 abstain 却仍给了预测。只输出 JSON:"
    '{"notes":[],"flags":[]}。flags 用简短英文标签。只输出 JSON。'
)


class LLMCriticAgent(BaseAgent):
    name = "LLMCritic"

    def __init__(self, client: LLMClient) -> None:
        self.client = client

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        report = message.payload["report"]
        res = self.client.complete(
            [{"role": "system", "content": _SYS},
             {"role": "user", "content": json.dumps(report, ensure_ascii=False)}],
            json_mode=True)
        out = {"notes": [], "flags": []}
        if res.get("content"):
            try:
                d = json.loads(res["content"])
                out["notes"] = list(d.get("notes") or [])
                out["flags"] = list(d.get("flags") or [])
            except json.JSONDecodeError:
                out["flags"] = ["llm_parse_failed"]
        else:
            out["flags"] = ["llm_unavailable"]
        bus.send(AgentMessage(message.message_id + ":llmcrit", self.name, "client",
            "llm_critic_notes", out, message.timestamp, message.message_id))
```

- [ ] **Step 4: 跑(pass)**。
- [ ] **Step 5: commit** `feat(vc-llm): LLMCriticAgent (notes-only)`

---

## Task 6:LLMReportAgent(NL 叙述,不编造)

**Files:** Create `agents_llm/llm_report.py`、`tests/test_llm_report.py`

- [ ] **Step 1: 写测试** `tests/test_llm_report.py`

```python
import os

import pytest

from praxis_virtualcell.agents_llm.llm_client import make_llm_client
from praxis_virtualcell.agents_llm.llm_report import LLMReportAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.config import Mode, RuntimeConfig, load_env
from praxis_virtualcell.core.message import AgentMessage


def _client():
    load_env()
    return make_llm_client(RuntimeConfig(mode=Mode.LLM_ASSISTED,
                                         deepseek_api_key=os.environ.get("DEEPSEEK_API_KEY", "")))


@pytest.mark.llm
def test_report_narrative_nonempty_for_abstain():
    bus = MessageBus()
    report = {"request_id": "r1", "abstain": True, "reliability": "low",
              "prediction": None, "models_used": [], "models_rejected": ["MockCPA"],
              "abstain_reasons": ["all_predictors_rejected"], "provenance": {"n_messages": 12}}
    LLMReportAgent(_client()).handle(
        AgentMessage("m1", "Report", "LLMReport", "llm_render", {"report": report}, "t1"), bus)
    narrative = bus.latest("llm_narrative").payload["narrative"]
    assert isinstance(narrative, str) and len(narrative) > 0
```

- [ ] **Step 2: 跑(fail)**。
- [ ] **Step 3: 实现** `agents_llm/llm_report.py`:

```python
"""结构化报告 → 中文 NL 叙述。忠实保留 abstain/参与/拒绝/reliability/provenance,不编造。"""
from __future__ import annotations

import json

from praxis_virtualcell.agents_llm.llm_client import LLMClient
from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage

_SYS = (
    "你把结构化的虚拟细胞预测报告改写成简洁中文科研叙述。必须忠实保留:是否 abstain、"
    "用了/拒了哪些模型、reliability、provenance 要点;不得编造报告里没有的预测数值或结论。"
    "只输出叙述文本,不要输出 JSON。"
)


class LLMReportAgent(BaseAgent):
    name = "LLMReport"

    def __init__(self, client: LLMClient) -> None:
        self.client = client

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        report = message.payload["report"]
        res = self.client.complete(
            [{"role": "system", "content": _SYS},
             {"role": "user", "content": json.dumps(report, ensure_ascii=False)}],
            max_tokens=800)
        narrative = res.get("content") or ""
        bus.send(AgentMessage(message.message_id + ":llmrep", self.name, "client",
            "llm_narrative", {"narrative": narrative}, message.timestamp, message.message_id))
```

- [ ] **Step 4: 跑(pass)**。
- [ ] **Step 5: commit** `feat(vc-llm): LLMReportAgent (narrative, faithful)`

---

## Task 7:runtime llm_assisted seam + build_runtime 接 LLM + 不变量/fallback/e2e 测试

**Files:** Modify `core/runtime.py`、`workflows/predict_delta_expression.py`;Create `tests/test_llm_numeric_invariance.py`、`tests/test_llm_fallback_offline.py`、`tests/test_llm_e2e_demo.py`

- [ ] **Step 1: 写测试**

`tests/test_llm_fallback_offline.py`(**offline,无需 key**):
```python
from praxis_virtualcell.core.config import Mode, RuntimeConfig
from praxis_virtualcell.workflows.predict_delta_expression import build_runtime

_HUMAN = {"request_id": "r1", "species": "human", "perturbation_type": "gene",
          "perturbation_targets": ["AHR"], "input_modality": "scRNA",
          "output_modality": "delta_expression", "task_type": "predict_delta_expression"}


def test_llm_assisted_without_key_equals_offline():
    from praxis_virtualcell.core.request import VirtualCellRequest
    off = build_runtime(RuntimeConfig(mode=Mode.OFFLINE)).run_workflow(
        VirtualCellRequest.from_dict(_HUMAN))
    # llm_assisted 但无 key → client disabled → 不注册 LLM agent → 等价 offline
    llm = build_runtime(RuntimeConfig(mode=Mode.LLM_ASSISTED, deepseek_api_key="")).run_workflow(
        VirtualCellRequest.from_dict(_HUMAN))
    for k in ("abstain", "prediction", "models_used", "models_rejected", "reliability"):
        assert off[k] == llm[k]
    assert "narrative" not in llm  # 无 LLM → 无叙述
```

`tests/test_llm_numeric_invariance.py`(**llm**):
```python
import os

import pytest

from praxis_virtualcell.core.config import Mode, RuntimeConfig, load_env
from praxis_virtualcell.core.request import VirtualCellRequest
from praxis_virtualcell.workflows.predict_delta_expression import build_runtime

_HUMAN = {"request_id": "r1", "species": "human", "perturbation_type": "gene",
          "perturbation_targets": ["AHR"], "input_modality": "scRNA",
          "output_modality": "delta_expression", "task_type": "predict_delta_expression"}


@pytest.mark.llm
def test_structured_fields_identical_offline_vs_llm_assisted():
    load_env()
    off = build_runtime(RuntimeConfig(mode=Mode.OFFLINE)).run_workflow(
        VirtualCellRequest.from_dict(_HUMAN))
    cfg = RuntimeConfig(mode=Mode.LLM_ASSISTED, deepseek_api_key=os.environ["DEEPSEEK_API_KEY"])
    llm = build_runtime(cfg).run_workflow(VirtualCellRequest.from_dict(_HUMAN))
    for k in ("abstain", "prediction", "models_used", "models_rejected",
              "reliability", "abstain_reasons", "critic_violations"):
        assert off[k] == llm[k], f"字段 {k} 在 llm_assisted 下被改了"
    assert "narrative" in llm  # LLM 只新增叙述
    assert "llm_route_suggestion" in llm["provenance"]
```

`tests/test_llm_e2e_demo.py`(**llm**):
```python
import os

import pytest

from praxis_virtualcell.core.config import Mode, RuntimeConfig, load_env
from praxis_virtualcell.workflows.predict_delta_expression import build_runtime


@pytest.mark.llm
def test_free_text_end_to_end_with_real_deepseek():
    load_env()
    cfg = RuntimeConfig(mode=Mode.LLM_ASSISTED, deepseek_api_key=os.environ["DEEPSEEK_API_KEY"])
    rt = build_runtime(cfg)
    report = rt.run_workflow_from_text("在 K562 细胞里敲除 AHR 基因,预测单细胞转录组变化")
    assert report.get("narrative")  # 有 LLM 中文叙述
    assert "MockCPA" in report["models_used"]  # AHR 已知 → 预测成功
    assert report["abstain"] is False
    types = [m.message_type for m in rt.bus.trace]
    assert "request_parsed" in types and "llm_narrative" in types
```

- [ ] **Step 2: 跑(fail)** → AttributeError(无 run_workflow_from_text / build_runtime 未接 LLM)。

- [ ] **Step 3: 实现** —— `core/runtime.py`:把 `run_workflow` 里 `app = self._dispatch_collect(m, "applicability_decided")` 之后到 `return rep.payload["report"]` 的尾段,替换为下面这版(加 LLM seam);并新增 `run_workflow_from_text`。

在 `run_workflow` 中,`app = self._dispatch_collect(m, "applicability_decided")` 行**之后紧接**插入:
```python
        llm_route = None
        if "LLMRouter" in self._agents:
            rmsg = self.mk_message("ModelApplicability", "LLMRouter", "route_suggest",
                {"request": app.payload["request"], "brain_context": app.payload["brain_context"],
                 "applicable": app.payload["applicable"],
                 "rejected_candidates": app.payload["rejected_candidates"]}, app.message_id)
            llm_route = self._dispatch_collect(rmsg, "llm_route_suggestion").payload
```
然后把最后 `return rep.payload["report"]` 改为:
```python
        report = rep.payload["report"]
        if llm_route is not None:
            report.setdefault("provenance", {})["llm_route_suggestion"] = llm_route
        if "LLMCritic" in self._agents:
            cm = self.mk_message("Report", "LLMCritic", "llm_review",
                                {"report": report}, rep.message_id)
            report.setdefault("provenance", {})["llm_critic_notes"] = \
                self._dispatch_collect(cm, "llm_critic_notes").payload
        if "LLMReport" in self._agents:
            nm = self.mk_message("Report", "LLMReport", "llm_render",
                                {"report": report}, rep.message_id)
            report["narrative"] = self._dispatch_collect(nm, "llm_narrative").payload["narrative"]
        return report
```
(注:predictor fan-out 仍用 `app.payload["applicable"]` 原值 → 数值路径不变。)

在 `export_outputs` 之后追加:
```python
    def run_workflow_from_text(self, text: str) -> dict:
        """free-text(仅 llm_assisted+key):LLMInputInterpreter 解析 → run_workflow。"""
        from praxis_virtualcell.core.exceptions import InputValidationError
        from praxis_virtualcell.core.request import VirtualCellRequest
        if "LLMInputInterpreter" not in self._agents:
            raise InputValidationError("free-text 需 llm_assisted + DEEPSEEK_API_KEY")
        m = self.mk_message("client", "LLMInputInterpreter", "parse_text", {"text": text})
        self.dispatch_message(m)
        parsed = self.bus.latest("request_parsed")
        if parsed is None:
            fail = self.bus.latest("llm_input_failed")
            return {"request_id": None, "abstain": True, "reliability": "low",
                    "prediction": None, "models_used": [], "models_rejected": [],
                    "abstain_reasons": ["input_missing"], "critic_violations": [],
                    "narrative": "", "provenance": {"llm_input_failed": fail.payload if fail else None}}
        return self.run_workflow(VirtualCellRequest.from_dict(parsed.payload["request"]))
```

`workflows/predict_delta_expression.py`:在 `build_runtime` 里 12 个 agent 注册之后、设 `run_workflow_from_dict` 之前,插入 LLM agent 注册:
```python
    from praxis_virtualcell.agents_llm.llm_client import make_llm_client
    client = make_llm_client(cfg)
    if client.enabled:
        from praxis_virtualcell.agents_llm.llm_critic import LLMCriticAgent
        from praxis_virtualcell.agents_llm.llm_input_interpreter import LLMInputInterpreterAgent
        from praxis_virtualcell.agents_llm.llm_report import LLMReportAgent
        from praxis_virtualcell.agents_llm.llm_router import LLMRouterAgent
        for a in (LLMInputInterpreterAgent(client), LLMRouterAgent(client),
                  LLMCriticAgent(client), LLMReportAgent(client)):
            rt.register_agent(a)
```

- [ ] **Step 4: 跑(pass)** `... pytest praxis_virtualcell/tests/test_llm_fallback_offline.py praxis_virtualcell/tests/test_llm_numeric_invariance.py praxis_virtualcell/tests/test_llm_e2e_demo.py praxis_virtualcell/tests/test_offline_workflow.py praxis_virtualcell/tests/test_no_fake_multiagent.py -q` → fallback/offline 必绿;llm 三个有 key 真跑绿。
- [ ] **Step 5: commit** `feat(vc-llm): runtime llm_assisted seam + free-text workflow`

---

## Task 8:.env.example + demo 例子 + 全套绿 + 硬门

**Files:** Create `.env.example`、`examples/free_text_request.txt`

- [ ] **Step 1: 创建**

`.env.example`(提交,占位):
```
# 复制为 .env 并填真实 key(.env 已被 .gitignore 忽略,勿提交)
DEEPSEEK_API_KEY=
PRAXIS_VC_LLM_BASE_URL=https://api.deepseek.com
PRAXIS_VC_LLM_MODEL=deepseek-chat
PRAXIS_VIRTUALCELL_MODE=offline
```
`examples/free_text_request.txt`:
```
在 K562 细胞里敲除 AHR 基因,预测单细胞转录组的变化。
```

- [ ] **Step 2: 全套 + 硬门**

Run:
```bash
cd /Volumes/T7/PRAXIS-virtualcell && find praxis_virtualcell -name '._*' -delete
.venv/bin/python -m pytest praxis_virtualcell/tests -q 2>&1 | tail -8
echo "=== 硬门:主链路无 openai/anthropic SDK import ==="
if grep -rnE "import openai|from openai|import anthropic|from anthropic" praxis_virtualcell --include='*.py'; then echo VIOLATION; else echo "CLEAN"; fi
echo "=== .env 仍被忽略 ==="; git check-ignore .env >/dev/null && echo "IGNORED ✓"
```
Expected: 全 pass(offline + 本机 .env 有 key 则 llm 真跑);`CLEAN`;`.env IGNORED`。

- [ ] **Step 3: 验收映射(spec §7)**:① 无 key offline 绿(test_llm_fallback_offline + 35 底座)② NL 解析(test_llm_input_interpreter)③ router 只建议(test_llm_router + numeric_invariance 的 applicable 不变)④ critic 不改数值(test_llm_critic)⑤ report 不编造(test_llm_report)⑥ 数值一致(test_llm_numeric_invariance)⑦ e2e demo(test_llm_e2e_demo)。

- [ ] **Step 4: commit** `git add -A praxis_virtualcell .env.example && git commit -m "feat(vc-llm): .env.example + free-text demo + week3 acceptance"`(确认 `git status` 不含 `.env`)。

---

## 验收(DoD)
1. `pytest praxis_virtualcell/tests`:offline 全绿(无 key 也行);有 `.env` key 时 llm 测试真打 DeepSeek 绿。
2. LLM 只增强:numeric_invariance 证结构化字段 offline==llm_assisted;router 不改 applicable 集。
3. free-text e2e demo 用真 DeepSeek 跑通(中文 narrative + provenance + trace 含 llm_* 消息)。
4. 主链路无 openai/anthropic SDK import;`.env` 未入库,`.env.example` 已提交。
5. Week 2 的 35 offline 测试零回归。
