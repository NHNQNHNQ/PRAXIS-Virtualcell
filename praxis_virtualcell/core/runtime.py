"""Register agents, dispatch messages, and drive workflows. Predictor fan-out also communicates through the bus."""

from __future__ import annotations

import hashlib
import json
import threading
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path

from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.config import (
    Clock,
    IdGen,
    Mode,
    RuntimeConfig,
    assert_llm_boundaries,
)
from praxis_virtualcell.core.domain_extension import (
    DomainExtension,
    DomainExtensionIdentityV1,
)
from praxis_virtualcell.core.exceptions import InputValidationError, UnknownAgentError
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.core.request import VirtualCellRequest
from praxis_virtualcell.core.request_v2 import VirtualCellRequestV2, legacy_request_to_v2
from praxis_virtualcell.data_packs.registry import (
    PackViewReceiptV1,
    PackViewReceiptV2,
    pack_view_receipt_from_dict,
    validate_selected_content_receipt_binding,
)
from praxis_virtualcell.data_packs.selected_content import PreparedSelectedContentV1
from praxis_virtualcell.governance.cell_type_domain import check_cell_type_domain
from praxis_virtualcell.governance.gate_util import apply_governance_gate
from praxis_virtualcell.governance.module_consistency import check_module_plan
from praxis_virtualcell.governance.narrative_consistency import check_narrative
from praxis_virtualcell.governance.provenance_completeness import check_report_provenance
from praxis_virtualcell.governance.provenance_hash import check_call_provenance
from praxis_virtualcell.model_zoo.adapter_sdk import (
    AdapterInputReceipt,
    AdapterInputReceiptV2,
    AdapterOutputEnvelope,
    PreparedAdapterInput,
    VirtualCellModelAdapter,
    adapter_input_receipt_from_dict,
)
from praxis_virtualcell.model_zoo.cache import ArtifactSnapshot
from praxis_virtualcell.model_zoo.capability_registry import ExecutionPlanV2, ExecutionPlanV3
from praxis_virtualcell.model_zoo.post_result_policy import (
    OutputReducerModelAdapterBindingV1,
    OutputReducerReceiptV1,
    OutputReducerStepReceiptV1,
    ResolvedOutputReducerPolicy,
    reduce_adapter_outputs,
    reducer_implementation_fingerprint,
)
from praxis_virtualcell.model_zoo.wrappers.base import ModelWrapper

_RLOCK_TYPE = type(threading.RLock())


def _aggregate_execution_scope(reports) -> str:
    return "research_only" if any(entry.research_execution_authorized is True for entry in reports) else "production"


class AgentRuntime:
    def __init__(
        self,
        config: RuntimeConfig,
        *,
        bus: MessageBus,
        clock: Clock,
        idgen: IdGen,
        require_pack_aware_execution: bool = False,
        domain_extensions: tuple[DomainExtension, ...] = (),
        execution_lock: object | None = None,
    ) -> None:
        self.config = config
        self.bus = bus
        self.clock = clock
        self.idgen = idgen
        if execution_lock is not None and not isinstance(execution_lock, _RLOCK_TYPE):
            raise TypeError("execution_lock must be a re-entrant context lock")
        self._execution_lock = threading.RLock() if execution_lock is None else execution_lock
        self._require_pack_aware_execution = require_pack_aware_execution
        if not isinstance(domain_extensions, tuple):
            raise TypeError("domain_extensions must be a tuple")
        self._domain_extensions: dict[str, DomainExtension] = {}
        for extension in domain_extensions:
            if not isinstance(extension, DomainExtension):
                raise TypeError("domain_extensions must contain DomainExtension")
            for taxonomy_id in extension.taxon_ids:
                if taxonomy_id in self._domain_extensions:
                    raise ValueError("domain extensions cannot overlap exact taxon IDs")
                self._domain_extensions[taxonomy_id] = extension
        self._agents: dict[str, BaseAgent] = {}

    @contextmanager
    def execution_context(self):
        """Serialize top-level work on one mutable runtime instance.

        MessageBus context/trace, the deterministic clock and ID generator, and
        broker-prepared handoffs all belong to this runtime.  A re-entrant lock
        keeps nested public entry points valid while preventing cross-request
        state from being interleaved.
        """

        with self._execution_lock:
            yield

    def register_agent(self, agent: BaseAgent) -> None:
        self._agents[agent.name] = agent

    def mk_message(
        self, sender: str, receiver: str, message_type: str, payload: dict, parent_message_id: str | None = None
    ) -> AgentMessage:
        return AgentMessage(
            self.idgen.next(), sender, receiver, message_type, payload, self.clock.now(), parent_message_id
        )

    def dispatch_message(self, message: AgentMessage) -> None:
        agent = self._agents.get(message.receiver)
        if agent is None:
            raise UnknownAgentError(f"unregistered agent: {message.receiver}")
        self.bus.send(message)
        agent.handle(message, self.bus)

    def _dispatch_collect(self, message: AgentMessage, expected_type: str) -> AgentMessage:
        self.dispatch_message(message)
        out = self.bus.latest(expected_type)
        if out is None:
            raise RuntimeError(f"{message.receiver} did not produce {expected_type}")
        return out

    def _dispatch_collect_direct_v2(self, message: AgentMessage) -> AgentMessage:
        """Collect only the Broker reply causally bound to this direct-v2 request."""

        self.dispatch_message(message)
        for out in reversed(self.bus.trace):
            if (
                out.message_type == "execution_plan_ready"
                and out.sender == "ModelBrokerAgent"
                and out.receiver == "AgentRuntime"
                and out.parent_message_id == message.message_id
                and out.trace_id == message.trace_id
                and out.task_id == message.task_id
            ):
                return out
        raise RuntimeError("ModelBrokerAgent did not produce the current direct-v2 execution_plan_ready")

    def run_workflow_v2(
        self,
        request: VirtualCellRequestV2,
        *,
        trace_id: str | None = None,
        task_id: str | None = None,
        pack_id: str | None = None,
        pack_version: str | None = None,
    ) -> dict:
        """Run the generic direct-v2 planning seam without projecting legacy input.

        One exact Broker-prepared step, or a V3 multi-step plan with an explicit
        generic reducer policy, is executable here.  This method never projects
        a legacy request or calls the legacy interpreter, brain, ensemble, or
        task-named runtime.
        """
        with self.execution_context():
            return self._run_workflow_v2(
                request,
                trace_id=trace_id,
                task_id=task_id,
                pack_id=pack_id,
                pack_version=pack_version,
            )

    def _run_workflow_v2(
        self,
        request: VirtualCellRequestV2,
        *,
        trace_id: str | None = None,
        task_id: str | None = None,
        pack_id: str | None = None,
        pack_version: str | None = None,
    ) -> dict:
        if self.config.mode != Mode.OFFLINE or self.config.llm_enabled:
            raise InputValidationError("direct-v2 runtime requires offline mode with LLM disabled")
        assert_llm_boundaries(self.config)
        if not isinstance(request, VirtualCellRequestV2):
            raise InputValidationError("run_workflow_v2 requires VirtualCellRequestV2")
        if (pack_id is None) != (pack_version is None):
            raise ValueError("pack_id and pack_version must be provided together")
        if pack_id is not None and (
            not isinstance(pack_id, str)
            or not pack_id
            or pack_id.strip() != pack_id
            or not isinstance(pack_version, str)
            or not pack_version
            or pack_version.strip() != pack_version
        ):
            raise ValueError("pack_id and pack_version must be non-empty strings without surrounding whitespace")

        request_dict = request.to_dict()
        request_fingerprint = hashlib.sha256(
            json.dumps(
                request_dict,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()
        request_hash = request_fingerprint[:8]
        self.bus.set_context(
            trace_id=trace_id or f"trace_{request_hash}",
            task_id=task_id or f"task_{request_hash}",
        )
        requested_domain_identity = None
        extension = self._domain_extensions.get(request.species.taxonomy_id)
        if extension is not None:
            requested_domain_identity = extension.evaluate(request)
        planned = self._dispatch_collect_direct_v2(
            self.mk_message(
                "client",
                "ModelBrokerAgent",
                "execution_plan_v2_request",
                {
                    "request": request_dict,
                    "request_fingerprint": request_fingerprint,
                    "pack_id": pack_id,
                    "pack_version": pack_version,
                    **(
                        {"domain_extension_identity": requested_domain_identity.to_dict()}
                        if requested_domain_identity is not None
                        else {}
                    ),
                },
            )
        )
        raw_plan = planned.payload["execution_plan"]
        if not isinstance(raw_plan, dict):
            raise RuntimeError("direct-v2 broker returned an invalid execution plan")
        if raw_plan.get("schema_version") == "vc.execution-plan.v2":
            plan = ExecutionPlanV2.from_dict(raw_plan)
        elif raw_plan.get("schema_version") == "vc.execution-plan.v3":
            plan = ExecutionPlanV3.from_dict(raw_plan)
        else:
            raise RuntimeError("direct-v2 broker returned an unsupported execution plan")
        raw_receipts = planned.payload.get("adapter_input_receipts", {})
        if not isinstance(raw_receipts, dict):
            raw_receipts = None
        receipts: dict[str, AdapterInputReceipt | AdapterInputReceiptV2] = {}
        if raw_receipts is not None:
            try:
                receipts = {
                    name: adapter_input_receipt_from_dict(value)
                    for name, value in raw_receipts.items()
                    if isinstance(name, str)
                }
                if len(receipts) != len(raw_receipts):
                    raise ValueError("receipt names must be text")
            except Exception:  # noqa: BLE001 - malformed Broker output must abstain
                raw_receipts = None

        raw_pack_view_receipt = planned.payload.get("pack_view_receipt")
        pack_view_receipt: PackViewReceiptV1 | PackViewReceiptV2 | None = None
        if raw_pack_view_receipt is not None:
            try:
                pack_view_receipt = pack_view_receipt_from_dict(raw_pack_view_receipt)
            except Exception:  # noqa: BLE001 - public receipt is a direct-v2 hard gate
                pack_view_receipt = None

        domain_identity_invalid = False
        domain_identity = None
        raw_domain_identity = planned.payload.get("domain_extension_identity")
        if raw_domain_identity is not None:
            try:
                domain_identity = DomainExtensionIdentityV1.from_dict(raw_domain_identity)
                if (
                    domain_identity.taxonomy_id != request.species.taxonomy_id
                    or requested_domain_identity is None
                    or domain_identity.to_dict() != requested_domain_identity.to_dict()
                ):
                    raise ValueError("domain extension identity drift")
            except Exception:  # noqa: BLE001 - Broker domain identity is fail-closed
                domain_identity_invalid = True
                domain_identity = None
        elif requested_domain_identity is not None:
            domain_identity_invalid = True

        provenance = {
            "execution_contract": "vc.direct-v2-execution.v1",
            "execution_plan": plan.to_dict(),
            "compatibility_reports": [entry.to_dict() for entry in plan.reports],
            "adapter_input_receipts": {name: receipt.to_dict() for name, receipt in receipts.items()},
            "per_call_hashes": {},
            **({"pack_view_receipt": pack_view_receipt.to_dict()} if pack_view_receipt is not None else {}),
            **({"domain_extension_identity": domain_identity.to_dict()} if domain_identity is not None else {}),
        }

        def discard_prepared_v2() -> None:
            broker = self._agents.get("ModelBrokerAgent")
            take_prepared = getattr(broker, "take_prepared_v2", None)
            if callable(take_prepared):
                try:
                    take_prepared(plan.plan_id)
                except Exception:  # noqa: BLE001 - cleanup cannot relax abstention
                    pass

        def complete(report: dict) -> dict:
            decision_identity = {
                "abstain": report["abstain"],
                "prediction": report["prediction"],
                "models_used": report["models_used"],
                "models_rejected": report["models_rejected"],
                "models_failed": report["models_failed"],
                "abstain_reasons": report["abstain_reasons"],
                "scientifically_validated": report["scientifically_validated"],
            }
            decision_fingerprint = hashlib.sha256(
                json.dumps(
                    decision_identity,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                ).encode("utf-8")
            ).hexdigest()
            self.bus.send(
                self.mk_message(
                    "AgentRuntime",
                    "client",
                    "execution_result_ready",
                    {
                        "request_fingerprint": request_fingerprint,
                        "plan_id": plan.plan_id,
                        "plan_fingerprint": hashlib.sha256(
                            json.dumps(
                                plan.to_dict(),
                                sort_keys=True,
                                separators=(",", ":"),
                                ensure_ascii=False,
                            ).encode("utf-8")
                        ).hexdigest(),
                        "decision_fingerprint": decision_fingerprint,
                    },
                    planned.message_id,
                )
            )
            # ``ExecutionPlanV2/V3`` retains local asset paths only while the
            # Broker and runtime are executing.  The public Python result uses
            # the exact same closed projection persisted by the job seam.
            from praxis_virtualcell.pack_product import _public_provenance

            public_report = json.loads(json.dumps(report))
            public_report["provenance"] = _public_provenance(report["provenance"])
            return public_report

        def abstain(
            *reasons: str,
            rejected: list[str] | None = None,
            failed: list[str] | None = None,
        ) -> dict:
            discard_prepared_v2()
            return complete(
                {
                    "request_id": request.request_id,
                    "request_fingerprint": request_fingerprint,
                    "execution_status": "abstained",
                    "execution_scope": None,
                    "scientifically_validated": False,
                    "prediction": None,
                    "models_used": [],
                    "models_rejected": rejected or [],
                    "models_failed": failed or [],
                    "abstain": True,
                    "abstain_reasons": list(dict.fromkeys(reasons)),
                    "reliability": "low",
                    "runtime_confidence": "low",
                    "provenance": provenance,
                }
            )

        requested_pack_matches = plan.pack_id == pack_id and plan.pack_version == pack_version
        unresolved_pack_empty_plan = (
            not plan.executable and plan.pack_id is None and plan.pack_version is None and plan.pack_fingerprint is None
        )
        if (
            plan.request_id != request.request_id
            or plan.request_fingerprint != request_fingerprint
            or (not requested_pack_matches and not unresolved_pack_empty_plan)
        ):
            return abstain("execution_plan_identity_drift")

        if domain_identity_invalid:
            return abstain("domain.extension_identity_invalid")
        if domain_identity is not None and not domain_identity.allow_execution and plan.executable:
            return abstain("domain.extension_identity_drift")

        if not plan.executable:
            reasons = ["execution_plan_not_executable"]
            if pack_id is None:
                reasons.append("pack_required")
            reasons.extend(
                reason
                for entry in plan.reports
                for reason in entry.reasons
                if reason.startswith("domain.policy.")
                or reason == "output_reducer_required"
                or reason == "runtime.preparation_failed"
                or reason == "adapter.input_preparation"
                or reason == "model.wrapper_initialization"
                or reason == "pack.integrity_drift"
                or reason == "pack.selected_content_materializer_unavailable"
                or reason == "pack.selected_content_unavailable"
                or reason == "artifact.snapshot_budget_unavailable"
                or reason == "artifact.snapshot_budget_exceeded"
            )
            return abstain(
                *reasons,
                rejected=[entry.model_name for entry in plan.reports],
            )

        if isinstance(plan, ExecutionPlanV2) and len(plan.steps) != 1:
            return abstain("output_reducer_required")
        if isinstance(plan, ExecutionPlanV3) and len(plan.steps) < 2:
            return abstain("output_reducer_required")
        if not (
            pack_view_receipt is not None
            and pack_view_receipt.pack_id == plan.pack_id
            and pack_view_receipt.pack_version == plan.pack_version
            and pack_view_receipt.pack_fingerprint == plan.pack_fingerprint
        ):
            return abstain("pack_view_receipt_invalid")
        if raw_receipts is None or set(receipts) != {step.model_name for step in plan.steps}:
            return abstain("prepared_execution_invalid")
        broker = self._agents.get("ModelBrokerAgent")
        take_prepared = getattr(broker, "take_prepared_v2", None)
        if not callable(take_prepared):
            return abstain("prepared_execution_invalid")
        try:
            handoff = take_prepared(plan.plan_id)
            reducer = None
            if isinstance(plan, ExecutionPlanV3):
                if not isinstance(handoff, dict) or set(handoff) != {
                    "executions",
                    "output_reducer",
                }:
                    raise ValueError("reducer-bound prepared executions are invalid")
                prepared_executions = handoff["executions"]
                reducer = handoff["output_reducer"]
                if not isinstance(reducer, ResolvedOutputReducerPolicy) or (
                    reducer.binding().to_dict() != plan.output_reducer.to_dict()
                ):
                    raise ValueError("prepared output reducer identity drift")
                resolve_reducer = getattr(broker, "resolve_prepared_output_reducer", None)
                if not callable(resolve_reducer) or resolve_reducer(plan.output_reducer) is not reducer:
                    raise ValueError("prepared output reducer registry drift")
                expected_bindings = tuple(
                    OutputReducerModelAdapterBindingV1(
                        schema_version="vc.output-reducer-model-adapter-binding.v1",
                        model_name=step.model_name,
                        model_fingerprint=step.model_fingerprint,
                        release_fingerprint=step.release_fingerprint,
                        adapter_fingerprint=step.adapter_fingerprints[0],
                    )
                    for step in plan.steps
                )
                if not (
                    reducer.spec.model_count == len(plan.steps)
                    and reducer.spec.model_adapter_bindings == expected_bindings
                    and reducer.spec.task == request.task.task_type
                    and reducer.spec.entrypoint == f"{reducer.reducer.__module__}.{reducer.reducer.__qualname__}"
                    and reducer.spec.implementation_fingerprint == reducer_implementation_fingerprint(reducer.reducer)
                ):
                    raise ValueError("prepared output reducer step bindings drifted")
            else:
                prepared_executions = handoff
            if not isinstance(prepared_executions, dict) or set(prepared_executions) != {
                step.model_name for step in plan.steps
            }:
                raise ValueError("prepared v2 executions do not match plan steps")
            if isinstance(plan, ExecutionPlanV3):
                for step in plan.steps:
                    execution = prepared_executions[step.model_name]
                    if not isinstance(execution, dict):
                        raise ValueError("reducer-bound prepared execution is invalid")
                    wrapper = execution.get("wrapper")
                    adapter = execution.get("adapter")
                    if not (
                        isinstance(wrapper, ModelWrapper)
                        and isinstance(adapter, VirtualCellModelAdapter)
                        and wrapper.name == step.model_name
                        and wrapper.model_version == step.model_version
                        and wrapper.capability_assets == {}
                        and isinstance(execution.get("artifact_snapshot"), ArtifactSnapshot)
                        and wrapper.capability_artifact_snapshot is execution["artifact_snapshot"]
                        and execution["artifact_snapshot"].is_intact()
                        and f"{type(wrapper).__module__}.{type(wrapper).__qualname__}" == step.wrapper
                        and len(step.adapter_fingerprints) == 1
                        and adapter.fingerprint() == step.adapter_fingerprints[0]
                        and adapter.output_contract.fingerprint() == reducer.spec.output_contract_fingerprint
                    ):
                        raise ValueError("reducer-bound prepared execution identity drifted")
        except Exception:  # noqa: BLE001 - private Broker state is fail-closed
            return abstain("prepared_execution_invalid")

        envelopes: list[AdapterOutputEnvelope] = []
        ordered_receipts: list[tuple[object, object]] = []
        reducer_adapter: VirtualCellModelAdapter | None = None
        for step in plan.steps:
            try:
                execution = prepared_executions[step.model_name]
                allowed_shapes = (
                    {"wrapper", "adapter", "adapter_input", "artifact_snapshot", "pack_verifier"},
                    {
                        "wrapper",
                        "adapter",
                        "adapter_input",
                        "artifact_snapshot",
                        "pack_verifier",
                        "selected_content",
                    },
                    {
                        "wrapper",
                        "adapter",
                        "adapter_input",
                        "artifact_snapshot",
                        "pack_verifier",
                        "selected_content",
                        "selected_content_verifier",
                    },
                )
                if not isinstance(execution, dict) or set(execution) not in allowed_shapes:
                    raise ValueError("prepared execution has an invalid shape")
                wrapper = execution["wrapper"]
                adapter = execution["adapter"]
                prepared_input = execution["adapter_input"]
                artifact_snapshot = execution["artifact_snapshot"]
                pack_verifier = execution["pack_verifier"]
                if (
                    not isinstance(wrapper, ModelWrapper)
                    or not isinstance(adapter, VirtualCellModelAdapter)
                    or not isinstance(prepared_input, PreparedAdapterInput)
                    or not isinstance(artifact_snapshot, ArtifactSnapshot)
                    or wrapper.capability_artifact_snapshot is not artifact_snapshot
                    or wrapper.capability_assets != {}
                    or not artifact_snapshot.is_intact()
                    or not callable(pack_verifier)
                ):
                    raise TypeError("prepared execution has an invalid type")
                prepared_input = adapter.validate_prepared_input(prepared_input)
                selected_content = execution.get("selected_content")
                selected_content_verifier = execution.get("selected_content_verifier")
                expected_receipt = receipts[step.model_name]
                if adapter.input_contract.pack_data_required:
                    if not (
                        isinstance(selected_content, PreparedSelectedContentV1)
                        and isinstance(expected_receipt, AdapterInputReceiptV2)
                        and callable(selected_content_verifier)
                        and pack_view_receipt is not None
                        and selected_content.receipt.model_id == step.model_name
                        and selected_content.receipt.model_version == step.model_version
                        and validate_selected_content_receipt_binding(selected_content.receipt, pack_view_receipt)
                        and selected_content_verifier(selected_content)
                    ):
                        raise ValueError("data-required direct-v2 execution lacks bound selected content")
                elif (
                    selected_content is not None
                    or selected_content_verifier is not None
                    or isinstance(expected_receipt, AdapterInputReceiptV2)
                ):
                    raise ValueError("data-free direct-v2 execution carries selected content")
                receipt = (
                    AdapterInputReceiptV2.from_prepared(prepared_input, selected_content)
                    if selected_content is not None
                    else AdapterInputReceipt.from_prepared(prepared_input)
                )
                if receipt.to_dict() != expected_receipt.to_dict() or not (
                    receipt.request_fingerprint == plan.request_fingerprint
                    and receipt.pack_fingerprint == plan.pack_fingerprint
                    and receipt.compatibility_fingerprint == step.compatibility_fingerprint
                    and adapter.fingerprint() in step.adapter_fingerprints
                    and len(step.adapter_fingerprints) == 1
                ):
                    raise ValueError("prepared input identity does not match plan")
                if pack_verifier() is not True:
                    return abstain("pack.integrity_drift", rejected=[step.model_name])
            except Exception:  # noqa: BLE001 - prepared Broker state is a hard gate
                return abstain("prepared_execution_invalid", failed=[step.model_name])
            try:
                raw_output = wrapper.run_prediction(prepared_input.model_input)
                envelope = adapter.validate_prepared_envelope(
                    prepared_input,
                    adapter.adapt_output(prepared_input, raw_output),
                )
                if not isinstance(envelope, AdapterOutputEnvelope):
                    raise TypeError("adapter returned an invalid output envelope")
                if isinstance(plan, ExecutionPlanV3):
                    if reducer_adapter is None:
                        reducer_adapter = adapter
                    elif (
                        adapter.fingerprint() != reducer_adapter.fingerprint()
                        or adapter.output_contract.fingerprint() != reducer_adapter.output_contract.fingerprint()
                    ):
                        raise ValueError("reducer-bound steps must use one exact adapter")
            except Exception:  # noqa: BLE001 - each adapter/wrapper boundary fails whole multi-plan closed
                return abstain("adapter_execution_failed", failed=[step.model_name])
            output_identity = envelope.to_dict()
            output_hash = hashlib.sha256(
                json.dumps(output_identity, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            ).hexdigest()
            provenance["per_call_hashes"][step.model_name] = {
                "model_name": step.model_name,
                "model_version": step.model_version,
                "input_hash": receipt.prepared_input_fingerprint,
                "output_hash": output_hash,
            }
            if envelope.abstain:
                return abstain("adapter_abstained", rejected=[step.model_name])
            envelopes.append(envelope)
            ordered_receipts.append((step, receipt))

        if isinstance(plan, ExecutionPlanV3):
            try:
                if reducer is None or reducer_adapter is None:
                    raise ValueError("reducer-bound execution lacks a shared adapter")
                # Re-resolve at the execution boundary.  A registration/source
                # change after Broker preparation cannot retain its old policy
                # fingerprint merely because the private callable survived.
                if reducer.binding() != plan.output_reducer:
                    raise ValueError("output reducer binding drifted")
                if reducer.spec.implementation_fingerprint != (reducer_implementation_fingerprint(reducer.reducer)):
                    raise ValueError("output reducer implementation drifted")
                envelope = reduce_adapter_outputs(tuple(envelopes), resolved=reducer)
                envelope = reducer_adapter.validate_envelope(envelope)
                if envelope.abstain or envelope.values is None:
                    return abstain("output_reducer_abstained")
                output_identity = envelope.to_dict()
                reduced_hash = hashlib.sha256(
                    json.dumps(output_identity, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
                        "utf-8"
                    )
                ).hexdigest()
                provenance["output_reducer_receipt"] = OutputReducerReceiptV1(
                    schema_version="vc.output-reducer-receipt.v1",
                    output_reducer=plan.output_reducer,
                    step_receipts=tuple(
                        OutputReducerStepReceiptV1(
                            schema_version="vc.output-reducer-step-receipt.v1",
                            model_name=step.model_name,
                            execution_step_fingerprint=step.fingerprint(),
                            input_hash=receipt.prepared_input_fingerprint,
                            output_hash=provenance["per_call_hashes"][step.model_name]["output_hash"],
                        )
                        for step, receipt in ordered_receipts
                    ),
                    reduced_output_hash=reduced_hash,
                ).to_dict()
            except Exception:  # noqa: BLE001 - reducer is a hard post-result boundary
                return abstain("output_reducer_failed")
        else:
            envelope = envelopes[0]
            output_identity = envelope.to_dict()

        reports_by_name = {entry.model_name: entry for entry in plan.reports}
        used_reports = [reports_by_name[step.model_name] for step in plan.steps]
        execution_scope = _aggregate_execution_scope(used_reports)
        return complete(
            {
                "request_id": request.request_id,
                "request_fingerprint": request_fingerprint,
                "execution_status": "completed",
                "execution_scope": execution_scope,
                "scientifically_validated": all(entry.scientifically_validated is True for entry in used_reports),
                "prediction": output_identity,
                "models_used": [step.model_name for step in plan.steps],
                "models_rejected": [],
                "models_failed": [],
                "abstain": False,
                "abstain_reasons": [],
                "reliability": "low",
                "runtime_confidence": "low",
                "provenance": provenance,
            }
        )

    def run_workflow(
        self,
        request,
        *,
        trace_id: str | None = None,
        task_id: str | None = None,
        pack_id: str | None = None,
        pack_version: str | None = None,
    ) -> dict:
        """Run a VirtualCellRequest entirely through the bus and return the final report. Missing trace_id/task_id
        use the canonical request hash; free-text entry points can inject one shared trace identity.
        """
        with self.execution_context():
            return self._run_workflow(
                request,
                trace_id=trace_id,
                task_id=task_id,
                pack_id=pack_id,
                pack_version=pack_version,
            )

    def _run_workflow(
        self,
        request,
        *,
        trace_id: str | None = None,
        task_id: str | None = None,
        pack_id: str | None = None,
        pack_version: str | None = None,
    ) -> dict:
        if (pack_id is None) != (pack_version is None):
            raise ValueError("pack_id and pack_version must be provided together")
        if pack_id is not None and (
            not isinstance(pack_id, str)
            or not pack_id
            or pack_id.strip() != pack_id
            or not isinstance(pack_version, str)
            or not pack_version
            or pack_version.strip() != pack_version
        ):
            raise ValueError("pack_id and pack_version must be non-empty strings without surrounding whitespace")
        capability_plan = None
        _req_dict = asdict(request)
        _h = hashlib.sha256(json.dumps(_req_dict, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:8]
        self.bus.set_context(trace_id=trace_id or f"trace_{_h}", task_id=task_id or f"task_{_h}")
        m = self.mk_message("client", "InputInterpreter", "parse_request", {"request_dict": _req_dict})
        out = self._dispatch_collect(m, "request_parsed")
        m = self.mk_message(out.sender, "BioObjectNormalizer", "normalize", out.payload, out.message_id)
        out = self._dispatch_collect(m, "object_normalized")
        m = self.mk_message(out.sender, "SpeciesBrain", "retrieve", out.payload, out.message_id)
        out = self._dispatch_collect(m, "brain_retrieved")
        if pack_id is None and not self._require_pack_aware_execution:
            m = self.mk_message(
                out.sender,
                "ModelApplicability",
                "decide",
                out.payload,
                out.message_id,
            )
            app = self._dispatch_collect(m, "applicability_decided")
        else:
            m = self.mk_message(
                out.sender,
                "ModelBrokerAgent",
                "execution_plan_request",
                {
                    "request": legacy_request_to_v2(VirtualCellRequest.from_dict(out.payload["request"])).to_dict(),
                    "pack_id": pack_id,
                    "pack_version": pack_version,
                },
                out.message_id,
            )
            planned = self._dispatch_collect(m, "execution_plan_ready")
            capability_plan = planned.payload["execution_plan"]
            broker = self._agents["ModelBrokerAgent"]
            take_prepared = getattr(broker, "take_prepared", None)
            if not callable(take_prepared):
                raise RuntimeError("registered ModelBrokerAgent cannot provide prepared models")
            prepared = take_prepared(capability_plan["plan_id"])
            for predictor in prepared:
                self.register_agent(predictor)
            brain_context = {
                **out.payload["brain_context"],
                "routing": {
                    "cautions": {},
                    "rejection_reasons": {},
                    "rules_hit": [],
                    "capability_plan_id": capability_plan["plan_id"],
                    "legacy_adapter": False,
                    "pack_required_for_execution": pack_id is None,
                },
            }
            app = self.mk_message(
                planned.sender,
                "EnsembleCoordinator",
                "applicability_decided",
                {
                    "request": out.payload["request"],
                    "brain_context": brain_context,
                    "applicable": [step["agent_name"] for step in capability_plan["steps"]],
                    "rejected_candidates": [],
                },
                planned.message_id,
            )
            self.bus.send(app)





        module_plan = None
        llm_cross_module = None
        if "ModuleRouterAgent" in self._agents and self._is_routable(app):
            module_plan = self._build_module_plan(app)
            if "LLMCrossModuleReasoner" in self._agents and module_plan is not None:
                xm = self.mk_message(
                    "ModuleRouterAgent",
                    "LLMCrossModuleReasoner",
                    "cross_module_review",
                    {"module_plan": module_plan},
                    app.message_id,
                )
                llm_cross_module = self._dispatch_collect(xm, "llm_cross_module_notes").payload
        llm_route = None
        if "LLMRouter" in self._agents:
            rmsg = self.mk_message(
                app.sender,
                "LLMRouter",
                "route_suggest",
                {
                    "request": app.payload["request"],
                    "brain_context": app.payload["brain_context"],
                    "applicable": app.payload["applicable"],
                    "rejected_candidates": app.payload["rejected_candidates"],
                },
                app.message_id,
            )
            llm_route = self._dispatch_collect(rmsg, "llm_route_suggestion").payload
        results = []
        for pname in list(app.payload["applicable"]) + list(app.payload["rejected_candidates"]):
            pm = self.mk_message(
                app.sender,
                pname,
                "predict",
                {"request": app.payload["request"], "brain_context": app.payload["brain_context"]},
                app.message_id,
            )
            r = self._dispatch_collect(pm, "predictor_result")
            results.append(r.payload)
        m = self.mk_message(
            app.sender,
            "EnsembleCoordinator",
            "ensemble",
            {"request": app.payload["request"], "brain_context": app.payload["brain_context"], "results": results},
            app.message_id,
        )
        ens = self._dispatch_collect(m, "ensemble_done")
        m = self.mk_message(ens.sender, "Reliability", "assess", ens.payload, ens.message_id)
        rel = self._dispatch_collect(m, "reliability_decided")
        m = self.mk_message(rel.sender, "Critic", "review", rel.payload, rel.message_id)
        crit = self._dispatch_collect(m, "critic_done")
        m = self.mk_message(crit.sender, "ProvenanceAgent", "assemble", crit.payload, crit.message_id)
        prov = self._dispatch_collect(m, "provenance_done")
        m = self.mk_message(prov.sender, "Report", "render", prov.payload, prov.message_id)
        rep = self._dispatch_collect(m, "report_done")
        report = rep.payload["report"]



        reliability_abstained = report.get("abstain", False)
        if capability_plan is not None:
            report.setdefault("provenance", {})["execution_plan"] = capability_plan
            report["provenance"]["compatibility_reports"] = capability_plan["reports"]
            if any("pack.unregistered" in item.get("reasons", []) for item in capability_plan["reports"]):
                # No Pack means no executable model input.  A legacy learned-reliability
                # score would be an unrelated numeric signal, not a property of this plan.
                report["learned_reliability"] = None
                reasons = report.setdefault("abstain_reasons", [])
                if "pack_unregistered" not in reasons:
                    report["abstain_reasons"] = ["pack_unregistered", *reasons]
                apply_governance_gate(
                    report,
                    "pack_unregistered",
                    "pack_identity_gate",
                    {"execution_plan_id": capability_plan["plan_id"]},
                )
        if llm_route is not None:
            report.setdefault("provenance", {})["llm_route_suggestion"] = llm_route
        if module_plan is not None:
            report.setdefault("provenance", {})["module_plan"] = module_plan





        if module_plan is not None:
            violations = check_module_plan(module_plan)
            if violations:
                reliability_abstain = report.get("abstain", False)
                gate_abstained = not reliability_abstain
                if gate_abstained:
                    report["abstain"] = True
                    report["prediction"] = None
                    if "adapter_output" in report:
                        report["adapter_output"] = None
                    report.setdefault("abstain_reasons", []).append("cross_module_inconsistency")
                report.setdefault("provenance", {})["cross_module_consistency"] = {
                    "violations": violations,
                    "gate_abstained": gate_abstained,
                    "reliability_original_abstain": reliability_abstain,
                }


        pch = report.get("provenance", {}).get("per_call_hashes", {})
        hash_missing = {
            n: miss for n in report.get("models_used", []) if (miss := check_call_provenance(pch.get(n, {})))
        }
        if hash_missing:
            apply_governance_gate(
                report, "incomplete_call_provenance", "provenance_hash_gate", {"missing": hash_missing}
            )


        prov_missing = check_report_provenance(report)
        if prov_missing:
            apply_governance_gate(
                report, "incomplete_provenance", "provenance_completeness_gate", {"missing": prov_missing}
            )



        ct_violations = check_cell_type_domain(
            app.payload["request"],
            app.payload["brain_context"],
            report.get("models_used", []),
            reliability_abstained=reliability_abstained,
        )
        if ct_violations:
            apply_governance_gate(
                report, "cell_type_out_of_domain", "cell_type_gate", {"out_of_domain_predictors": ct_violations}
            )
        if llm_cross_module is not None:
            report.setdefault("provenance", {})["llm_cross_module_notes"] = llm_cross_module




        evidence_level = None
        if "EvidenceLevelAgent" in self._agents:
            em = self.mk_message(
                "Report", "EvidenceLevelAgent", "evidence_level_request", {"report": report}, rep.message_id
            )
            evidence_level = self._dispatch_collect(em, "evidence_level_ready").payload["evidence_level"]
            report.setdefault("provenance", {})["evidence_level"] = evidence_level
        if "ActiveLearningAgent" in self._agents:
            am = self.mk_message(
                "EvidenceLevelAgent",
                "ActiveLearningAgent",
                "learning_queue_request",
                {"report": report, "evidence_level": evidence_level},
                rep.message_id,
            )
            report.setdefault("provenance", {})["learning_queue"] = self._dispatch_collect(
                am, "learning_queue_ready"
            ).payload["learning_queue"]
        if "LLMCritic" in self._agents:
            cm = self.mk_message("Report", "LLMCritic", "llm_review", {"report": report}, rep.message_id)
            report.setdefault("provenance", {})["llm_critic_notes"] = self._dispatch_collect(
                cm, "llm_critic_notes"
            ).payload
        if "LLMReport" in self._agents:
            nm = self.mk_message("Report", "LLMReport", "llm_render", {"report": report}, rep.message_id)
            report["narrative"] = self._dispatch_collect(nm, "llm_narrative").payload["narrative"]





            nv = check_narrative(report, report["narrative"])
            if nv:
                report.setdefault("provenance", {})["narrative_consistency_gate"] = {
                    "violations": nv,
                    "original_narrative": report["narrative"],
                }
                report["narrative"] = ""
        return report

    @staticmethod
    def _is_routable(app: AgentMessage) -> bool:
        """Determine whether side-path module routing is meaningful using explicit predicates. Exclude unsupported
        species with no applicable predictors and empty perturbation_targets that trigger hard abstention. These
        are also schema-normalization failures; do not manufacture a module plan.
        """
        req = app.payload.get("request", {})
        applicable = app.payload.get("applicable") or []
        targets = [t for t in (req.get("perturbation_targets") or []) if str(t).strip()]
        return bool(applicable) and bool(targets)

    def _build_module_plan(self, app: AgentMessage) -> dict | None:
        """Build a module plan through SpeciesContext, optional LLMModulePlanner, and ModuleRouter. Offline
        secondary selection is deterministic and makes no LLM call.
        """
        module_req = self._request_to_module_input(app.payload["request"])
        sm = self.mk_message(
            "ModelApplicability", "SpeciesContextAgent", "species_context", {"request": module_req}, app.message_id
        )
        ctx = self._dispatch_collect(sm, "species_context_ready").payload
        base_payload = {
            "request": module_req,
            "module_support": ctx["module_support"],
            "mismatch_queries": ctx["mismatch_queries"],
        }
        if "LLMModulePlanner" in self._agents:
            pm = self.mk_message(
                "SpeciesContextAgent", "LLMModulePlanner", "module_plan_request", base_payload, app.message_id
            )
            mc = self._dispatch_collect(pm, "module_candidates_llm").payload
            route_payload = mc
        else:
            route_payload = base_payload
        rm = self.mk_message("SpeciesContextAgent", "ModuleRouterAgent", "module_route", route_payload, app.message_id)
        return self._dispatch_collect(rm, "module_plan_ready").payload

    @staticmethod
    def _request_to_module_input(req: dict) -> dict:
        """Delegate to agents.request_adapter.request_to_module_input without changing behavior."""
        from praxis_virtualcell.agents.request_adapter import request_to_module_input

        return request_to_module_input(req)

    def _direct_v2_export_messages(self, report: dict) -> list[AgentMessage]:
        """Recover only the public report's exact direct-v2 causal message spine."""

        provenance = report.get("provenance") if isinstance(report, dict) else None
        plan = provenance.get("execution_plan") if isinstance(provenance, dict) else None
        if not isinstance(plan, dict):
            return []
        plan_id = plan.get("plan_id")
        request_id = plan.get("request_id")
        if not isinstance(plan_id, str) or not isinstance(request_id, str):
            return []
        messages = self.bus.trace
        planned = [
            message
            for message in messages
            if (
                message.message_type == "execution_plan_ready"
                and message.sender == "ModelBrokerAgent"
                and message.receiver == "AgentRuntime"
                and isinstance(message.payload.get("execution_plan"), dict)
                and message.payload["execution_plan"].get("plan_id") == plan_id
                and message.payload["execution_plan"].get("request_id") == request_id
            )
        ]
        if len(planned) != 1:
            return []
        plan_message = planned[0]
        request_messages = [
            message
            for message in messages
            if (
                message.message_id == plan_message.parent_message_id
                and message.message_type == "execution_plan_v2_request"
                and message.sender == "client"
                and message.receiver == "ModelBrokerAgent"
                and isinstance(message.payload.get("request"), dict)
                and message.payload["request"].get("request_id") == request_id
            )
        ]
        result_messages = [
            message
            for message in messages
            if (
                message.message_type == "execution_result_ready"
                and message.sender == "AgentRuntime"
                and message.receiver == "client"
                and message.parent_message_id == plan_message.message_id
                and message.payload.get("plan_id") == plan_id
            )
        ]
        if len(request_messages) != 1 or len(result_messages) != 1:
            return []
        request_message = request_messages[0]
        result_message = result_messages[0]
        if not (
            request_message.trace_id == plan_message.trace_id == result_message.trace_id
            and request_message.task_id == plan_message.task_id == result_message.task_id
            and messages.index(request_message) < messages.index(plan_message) < messages.index(result_message)
        ):
            return []
        return [request_message, plan_message, result_message]

    def export_outputs(self, out_dir: str, report: dict) -> None:
        d = Path(out_dir)
        d.mkdir(parents=True, exist_ok=True)
        provenance = report.get("provenance", {}) if isinstance(report, dict) else {}
        if isinstance(provenance, dict) and provenance.get("execution_contract") == "vc.direct-v2-execution.v1":
            from praxis_virtualcell.workflows.submit_job import _public_trace

            (d / "trace.json").write_text(
                json.dumps(_public_trace(self._direct_v2_export_messages(report)), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        else:
            self.bus.export_trace(str(d / "trace.json"))
        (d / "prediction_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        (d / "provenance.json").write_text(
            json.dumps(report.get("provenance", {}), ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def run_workflow_from_text(self, text: str) -> dict:
        """Parse free text through LLMInputInterpreter, then run_workflow; requires llm_assisted and credentials."""
        with self.execution_context():
            return self._run_workflow_from_text(text)

    def _run_workflow_from_text(self, text: str) -> dict:
        from praxis_virtualcell.core.config import assert_llm_boundaries
        from praxis_virtualcell.core.exceptions import InputValidationError
        from praxis_virtualcell.core.request import VirtualCellRequest

        assert_llm_boundaries(self.config)
        if "LLMInputInterpreter" not in self._agents:
            raise InputValidationError("free-text requires llm_assisted and DEEPSEEK_API_KEY")


        _th = hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]
        tid, kid = f"trace_{_th}", f"task_{_th}"
        self.bus.set_context(trace_id=tid, task_id=kid)
        m = self.mk_message("client", "LLMInputInterpreter", "parse_text", {"text": text})
        self.dispatch_message(m)
        parsed = self.bus.latest("request_parsed")
        if parsed is None:
            fail = self.bus.latest("llm_input_failed")
            return {
                "request_id": None,
                "abstain": True,
                "reliability": "low",
                "prediction": None,
                "models_used": [],
                "models_rejected": [],
                "abstain_reasons": ["input_missing"],
                "critic_violations": [],
                "narrative": "",
                "provenance": {"llm_input_failed": fail.payload if fail else None},
            }
        return self.run_workflow(VirtualCellRequest.from_dict(parsed.payload["request"]), trace_id=tid, task_id=kid)
