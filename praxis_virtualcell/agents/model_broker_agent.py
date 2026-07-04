"""ModelBrokerAgent:模型治理代理,进 message bus。

收 model_request(payload {model_name})→ 查 ModelZooRegistry + 检 requires 依赖 + 解析 source →
产 model_broker_result({model_name, available, status, wrapper, reason})。

铁律(本 Phase 核心):status != available / requires 依赖不满足 / source 需人工获取 →
available=False + reason,fail-closed,绝不 silent accept。gpu 无法静态检测,按声明降级
(available=False,reason 注明需运行时确认 gpu)。
"""
from __future__ import annotations

import importlib.util

from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.model_zoo.downloader import resolve_source
from praxis_virtualcell.model_zoo.registry import ModelZooRegistry

# 可静态检测的 python 依赖(gpu 不可静态检 → 见下)
_PY_DEPS = {"torch", "cobra"}


def _dep_available(dep: str) -> bool:
    """python 依赖是否可 import(gpu 类非 python 依赖返 False,交由 reason 说明)。"""
    if dep in _PY_DEPS:
        return importlib.util.find_spec(dep) is not None
    return False  # gpu 等运行时资源无法静态确认 → 保守判不满足(fail-closed)


class ModelBrokerAgent(BaseAgent):
    name = "ModelBrokerAgent"

    def __init__(self, registry: ModelZooRegistry | None = None) -> None:
        self._reg = registry or ModelZooRegistry()

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        model_name = message.payload.get("model_name")
        result = self._resolve(model_name)
        bus.send(AgentMessage(
            message_id=message.message_id + ":broker",
            sender=self.name, receiver="EnsembleCoordinator",
            message_type="model_broker_result", payload=result,
            timestamp=message.timestamp, parent_message_id=message.message_id))

    def _resolve(self, model_name: str | None) -> dict:
        base = {"model_name": model_name, "available": False, "status": "missing",
                "wrapper": None, "reason": ""}
        # 1) 未知模型 → fail-closed
        try:
            entry = self._reg.get(model_name)
        except KeyError:
            base["reason"] = f"unknown model: {model_name}(未知模型,不静默接受)"
            return base

        status = entry["status"]
        base["status"] = status
        base["wrapper"] = entry.get("wrapper")

        # 2) status 非 available → fail-closed(planned/missing)
        if status != "available":
            base["reason"] = f"model status={status}, not available(fail-closed,not silent accept)"
            return base

        # 3) requires 依赖检查(缺任一 → 明确降级,点名缺的依赖)
        missing_deps = [d for d in entry.get("requires", []) if not _dep_available(d)]
        if missing_deps:
            base["reason"] = f"missing required dependencies: {missing_deps}(fail-closed)"
            return base

        # 4) source 解析(远端 gated → requires_manual_fetch → 不可用)
        src = resolve_source(entry)
        if not src["available"]:
            base["reason"] = f"source not resolvable: {src['reason']}"
            return base

        # 全部通过 → available
        base["available"] = True
        base["reason"] = "ok"
        return base
