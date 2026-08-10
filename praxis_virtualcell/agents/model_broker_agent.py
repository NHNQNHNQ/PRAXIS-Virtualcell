"""ModelBrokerAgent:模型治理代理,进 message bus。

收 model_request(payload {model_name})→ 查 ModelZooRegistry + 检 requires 依赖 + 解析 source →
产 model_broker_result({model_name, available, status, wrapper, reason})。

铁律(本 Phase 核心):status != available / requires 依赖不满足 / source 需人工获取 →
available=False + reason,fail-closed,绝不 silent accept。gpu 无法静态检测,按声明降级
(available=False,reason 注明需运行时确认 gpu)。
"""

from __future__ import annotations

import hashlib
import importlib.util

from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.core.request_v2 import VirtualCellRequestV2
from praxis_virtualcell.data_packs.errors import PackRegistryError
from praxis_virtualcell.data_packs.registry import PackRegistry, RegisteredPack
from praxis_virtualcell.model_zoo.adapter_sdk import (
    AdapterContractError,
    AdapterRegistry,
)
from praxis_virtualcell.model_zoo.cache import ModelCache
from praxis_virtualcell.model_zoo.capability_registry import (
    CapabilityRegistry,
    EnvironmentSnapshot,
    ExecutionPlan,
    ExecutionPlanV2,
)
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

    def __init__(
        self,
        registry: ModelZooRegistry | None = None,
        cache: ModelCache | None = None,
        pack_registry: PackRegistry | None = None,
        environment: EnvironmentSnapshot | None = None,
        adapter_registry: AdapterRegistry | None = None,
    ) -> None:
        self._reg = registry or ModelZooRegistry()
        self._cache = cache or ModelCache()
        self._packs = pack_registry or PackRegistry()
        cards = tuple(self._reg.card(name) for name in self._reg.capability_names())
        self._environment = environment or EnvironmentSnapshot.detect(cards)
        self._capabilities = CapabilityRegistry(
            self._reg,
            self._cache,
            adapter_registry=adapter_registry,
        )
        self._prepared: dict[str, list] = {}

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        if message.message_type == "execution_plan_request":
            self._handle_execution_plan(message, bus)
            return
        model_name = message.payload.get("model_name")
        result = self._resolve(model_name)
        bus.send(
            AgentMessage(
                message_id=message.message_id + ":broker",
                sender=self.name,
                receiver="EnsembleCoordinator",
                message_type="model_broker_result",
                payload=result,
                timestamp=message.timestamp,
                parent_message_id=message.message_id,
            )
        )

    def plan(
        self,
        request: VirtualCellRequestV2,
        pack: RegisteredPack | None,
    ) -> ExecutionPlan | ExecutionPlanV2:
        """Build the authoritative plan without preparing model wrappers."""
        return self._capabilities.plan(request, pack, self._environment)

    def _handle_execution_plan(
        self,
        message: AgentMessage,
        bus: MessageBus,
    ) -> None:
        request = VirtualCellRequestV2.from_dict(message.payload.get("request"))
        pack_id = message.payload.get("pack_id")
        pack_version = message.payload.get("pack_version")
        if pack_id is None or pack_version is None:
            pack = None
        else:
            try:
                pack = self._packs.record(pack_id, pack_version)
            except PackRegistryError:
                pack = None
        plan = self.plan(request, pack)
        reports = {report.model_name: report for report in plan.reports}
        prepared = []
        failed: dict[str, str] = {}
        for step in plan.steps:
            try:
                prepared.append(
                    self._capabilities.instantiate(
                        step,
                        reports[step.model_name],
                        request=request,
                        pack=pack,
                    )
                )
            except AdapterContractError:
                failed[step.model_name] = "adapter.input_preparation"
            except Exception:  # noqa: BLE001 - constructor/import failures are a broker gate
                failed[step.model_name] = "model.wrapper_initialization"
        if failed:
            revised_reports = []
            for report in plan.reports:
                if report.model_name not in failed:
                    revised_reports.append(report)
                    continue
                checks = dict(report.checks)
                reason = failed[report.model_name]
                checks[reason] = False
                revised = report.to_dict()
                revised.update(
                    {
                        "wrapper_ready": False,
                        "environment_compatible": False,
                        "executable": False,
                        "checks": checks,
                        "reasons": list(report.reasons) + [reason],
                    }
                )
                revised_reports.append(type(report).from_dict(revised))
            steps = tuple(step for step in plan.steps if step.model_name not in failed)
            if isinstance(plan, ExecutionPlanV2):
                plan = plan.rebuild(
                    reports=tuple(revised_reports),
                    steps=steps,
                )
            else:
                identity = (plan.plan_id + "|" + "|".join(sorted(failed))).encode("utf-8")
                revised_plan = plan.to_dict()
                revised_plan.update(
                    {
                        "plan_id": f"plan_{hashlib.sha256(identity).hexdigest()[:24]}",
                        "executable": bool(steps),
                        "steps": [step.to_dict() for step in steps],
                        "reports": [report.to_dict() for report in revised_reports],
                    }
                )
                plan = type(plan).from_dict(revised_plan)
        self._prepared[plan.plan_id] = prepared
        bus.send(
            AgentMessage(
                message_id=message.message_id + ":plan",
                sender=self.name,
                receiver="EnsembleCoordinator",
                message_type="execution_plan_ready",
                payload={"execution_plan": plan.to_dict()},
                timestamp=message.timestamp,
                parent_message_id=message.message_id,
            )
        )

    def take_prepared(self, plan_id: str) -> list:
        return self._prepared.pop(plan_id, [])

    def _resolve(self, model_name: str | None) -> dict:
        base = {"model_name": model_name, "available": False, "status": "missing", "wrapper": None, "reason": ""}
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

        # 5) assets 版本锁关(有 assets 时每条须落地 + sha 对;sha=null 占位 → requires_manual_fetch)。
        #    这是 fail-closed 第二道锁:即便依赖/source 齐,ckpt 未取到/sha 不匹配 → 不静默 accept(红线 6)。
        for a in entry.get("assets", []) or []:
            declared_sha = a.get("sha256")
            if declared_sha is None:
                base["reason"] = (
                    f"asset requires_manual_fetch: {a.get('filename')} sha256 未登记"
                    f"(占位)—— 需按 source_note 手动获取并登记 sha 后方可用"
                )
                return base
            st = self._cache.check(model_name, a["filename"], sha256=declared_sha)
            if not st.available:
                base["reason"] = f"asset unavailable: {st.reason}"
                return base

        # 全部通过 → available
        base["available"] = True
        base["reason"] = "ok"
        return base
