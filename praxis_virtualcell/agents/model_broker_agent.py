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
from praxis_virtualcell.core.domain_extension import DomainExtensionIdentityV1
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.core.request_v2 import VirtualCellRequestV2
from praxis_virtualcell.data_packs.errors import PackRegistryError
from praxis_virtualcell.data_packs.registry import (
    PackRegistry,
    PreparedPackViewV1,
    PreparedPackViewV2,
    RegisteredPack,
)
from praxis_virtualcell.data_packs.selected_content import (
    PreparedSelectedContentV1,
    SelectedContentRequestV1,
)
from praxis_virtualcell.model_zoo.adapter_sdk import (
    AdapterContractError,
    AdapterInputReceipt,
    AdapterInputReceiptV2,
    AdapterRegistry,
)
from praxis_virtualcell.model_zoo.cache import ModelCache
from praxis_virtualcell.model_zoo.capability_registry import (
    CapabilityRegistry,
    EnvironmentSnapshot,
    ExecutionPlan,
    ExecutionPlanV2,
    ExecutionPlanV3,
    direct_v2_execution_report,
)
from praxis_virtualcell.model_zoo.downloader import resolve_source
from praxis_virtualcell.model_zoo.post_result_policy import (
    OutputReducerBindingV1,
    OutputReducerModelAdapterBindingV1,
    OutputReducerPolicyNotFoundError,
    OutputReducerPolicyRegistry,
    ResolvedOutputReducerPolicy,
)
from praxis_virtualcell.model_zoo.registry import ModelZooRegistry
from praxis_virtualcell.model_zoo.wrapper_registry import WrapperRegistry

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
        wrapper_registry: WrapperRegistry | None = None,
        output_reducer_registry: OutputReducerPolicyRegistry | None = None,
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
            wrapper_registry=wrapper_registry,
        )
        self._prepared: dict[str, list] = {}
        self._prepared_v2: dict[str, dict[str, dict]] = {}
        if output_reducer_registry is not None and not isinstance(
            output_reducer_registry,
            OutputReducerPolicyRegistry,
        ):
            raise TypeError("output_reducer_registry must be OutputReducerPolicyRegistry")
        self._output_reducers = output_reducer_registry

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        if message.message_type in {
            "execution_plan_request",
            "execution_plan_v2_request",
        }:
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
        *,
        require_registered_wrapper: bool = False,
    ) -> ExecutionPlan | ExecutionPlanV2:
        """Build the authoritative plan without preparing model wrappers."""
        if not require_registered_wrapper:
            # Preserve the legacy call shape and behavior exactly.  The explicit
            # registry gate is only part of the new direct-v2 submission seam.
            return self._capabilities.plan(request, pack, self._environment)
        return self._capabilities.plan(
            request,
            pack,
            self._environment,
            require_registered_wrapper=True,
        )

    @staticmethod
    def _deny_domain_execution(
        plan: ExecutionPlanV2 | ExecutionPlanV3,
        reasons: tuple[str, ...],
    ) -> ExecutionPlanV2 | ExecutionPlanV3:
        reports = []
        for report in plan.reports:
            value = report.to_dict()
            checks = dict(report.checks)
            checks["domain.extension"] = False
            value.update(
                {
                    "executable": False,
                    "checks": checks,
                    "reasons": list(dict.fromkeys((*report.reasons, *reasons))),
                }
            )
            reports.append(type(report).from_dict(value))
        return plan.rebuild(reports=tuple(reports), steps=())

    @staticmethod
    def _deny_unreduced_multi_step_execution(
        plan: ExecutionPlanV2 | ExecutionPlanV3,
    ) -> ExecutionPlanV2 | ExecutionPlanV3:
        """Keep U2-disabled multi-model plans out of adapter/wrapper preparation."""

        reports = []
        for report in plan.reports:
            value = report.to_dict()
            checks = dict(report.checks)
            checks["runtime.output_reducer"] = False
            value.update(
                {
                    "executable": False,
                    "checks": checks,
                    "reasons": list(dict.fromkeys((*report.reasons, "output_reducer_required"))),
                }
            )
            reports.append(type(report).from_dict(value))
        return plan.rebuild(reports=tuple(reports), steps=())

    @staticmethod
    def _deny_pack_integrity_execution(
        plan: ExecutionPlanV2 | ExecutionPlanV3,
    ) -> ExecutionPlanV2 | ExecutionPlanV3:
        """Record a pre-execution Pack byte drift without preparing a model."""

        reports = []
        for report in plan.reports:
            value = report.to_dict()
            checks = dict(report.checks)
            checks["pack.integrity"] = False
            value.update(
                {
                    "executable": False,
                    "checks": checks,
                    "reasons": list(dict.fromkeys((*report.reasons, "pack.integrity_drift"))),
                }
            )
            reports.append(type(report).from_dict(value))
        return plan.rebuild(reports=tuple(reports), steps=())

    @staticmethod
    def _deny_artifact_snapshot_budget_execution(
        plan: ExecutionPlanV2 | ExecutionPlanV3,
        reason: str,
    ) -> ExecutionPlanV2 | ExecutionPlanV3:
        """Fail closed before any content/materialization/wrapper work."""

        reports = []
        for report in plan.reports:
            value = report.to_dict()
            checks = dict(report.checks)
            checks["artifact.snapshot_budget"] = False
            value.update(
                {
                    "executable": False,
                    "checks": checks,
                    "reasons": list(dict.fromkeys((*report.reasons, reason))),
                }
            )
            reports.append(type(report).from_dict(value))
        return plan.rebuild(reports=tuple(reports), steps=())

    def _artifact_snapshot_budget_reason(
        self,
        plan: ExecutionPlanV2 | ExecutionPlanV3,
    ) -> str | None:
        """Validate the release-bound aggregate snapshot budget without reads."""

        identity = self._environment.identity
        if self._environment.schema_version != "vc.environment.v3" or identity is None:
            return "artifact.snapshot_budget_unavailable"
        budget = getattr(identity, "artifact_snapshot_budget_policy", None)
        if budget is None:
            return "artifact.snapshot_budget_unavailable"
        try:
            bindings = tuple(
                binding
                for step in plan.steps
                for binding in self._capabilities.direct_v2_artifact_bindings(
                    step,
                    {report.model_name: report for report in plan.reports}[step.model_name],
                )
            )
        except Exception:  # noqa: BLE001 - exact release/binding preflight is fail-closed
            return "artifact.snapshot_budget_unavailable"
        if (
            len(bindings) > budget.max_snapshot_entries_per_execution
            or sum(binding[3] for binding in bindings) > budget.max_live_snapshot_payload_bytes
        ):
            return "artifact.snapshot_budget_exceeded"
        return None

    def _resolve_output_reducer(
        self,
        plan: ExecutionPlanV2,
        request: VirtualCellRequestV2,
    ) -> tuple[ExecutionPlanV3, ResolvedOutputReducerPolicy]:
        """Turn an exact provisional V2 multi-step plan into one U2 V3 plan.

        This happens before any Pack content materialization, adapter input
        preparation, or wrapper construction.  No registry/policy is a hard
        empty-plan gate rather than a chance to choose an implicit mean.
        """

        if self._output_reducers is None:
            raise OutputReducerPolicyNotFoundError("no output reducer registry is configured")
        requested_outputs = request.task.requested_outputs or (request.output_modality.name,)
        adapter = self._capabilities.adapter_registry.resolve_requested(
            request.task.task_type,
            requested_outputs,
        )
        if not (
            len(plan.steps) >= 2
            and all(
                len(step.adapter_fingerprints) == 1 and step.adapter_fingerprints[0] == adapter.fingerprint()
                for step in plan.steps
            )
        ):
            raise OutputReducerPolicyNotFoundError("multi-step plan does not have one exact shared adapter")
        bindings = tuple(
            OutputReducerModelAdapterBindingV1(
                schema_version="vc.output-reducer-model-adapter-binding.v1",
                model_name=step.model_name,
                model_fingerprint=step.model_fingerprint,
                release_fingerprint=step.release_fingerprint,
                adapter_fingerprint=step.adapter_fingerprints[0],
            )
            for step in plan.steps
        )
        resolved = self._output_reducers.resolve(
            task=request.task.task_type,
            output_contract_fingerprint=adapter.output_contract.fingerprint(),
            model_adapter_bindings=bindings,
        )
        return (
            ExecutionPlanV3.build(
                request_id=plan.request_id,
                request_fingerprint=plan.request_fingerprint,
                pack_id=plan.pack_id,
                pack_version=plan.pack_version,
                pack_fingerprint=plan.pack_fingerprint,
                environment_snapshot_fingerprint=plan.environment_snapshot_fingerprint,
                output_reducer=resolved.binding(),
                reports=plan.reports,
                steps=plan.steps,
            ),
            resolved,
        )

    def _handle_execution_plan(
        self,
        message: AgentMessage,
        bus: MessageBus,
    ) -> None:
        direct_v2 = message.message_type == "execution_plan_v2_request"
        request = VirtualCellRequestV2.from_dict(message.payload.get("request"))
        domain_identity = None
        domain_denial_reasons: tuple[str, ...] = ()
        if direct_v2 and "domain_extension_identity" in message.payload:
            try:
                domain_identity = DomainExtensionIdentityV1.from_dict(message.payload["domain_extension_identity"])
                if domain_identity.taxonomy_id != request.species.taxonomy_id:
                    raise ValueError("domain extension identity taxon mismatch")
                if not domain_identity.allow_execution:
                    domain_denial_reasons = tuple(f"domain.policy.{reason}" for reason in domain_identity.reasons)
            except Exception:  # noqa: BLE001 - domain identity is a hard broker gate
                domain_identity = None
                domain_denial_reasons = ("domain.extension_identity_invalid",)
        pack_id = message.payload.get("pack_id")
        pack_version = message.payload.get("pack_version")
        if pack_id is None or pack_version is None:
            pack = None
        else:
            try:
                pack = self._packs.record(pack_id, pack_version)
            except PackRegistryError:
                pack = None
        pack_view: PreparedPackViewV1 | PreparedPackViewV2 | None = None
        pack_integrity_drift = False
        resolved_reducer: ResolvedOutputReducerPolicy | None = None
        if direct_v2 and pack is not None:
            try:
                pack_view = self._packs.issue_execution_view(pack)
            except PackRegistryError:
                pack_integrity_drift = True
        plan = self.plan(
            request,
            pack,
            require_registered_wrapper=direct_v2,
        )
        if domain_denial_reasons:
            if not isinstance(plan, (ExecutionPlanV2, ExecutionPlanV3)):
                raise RuntimeError("direct-v2 domain execution requires an execution plan v2 or v3")
            plan = self._deny_domain_execution(plan, domain_denial_reasons)
        if pack_integrity_drift:
            if not isinstance(plan, (ExecutionPlanV2, ExecutionPlanV3)):
                raise RuntimeError("direct-v2 Pack integrity requires an execution plan v2 or v3")
            plan = self._deny_pack_integrity_execution(plan)
        if direct_v2 and len(plan.steps) > 1:
            if not isinstance(plan, ExecutionPlanV2):
                raise RuntimeError("direct-v2 reducer binding requires a provisional ExecutionPlanV2")
            try:
                plan, resolved_reducer = self._resolve_output_reducer(plan, request)
            except Exception:  # noqa: BLE001 - no exact reducer is a hard empty-plan gate
                plan = self._deny_unreduced_multi_step_execution(plan)
        if direct_v2:
            budget_reason = (
                self._artifact_snapshot_budget_reason(plan)
                if plan.steps
                else (
                    "artifact.snapshot_budget_unavailable"
                    if self._environment.schema_version != "vc.environment.v3"
                    else None
                )
            )
            if budget_reason is not None:
                plan = self._deny_artifact_snapshot_budget_execution(plan, budget_reason)
        reports = {report.model_name: report for report in plan.reports}
        prepared = []
        prepared_v2: dict[str, dict] = {}
        failed: dict[str, str] = {}
        for step in plan.steps:
            try:
                selected_content: PreparedSelectedContentV1 | None = None
                selected_content_verifier = None
                if direct_v2:
                    requested_outputs = request.task.requested_outputs or (request.output_modality.name,)
                    try:
                        adapter = self._capabilities.adapter_registry.resolve_requested(
                            request.task.task_type,
                            requested_outputs,
                        )
                    except AdapterContractError:
                        # The exact adapter gate below remains authoritative.
                        # Keeping this preflight optional preserves the private
                        # wrapper boundary for synthetic/test-only planners.
                        adapter = None
                    if adapter is not None and not (
                        len(step.adapter_fingerprints) == 1 and adapter.fingerprint() == step.adapter_fingerprints[0]
                    ):
                        raise AdapterContractError("direct-v2 adapter identity drift")
                    if adapter is not None and adapter.input_contract.pack_data_required:
                        if pack is None or pack_view is None:
                            raise AdapterContractError("direct-v2 selected content is unavailable")
                        if pack.manifest.schema_version != "vc.pack.v0.4":
                            raise AdapterContractError("selected content materializer is unavailable")
                        if type(pack_view) is not PreparedPackViewV2:
                            raise AdapterContractError("selected content materializer is unavailable")
                        selection = adapter.select_content(
                            request,
                            pack=pack_view,
                            compatibility_report=direct_v2_execution_report(reports[step.model_name]),
                        )
                        if type(selection) is not SelectedContentRequestV1:
                            raise AdapterContractError("direct-v2 selected content selector is invalid")
                        if (
                            selection.feature_contract.model_id != step.model_name
                            or selection.feature_contract.model_version != step.model_version
                        ):
                            raise AdapterContractError("direct-v2 selected content model binding is invalid")
                        selected_content = self._packs.materialize_selected_content(
                            pack,
                            request=request,
                            selection=selection,
                            pack_view=pack_view,
                        )

                        def selected_content_verifier(
                            content: PreparedSelectedContentV1,
                            *,
                            _selection: SelectedContentRequestV1 = selection,
                            _pack: RegisteredPack = pack,
                            _view: PreparedPackViewV2 = pack_view,
                        ) -> bool:
                            return self._packs.verify_selected_content(
                                _pack,
                                request=request,
                                selection=_selection,
                                pack_view=_view,
                                content=content,
                            )

                wrapper = self._capabilities.instantiate(
                    step,
                    reports[step.model_name],
                    request=request,
                    pack=pack,
                    adapter_pack=pack_view if direct_v2 else None,
                    selected_content=selected_content,
                    selected_content_verifier=selected_content_verifier,
                    require_registered_wrapper=direct_v2,
                )
                prepared.append(wrapper)
                if direct_v2:
                    artifact_snapshot = wrapper.capability_artifact_snapshot
                    if artifact_snapshot is None:
                        raise ValueError("direct-v2 wrapper lacks its sealed artifact snapshot")

                    def pack_verifier(*, _pack: RegisteredPack | None = pack) -> bool:
                        return _pack is not None and self._packs.revalidate(_pack)

                    adapter, adapter_input = wrapper.bound_adapter_execution()
                    if not (
                        len(step.adapter_fingerprints) == 1
                        and adapter.fingerprint() == step.adapter_fingerprints[0]
                        and adapter_input.request_fingerprint == reports[step.model_name].request_fingerprint
                        and adapter_input.pack_fingerprint == reports[step.model_name].pack_fingerprint
                        and adapter_input.compatibility_fingerprint == step.compatibility_fingerprint
                    ):
                        raise AdapterContractError("prepared direct-v2 input identity does not match plan")
                    execution = {
                        "wrapper": wrapper,
                        "adapter": adapter,
                        "adapter_input": adapter_input,
                        "artifact_snapshot": artifact_snapshot,
                        "pack_verifier": pack_verifier,
                    }
                    if selected_content is not None:
                        execution["selected_content"] = selected_content
                        execution["selected_content_verifier"] = selected_content_verifier
                    prepared_v2[step.model_name] = execution
            except PackRegistryError as exc:
                failed[step.model_name] = (
                    "pack.selected_content_materializer_unavailable"
                    if "requires vc.pack.v0.4" in str(exc)
                    else "pack.selected_content_unavailable"
                )
            except AdapterContractError as exc:
                failed[step.model_name] = (
                    "pack.selected_content_materializer_unavailable"
                    if "selected content materializer is unavailable" in str(exc)
                    else "pack.selected_content_unavailable"
                    if "selected content" in str(exc)
                    else "adapter.input_preparation"
                )
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
            if isinstance(plan, ExecutionPlanV3):
                # A reducer-bound execution cannot be narrowed to a subset.
                # Rebuild it directly as an empty plan; attempting an interim
                # one-step V3 would violate the write-new V3 invariant.
                fail_closed_reports = []
                for report in revised_reports:
                    value = report.to_dict()
                    checks = dict(report.checks)
                    checks["runtime.preparation"] = False
                    value.update(
                        {
                            "executable": False,
                            "checks": checks,
                            "reasons": list(dict.fromkeys((*report.reasons, "runtime.preparation_failed"))),
                        }
                    )
                    fail_closed_reports.append(type(report).from_dict(value))
                plan = plan.rebuild(
                    reports=tuple(fail_closed_reports),
                    steps=(),
                )
            elif isinstance(plan, ExecutionPlanV2):
                steps = tuple(step for step in plan.steps if step.model_name not in failed)
                plan = plan.rebuild(
                    reports=tuple(revised_reports),
                    steps=steps,
                )
            else:
                steps = tuple(step for step in plan.steps if step.model_name not in failed)
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
        if direct_v2:
            if isinstance(plan, ExecutionPlanV3) and failed:
                # Multi-model reduction cannot silently continue with a subset.
                # The V3 branch above already rebuilt every report as a
                # fail-closed empty plan.  Do not rebuild again: that would
                # alter the same public result after its identity was sealed.
                prepared_v2 = {}
                resolved_reducer = None
            prepared_v2 = {
                step.model_name: prepared_v2[step.model_name] for step in plan.steps if step.model_name in prepared_v2
            }
            if prepared_v2:
                if isinstance(plan, ExecutionPlanV3):
                    if resolved_reducer is None:
                        raise RuntimeError("reducer-bound V3 plan lacks a private reducer")
                    self._prepared_v2[plan.plan_id] = {
                        "executions": prepared_v2,
                        "output_reducer": resolved_reducer,
                    }
                else:
                    self._prepared_v2[plan.plan_id] = prepared_v2
            else:
                self._prepared_v2.pop(plan.plan_id, None)
            payload = {
                "execution_plan": plan.to_dict(),
                "adapter_input_receipts": {
                    name: (
                        AdapterInputReceiptV2.from_prepared(
                            execution["adapter_input"],
                            execution["selected_content"],
                        )
                        if "selected_content" in execution
                        else AdapterInputReceipt.from_prepared(execution["adapter_input"])
                    ).to_dict()
                    for name, execution in prepared_v2.items()
                },
                **({"domain_extension_identity": domain_identity.to_dict()} if domain_identity is not None else {}),
                **({"pack_view_receipt": pack_view.receipt.to_dict()} if pack_view is not None else {}),
            }
            receiver = "AgentRuntime"
        else:
            self._prepared[plan.plan_id] = prepared
            payload = {"execution_plan": plan.to_dict()}
            receiver = "EnsembleCoordinator"
        bus.send(
            AgentMessage(
                message_id=message.message_id + ":plan",
                sender=self.name,
                receiver=receiver,
                message_type="execution_plan_ready",
                payload=payload,
                timestamp=message.timestamp,
                parent_message_id=message.message_id,
            )
        )

    def take_prepared(self, plan_id: str) -> list:
        return self._prepared.pop(plan_id, [])

    def take_prepared_v2(self, plan_id: str) -> dict:
        return self._prepared_v2.pop(plan_id, {})

    def resolve_prepared_output_reducer(
        self,
        binding: OutputReducerBindingV1,
    ) -> ResolvedOutputReducerPolicy:
        """Re-check a prepared V3 policy against the current explicit registry."""

        if self._output_reducers is None:
            raise OutputReducerPolicyNotFoundError("no output reducer registry is configured")
        return self._output_reducers.resolve_binding(binding)

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
